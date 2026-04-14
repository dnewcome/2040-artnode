#!/usr/bin/env python3
"""
ArtNet LED Controller - KiCad 7 PCB Generator
Produces artnet-led-controller.kicad_pcb with:
  - 100x70mm 2-layer board
  - JLCPCB 2-layer design rules
  - All components placed (update nets from schematic in KiCad)
  - GND copper pours on both layers
"""
import re
import uuid, json
from pathlib import Path

DIR  = Path(__file__).resolve().parent
PROJ = "artnet-led-controller"

def u(): return str(uuid.uuid4())

W = 100.0  # board width  mm
H = 70.0   # board height mm

# ─── PCB helpers ────────────────────────────────────────────────────────────

def _replace_property(text, name, value):
    pat = re.compile(rf'\(\s*property\s+"{re.escape(name)}"\s+"[^"]*"', re.M)
    return pat.sub(f'(property "{name}" "{value}"', text, count=1)

def _insert_lcsc_property(text, lcsc):
    if not lcsc:
        return text
    prop = (f'\t(property "LCSC" "{lcsc}"\n'
            f'\t\t(at 0 0 0)\n'
            f'\t\t(layer "F.Fab")\n'
            f'\t\t(effects\n'
            f'\t\t\t(font\n'
            f'\t\t\t\t(size 1 1)\n'
            f'\t\t\t\t(thickness 0.15)\n'
            f'\t\t\t)\n'
            f'\t\t\t(hide yes)\n'
            f'\t\t)\n'
            f'\t)')
    value_match = re.search(r'\n\t\(property "Value".*?\n\t\)', text, re.S)
    if value_match:
        return text[:value_match.end()] + '\n' + prop + text[value_match.end():]
    return text.replace('\n\t(attr ', '\n' + prop + '\n\t(attr ', 1)

def fp(lib_ref, ref, val, x, y, layer='F.Cu', angle=0, lcsc='', pads=None):
    """Generate a board footprint with real library geometry when available."""
    if pads:
        lines = [
            f'  (footprint "{lib_ref}" (layer "{layer}") (at {x:.3f} {y:.3f}{f" {angle}" if angle else ""})',
            f'    (descr "{val}")',
            f'    (tags "")',
            f'    (property "Reference" "{ref}" (at 0 -3 0) (layer "F.SilkS")',
            f'      (effects (font (size 1 1))))',
            f'    (property "Value" "{val}" (at 0 3 0) (layer "F.Fab")',
            f'      (effects (font (size 1 1))))',
        ]
        if lcsc:
            lines.append(f'    (property "LCSC" "{lcsc}" (at 0 0 0) (layer "F.Fab")')
            lines.append(f'      (effects (font (size 1 1)) (hide yes)))')
        lines.extend(pads)
        lines.append(f'  )')
        return '\n'.join(lines)

    lib, name = lib_ref.split(':', 1)
    mod_path = Path('/usr/share/kicad/footprints') / f'{lib}.pretty' / f'{name}.kicad_mod'
    if not mod_path.exists():
        raise FileNotFoundError(f"Footprint not found: {lib_ref} ({mod_path})")

    lines = [
        line for line in mod_path.read_text().splitlines()
        if not re.match(r'\s*\((version|generator|generator_version|embedded_fonts)\b', line)
    ]
    lines[0] = f'  (footprint "{lib_ref}"'
    at = f'\t(at {x:.3f} {y:.3f}{f" {angle}" if angle else ""})'
    lines.insert(1, at)
    text = '\n'.join(lines)
    text = _replace_property(text, 'Reference', ref)
    text = _replace_property(text, 'Value', val)
    text = _insert_lcsc_property(text, lcsc)
    return text

def rect_pad(num, x, y, w, h, layer='F.Cu', drill=None):
    shape = 'roundrect' if not drill else 'circle'
    dstr = f' (drill {drill:.2f})' if drill else ''
    return (f'    (pad "{num}" {"thru_hole" if drill else "smd"} rect'
            f' (at {x:.3f} {y:.3f}) (size {w:.3f} {h:.3f})'
            f' (layers "{layer}" "*.Cu"){dstr})')

def circ_pad(num, x, y, d, drill=None):
    dstr = f' (drill {drill:.2f})' if drill else ''
    layers = '"*.Cu" "*.Mask"' if drill else f'"F.Cu" "F.Mask"'
    return (f'    (pad "{num}" {"thru_hole" if drill else "smd"} circle'
            f' (at {x:.3f} {y:.3f}) (size {d:.3f} {d:.3f})'
            f' (layers {layers}){dstr})')

def via(x, y, drill=0.4, size=0.8):
    return (f'  (via (at {x:.3f} {y:.3f}) (size {size:.3f}) (drill {drill:.3f})'
            f' (layers "F.Cu" "B.Cu") (uuid "{u()}"))')

def track(x1,y1,x2,y2, width=0.25, layer='F.Cu'):
    return (f'  (segment (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})'
            f' (width {width:.3f}) (layer "{layer}") (uuid "{u()}"))')

def zone(net_name, layer, pts, min_thk=0.25):
    """Copper zone/pour"""
    pt_str = ' '.join(f'(xy {x:.3f} {y:.3f})' for x,y in pts)
    return f'''  (zone (net 0) (net_name "{net_name}") (layer "{layer}") (uuid "{u()}")
    (connect_pads (clearance 0.3))
    (min_thickness {min_thk:.3f}) (filled_areas_thickness no)
    (fill yes (thermal_gap 0.5) (thermal_bridge_width 0.3))
    (polygon (pts {pt_str}))
  )'''

def edge(x1,y1,x2,y2):
    return (f'  (gr_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})'
            f' (layer "Edge.Cuts") (width 0.05) (uuid "{u()}"))')

def silk_text(txt, x, y, layer='F.SilkS', size=1.0):
    return (f'  (gr_text "{txt}" (at {x:.3f} {y:.3f}) (layer "{layer}")'
            f' (effects (font (size {size} {size}) (thickness 0.15))))')

# ─── Board outline ───────────────────────────────────────────────────────────
edges = [
    edge(0,0,W,0), edge(W,0,W,H), edge(W,H,0,H), edge(0,H,0,0)
]

# Corner mounting holes (M3, 3.2mm drill, 3mm from edges)
mholes = []
for mx,my in [(4,4),(W-4,4),(4,H-4),(W-4,H-4)]:
    mholes.append(f'  (footprint "MountingHole:MountingHole_3.2mm_M3" (layer "F.Cu") (at {mx:.1f} {my:.1f})\n'
                  f'    (pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu" "*.Mask"))\n'
                  f'  )')

# ─── Component placement ─────────────────────────────────────────────────────
# Board: 100x70mm, origin top-left
# Silk labels for regions
silks = [
    silk_text("ArtNet LED Controller v1.0", W/2, 1.5, 'F.SilkS', 1.5),
    silk_text("RP2354A + W5500 | 4x Serial LED | LiPo+USB-C", W/2, 4.0, 'F.SilkS', 0.8),
]

footprints = []

# ── USB-C (left edge, horizontal) ──────────────────────────────────────────
footprints.append(fp(
    "Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal",
    "J1","USB4125-GF-A", 3.5, 35, lcsc='C165948'))

# ── Battery connector JST-PH-2 (left edge) ─────────────────────────────────
footprints.append(fp(
    "Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",
    "J3","VBAT JST-PH-2", 3.5, 50, lcsc='C131337'))

# ── TP4056 LiPo charger ─────────────────────────────────────────────────────
footprints.append(fp(
    "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "U5","TP4056", 20, 18, lcsc='C16581'))

# ── MT3608 Boost converter ──────────────────────────────────────────────────
footprints.append(fp(
    "Package_TO_SOT_SMD:SOT-23-6",
    "U6","MT3608", 33, 18, lcsc='C84817'))

# ── Boost inductor L1 ───────────────────────────────────────────────────────
footprints.append(fp(
    "Inductor_SMD:L_0805_2012Metric",
    "L1","22uH", 42, 18, lcsc='C1046'))

# ── AMS1117-3.3 ─────────────────────────────────────────────────────────────
footprints.append(fp(
    "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "U7","AMS1117-3.3", 55, 15, lcsc='C6186'))

# ── 12MHz Crystal Y1 ────────────────────────────────────────────────────────
footprints.append(fp(
    "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    "Y1","12MHz", 38, 42, lcsc='C9002'))

# ── RP2354A (center) ────────────────────────────────────────────────────────
footprints.append(fp(
    "Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm",
    "U1","RP2354A", 52, 40, lcsc='C41378174'))

# ── W5500 Ethernet ──────────────────────────────────────────────────────────
footprints.append(fp(
    "Package_QFP:LQFP-48_7x7mm_P0.5mm",
    "U3","W5500", 75, 35, lcsc='C32646'))

# ── 25MHz Crystal Y2 ────────────────────────────────────────────────────────
footprints.append(fp(
    "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    "Y2","25MHz", 75, 20, lcsc='C13738'))

# ── HR911105A RJ45 (right edge) ─────────────────────────────────────────────
footprints.append(fp(
    "Connector_RJ:RJ45_Hanrun_HR911105A_Horizontal",
    "J2","HR911105A", 94, 35, lcsc='C12074'))

# ── SN74AHCT125 level shifter ───────────────────────────────────────────────
footprints.append(fp(
    "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    "U4","SN74AHCT125", 35, 55, lcsc='C7484'))

# ── OLED connector (bottom edge area) ────────────────────────────────────────
footprints.append(fp(
    "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    "J9","OLED_SSD1306", 16, 58, lcsc='C124376'))

# ── LED output connectors (bottom edge) ─────────────────────────────────────
for i in range(4):
    footprints.append(fp(
        "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
        f"J{5+i}", f"LED_OUT_{i+1}", 52+i*8, 65, lcsc='C124375'))

# ── SWD debug header ─────────────────────────────────────────────────────────
footprints.append(fp(
    "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
    "J10","SWD_DEBUG", 52, 55, lcsc='C124375'))

# ── Buttons SW1, SW2 (user), SW3 (reset), SW4 (BOOTSEL) ────────────────────
for i,(bx,by) in enumerate([(16,48),(22,48),(28,48),(34,48)]):
    ref = f"SW{i+1}"
    footprints.append(fp(
        "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ",
        ref, "SW_Push", bx, by, lcsc='C318884'))

# ── Resistors (0402) - placed in clusters near their ICs ────────────────────
r_placements = [
    # (ref, value, x, y)
    ('R1','750k',  46, 22),  # MT3608 FB top
    ('R2','100k',  46, 26),  # MT3608 FB bot
    ('R3','2k',    24, 22),  # TP4056 PROG
    ('R4','5.1k',   9, 31),  # USB CC1
    ('R5','5.1k',   9, 36),  # USB CC2
    ('R6','330',   20, 28),  # LED resistor
    ('R7','10k',   26, 28),  # CHRG pullup
    ('R8','10k',   44, 50),  # RUN pullup
    ('R9','27',    10, 40),  # USB D+
    ('R10','27',   10, 43),  # USB D-
    ('R11','12.4k',84, 22),  # W5500 EXRES0
    ('R12','12.4k',84, 26),  # W5500 RCLK
    ('R13','12.4k',84, 30),  # W5500 EXRES1
    ('R14','10k',  62, 26),  # SPI MISO pullup
    ('R15','10k',  66, 26),  # SPI CS pullup
    ('R16','10k',  70, 26),  # W5500 RST pullup
    ('R17','49.9', 86, 22),  # ETH CT1
    ('R18','49.9', 86, 26),  # ETH CT2
    ('R19','4.7k', 16, 52),  # I2C SCL pullup
    ('R20','4.7k', 20, 52),  # I2C SDA pullup
    ('R21','10k',  16, 44),  # BTN1 pullup
    ('R22','10k',  22, 44),  # BTN2 pullup
    ('R23','33',   58, 34),  # RP2354A VREG_AVDD filter
    ('R24','1k',   34, 44),  # BOOTSEL series resistor
]
for ref,val,x,y in r_placements:
    footprints.append(fp("Resistor_SMD:R_0402_1005Metric", ref, val, x, y))

# ── Capacitors (0402 unless noted) ───────────────────────────────────────────
c_placements = [
    # (ref, val, x, y, fp_override)
    ('C2','12pF',  32, 42, None),   # XTAL1 load
    ('C3','12pF',  35, 42, None),   # XTAL2 load
    ('C4','100nF', 72, 42, None),   # W5_VDD
    ('C5','18pF',  70, 20, None),   # W5 XTAL1 load
    ('C6','18pF',  73, 20, None),   # W5 XTAL2 load
    ('C7','4.7uF',  57, 48, 'Capacitor_SMD:C_0402_1005Metric'),  # RP2354A 1V1
    ('C8','100nF',  60, 48, None),   # RP2354A VREG_AVDD
    ('C9','4.7uF',  63, 48, 'Capacitor_SMD:C_0402_1005Metric'),  # RP2354A 1V1
    ('C10','4.7uF', 66, 48, 'Capacitor_SMD:C_0402_1005Metric'),  # RP2354A 1V1
    # Power section
    ('C31','10uF',  8, 20, 'Capacitor_SMD:C_0805_2012Metric'),  # VUSB bulk
    ('C32','100nF', 12, 20, None),
    ('C33','10uF',  8, 50, 'Capacitor_SMD:C_0805_2012Metric'),  # VBAT bulk
    ('C34','10uF',  60, 12, 'Capacitor_SMD:C_0805_2012Metric'), # 5V bulk
    ('C35','100nF', 64, 12, None),
    ('C36','10uF',  60, 8, 'Capacitor_SMD:C_0805_2012Metric'),  # 3V3 bulk
    ('C37','100nF', 64, 8, None),
    ('C38','100nF', 68, 8, None),
    # RP2354A bypass
    ('C39','100nF', 45, 36, None),
    ('C40','100nF', 48, 36, None),
    ('C41','100nF', 51, 36, None),
    ('C42','100nF', 45, 44, None),
    ('C43','100nF', 48, 44, None),
    ('C44','100nF', 51, 44, None),
    ('C45','100nF', 54, 44, None),
    ('C46','4.7uF', 54, 36, 'Capacitor_SMD:C_0402_1005Metric'),
    # W5500 bypass
    ('C47','100nF', 68, 28, None),
    ('C48','100nF', 70, 28, None),
    ('C49','100nF', 68, 40, None),
    ('C50','100nF', 70, 40, None),
    ('C51','4.7uF', 72, 40, 'Capacitor_SMD:C_0402_1005Metric'),
    # Level shifter bypass
    ('C52','100nF', 40, 55, None),
]
for item in c_placements:
    ref,val,x,y = item[0],item[1],item[2],item[3]
    fp_lib = item[4] if item[4] else 'Capacitor_SMD:C_0402_1005Metric'
    footprints.append(fp(fp_lib, ref, val, x, y))

# ── RP2354A internal core regulator inductor ────────────────────────────────
footprints.append(fp(
    "Inductor_SMD:L_0805_2012Metric",
    "L2","3.3uH", 62, 52, lcsc='C25923'))

# ── LEDs ─────────────────────────────────────────────────────────────────────
footprints.append(fp("LED_SMD:LED_0402_1005Metric","D2","LED_GREEN",26,28,lcsc='C72043'))

# ── Schottky diode placeholder for power OR-ing ──────────────────────────────
footprints.append(fp("Diode_SMD:D_SOD-123","D1","SS14",48,18,lcsc='C2480'))

# ── GND copper pours ──────────────────────────────────────────────────────────
gnd_zone_f = zone("GND","F.Cu", [(1,1),(W-1,1),(W-1,H-1),(1,H-1)])
gnd_zone_b = zone("GND","B.Cu", [(1,1),(W-1,1),(W-1,H-1),(1,H-1)])

# ─── Generate PCB ─────────────────────────────────────────────────────────────

STACKUP = '''  (setup
    (stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
      (copper_finish "ENIG")
      (dielectric_constraints no)
    )
    (pad_to_mask_clearance 0.05)
    (solder_mask_min_width 0)
    (pad_to_paste_clearance 0)
    (pad_to_paste_clearance_ratio 0)
    (allow_soldermask_bridges_in_footprints no)
  )'''

pcb = ['(kicad_pcb (version 20230121) (generator pcbnew)',
       '  (general (thickness 1.6) (legacy_teardrops no))',
       '  (paper "A3")',
       f'  (title_block (title "ArtNet LED Controller")(rev "1.0")(company "Open Source"))',
       '',
       '  (layers',
       '    (0 "F.Cu" signal)',
       '    (31 "B.Cu" signal)',
       '    (32 "B.Adhes" user)',
       '    (33 "F.Adhes" user)',
       '    (34 "B.Paste" user)',
       '    (35 "F.Paste" user)',
       '    (36 "B.SilkS" user)',
       '    (37 "F.SilkS" user)',
       '    (38 "B.Mask" user)',
       '    (39 "F.Mask" user)',
       '    (40 "Dwgs.User" user)',
       '    (41 "Cmts.User" user)',
       '    (44 "Edge.Cuts" user)',
       '    (45 "Margin" user)',
       '    (46 "B.CrtYd" user)',
       '    (47 "F.CrtYd" user)',
       '    (48 "B.Fab" user)',
       '    (49 "F.Fab" user)',
       '  )',
       '',
       STACKUP,
       '',
       '  (net 0 "")',
       '  (net 1 "GND")',
       '  (net 2 "VCC3V3")',
       '  (net 3 "VCC5V")',
       '  (net 4 "VBAT")',
       '  (net 5 "VUSB")',
       '',
       ]

# Add board outline
pcb.extend(edges)

# Add mounting holes
pcb.extend(mholes)

# Silk labels
pcb.extend(silks)

# Add footprints
pcb.extend(footprints)

# Add copper pours
pcb.append(gnd_zone_f)
pcb.append(gnd_zone_b)

# Closing
pcb.append(')')

out = '\n'.join(pcb)
pcb_path = DIR / f"{PROJ}.kicad_pcb"
with open(pcb_path,'w') as f:
    f.write(out)
print(f"PCB written: {pcb_path} ({len(out):,} bytes)")
