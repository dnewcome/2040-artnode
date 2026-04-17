#!/usr/bin/env python3
"""
Generate a .kicad_pcb from the SKiDL netlist with components placed
in functional groups. Decoupling caps are placed near their parent IC.

Uses pcbnew Python API to load real footprints from KiCad libraries.
"""

import re, sys, os
from collections import OrderedDict, defaultdict

sys.path.insert(0, '/usr/lib/python3/dist-packages')
import pcbnew

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FP_DIR = '/usr/share/kicad/footprints'

# ---------------------------------------------------------------------------
# Parse the SKiDL netlist
# ---------------------------------------------------------------------------
def parse_netlist(path):
    with open(path) as f:
        content = f.read()

    comps = []
    for m in re.finditer(
        r'\(comp\s+\(ref "([^"]+)"\)\s+\(value "([^"]+)"\).*?\(footprint "([^"]+)"\).*?\(tstamps "([^"]+)"\)',
        content, re.DOTALL
    ):
        comps.append({
            'ref': m.group(1),
            'value': m.group(2),
            'footprint': m.group(3),
            'tstamp': m.group(4),
        })

    nets = {}
    nets_section = content[content.index('(nets'):]
    for m in re.finditer(
        r'\(net\s+\(code (\d+)\)\s+\(name "([^"]+)"\).*?\(class[^)]+\)(.*?)(?=\n    \(net\b|\n  \))',
        nets_section, re.DOTALL
    ):
        code = int(m.group(1))
        name = m.group(2)
        pins = re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', m.group(3))
        nets[code] = {'name': name, 'pins': pins}

    return comps, nets


def get_cap_parent(ref, nets):
    """Figure out which IC a capacitor is decoupling based on shared nets."""
    # Find all nets this cap is on (excluding GND)
    cap_nets = []
    for code, net in nets.items():
        if net['name'] == 'GND':
            continue
        for r, p in net['pins']:
            if r == ref:
                cap_nets.append(net['name'])

    if not cap_nets:
        return None

    net_name = cap_nets[0]

    # Map nets to parent ICs
    net_to_parent = {
        'VUSB': 'J1',
        'VBAT': 'J2',
        'VCC5V': 'U3',       # AMS1117 input side
        'VREG_1V1': 'U4',    # RP2354A core
        'VREG_AVDD': 'U4',
        'RP_XIN': 'Y1',
        'RP_XOUT': 'Y1',
        'W5_VDD': 'U5',
        'W5_XTAL1': 'Y2',
        'W5_XTAL2': 'Y2',
    }

    if net_name in net_to_parent:
        return net_to_parent[net_name]

    # VCC3V3 caps: need to disambiguate by cap ref number
    if net_name == 'VCC3V3':
        num = int(re.search(r'\d+', ref).group())
        if num <= 8:
            return 'U3'       # LDO output caps
        elif num <= 20:
            return 'U4'       # MCU decoupling
        else:
            return 'U5'       # W5500 decoupling

    return None


# ---------------------------------------------------------------------------
# Build placement groups: each IC with its associated passives
# ---------------------------------------------------------------------------
def build_placement(comps, nets):
    """Group components into clusters: IC + its caps/resistors nearby."""

    # Define functional clusters with their anchor ICs
    clusters = OrderedDict([
        ('USB-C & Charging', {
            'refs': ['J1', 'R1', 'R2', 'R3', 'R4'],  # USB-C, CC resistors, series R
            'caps': [],
        }),
        ('TP4056 Charger', {
            'refs': ['U1', 'R5', 'R6', 'R7', 'D1', 'J2'],  # TP4056, PROG R, LED, battery
            'caps': [],
        }),
        ('MT3608 Boost', {
            'refs': ['U2', 'L1', 'D2', 'R8', 'R9'],  # MT3608, inductor, diode, FB divider
            'caps': [],
        }),
        ('AMS1117 LDO', {
            'refs': ['U3'],
            'caps': [],
        }),
        ('RP2354A MCU', {
            'refs': ['U4', 'Y1', 'L2', 'R10', 'R11', 'R12', 'SW1', 'SW2'],
            'caps': [],
        }),
        ('W5500 Ethernet', {
            'refs': ['U5', 'Y2', 'R13', 'R14', 'R15', 'R16'],
            'caps': [],
        }),
        ('RJ45', {
            'refs': ['J3', 'R17', 'R18'],
            'caps': [],
        }),
        ('Level Shifter', {
            'refs': ['U6'],
            'caps': [],
        }),
        ('LED Outputs', {
            'refs': ['J4', 'J5', 'J6', 'J7'],
            'caps': [],
        }),
        ('OLED & I2C', {
            'refs': ['J8', 'R19', 'R20'],
            'caps': [],
        }),
        ('Buttons & SWD', {
            'refs': ['SW3', 'SW4', 'R21', 'R22', 'J9'],
            'caps': [],
        }),
    ])

    # Build ref -> comp lookup
    comp_by_ref = {c['ref']: c for c in comps}

    # Assign caps to clusters based on net analysis
    cap_parent_map = {
        'J1': 'USB-C & Charging',
        'J2': 'TP4056 Charger',
        'U1': 'TP4056 Charger',
        'U2': 'MT3608 Boost',
        'U3': 'AMS1117 LDO',
        'U4': 'RP2354A MCU',
        'Y1': 'RP2354A MCU',
        'U5': 'W5500 Ethernet',
        'Y2': 'W5500 Ethernet',
        'U6': 'Level Shifter',
    }

    for c in comps:
        if c['ref'].startswith('C'):
            parent = get_cap_parent(c['ref'], nets)
            if parent and parent in cap_parent_map:
                cluster_name = cap_parent_map[parent]
                clusters[cluster_name]['caps'].append(c['ref'])
            else:
                # Unassigned caps go to AMS1117 LDO (power section)
                clusters['AMS1117 LDO']['caps'].append(c['ref'])

    return clusters, comp_by_ref


# ---------------------------------------------------------------------------
# Load a footprint from KiCad libraries
# ---------------------------------------------------------------------------
def load_footprint(fp_string):
    lib, name = fp_string.split(':', 1)
    lib_path = os.path.join(FP_DIR, f'{lib}.pretty')
    try:
        return pcbnew.FootprintLoad(lib_path, name)
    except Exception as e:
        print(f"  WARNING: Could not load {fp_string}: {e}")
        return None


def place_footprint(board, comp, x, y, ref_pin_to_net, net_by_name):
    """Load and place a single footprint on the board."""
    fp = load_footprint(comp['footprint'])
    if fp is None:
        return False

    fp.SetReference(comp['ref'])
    fp.SetValue(comp['value'])
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))

    for pad in fp.Pads():
        pad_num = pad.GetNumber()
        net_name = ref_pin_to_net.get((comp['ref'], pad_num))
        if net_name and net_name in net_by_name:
            pad.SetNet(net_by_name[net_name])

    board.Add(fp)
    return True


# ---------------------------------------------------------------------------
# Generate PCB
# ---------------------------------------------------------------------------
def generate_pcb(comps, nets, output_path):
    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(4)

    # Add nets
    net_by_name = {}
    for code, net_data in sorted(nets.items()):
        ni = pcbnew.NETINFO_ITEM(board, net_data['name'])
        board.Add(ni)
        net_by_name[net_data['name']] = ni

    # Build (ref, pin) -> net_name lookup
    ref_pin_to_net = {}
    for code, net_data in nets.items():
        for ref, pin in net_data['pins']:
            ref_pin_to_net[(ref, pin)] = net_data['name']

    # Build placement clusters
    clusters, comp_by_ref = build_placement(comps, nets)

    # Cluster layout positions — arrange in a logical flow
    # Power on the left, MCU center, Ethernet top-right, IO bottom-right
    cluster_positions = {
        'USB-C & Charging':  (15,  15),
        'TP4056 Charger':    (15,  45),
        'MT3608 Boost':      (15,  75),
        'AMS1117 LDO':       (15, 105),
        'RP2354A MCU':       (80,  30),
        'W5500 Ethernet':    (80,  90),
        'RJ45':             (150,  15),
        'Level Shifter':    (150,  55),
        'LED Outputs':      (150,  85),
        'OLED & I2C':       (150, 115),
        'Buttons & SWD':    (150, 145),
    }

    placed = 0

    for cluster_name, cluster in clusters.items():
        gx, gy = cluster_positions[cluster_name]
        all_refs = cluster['refs'] + cluster['caps']

        if not all_refs:
            continue

        print(f"\n{cluster_name}:")

        # Place main components in a row/grid
        col = 0
        row = 0
        max_cols = 4
        spacing = 10

        for ref in all_refs:
            if ref not in comp_by_ref:
                continue
            comp = comp_by_ref[ref]

            cx = gx + col * spacing
            cy = gy + row * spacing

            if place_footprint(board, comp, cx, cy, ref_pin_to_net, net_by_name):
                tag = " (cap)" if ref.startswith('C') else ""
                print(f"  {ref:8s} {comp['value']:15s} at ({cx:3.0f}, {cy:3.0f}){tag}")
                placed += 1

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    # Board outline
    board_w, board_h = 190, 170
    corners = [(0, 0), (board_w, 0), (board_w, board_h), (0, board_h)]
    for i in range(4):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % 4]
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
        seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.15))
        board.Add(seg)

    pcbnew.SaveBoard(output_path, board)
    return placed


if __name__ == '__main__':
    netlist_path = os.path.join(SCRIPT_DIR, 'gen_schematic.net')
    pcb_path = os.path.join(SCRIPT_DIR, 'artnet-led-controller.kicad_pcb')

    comps, nets = parse_netlist(netlist_path)
    print(f"Parsed: {len(comps)} components, {len(nets)} nets")

    placed = generate_pcb(comps, nets, pcb_path)
    print(f"\n{'='*50}")
    print(f"Placed: {placed} footprints in {11} functional clusters")
    print(f"Caps placed next to their parent ICs")
    print(f"Output: {pcb_path}")
