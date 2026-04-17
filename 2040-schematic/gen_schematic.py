#!/usr/bin/env python3
"""
ArtNet LED Controller — Multi-sheet KiCad 9 Schematic Generator
Generates a root .kicad_sch with hierarchical sub-sheets for readability.
Exports netlist.json for downstream PCB layout tools.

Sheets:
  1. Root        — title block, power flags, sheet instances
  2. power.kicad_sch   — USB-C, TP4056, MT3608, AMS1117, battery
  3. mcu.kicad_sch     — RP2354A, crystal, buttons, USB resistors, decoupling
  4. ethernet.kicad_sch — W5500, RJ45, crystal, SPI/reset pullups
  5. led_io.kicad_sch  — 74AHCT125, LED connectors, OLED, user buttons, SWD
"""

import uuid, json
from pathlib import Path

DIR = Path(__file__).resolve().parent
PROJECT = "artnet-led-controller"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def u():
    return str(uuid.uuid4())

_pwr_n = 0
def pwr_ref():
    global _pwr_n; _pwr_n += 1
    return f"#PWR{_pwr_n:03d}"

# S-expression primitives
def wire(x1, y1, x2, y2):
    return (f'  (wire (pts (xy {x1:.3f} {y1:.3f}) (xy {x2:.3f} {y2:.3f}))\n'
            f'    (stroke (width 0) (type default)) (uuid "{u()}"))')

def no_connect(x, y):
    return f'  (no_connect (at {x:.3f} {y:.3f}) (uuid "{u()}"))'

def net_label(name, x, y, angle=0):
    return (f'  (label "{name}" (at {x:.3f} {y:.3f} {angle}) (fields_autoplaced)\n'
            f'    (effects (font (size 1.27 1.27)) (justify left))\n'
            f'    (uuid "{u()}")\n'
            f'    (property "Intersheet References" "" (at {x:.3f} {y:.3f} 0)\n'
            f'      (effects (font (size 1.27 1.27)) (hide yes))))')

def global_label(name, x, y, angle=0, shape="bidirectional"):
    """Global label for inter-sheet connections."""
    return (f'  (global_label "{name}" (shape {shape}) (at {x:.3f} {y:.3f} {angle})\n'
            f'    (effects (font (size 1.27 1.27)) (justify left))\n'
            f'    (uuid "{u()}")\n'
            f'    (property "Intersheet References" "" (at {x:.3f} {y:.3f} 0)\n'
            f'      (effects (font (size 1.27 1.27)) (hide yes))))')

def power_sym(net, x, y, angle=0):
    ref = pwr_ref()
    ya = y + 2.54 if angle == 0 else y
    yv = y - 2.54 if angle == 0 else y + 2.54
    return (f'  (symbol (lib_id "power:{net}") (at {x:.3f} {y:.3f} {angle})(unit 1)(in_bom yes)(on_board yes)\n'
            f'    (uuid "{u()}")\n'
            f'    (property "Reference" "{ref}" (at {x:.3f} {ya:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))\n'
            f'    (property "Value" "{net}" (at {x:.3f} {yv:.3f} 0)(effects (font (size 1.27 1.27))))\n'
            f'    (property "Footprint" "" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))\n'
            f'    (property "Datasheet" "" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))\n'
            f'    (instances (project "{PROJECT}" (path "/{u()}" (reference "{ref}")(unit 1)))))')

def comp(lib_id, ref, value, fp, x, y, lcsc="", angle=0):
    lines = [
        f'  (symbol (lib_id "{lib_id}") (at {x:.3f} {y:.3f} {angle})(unit 1)(in_bom yes)(on_board yes)',
        f'    (uuid "{u()}")',
        f'    (property "Reference" "{ref}" (at {x:.3f} {y - 3.81:.3f} 0)(effects (font (size 1.27 1.27))))',
        f'    (property "Value" "{value}" (at {x:.3f} {y + 3.81:.3f} 0)(effects (font (size 1.27 1.27))))',
        f'    (property "Footprint" "{fp}" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))',
        f'    (property "Datasheet" "" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))',
    ]
    if lcsc:
        lines += [
            f'    (property "LCSC" "{lcsc}" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))',
        ]
    lines += [
        f'    (instances (project "{PROJECT}" (path "/{u()}" (reference "{ref}")(unit 1))))',
        f'  )',
    ]
    return '\n'.join(lines)

def text_note(text, x, y):
    return (f'  (text "{text}" (at {x:.3f} {y:.3f} 0)\n'
            f'    (effects (font (size 2.54 2.54)) (justify left)))')


# ---------------------------------------------------------------------------
# Symbol library definitions (inline)
# All custom symbols are defined here; standard R/C/L use KiCad builtins.
# ---------------------------------------------------------------------------
PIN_LEN = 2.54
_sym_pin_defs = {}  # for netlist extraction

def build_symbol(sym_name, body, pins, pin_names_offset=1.016):
    _sym_pin_defs[sym_name] = (body, pins)
    x1, y1, x2, y2 = body
    endpoints = {}
    pin_lines = []
    for side, off, name, num, ptype in pins:
        if ptype == 'bidir':
            ptype = 'bidirectional'
        if side == 'L':
            px, py, ang = x1 - PIN_LEN, off, 0
        elif side == 'R':
            px, py, ang = x2 + PIN_LEN, off, 180
        elif side == 'T':
            px, py, ang = off, y1 - PIN_LEN, 270
        else:
            px, py, ang = off, y2 + PIN_LEN, 90
        endpoints[name] = (px, py)
        pin_lines.append(
            f'      (pin {ptype} line (at {px:.3f} {py:.3f} {ang}) (length {PIN_LEN})\n'
            f'        (name "{name}" (effects (font (size 1.016 1.016))))\n'
            f'        (number "{num}" (effects (font (size 1.016 1.016)))))'
        )
    body_rect = (f'    (symbol "{sym_name}_0_1"\n'
                 f'      (rectangle (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f})\n'
                 f'        (stroke (width 0) (type default)) (fill (type background))))\n')
    pin_block = (f'    (symbol "{sym_name}_1_1"\n' +
                 '\n'.join(pin_lines) + '\n    )\n')
    sym_text = (f'    (symbol "{sym_name}"\n'
                f'      (pin_names (offset {pin_names_offset:.3f}))\n'
                f'      (in_bom yes) (on_board yes)\n'
                f'      (property "Reference" "U" (at 0 {y1 - 3.81:.3f} 0)\n'
                f'        (effects (font (size 1.27 1.27))))\n'
                f'      (property "Value" "{sym_name}" (at 0 {y2 + 3.81:.3f} 0)\n'
                f'        (effects (font (size 1.27 1.27))))\n'
                f'      (property "Footprint" "" (at 0 0 0)\n'
                f'        (effects (font (size 1.27 1.27)) (hide yes)))\n'
                f'      (property "Datasheet" "" (at 0 0 0)\n'
                f'        (effects (font (size 1.27 1.27)) (hide yes)))\n'
                + body_rect + pin_block + '    )\n')
    return sym_text, endpoints


# ── Build all symbol definitions ────────────────────────────────────────────
lib_symbols = []
all_endpoints = {}

# RP2354A (QFN-60)
S = 2.54
rp_body = (-20.32, -31.75, 20.32, 31.75)
def lpin(i, name, num, ptype='bidir'): return ('L', -25.4 + i * S, name, num, ptype)
def rpin(i, name, num, ptype='bidir'): return ('R', -27.94 + i * S, name, num, ptype)
def tpin(i, name, num, ptype='power_in'): return ('T', -5.08 + i * S, name, num, ptype)
def bpin(i, name, num, ptype='power_in'): return ('B', -8.89 + i * S, name, num, ptype)

rp_pins = [
    lpin(0,'GPIO0','2'), lpin(1,'GPIO1','3'), lpin(2,'GPIO2','4'),
    lpin(3,'GPIO3','5'), lpin(4,'GPIO4','7'), lpin(5,'GPIO5','8'),
    lpin(6,'GPIO6','9'), lpin(7,'GPIO7','10'), lpin(8,'GPIO8','12'),
    lpin(9,'GPIO9','13'), lpin(10,'GPIO10','14'), lpin(11,'GPIO11','15'),
    lpin(12,'GPIO12','16'), lpin(13,'GPIO13','17'), lpin(14,'GPIO14','18'),
    lpin(15,'GPIO15','19'), lpin(16,'XIN','21','input'), lpin(17,'XOUT','22','output'),
    lpin(18,'USB_DP','52','bidir'), lpin(19,'USB_DM','51','bidir'),
    lpin(20,'RUN','26','input'),
    lpin(21,'SWCLK','24','input'), lpin(22,'SWDIO','25','bidir'),
    rpin(0,'GPIO16','27'), rpin(1,'GPIO17','28'), rpin(2,'GPIO18','29'),
    rpin(3,'GPIO19','31'), rpin(4,'GPIO20','32'), rpin(5,'GPIO21','33'),
    rpin(6,'GPIO22','34'), rpin(7,'GPIO23','35'), rpin(8,'GPIO24','36'),
    rpin(9,'GPIO25','37'), rpin(10,'GPIO26','40'), rpin(11,'GPIO27','41'),
    rpin(12,'GPIO28','42'), rpin(13,'GPIO29','43'),
    rpin(14,'QSPI_SS','60','bidir'),
    rpin(15,'QSPI_SCLK','56','bidir'), rpin(16,'QSPI_SD0','57','bidir'),
    rpin(17,'QSPI_SD1','59','bidir'), rpin(18,'QSPI_SD2','58','bidir'),
    rpin(19,'QSPI_SD3','55','bidir'),
    tpin(0,'IOVDD1','1'), tpin(1,'IOVDD2','11'), tpin(2,'IOVDD3','20'),
    tpin(3,'IOVDD4','30'), tpin(4,'IOVDD5','38'), tpin(5,'IOVDD6','45'),
    tpin(6,'USB_OTP_VDD','53'), tpin(7,'QSPI_IOVDD','54'),
    tpin(8,'ADC_AVDD','44'), tpin(9,'VREG_AVDD','46'),
    tpin(10,'VREG_VIN','49'),
    bpin(0,'DVDD1','6'), bpin(1,'DVDD2','23'), bpin(2,'DVDD3','39'),
    bpin(3,'GND','61'), bpin(4,'VREG_PGND','47'),
    bpin(5,'VREG_LX','48','power_out'), bpin(6,'VREG_FB','50','input'),
]
sym, ep = build_symbol('RP2354A', rp_body, rp_pins)
lib_symbols.append(sym); all_endpoints['RP2354A'] = ep

# W5500 (LQFP-48)
w_body = (-16.51, -16.51, 16.51, 16.51)
def wp(side, i, name, num, pt='bidir'):
    return (side, -13.97 + i * 2.54, name, num, pt)
w_pins = [
    wp('L',0,'MISO','21','output'), wp('L',1,'MOSI','22','input'),
    wp('L',2,'SCLK','23','input'), wp('L',3,'/SCSn','24','input'),
    wp('L',4,'/INTn','27','output'), wp('L',5,'/RSTn','28','input'),
    wp('L',6,'RSVD1','1','no_connect'), wp('L',7,'RSVD2','2','no_connect'),
    wp('L',8,'RSVD3','3','no_connect'), wp('L',9,'RSVD4','4','no_connect'),
    wp('L',10,'RSVD5','17','no_connect'), wp('L',11,'EXRES1','5','passive'),
    wp('R',0,'TXP','11','output'), wp('R',1,'TXN','12','output'),
    wp('R',2,'RXP','14','input'), wp('R',3,'RXN','13','input'),
    wp('R',4,'XTAL1','15','input'), wp('R',5,'XTAL2','16','output'),
    wp('R',6,'EXRES0','10','passive'), wp('R',7,'RCLK','9','passive'),
    wp('R',8,'AVCCRST','6','power_in'),
    wp('R',9,'RSVD6','29','no_connect'), wp('R',10,'RSVD7','30','no_connect'),
    wp('R',11,'RSVD8','31','no_connect'),
    ('T',-7.62,'VDDIO','19','power_in'), ('T',-5.08,'AVDD','7','power_in'),
    ('T',-2.54,'VDD','26','power_out'), ('T',0,'AVDD2','20','power_in'),
    ('T',2.54,'VDDIO2','25','power_in'),
    ('B',-5.08,'GND','8','power_in'), ('B',-2.54,'GND2','32','power_in'),
    ('B',0,'AGNDB','8b','power_in'), ('B',2.54,'GND3','20b','power_in'),
    ('B',5.08,'GND4','25b','power_in'),
]
sym, ep = build_symbol('W5500', w_body, w_pins)
lib_symbols.append(sym); all_endpoints['W5500'] = ep

# SN74AHCT125 (SOIC-14)
ah_body = (-7.62, -8.89, 7.62, 8.89)
ah_pins = [
    ('L',-6.35,'/OE_A','1','input'), ('L',-3.81,'A1','2','input'),
    ('L',-1.27,'/OE_B','4','input'), ('L',1.27,'A2','5','input'),
    ('L',3.81,'/OE_C','9','input'), ('L',6.35,'A3','10','input'),
    ('R',-6.35,'Y1','3','output'), ('R',-3.81,'Y2','6','output'),
    ('R',-1.27,'/OE_D','12','input'), ('R',1.27,'A4','13','input'),
    ('R',3.81,'Y3','8','output'), ('R',6.35,'Y4','11','output'),
    ('T',0,'VCC','14','power_in'), ('B',0,'GND','7','power_in'),
]
sym, ep = build_symbol('SN74AHCT125', ah_body, ah_pins)
lib_symbols.append(sym); all_endpoints['SN74AHCT125'] = ep

# TP4056 (SOP-8)
tp_body = (-5.08, -5.08, 5.08, 5.08)
tp_pins = [
    ('L',-2.54,'TEMP','1','input'), ('L',0,'PROG','2','passive'),
    ('L',2.54,'GND','3','power_in'), ('T',0,'VCC','4','power_in'),
    ('R',-2.54,'BAT','5','power_out'), ('R',0,'/CHRG','6','output'),
    ('R',2.54,'/STDBY','7','output'), ('B',0,'TE','8','input'),
]
sym, ep = build_symbol('TP4056', tp_body, tp_pins)
lib_symbols.append(sym); all_endpoints['TP4056'] = ep

# MT3608 (SOT-23-6)
mt_body = (-3.81, -3.81, 3.81, 3.81)
mt_pins = [
    ('L',-1.27,'IN','1','power_in'), ('L',1.27,'GND','2','power_in'),
    ('T',0,'EN','3','input'), ('R',-1.27,'FB','4','input'),
    ('R',1.27,'SW','5','output'), ('B',0,'NC','6','no_connect'),
]
sym, ep = build_symbol('MT3608', mt_body, mt_pins)
lib_symbols.append(sym); all_endpoints['MT3608'] = ep

# AMS1117-3.3 (SOT-223-3)
am_body = (-3.81, -3.81, 3.81, 3.81)
am_pins = [
    ('L',0,'ADJ_GND','1','power_in'), ('T',0,'VIN','3','power_in'),
    ('R',0,'VOUT','2','power_out'), ('B',0,'VOUT2','4','power_out'),
]
sym, ep = build_symbol('AMS1117-3.3', am_body, am_pins)
lib_symbols.append(sym); all_endpoints['AMS1117-3.3'] = ep

# USB-C Receptacle
uc_body = (-6.35, -7.62, 6.35, 7.62)
uc_pins = [
    ('L',-5.08,'VBUS','A1','power_in'), ('L',-2.54,'D-','A7','bidir'),
    ('L',0,'D+','A6','bidir'), ('L',2.54,'CC1','A5','passive'),
    ('L',5.08,'CC2','B5','passive'), ('R',-5.08,'SHIELD','S1','passive'),
    ('T',0,'VBUS2','B1','power_in'),
    ('B',0,'GND','A12','power_in'), ('B',2.54,'GND2','B12','power_in'),
]
sym, ep = build_symbol('USB_C_Receptacle', uc_body, uc_pins)
lib_symbols.append(sym); all_endpoints['USB_C_Receptacle'] = ep

# HR911105A RJ45
rj_body = (-7.62, -10.16, 7.62, 10.16)
rj_pins = [
    ('L',-7.62,'TD+','1','bidir'), ('L',-5.08,'TD-','2','bidir'),
    ('L',-2.54,'RD+','3','bidir'), ('L',0,'RD-','6','bidir'),
    ('L',2.54,'VCC_LED','7','power_in'), ('L',5.08,'GND_LED','4','power_in'),
    ('L',7.62,'GND2','5','power_in'),
    ('R',-7.62,'MDI+','11','bidir'), ('R',-5.08,'MDI-','12','bidir'),
    ('R',-2.54,'MDO+','13','bidir'), ('R',0,'MDO-','14','bidir'),
    ('R',2.54,'LINK_LED','15','output'), ('R',5.08,'ACT_LED','16','output'),
    ('R',7.62,'SHIELD','17','passive'),
    ('T',0,'CT1','8','passive'), ('B',0,'CT2','9','passive'),
]
sym, ep = build_symbol('HR911105A', rj_body, rj_pins)
lib_symbols.append(sym); all_endpoints['HR911105A'] = ep

# Simple 2-pin passives
for sym_name, body, pins in [
    ('Crystal', (-2.54,-1.27,2.54,1.27), [('L',0,'XIN','1','passive'),('R',0,'XOUT','2','passive')]),
    ('R', (-1.016,-1.778,1.016,1.778), [('T',0,'~','1','passive'),('B',0,'~','2','passive')]),
    ('C', (-1.016,-0.508,1.016,0.508), [('T',0,'+','1','passive'),('B',0,'~','2','passive')]),
    ('L', (-1.016,-2.032,1.016,2.032), [('T',0,'~','1','passive'),('B',0,'~','2','passive')]),
    ('D_Schottky', (-1.016,-1.27,1.016,1.27), [('T',0,'A','1','passive'),('B',0,'K','2','passive')]),
    ('LED', (-1.016,-1.27,1.016,1.27), [('T',0,'A','1','passive'),('B',0,'K','2','passive')]),
    ('SW_Push', (-2.54,-2.54,2.54,2.54), [('L',0,'A','1','passive'),('R',0,'B','2','passive')]),
]:
    s, e = build_symbol(sym_name, body, pins)
    lib_symbols.append(s); all_endpoints[sym_name] = e

# Connectors
for n in [2, 3, 4]:
    body_h = (n - 1) * 1.27 + 1.27
    body = (-2.54, -body_h, 2.54, body_h)
    pins = [('R', -body_h + 1.27 + i * 2.54, f'Pin{i+1}', str(i+1), 'passive') for i in range(n)]
    s, e = build_symbol(f'Conn_1x{n:02d}', body, pins)
    lib_symbols.append(s); all_endpoints[f'Conn_1x{n:02d}'] = e


# ---------------------------------------------------------------------------
# Pin endpoint helper
# ---------------------------------------------------------------------------
def pin_xy(sym_name, cx, cy, pin_name):
    px, py = all_endpoints[sym_name][pin_name]
    return cx + px, cy - py

# Passive pin endpoints (top/bottom) by body geometry
def passive_top(cx, cy, sym_name):
    body = _sym_pin_defs[sym_name][0]
    return cx, cy - (abs(body[1]) + PIN_LEN)

def passive_bot(cx, cy, sym_name):
    body = _sym_pin_defs[sym_name][0]
    return cx, cy + (body[3] + PIN_LEN)


# ---------------------------------------------------------------------------
# Sheet builder
# ---------------------------------------------------------------------------
class Sheet:
    """Accumulates schematic elements for one .kicad_sch file."""
    def __init__(self, title, paper="A3"):
        self.title = title
        self.paper = paper
        self.elements = []   # raw S-expression strings
        self.components = [] # (sym_name, ref, val, fp, cx, cy, lcsc)
        self.netlist_labels = []  # (net, x, y) for netlist extraction
        self.netlist_powers = []  # (net, x, y) for netlist extraction

    def add(self, sexp):
        self.elements.append(sexp)

    def add_comp(self, lib_id, ref, value, fp, x, y, lcsc="", angle=0):
        self.elements.append(comp(lib_id, ref, value, fp, x, y, lcsc, angle))
        self.components.append((lib_id, ref, value, fp, x, y, lcsc))

    def add_wire(self, x1, y1, x2, y2):
        self.elements.append(wire(x1, y1, x2, y2))

    def add_label(self, name, x, y, angle=0):
        self.elements.append(net_label(name, x, y, angle))
        self.netlist_labels.append((name, x, y))

    def add_global(self, name, x, y, angle=0, shape="bidirectional"):
        self.elements.append(global_label(name, x, y, angle, shape))
        self.netlist_labels.append((name, x, y))

    def add_power(self, net, x, y, angle=0):
        self.elements.append(power_sym(net, x, y, angle))
        self.netlist_powers.append((net, x, y))

    def add_nc(self, x, y):
        self.elements.append(no_connect(x, y))

    def add_note(self, text, x, y):
        self.elements.append(text_note(text, x, y))

    def add_resistor(self, ref, value, x, y, top_net, bot_net,
                     top_is_global=False, bot_is_global=False,
                     top_is_power=False, bot_is_power=False,
                     lcsc='C25744', fp='Resistor_SMD:R_0402_1005Metric'):
        self.add_comp('R', ref, value, fp, x, y, lcsc)
        tx, ty = passive_top(x, y, 'R')
        bx, by = passive_bot(x, y, 'R')
        if top_is_power:
            self.add_power(top_net, tx, ty)
        elif top_is_global:
            self.add_global(top_net, tx, ty)
        else:
            self.add_label(top_net, tx, ty)
        if bot_is_power:
            self.add_power(bot_net, bx, by, 270)
        elif bot_is_global:
            self.add_global(bot_net, bx, by)
        else:
            self.add_label(bot_net, bx, by)

    def add_cap(self, ref, value, x, y, top_net,
                top_is_global=False, top_is_power=False,
                lcsc='C14663', fp='Capacitor_SMD:C_0402_1005Metric'):
        """Decoupling cap: top_net on pin 1, GND on pin 2."""
        self.add_comp('C', ref, value, fp, x, y, lcsc)
        tx, ty = passive_top(x, y, 'C')
        bx, by = passive_bot(x, y, 'C')
        if top_is_power:
            self.add_power(top_net, tx, ty)
        elif top_is_global:
            self.add_global(top_net, tx, ty)
        else:
            self.add_label(top_net, tx, ty)
        self.add_power('GND', bx, by, 270)

    def render(self):
        lines = [
            f'(kicad_sch (version 20230121) (generator "gen_schematic.py")',
            f'  (paper "{self.paper}")',
            f'  (title_block',
            f'    (title "{self.title}")',
            f'    (rev "2.0")',
            f'    (company "Open Source")',
            f'  )',
            '',
            '  (lib_symbols',
        ]
        for sym in lib_symbols:
            lines.append(sym)
        lines.append('  )')
        lines.append('')
        for el in self.elements:
            lines.append(el)
        lines.append(')')
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# SHEET 1: POWER
# ---------------------------------------------------------------------------
pwr = Sheet("ArtNet LED Controller — Power Supply", "A3")
pwr.add_note("USB-C Input", 25, 25)

# USB-C connector
UX, UY = 55, 70
pwr.add_comp('USB_C_Receptacle', 'J1', 'USB4125-GF-A',
    'Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal', UX, UY, 'C165948')
pwr.add_global('VUSB', *pin_xy('USB_C_Receptacle', UX, UY, 'VBUS'), shape="power_in")
pwr.add_global('VUSB', *pin_xy('USB_C_Receptacle', UX, UY, 'VBUS2'), shape="power_in")
pwr.add_power('GND', *pin_xy('USB_C_Receptacle', UX, UY, 'GND'), 270)
pwr.add_power('GND', *pin_xy('USB_C_Receptacle', UX, UY, 'GND2'), 270)
pwr.add_global('USB_DP', *pin_xy('USB_C_Receptacle', UX, UY, 'D+'))
pwr.add_global('USB_DM', *pin_xy('USB_C_Receptacle', UX, UY, 'D-'))
pwr.add_nc(*pin_xy('USB_C_Receptacle', UX, UY, 'SHIELD'))

# CC resistors (5.1k to GND for USB-C)
pwr.add_resistor('R4', '5.1k', 35, 90, 'USB_CC1', 'GND',
                  bot_is_power=True, lcsc='C25905')
pwr.add_resistor('R5', '5.1k', 25, 90, 'USB_CC2', 'GND',
                  bot_is_power=True, lcsc='C25905')
pwr.add_label('USB_CC1', *pin_xy('USB_C_Receptacle', UX, UY, 'CC1'))
pwr.add_label('USB_CC2', *pin_xy('USB_C_Receptacle', UX, UY, 'CC2'))

# USB series resistors (27 ohm)
pwr.add_note("USB Series Resistors", 90, 25)
pwr.add_resistor('R9', '27', 95, 70, 'USB_DP', 'USB_DP_MCU',
                  top_is_global=True, bot_is_global=True, lcsc='C352446')
pwr.add_resistor('R10', '27', 105, 70, 'USB_DM', 'USB_DM_MCU',
                  top_is_global=True, bot_is_global=True, lcsc='C352446')

# TP4056 LiPo charger
pwr.add_note("LiPo Charger", 130, 25)
TX, TY = 155, 70
pwr.add_comp('TP4056', 'U5', 'TP4056',
    'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', TX, TY, 'C16581')
pwr.add_global('VUSB', *pin_xy('TP4056', TX, TY, 'VCC'), shape="power_in")
pwr.add_power('GND', *pin_xy('TP4056', TX, TY, 'GND'), 270)
pwr.add_global('VBAT', *pin_xy('TP4056', TX, TY, 'BAT'), shape="power_out")
pwr.add_label('CHRG_STAT', *pin_xy('TP4056', TX, TY, '/CHRG'))
pwr.add_label('STDBY_STAT', *pin_xy('TP4056', TX, TY, '/STDBY'))
pwr.add_power('GND', *pin_xy('TP4056', TX, TY, 'TEMP'), 270)  # NTC bypass
pwr.add_global('VUSB', *pin_xy('TP4056', TX, TY, 'TE'), shape="power_in")  # disable timer

# PROG resistor (2k for 500mA charge current)
pwr.add_resistor('R3', '2k', TX - 12, TY + 15, 'TP4056_PROG', 'GND',
                  bot_is_power=True, lcsc='C25879')
pwr.add_label('TP4056_PROG', *pin_xy('TP4056', TX, TY, 'PROG'))

# Charge LED
pwr.add_comp('LED', 'D2', 'LED_GREEN', 'LED_SMD:LED_0402_1005Metric', TX + 20, TY + 10, 'C72043')
pwr.add_label('CHRG_STAT', TX + 20, TY + 10 - 3.81)
pwr.add_power('GND', TX + 20, TY + 10 + 3.81, 270)
pwr.add_resistor('R6', '330', TX + 27, TY + 10, 'CHRG_STAT', 'GND',
                  bot_is_power=True, lcsc='C25104')
pwr.add_resistor('R7', '10k', TX + 20, TY - 5, 'VCC3V3', 'CHRG_STAT',
                  top_is_global=True, lcsc='C25744')

# Battery connector
pwr.add_note("Battery", 25, 130)
BX, BY = 55, 155
pwr.add_comp('Conn_1x02', 'J3', 'JST-PH-2',
    'Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical', BX, BY, 'C131337')
pwr.add_global('VBAT', *pin_xy('Conn_1x02', BX, BY, 'Pin1'), shape="power_out")
pwr.add_power('GND', *pin_xy('Conn_1x02', BX, BY, 'Pin2'), 270)

# MT3608 Boost Converter (VBAT -> 5V)
pwr.add_note("Boost Converter (VBAT -> 5V)", 220, 25)
MX, MY = 245, 70
pwr.add_comp('MT3608', 'U6', 'MT3608',
    'Package_TO_SOT_SMD:SOT-23-6', MX, MY, 'C84817')
pwr.add_global('VBAT', *pin_xy('MT3608', MX, MY, 'IN'), shape="power_in")
pwr.add_power('GND', *pin_xy('MT3608', MX, MY, 'GND'), 270)
pwr.add_global('VCC5V', *pin_xy('MT3608', MX, MY, 'EN'), shape="power_in")
pwr.add_label('MT3608_SW', *pin_xy('MT3608', MX, MY, 'SW'))
pwr.add_label('MT3608_FB', *pin_xy('MT3608', MX, MY, 'FB'))
pwr.add_nc(*pin_xy('MT3608', MX, MY, 'NC'))

# Boost inductor
pwr.add_comp('L', 'L1', '22uH', 'Inductor_SMD:L_0805_2012Metric', MX + 18, MY - 8, 'C1046')
pwr.add_label('MT3608_SW', MX + 18, MY - 8 - 4.572)
pwr.add_label('VBOOST_RAW', MX + 18, MY - 8 + 4.572)

# Boost rectifier diode
pwr.add_comp('D_Schottky', 'D1', 'SS14', 'Diode_SMD:D_SOD-123', MX + 28, MY - 8, 'C2480')
pwr.add_label('VBOOST_RAW', MX + 28, MY - 8 - 3.81)
pwr.add_global('VCC5V', MX + 28, MY - 8 + 3.81, shape="power_out")

# Feedback divider
pwr.add_resistor('R1', '750k', MX + 18, MY + 10, 'VCC5V', 'MT3608_FB',
                  top_is_global=True, lcsc='C25022')
pwr.add_resistor('R2', '100k', MX + 18, MY + 20, 'MT3608_FB', 'GND',
                  bot_is_power=True, lcsc='C25741')

# AMS1117-3.3 LDO (5V -> 3.3V)
pwr.add_note("LDO (5V -> 3.3V)", 330, 25)
AX, AY = 350, 70
pwr.add_comp('AMS1117-3.3', 'U7', 'AMS1117-3.3',
    'Package_TO_SOT_SMD:SOT-223-3_TabPin2', AX, AY, 'C6186')
pwr.add_global('VCC5V', *pin_xy('AMS1117-3.3', AX, AY, 'VIN'), shape="power_in")
pwr.add_power('GND', *pin_xy('AMS1117-3.3', AX, AY, 'ADJ_GND'), 270)
pwr.add_global('VCC3V3', *pin_xy('AMS1117-3.3', AX, AY, 'VOUT'), shape="power_out")
pwr.add_global('VCC3V3', *pin_xy('AMS1117-3.3', AX, AY, 'VOUT2'), shape="power_out")

# Power decoupling caps
cap_idx = 30
def next_cap():
    global cap_idx; cap_idx += 1; return f'C{cap_idx}'

pwr.add_cap(next_cap(), '10uF', UX + 15, UY - 15, 'VUSB', top_is_global=True, lcsc='C19702')
pwr.add_cap(next_cap(), '100nF', UX + 22, UY - 15, 'VUSB', top_is_global=True)
pwr.add_cap(next_cap(), '10uF', BX + 15, BY - 15, 'VBAT', top_is_global=True, lcsc='C19702')
pwr.add_cap(next_cap(), '10uF', AX + 15, AY - 15, 'VCC5V', top_is_global=True, lcsc='C19702')
pwr.add_cap(next_cap(), '100nF', AX + 22, AY - 15, 'VCC5V', top_is_global=True)
pwr.add_cap(next_cap(), '10uF', AX + 15, AY + 15, 'VCC3V3', top_is_global=True, lcsc='C19702')
pwr.add_cap(next_cap(), '100nF', AX + 22, AY + 15, 'VCC3V3', top_is_global=True)
pwr.add_cap(next_cap(), '100nF', AX + 29, AY + 15, 'VCC3V3', top_is_global=True)

# Power flags (for ERC)
for i, net in enumerate(['VCC3V3', 'VCC5V', 'GND', 'VBAT', 'VUSB']):
    fx = 25 + i * 15
    pwr.add(power_sym('PWR_FLAG', fx, 210))
    pwr.add(power_sym(net, fx, 215))


# ---------------------------------------------------------------------------
# SHEET 2: MCU
# ---------------------------------------------------------------------------
mcu = Sheet("ArtNet LED Controller — MCU (RP2354A)", "A3")

# RP2354A — centered on A3
RX, RY = 200, 140
mcu.add_comp('RP2354A', 'U1', 'RP2354A',
    'Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm', RX, RY, 'C41378174')

# GPIO → global labels for inter-sheet connections
for i, gpio in enumerate(['GPIO0', 'GPIO1', 'GPIO2', 'GPIO3']):
    mcu.add_global(f'LED{i+1}_DATA_3V3', *pin_xy('RP2354A', RX, RY, gpio))
mcu.add_global('I2C_SDA', *pin_xy('RP2354A', RX, RY, 'GPIO4'))
mcu.add_global('I2C_SCL', *pin_xy('RP2354A', RX, RY, 'GPIO5'))

# SPI for W5500
mcu.add_global('SPI_MISO', *pin_xy('RP2354A', RX, RY, 'GPIO16'))
mcu.add_global('SPI_CS', *pin_xy('RP2354A', RX, RY, 'GPIO17'))
mcu.add_global('SPI_SCK', *pin_xy('RP2354A', RX, RY, 'GPIO18'))
mcu.add_global('SPI_MOSI', *pin_xy('RP2354A', RX, RY, 'GPIO19'))
mcu.add_global('W5500_INT', *pin_xy('RP2354A', RX, RY, 'GPIO20'))
mcu.add_global('W5500_RST', *pin_xy('RP2354A', RX, RY, 'GPIO21'))

# Buttons
mcu.add_global('BTN1', *pin_xy('RP2354A', RX, RY, 'GPIO22'))
mcu.add_global('BTN2', *pin_xy('RP2354A', RX, RY, 'GPIO23'))

# Unused GPIOs
for g in ['GPIO6','GPIO7','GPIO8','GPIO9','GPIO10','GPIO11','GPIO12','GPIO13',
          'GPIO14','GPIO15','GPIO24','GPIO25','GPIO26','GPIO27','GPIO28','GPIO29']:
    mcu.add_nc(*pin_xy('RP2354A', RX, RY, g))

# QSPI (internal flash, leave external pads NC except SS=USB_BOOT)
mcu.add_global('USB_BOOT', *pin_xy('RP2354A', RX, RY, 'QSPI_SS'))
for qpin in ['QSPI_SCLK','QSPI_SD0','QSPI_SD1','QSPI_SD2','QSPI_SD3']:
    mcu.add_nc(*pin_xy('RP2354A', RX, RY, qpin))

# USB
mcu.add_global('USB_DP_MCU', *pin_xy('RP2354A', RX, RY, 'USB_DP'))
mcu.add_global('USB_DM_MCU', *pin_xy('RP2354A', RX, RY, 'USB_DM'))

# Crystal
mcu.add_label('RP_XIN', *pin_xy('RP2354A', RX, RY, 'XIN'))
mcu.add_label('RP_XOUT', *pin_xy('RP2354A', RX, RY, 'XOUT'))

# RUN, SWD
mcu.add_global('RP_RUN', *pin_xy('RP2354A', RX, RY, 'RUN'))
mcu.add_global('SWCLK', *pin_xy('RP2354A', RX, RY, 'SWCLK'))
mcu.add_global('SWDIO', *pin_xy('RP2354A', RX, RY, 'SWDIO'))

# Power pins
for p in ['IOVDD1','IOVDD2','IOVDD3','IOVDD4','IOVDD5','IOVDD6',
          'USB_OTP_VDD','QSPI_IOVDD','ADC_AVDD','VREG_VIN']:
    mcu.add_power('VCC3V3', *pin_xy('RP2354A', RX, RY, p))
mcu.add_power('GND', *pin_xy('RP2354A', RX, RY, 'GND'), 270)
mcu.add_power('GND', *pin_xy('RP2354A', RX, RY, 'VREG_PGND'), 270)

# Core regulator
mcu.add_label('VREG_LX', *pin_xy('RP2354A', RX, RY, 'VREG_LX'))
mcu.add_label('VREG_1V1', *pin_xy('RP2354A', RX, RY, 'VREG_FB'))
for p in ['DVDD1', 'DVDD2', 'DVDD3']:
    mcu.add_label('VREG_1V1', *pin_xy('RP2354A', RX, RY, p))
mcu.add_label('VREG_AVDD', *pin_xy('RP2354A', RX, RY, 'VREG_AVDD'))

# VREG inductor
mcu.add_comp('L', 'L2', '3.3uH', 'Inductor_SMD:L_0805_2012Metric', RX + 30, RY + 40, 'C25923')
mcu.add_label('VREG_LX', RX + 30, RY + 40 - 4.572)
mcu.add_label('VREG_1V1', RX + 30, RY + 40 + 4.572)

# VREG_AVDD filter resistor
mcu.add_resistor('R23', '33', RX + 40, RY + 30, 'VCC3V3', 'VREG_AVDD',
                  top_is_power=True, lcsc='C25105')

# Core regulator caps
for i, (ref, val, net, lcsc) in enumerate([
    ('C7', '4.7uF', 'VREG_1V1', 'C19712'),
    ('C8', '100nF', 'VREG_AVDD', 'C14663'),
    ('C9', '4.7uF', 'VREG_1V1', 'C19712'),
    ('C10', '4.7uF', 'VREG_1V1', 'C19712'),
]):
    cx = RX + 38 + i * 8
    cy = RY + 43
    mcu.add_cap(ref, val, cx, cy, net, lcsc=lcsc)

# 3.3V decoupling (8 caps around MCU)
for i in range(7):
    mcu.add_cap(next_cap(), '100nF', RX - 30 + i * 8, RY - 45, 'VCC3V3', top_is_power=True)
mcu.add_cap(next_cap(), '4.7uF', RX + 30, RY - 45, 'VCC3V3', top_is_power=True, lcsc='C19712')

# 12MHz Crystal
mcu.add_note("12 MHz Crystal", RX - 55, RY - 60)
YX, YY = RX - 45, RY - 50
mcu.add_comp('Crystal', 'Y1', '12MHz',
    'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', YX, YY, 'C9002')
mcu.add_label('RP_XIN', *pin_xy('Crystal', YX, YY, 'XIN'))
mcu.add_label('RP_XOUT', *pin_xy('Crystal', YX, YY, 'XOUT'))
mcu.add_cap('C2', '12pF', YX - 10, YY, 'RP_XIN', lcsc='C1525')
mcu.add_cap('C3', '12pF', YX + 10, YY, 'RP_XOUT', lcsc='C1525')

# Reset button + pullup
mcu.add_note("Reset / Boot", RX - 70, RY + 10)
mcu.add_resistor('R8', '10k', RX - 55, RY + 20, 'VCC3V3', 'RP_RUN',
                  top_is_power=True, bot_is_global=True, lcsc='C25744')
mcu.add_comp('SW_Push', 'SW3', 'RESET',
    'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ', RX - 70, RY + 20, 'C318884')
mcu.add_global('RP_RUN', *pin_xy('SW_Push', RX - 70, RY + 20, 'A'))
mcu.add_power('GND', *pin_xy('SW_Push', RX - 70, RY + 20, 'B'), 270)

# Boot button
mcu.add_resistor('R24', '1k', RX - 55, RY + 35, 'USB_BOOT', 'USB_BOOT_SW',
                  top_is_global=True, lcsc='C11702')
mcu.add_comp('SW_Push', 'SW4', 'BOOTSEL',
    'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ', RX - 70, RY + 35, 'C318884')
mcu.add_label('USB_BOOT_SW', *pin_xy('SW_Push', RX - 70, RY + 35, 'A'))
mcu.add_power('GND', *pin_xy('SW_Push', RX - 70, RY + 35, 'B'), 270)


# ---------------------------------------------------------------------------
# SHEET 3: ETHERNET
# ---------------------------------------------------------------------------
eth = Sheet("ArtNet LED Controller — Ethernet (W5500 + RJ45)", "A3")

# W5500
WX, WY = 120, 140
eth.add_comp('W5500', 'U3', 'W5500',
    'Package_QFP:LQFP-48_7x7mm_P0.5mm', WX, WY, 'C32646')

# SPI
eth.add_global('SPI_MISO', *pin_xy('W5500', WX, WY, 'MISO'))
eth.add_global('SPI_MOSI', *pin_xy('W5500', WX, WY, 'MOSI'))
eth.add_global('SPI_SCK', *pin_xy('W5500', WX, WY, 'SCLK'))
eth.add_global('SPI_CS', *pin_xy('W5500', WX, WY, '/SCSn'))
eth.add_global('W5500_INT', *pin_xy('W5500', WX, WY, '/INTn'))
eth.add_global('W5500_RST', *pin_xy('W5500', WX, WY, '/RSTn'))

# PHY
eth.add_label('ETH_TXP', *pin_xy('W5500', WX, WY, 'TXP'))
eth.add_label('ETH_TXN', *pin_xy('W5500', WX, WY, 'TXN'))
eth.add_label('ETH_RXP', *pin_xy('W5500', WX, WY, 'RXP'))
eth.add_label('ETH_RXN', *pin_xy('W5500', WX, WY, 'RXN'))

# Crystal
eth.add_label('W5_XTAL1', *pin_xy('W5500', WX, WY, 'XTAL1'))
eth.add_label('W5_XTAL2', *pin_xy('W5500', WX, WY, 'XTAL2'))

# EXRES/RCLK
eth.add_label('W5500_EXRES0', *pin_xy('W5500', WX, WY, 'EXRES0'))
eth.add_label('W5500_RCLK', *pin_xy('W5500', WX, WY, 'RCLK'))
eth.add_label('W5500_EXRES1', *pin_xy('W5500', WX, WY, 'EXRES1'))
eth.add_label('W5500_EXRES1', *pin_xy('W5500', WX, WY, 'AVCCRST'))

# Power
for p in ['VDDIO', 'AVDD', 'AVDD2', 'VDDIO2']:
    eth.add_power('VCC3V3', *pin_xy('W5500', WX, WY, p))
for p in ['GND', 'GND2', 'AGNDB', 'GND3', 'GND4']:
    eth.add_power('GND', *pin_xy('W5500', WX, WY, p), 270)

# VDD (internal 1.1V)
eth.add_label('W5_VDD', *pin_xy('W5500', WX, WY, 'VDD'))
eth.add_cap('C4', '100nF', WX - 10, WY - 25, 'W5_VDD')

# RSVD pins
for rsvd in ['RSVD1','RSVD2','RSVD3','RSVD4','RSVD5','RSVD6','RSVD7','RSVD8']:
    eth.add_nc(*pin_xy('W5500', WX, WY, rsvd))

# Bias resistors
eth.add_note("Bias Resistors", WX + 25, WY - 5)
eth.add_resistor('R11', '12.4k', WX + 30, WY + 5, 'W5500_EXRES0', 'GND',
                  bot_is_power=True, lcsc='C25502')
eth.add_resistor('R12', '12.4k', WX + 38, WY + 5, 'W5500_RCLK', 'GND',
                  bot_is_power=True, lcsc='C25502')
eth.add_resistor('R13', '12.4k', WX + 46, WY + 5, 'VCC3V3', 'W5500_EXRES1',
                  top_is_power=True, lcsc='C25502')

# SPI/RST pullups
eth.add_note("Pullups", WX + 25, WY - 30)
eth.add_resistor('R14', '10k', WX + 30, WY - 22, 'VCC3V3', 'SPI_MISO',
                  top_is_power=True, bot_is_global=True, lcsc='C25744')
eth.add_resistor('R15', '10k', WX + 38, WY - 22, 'VCC3V3', 'SPI_CS',
                  top_is_power=True, bot_is_global=True, lcsc='C25744')
eth.add_resistor('R16', '10k', WX + 46, WY - 22, 'VCC3V3', 'W5500_RST',
                  top_is_power=True, bot_is_global=True, lcsc='C25744')

# W5500 decoupling
for i in range(4):
    eth.add_cap(next_cap(), '100nF', WX - 25 + i * 8, WY - 28, 'VCC3V3', top_is_power=True)
eth.add_cap(next_cap(), '4.7uF', WX + 7, WY - 28, 'VCC3V3', top_is_power=True, lcsc='C19712')

# 25MHz Crystal
eth.add_note("25 MHz Crystal", WX + 60, WY - 50)
Y2X, Y2Y = WX + 70, WY - 40
eth.add_comp('Crystal', 'Y2', '25MHz',
    'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm', Y2X, Y2Y, 'C13738')
eth.add_label('W5_XTAL1', *pin_xy('Crystal', Y2X, Y2Y, 'XIN'))
eth.add_label('W5_XTAL2', *pin_xy('Crystal', Y2X, Y2Y, 'XOUT'))
eth.add_cap('C5', '18pF', Y2X - 10, Y2Y, 'W5_XTAL1', lcsc='C1810')
eth.add_cap('C6', '18pF', Y2X + 10, Y2Y, 'W5_XTAL2', lcsc='C1810')

# HR911105A RJ45
eth.add_note("RJ45 (HR911105A)", 280, 80)
JX, JY = 310, 140
eth.add_comp('HR911105A', 'J2', 'HR911105A',
    'Connector_RJ:RJ45_Hanrun_HR911105A_Horizontal', JX, JY, 'C12074')
eth.add_label('ETH_TXP', *pin_xy('HR911105A', JX, JY, 'MDI+'))
eth.add_label('ETH_TXN', *pin_xy('HR911105A', JX, JY, 'MDI-'))
eth.add_label('ETH_RXP', *pin_xy('HR911105A', JX, JY, 'MDO+'))
eth.add_label('ETH_RXN', *pin_xy('HR911105A', JX, JY, 'MDO-'))
eth.add_power('GND', *pin_xy('HR911105A', JX, JY, 'GND_LED'), 270)
eth.add_power('GND', *pin_xy('HR911105A', JX, JY, 'GND2'), 270)
eth.add_power('VCC3V3', *pin_xy('HR911105A', JX, JY, 'VCC_LED'))
eth.add_label('ETH_CT1', *pin_xy('HR911105A', JX, JY, 'CT1'))
eth.add_label('ETH_CT2', *pin_xy('HR911105A', JX, JY, 'CT2'))
eth.add_nc(*pin_xy('HR911105A', JX, JY, 'SHIELD'))
eth.add_nc(*pin_xy('HR911105A', JX, JY, 'LINK_LED'))
eth.add_nc(*pin_xy('HR911105A', JX, JY, 'ACT_LED'))

# Center tap bias resistors
eth.add_resistor('R17', '49.9', JX - 15, JY - 18, 'VCC3V3', 'ETH_CT1',
                  top_is_power=True, lcsc='C23182')
eth.add_resistor('R18', '49.9', JX - 8, JY - 18, 'VCC3V3', 'ETH_CT2',
                  top_is_power=True, lcsc='C23182')


# ---------------------------------------------------------------------------
# SHEET 4: LED & IO
# ---------------------------------------------------------------------------
led = Sheet("ArtNet LED Controller — LED Outputs & IO", "A3")

# 74AHCT125 Level Shifter
led.add_note("3.3V -> 5V Level Shifter", 50, 25)
LX, LY = 120, 75
led.add_comp('SN74AHCT125', 'U4', 'SN74AHCT125',
    'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm', LX, LY, 'C7484')

# OE tied low
for oe in ['/OE_A', '/OE_B', '/OE_C', '/OE_D']:
    led.add_power('GND', *pin_xy('SN74AHCT125', LX, LY, oe), 270)

# Inputs from MCU
led.add_global('LED1_DATA_3V3', *pin_xy('SN74AHCT125', LX, LY, 'A1'))
led.add_global('LED2_DATA_3V3', *pin_xy('SN74AHCT125', LX, LY, 'A2'))
led.add_global('LED3_DATA_3V3', *pin_xy('SN74AHCT125', LX, LY, 'A3'))
led.add_global('LED4_DATA_3V3', *pin_xy('SN74AHCT125', LX, LY, 'A4'))

# Outputs to connectors
led.add_label('LED1_DATA_5V', *pin_xy('SN74AHCT125', LX, LY, 'Y1'))
led.add_label('LED2_DATA_5V', *pin_xy('SN74AHCT125', LX, LY, 'Y2'))
led.add_label('LED3_DATA_5V', *pin_xy('SN74AHCT125', LX, LY, 'Y3'))
led.add_label('LED4_DATA_5V', *pin_xy('SN74AHCT125', LX, LY, 'Y4'))

led.add_power('VCC5V', *pin_xy('SN74AHCT125', LX, LY, 'VCC'))
led.add_power('GND', *pin_xy('SN74AHCT125', LX, LY, 'GND'), 270)
led.add_cap(next_cap(), '100nF', LX + 15, LY, 'VCC5V', top_is_power=True)

# LED output connectors
led.add_note("LED Output Connectors (WS2812)", 50, 130)
for i in range(4):
    lx = 80 + i * 40
    ly = 160
    ref = f'J{5 + i}'
    led.add_comp('Conn_1x03', ref, f'LED_OUT_{i+1}',
        'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical', lx, ly, 'C124375')
    led.add_power('GND', *pin_xy('Conn_1x03', lx, ly, 'Pin1'), 270)
    led.add_label(f'LED{i+1}_DATA_5V', *pin_xy('Conn_1x03', lx, ly, 'Pin2'))
    led.add_power('VCC5V', *pin_xy('Conn_1x03', lx, ly, 'Pin3'))

# OLED connector
led.add_note("OLED Display (I2C)", 50, 200)
OX, OY = 80, 230
led.add_comp('Conn_1x04', 'J9', 'OLED_SSD1306',
    'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical', OX, OY, 'C124376')
led.add_power('VCC3V3', *pin_xy('Conn_1x04', OX, OY, 'Pin1'))
led.add_power('GND', *pin_xy('Conn_1x04', OX, OY, 'Pin2'), 270)
led.add_global('I2C_SCL', *pin_xy('Conn_1x04', OX, OY, 'Pin3'))
led.add_global('I2C_SDA', *pin_xy('Conn_1x04', OX, OY, 'Pin4'))

# I2C pullups
led.add_resistor('R19', '4.7k', OX + 15, OY - 10, 'VCC3V3', 'I2C_SCL',
                  top_is_power=True, bot_is_global=True, lcsc='C25900')
led.add_resistor('R20', '4.7k', OX + 23, OY - 10, 'VCC3V3', 'I2C_SDA',
                  top_is_power=True, bot_is_global=True, lcsc='C25900')

# User buttons
led.add_note("User Buttons", 280, 130)
for i, bx in enumerate([300, 340]):
    by = 160
    ref = f'SW{i + 1}'
    led.add_comp('SW_Push', ref, f'BTN{i+1}',
        'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ', bx, by, 'C318884')
    led.add_global(f'BTN{i+1}', *pin_xy('SW_Push', bx, by, 'A'))
    led.add_power('GND', *pin_xy('SW_Push', bx, by, 'B'), 270)
    led.add_resistor(f'R{21+i}', '10k', bx, by - 15, 'VCC3V3', f'BTN{i+1}',
                      top_is_power=True, bot_is_global=True, lcsc='C25744')

# SWD debug header
led.add_note("SWD Debug", 280, 200)
SX, SY = 310, 230
led.add_comp('Conn_1x03', 'J10', 'SWD_DEBUG',
    'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical', SX, SY, 'C124375')
led.add_global('SWCLK', *pin_xy('Conn_1x03', SX, SY, 'Pin1'))
led.add_global('SWDIO', *pin_xy('Conn_1x03', SX, SY, 'Pin2'))
led.add_power('GND', *pin_xy('Conn_1x03', SX, SY, 'Pin3'), 270)


# ---------------------------------------------------------------------------
# ROOT SHEET — references sub-sheets
# ---------------------------------------------------------------------------
root_uuid = u()
pwr_uuid = u()
mcu_uuid = u()
eth_uuid = u()
led_uuid = u()

def sheet_ref(name, filename, uid, x, y, w=30, h=10):
    return (
        f'  (sheet (at {x} {y}) (size {w} {h})\n'
        f'    (stroke (width 0.2) (type solid) (color 0 0 0 1))\n'
        f'    (fill (color 255 255 255 1))\n'
        f'    (uuid "{uid}")\n'
        f'    (property "Sheetname" "{name}" (at {x} {y - 1} 0)\n'
        f'      (effects (font (size 1.27 1.27)) (justify left bottom)))\n'
        f'    (property "Sheetfile" "{filename}" (at {x} {y + h + 1} 0)\n'
        f'      (effects (font (size 1.27 1.27)) (justify left top))))'
    )

root_content = f"""(kicad_sch (version 20230121) (generator "gen_schematic.py")
  (paper "A3")
  (title_block
    (title "ArtNet LED Controller")
    (rev "2.0")
    (company "Open Source")
    (comment 1 "RP2354A + W5500 + 4x WS2812 outputs + LiPo charging")
    (comment 2 "Multi-sheet schematic — see sub-sheets for details")
  )

  (lib_symbols)

{sheet_ref("Power Supply", "power.kicad_sch", pwr_uuid, 30, 30, 40, 12)}
{sheet_ref("MCU (RP2354A)", "mcu.kicad_sch", mcu_uuid, 30, 55, 40, 12)}
{sheet_ref("Ethernet (W5500 + RJ45)", "ethernet.kicad_sch", eth_uuid, 30, 80, 40, 12)}
{sheet_ref("LED Outputs & IO", "led_io.kicad_sch", led_uuid, 30, 105, 40, 12)}

  (sheet_instances
    (path "/" (page "1"))
    (path "/{pwr_uuid}" (page "2"))
    (path "/{mcu_uuid}" (page "3"))
    (path "/{eth_uuid}" (page "4"))
    (path "/{led_uuid}" (page "5"))
  )
)"""


# ---------------------------------------------------------------------------
# Write all files
# ---------------------------------------------------------------------------
files = {
    f'{PROJECT}.kicad_sch': root_content,
    'power.kicad_sch': pwr.render(),
    'mcu.kicad_sch': mcu.render(),
    'ethernet.kicad_sch': eth.render(),
    'led_io.kicad_sch': led.render(),
}

for fname, content in files.items():
    path = DIR / fname
    with open(path, 'w') as f:
        f.write(content)
    print(f"  {fname}: {len(content):,} bytes")

# ---------------------------------------------------------------------------
# Generate netlist.json
# ---------------------------------------------------------------------------
def build_netlist():
    """Build {ref: {pad_num: net_name}} from all sheets."""
    pos_to_net = {}
    netlist = {}

    for sheet in [pwr, mcu, eth, led]:
        sheet_pos = {}
        for net, x, y in sheet.netlist_powers:
            sheet_pos[(round(x, 3), round(y, 3))] = net
        for net, x, y in sheet.netlist_labels:
            sheet_pos[(round(x, 3), round(y, 3))] = net

        for sym_name, ref, _val, _fp, cx, cy, _lcsc in sheet.components:
            if sym_name not in _sym_pin_defs:
                continue
            body, pins = _sym_pin_defs[sym_name]
            ref_nets = {}
            for side, off, _name, num, _ptype in pins:
                if side == 'L':
                    px, py = body[0] - PIN_LEN, off
                elif side == 'R':
                    px, py = body[2] + PIN_LEN, off
                elif side == 'T':
                    px, py = off, body[1] - PIN_LEN
                else:
                    px, py = off, body[3] + PIN_LEN
                key = (round(cx + px, 3), round(cy - py, 3))
                net = sheet_pos.get(key)
                if net:
                    ref_nets[num] = net
            netlist[ref] = ref_nets
    return netlist

netlist = build_netlist()
nl_path = DIR / "netlist.json"
with open(nl_path, 'w') as f:
    json.dump(netlist, f, indent=2)
assigned = sum(len(v) for v in netlist.values())
print(f"\n  netlist.json: {len(netlist)} refs, {assigned} pin assignments")

# ---------------------------------------------------------------------------
# Generate KiCad project file
# ---------------------------------------------------------------------------
kicad_pro = {
    "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 1},
    "net_settings": {"classes": [{"name": "Default", "clearance": 0.2, "track_width": 0.25}]},
    "schematic": {"drawing": {"default_line_thickness": 6.0}},
    "boards": [],
}
pro_path = DIR / f"{PROJECT}.kicad_pro"
with open(pro_path, 'w') as f:
    json.dump(kicad_pro, f, indent=2)
print(f"  {PROJECT}.kicad_pro")

print("\nDone. Open the root schematic in KiCad:")
print(f"  {DIR / f'{PROJECT}.kicad_sch'}")
