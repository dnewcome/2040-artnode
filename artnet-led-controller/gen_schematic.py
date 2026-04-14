#!/usr/bin/env python3
"""
ArtNet LED Controller - KiCad 7 Schematic Generator
Generates artnet-led-controller.kicad_sch (self-contained, all symbols inline)
"""
import uuid, json
from pathlib import Path

DIR = Path(__file__).resolve().parent
PROJECT = "artnet-led-controller"
_pwr_n = 0

def u(): return str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Low-level S-expression writers
# ---------------------------------------------------------------------------

def wire(x1,y1,x2,y2):
    return f'  (wire (pts (xy {x1:.3f} {y1:.3f}) (xy {x2:.3f} {y2:.3f})) (stroke (width 0)(type default))(uuid "{u()}"))'

def no_connect(x,y):
    return f'  (no_connect (at {x:.3f} {y:.3f})(uuid "{u()}"))'

def net_label(name, x, y, angle=0):
    return (f'  (label "{name}" (at {x:.3f} {y:.3f} {angle})(fields_autoplaced)\n'
            f'    (effects (font (size 1.27 1.27))(justify left))\n'
            f'    (uuid "{u()}")\n'
            f'    (property "Intersheet References" "" (at {x:.3f} {y:.3f} 0)\n'
            f'      (effects (font (size 1.27 1.27))(hide yes)))\n'
            f'  )')

def power_sym(net, x, y, angle=0):
    global _pwr_n; _pwr_n += 1
    ref = f"#PWR{_pwr_n:03d}"
    ya = y+2.54 if angle==0 else y
    yv = y-2.54 if angle==0 else y+2.54
    return (f'  (symbol (lib_id "power:{net}") (at {x:.3f} {y:.3f} {angle})(unit 1)(in_bom yes)(on_board yes)\n'
            f'    (uuid "{u()}")\n'
            f'    (property "Reference" "{ref}" (at {x:.3f} {ya:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))\n'
            f'    (property "Value" "{net}" (at {x:.3f} {yv:.3f} 0)(effects (font (size 1.27 1.27))))\n'
            f'    (property "Footprint" "" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))\n'
            f'    (property "Datasheet" "" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))\n'
            f'    (instances (project "{PROJECT}" (path "/{u()}" (reference "{ref}")(unit 1))))\n'
            f'  )')

def comp(lib_id, ref, value, fp, x, y, lcsc="", angle=0, extra_props=None, hide_val=False):
    props = extra_props or {}
    lines = [
        f'  (symbol (lib_id "{lib_id}") (at {x:.3f} {y:.3f} {angle})(unit 1)(in_bom yes)(on_board yes)',
        f'    (uuid "{u()}")',
        f'    (property "Reference" "{ref}" (at {x:.3f} {y-3.81:.3f} 0)(effects (font (size 1.27 1.27))))',
        f'    (property "Value" "{value}" (at {x:.3f} {y+3.81:.3f} 0)(effects (font (size 1.27 1.27)){"(hide yes)" if hide_val else ""}))',
        f'    (property "Footprint" "{fp}" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))',
        f'    (property "Datasheet" "" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))',
    ]
    if lcsc:
        lines.append(f'    (property "LCSC" "{lcsc}" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))')
    for k,v in props.items():
        lines.append(f'    (property "{k}" "{v}" (at {x:.3f} {y:.3f} 0)(effects (font (size 1.27 1.27))(hide yes)))')
    lines.append(f'    (instances (project "{PROJECT}" (path "/{u()}" (reference "{ref}")(unit 1))))')
    lines.append('  )')
    return '\n'.join(lines)

# ---------------------------------------------------------------------------
# Symbol body builder
# Pin sides: L=left, R=right, T=top, B=bottom
# pin_def: (side, offset_along_side, name, num, type)
#   type: bidir | input | output | power_in | power_out | passive | no_connect
# body: (x1,y1,x2,y2) — bounding box of rectangle
# Returns (symbol_text, pin_endpoints_dict)
#   pin_endpoints_dict maps name -> (abs_x_from_center, abs_y_from_center)
# ---------------------------------------------------------------------------
PIN_LEN = 2.54

def build_symbol(sym_name, body, pins, pin_names_offset=1.016):
    _sym_pin_defs[sym_name] = (body, pins)
    """
    body = (x1, y1, x2, y2)  — the rectangle corners
    pins = list of (side, offset, name, num, ptype)
      side='L': pin endpoint at (x1-PIN_LEN, offset), direction=0 (→ body)
      side='R': pin endpoint at (x2+PIN_LEN, offset), direction=180 (← body)
      side='T': pin endpoint at (offset, y1-PIN_LEN), direction=270 (↓ body)
      side='B': pin endpoint at (offset, y2+PIN_LEN), direction=90  (↑ body)
    """
    x1,y1,x2,y2 = body
    endpoints = {}
    pin_lines = []
    for side, off, name, num, ptype in pins:
        if ptype == 'bidir':
            ptype = 'bidirectional'
        if side == 'L':
            px, py, ang = x1-PIN_LEN, off, 0
        elif side == 'R':
            px, py, ang = x2+PIN_LEN, off, 180
        elif side == 'T':
            px, py, ang = off, y1-PIN_LEN, 270
        else:  # B
            px, py, ang = off, y2+PIN_LEN, 90
        endpoints[name] = (px, py)
        pin_lines.append(
            f'      (pin {ptype} line (at {px:.3f} {py:.3f} {ang}) (length {PIN_LEN})\n'
            f'        (name "{name}" (effects (font (size 1.016 1.016))))\n'
            f'        (number "{num}" (effects (font (size 1.016 1.016)))))'
        )
    body_rect = (f'    (symbol "{sym_name}_0_1"\n'
                 f'      (rectangle (start {x1:.3f} {y1:.3f})(end {x2:.3f} {y2:.3f})\n'
                 f'        (stroke (width 0)(type default))(fill (type background))))\n')
    pin_block = (f'    (symbol "{sym_name}_1_1"\n' +
                 '\n'.join(pin_lines) + '\n    )\n')
    sym_text = (f'    (symbol "{sym_name}"\n'
                f'      (pin_names (offset {pin_names_offset:.3f}))\n'
                f'      (in_bom yes)(on_board yes)\n'
                f'      (property "Reference" "U" (at 0 {y1-3.81:.3f} 0)(effects (font (size 1.27 1.27))))\n'
                f'      (property "Value" "{sym_name}" (at 0 {y2+3.81:.3f} 0)(effects (font (size 1.27 1.27))))\n'
                f'      (property "Footprint" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))\n'
                f'      (property "Datasheet" "" (at 0 0 0)(effects (font (size 1.27 1.27))(hide yes)))\n'
                + body_rect + pin_block + '    )\n')
    return sym_text, endpoints

# ---------------------------------------------------------------------------
# Define all custom inline symbols
# ---------------------------------------------------------------------------

lib_symbols = []
all_endpoints = {}   # sym_name -> endpoints dict (pin_name -> (px, py))
_sym_pin_defs = {}   # sym_name -> (body, pins)  — used for netlist extraction

# ── RP2354A ─────────────────────────────────────────────────────────────────
# RP2354A is the QFN-60 RP2350A variant with 2MB flash-in-package.
# Dedicated QSPI pads remain externally available and are shared with the
# internal flash die, so do not route an external primary flash here.
# Body: 40.64 wide, 63.5 tall → (-20.32,-31.75) to (+20.32,+31.75)
rp_body = (-20.32, -31.75, 20.32, 31.75)
S = 2.54  # step

def lpin(i, name, num, ptype='bidir'):
    return ('L', -25.4 + i*S, name, num, ptype)
def rpin(i, name, num, ptype='bidir'):
    return ('R', -27.94 + i*S, name, num, ptype)
def tpin(i, name, num, ptype='power_in'):
    return ('T', -5.08 + i*S, name, num, ptype)
def bpin(i, name, num, ptype='power_in'):
    return ('B', -8.89 + i*S, name, num, ptype)

rp_pins = [
    # Left side: GPIO0-15, XIN, XOUT, USB, RUN, SWD
    lpin(0,'GPIO0','2'),   lpin(1,'GPIO1','3'),   lpin(2,'GPIO2','4'),
    lpin(3,'GPIO3','5'),   lpin(4,'GPIO4','7'),   lpin(5,'GPIO5','8'),
    lpin(6,'GPIO6','9'),   lpin(7,'GPIO7','10'),  lpin(8,'GPIO8','12'),
    lpin(9,'GPIO9','13'),  lpin(10,'GPIO10','14'),lpin(11,'GPIO11','15'),
    lpin(12,'GPIO12','16'),lpin(13,'GPIO13','17'),lpin(14,'GPIO14','18'),
    lpin(15,'GPIO15','19'),lpin(16,'XIN','21','input'), lpin(17,'XOUT','22','output'),
    lpin(18,'USB_DP','52','bidir'), lpin(19,'USB_DM','51','bidir'),
    lpin(20,'RUN','26','input'),
    lpin(21,'SWCLK','24','input'), lpin(22,'SWDIO','25','bidir'),
    # Right side: GPIO16-29, QSPI
    rpin(0,'GPIO16','27'),  rpin(1,'GPIO17','28'),  rpin(2,'GPIO18','29'),
    rpin(3,'GPIO19','31'),  rpin(4,'GPIO20','32'),  rpin(5,'GPIO21','33'),
    rpin(6,'GPIO22','34'),  rpin(7,'GPIO23','35'),  rpin(8,'GPIO24','36'),
    rpin(9,'GPIO25','37'),  rpin(10,'GPIO26','40'), rpin(11,'GPIO27','41'),
    rpin(12,'GPIO28','42'), rpin(13,'GPIO29','43'),
    rpin(14,'QSPI_SS','60','bidir'),
    rpin(15,'QSPI_SCLK','56','bidir'),
    rpin(16,'QSPI_SD0','57','bidir'),
    rpin(17,'QSPI_SD1','59','bidir'),
    rpin(18,'QSPI_SD2','58','bidir'),
    rpin(19,'QSPI_SD3','55','bidir'),
    # Top: power
    tpin(0,'IOVDD1','1','power_in'),
    tpin(1,'IOVDD2','11','power_in'),
    tpin(2,'IOVDD3','20','power_in'),
    tpin(3,'IOVDD4','30','power_in'),
    tpin(4,'IOVDD5','38','power_in'),
    tpin(5,'IOVDD6','45','power_in'),
    tpin(6,'USB_OTP_VDD','53','power_in'),
    tpin(7,'QSPI_IOVDD','54','power_in'),
    tpin(8,'ADC_AVDD','44','power_in'),
    tpin(9,'VREG_AVDD','46','power_in'),
    tpin(10,'VREG_VIN','49','power_in'),
    # Bottom: GND + core regulator pins
    bpin(0,'DVDD1','6','power_in'),
    bpin(1,'DVDD2','23','power_in'),
    bpin(2,'DVDD3','39','power_in'),
    bpin(3,'GND','61','power_in'),
    bpin(4,'VREG_PGND','47','power_in'),
    bpin(5,'VREG_LX','48','power_out'),
    bpin(6,'VREG_FB','50','input'),
]
sym, ep = build_symbol('RP2354A', rp_body, rp_pins)
lib_symbols.append(sym)
all_endpoints['RP2354A'] = ep

# ── W5500 (LQFP-48) ─────────────────────────────────────────────────────────
# 12 pins each side
w_step = 2.54
w_body = (-16.51, -16.51, 16.51, 16.51)
def wp(side, i, name, num, pt='bidir'):
    off = -13.97 + i*w_step
    return (side, off, name, num, pt)

w_pins = [
    # Left: SPI + control
    wp('L',0,'MISO','21','output'),
    wp('L',1,'MOSI','22','input'),
    wp('L',2,'SCLK','23','input'),
    wp('L',3,'/SCSn','24','input'),
    wp('L',4,'/INTn','27','output'),
    wp('L',5,'/RSTn','28','input'),
    wp('L',6,'RSVD1','1','no_connect'),
    wp('L',7,'RSVD2','2','no_connect'),
    wp('L',8,'RSVD3','3','no_connect'),
    wp('L',9,'RSVD4','4','no_connect'),
    wp('L',10,'RSVD5','17','no_connect'),
    wp('L',11,'EXRES1','5','passive'),
    # Right: Ethernet PHY
    wp('R',0,'TXP','11','output'),
    wp('R',1,'TXN','12','output'),
    wp('R',2,'RXP','14','input'),
    wp('R',3,'RXN','13','input'),
    wp('R',4,'XTAL1','15','input'),
    wp('R',5,'XTAL2','16','output'),
    wp('R',6,'EXRES0','10','passive'),
    wp('R',7,'RCLK','9','passive'),
    wp('R',8,'AVCCRST','6','power_in'),
    wp('R',9,'RSVD6','29','no_connect'),
    wp('R',10,'RSVD7','30','no_connect'),
    wp('R',11,'RSVD8','31','no_connect'),
    # Top: power
    ('T',-7.62,'VDDIO','19','power_in'),
    ('T',-5.08,'AVDD','7','power_in'),
    ('T',-2.54,'VDD','26','power_out'),
    ('T', 0,   'AVDD2','20','power_in'),
    ('T', 2.54,'VDDIO2','25','power_in'),
    # Bottom: GND
    ('B',-5.08,'GND','8','power_in'),
    ('B',-2.54,'GND2','32','power_in'),
    ('B', 0,   'AGNDB','8b','power_in'),
    ('B', 2.54,'GND3','20b','power_in'),
    ('B', 5.08,'GND4','25b','power_in'),
]
sym, ep = build_symbol('W5500', w_body, w_pins)
lib_symbols.append(sym)
all_endpoints['W5500'] = ep

# ── SN74AHCT125 (SOIC-14) ────────────────────────────────────────────────────
# 4 buffers, use all 4 with separate enables tied low
ah_body = (-7.62, -8.89, 7.62, 8.89)
ah_pins = [
    ('L',-6.35, '/OE_A','1','input'),
    ('L',-3.81, 'A1',   '2','input'),
    ('L',-1.27, '/OE_B','4','input'),
    ('L', 1.27, 'A2',   '5','input'),
    ('L', 3.81, '/OE_C','9','input'),
    ('L', 6.35, 'A3',  '10','input'),
    ('R',-6.35, 'Y1',   '3','output'),
    ('R',-3.81, 'Y2',   '6','output'),
    ('R',-1.27, '/OE_D','12','input'),
    ('R', 1.27, 'A4',  '13','input'),
    ('R', 3.81, 'Y3',  '8','output'),
    ('R', 6.35, 'Y4',  '11','output'),
    ('T', 0,    'VCC', '14','power_in'),
    ('B', 0,    'GND',  '7','power_in'),
]
sym, ep = build_symbol('SN74AHCT125', ah_body, ah_pins)
lib_symbols.append(sym)
all_endpoints['SN74AHCT125'] = ep

# ── TP4056 (SOP-8) ───────────────────────────────────────────────────────────
tp_body = (-5.08, -5.08, 5.08, 5.08)
tp_pins = [
    ('L',-2.54,'TEMP','1','input'),
    ('L', 0,   'PROG','2','passive'),
    ('L', 2.54,'GND', '3','power_in'),
    ('T', 0,   'VCC', '4','power_in'),
    ('R',-2.54,'BAT', '5','power_out'),
    ('R', 0,   '/CHRG','6','output'),
    ('R', 2.54,'/STDBY','7','output'),
    ('B', 0,   'TE',  '8','input'),
]
sym, ep = build_symbol('TP4056', tp_body, tp_pins)
lib_symbols.append(sym)
all_endpoints['TP4056'] = ep

# ── MT3608 (SOT-23-6) ────────────────────────────────────────────────────────
mt_body = (-3.81, -3.81, 3.81, 3.81)
mt_pins = [
    ('L',-1.27,'IN',  '1','power_in'),
    ('L', 1.27,'GND', '2','power_in'),
    ('T', 0,   'EN',  '3','input'),
    ('R',-1.27,'FB',  '4','input'),
    ('R', 1.27,'SW',  '5','output'),
    ('B', 0,   'NC',  '6','no_connect'),
]
sym, ep = build_symbol('MT3608', mt_body, mt_pins)
lib_symbols.append(sym)
all_endpoints['MT3608'] = ep

# ── AMS1117-3.3 (SOT-223-3) ──────────────────────────────────────────────────
am_body = (-3.81, -3.81, 3.81, 3.81)
am_pins = [
    ('L', 0,   'ADJ_GND','1','power_in'),
    ('T', 0,   'VIN',    '3','power_in'),
    ('R', 0,   'VOUT',   '2','power_out'),
    ('B', 0,   'VOUT2',  '4','power_out'),
]
sym, ep = build_symbol('AMS1117-3.3', am_body, am_pins)
lib_symbols.append(sym)
all_endpoints['AMS1117-3.3'] = ep

# ── USB-C Receptacle (GCT USB4125) ───────────────────────────────────────────
uc_body = (-6.35, -7.62, 6.35, 7.62)
uc_pins = [
    ('L',-5.08,'VBUS','A1','power_in'),
    ('L',-2.54,'D-',  'A7','bidir'),
    ('L', 0,   'D+',  'A6','bidir'),
    ('L', 2.54,'CC1', 'A5','passive'),
    ('L', 5.08,'CC2', 'B5','passive'),
    ('R',-5.08,'SHIELD','S1','passive'),
    ('T', 0,   'VBUS2','B1','power_in'),
    ('B', 0,   'GND',  'A12','power_in'),
    ('B', 2.54,'GND2', 'B12','power_in'),
]
sym, ep = build_symbol('USB_C_Receptacle', uc_body, uc_pins)
lib_symbols.append(sym)
all_endpoints['USB_C_Receptacle'] = ep

# ── HR911105A RJ45 ────────────────────────────────────────────────────────────
rj_body = (-7.62, -10.16, 7.62, 10.16)
rj_pins = [
    ('L',-7.62,'TD+','1','bidir'),
    ('L',-5.08,'TD-','2','bidir'),
    ('L',-2.54,'RD+','3','bidir'),
    ('L', 0,   'RD-','6','bidir'),
    ('L', 2.54,'VCC_LED','7','power_in'),
    ('L', 5.08,'GND_LED','4','power_in'),
    ('L', 7.62,'GND2',  '5','power_in'),
    ('R',-7.62,'MDI+','11','bidir'),
    ('R',-5.08,'MDI-','12','bidir'),
    ('R',-2.54,'MDO+','13','bidir'),
    ('R', 0,   'MDO-','14','bidir'),
    ('R', 2.54,'LINK_LED','15','output'),
    ('R', 5.08,'ACT_LED', '16','output'),
    ('R', 7.62,'SHIELD',  '17','passive'),
    ('T', 0,   'CT1',    '8','passive'),
    ('B', 0,   'CT2',    '9','passive'),
]
sym, ep = build_symbol('HR911105A', rj_body, rj_pins)
lib_symbols.append(sym)
all_endpoints['HR911105A'] = ep

# ── Crystal (2-pin) ──────────────────────────────────────────────────────────
xtal_body = (-2.54, -1.27, 2.54, 1.27)
xtal_pins = [
    ('L', 0, 'XIN', '1', 'passive'),
    ('R', 0, 'XOUT','2', 'passive'),
]
sym, ep = build_symbol('Crystal', xtal_body, xtal_pins)
lib_symbols.append(sym)
all_endpoints['Crystal'] = ep

# ── Resistor (2-pin, vertical) ───────────────────────────────────────────────
r_body = (-1.016, -1.778, 1.016, 1.778)
r_pins = [
    ('T', 0, '~', '1', 'passive'),
    ('B', 0, '~', '2', 'passive'),
]
sym, ep = build_symbol('R', r_body, r_pins)
lib_symbols.append(sym)
all_endpoints['R'] = ep

# ── Capacitor (2-pin, vertical) ──────────────────────────────────────────────
c_body = (-1.016, -0.508, 1.016, 0.508)
c_pins = [
    ('T', 0, '+', '1', 'passive'),
    ('B', 0, '~', '2', 'passive'),
]
sym, ep = build_symbol('C', c_body, c_pins)
lib_symbols.append(sym)
all_endpoints['C'] = ep

# ── Inductor (2-pin, vertical) ───────────────────────────────────────────────
l_body = (-1.016, -2.032, 1.016, 2.032)
l_pins = [
    ('T', 0, '~', '1', 'passive'),
    ('B', 0, '~', '2', 'passive'),
]
sym, ep = build_symbol('L', l_body, l_pins)
lib_symbols.append(sym)
all_endpoints['L'] = ep

# ── Schottky Diode ───────────────────────────────────────────────────────────
d_body = (-1.016, -1.27, 1.016, 1.27)
d_pins = [
    ('T', 0, 'A', '1', 'passive'),
    ('B', 0, 'K', '2', 'passive'),
]
sym, ep = build_symbol('D_Schottky', d_body, d_pins)
lib_symbols.append(sym)
all_endpoints['D_Schottky'] = ep

# ── LED ───────────────────────────────────────────────────────────────────────
led_body = (-1.016, -1.27, 1.016, 1.27)
led_pins = [
    ('T', 0, 'A', '1', 'passive'),
    ('B', 0, 'K', '2', 'passive'),
]
sym, ep = build_symbol('LED', led_body, led_pins)
lib_symbols.append(sym)
all_endpoints['LED'] = ep

# ── Tactile Switch ───────────────────────────────────────────────────────────
sw_body = (-2.54, -2.54, 2.54, 2.54)
sw_pins = [
    ('L', 0, 'A', '1', 'passive'),
    ('R', 0, 'B', '2', 'passive'),
]
sym, ep = build_symbol('SW_Push', sw_body, sw_pins)
lib_symbols.append(sym)
all_endpoints['SW_Push'] = ep

# ── 4-pin connector (OLED) ───────────────────────────────────────────────────
j4_body = (-2.54, -3.81, 2.54, 3.81)
j4_pins = [
    ('L',-2.54,'Pin1','1','passive'),
    ('L', 0,   'Pin2','2','passive'),
    ('L', 2.54,'Pin3','3','passive'),
    ('R', 0,   'Pin4','4','passive'),
]
# actually use a connector with all pins on right
j4_pins = [('R', -2.54+i*2.54, f'Pin{i+1}', str(i+1), 'passive') for i in range(4)]
sym, ep = build_symbol('Conn_1x04', j4_body, j4_pins)
lib_symbols.append(sym)
all_endpoints['Conn_1x04'] = ep

# ── 3-pin connector (LED output) ─────────────────────────────────────────────
j3_body = (-2.54, -2.54, 2.54, 2.54)
j3_pins = [('R', -2.54+i*2.54, f'Pin{i+1}', str(i+1), 'passive') for i in range(3)]
sym, ep = build_symbol('Conn_1x03', j3_body, j3_pins)
lib_symbols.append(sym)
all_endpoints['Conn_1x03'] = ep

# ── 2-pin connector (battery) ─────────────────────────────────────────────────
j2_body = (-2.54, -1.27, 2.54, 1.27)
j2_pins = [('R', -1.27+i*2.54, f'Pin{i+1}', str(i+1), 'passive') for i in range(2)]
sym, ep = build_symbol('Conn_1x02', j2_body, j2_pins)
lib_symbols.append(sym)
all_endpoints['Conn_1x02'] = ep

# ---------------------------------------------------------------------------
# Component placement: (sym_name, ref, value, footprint, cx, cy, lcsc)
# ---------------------------------------------------------------------------
components = []
labels  = []   # (name, x, y, angle)
wires   = []   # (x1,y1,x2,y2)
pwrs    = []   # (net, x, y, angle)
noconns = []   # (x, y)

# Helper: get absolute pin endpoint given component center and pin name
def pin_ep(sym_name, cx, cy, pin_name):
    ep = all_endpoints[sym_name]
    px, py = ep[pin_name]
    return cx+px, cy-py

def place_power(net, sym, cx, cy, pin_name, gnd=False, angle=0):
    """Wire power symbol to a component pin"""
    x, y = pin_ep(sym, cx, cy, pin_name)
    pwrs.append((net, x, y, 270 if gnd else 0))

def connect(label_name, sym, cx, cy, pin_name, angle=0):
    """Put a net label at a pin endpoint"""
    x, y = pin_ep(sym, cx, cy, pin_name)
    labels.append((label_name, x, y, angle))

def short(sym1, cx1, cy1, p1, sym2, cx2, cy2, p2):
    """Wire two pin endpoints directly"""
    x1,y1 = pin_ep(sym1,cx1,cy1,p1)
    x2,y2 = pin_ep(sym2,cx2,cy2,p2)
    wires.append((x1,y1,x2,y2))

def nc(sym, cx, cy, pin_name):
    x,y = pin_ep(sym,cx,cy,pin_name)
    noconns.append((x,y))

# ─── DECOUPLING CAP HELPER ────────────────────────────────────────────────
cap_n = 0
def decap(net, cx, cy, val='100nF', lcsc='C14663'):
    """Place a decoupling cap between net and GND at (cx,cy)"""
    global cap_n; cap_n+=1
    ref = f"C{cap_n+30}"
    ct_x, ct_y = cx, cy
    tp_x,tp_y = pin_ep('C',ct_x,ct_y,'+'  )
    bp_x,bp_y = pin_ep('C',ct_x,ct_y,'~'  )
    components.append(('C',ref,val,'Capacitor_SMD:C_0402_1005Metric',ct_x,ct_y,lcsc))
    pwrs.append((net, tp_x, tp_y, 0))
    pwrs.append(('GND',bp_x,bp_y,270))

# ---------------------------------------------------------------------------
# ── POWER SECTION ────────────────────────────────────────────────────────────
# USB-C at (30, 30), TP4056 at (60, 30), MT3608 at (95, 30), AMS1117 at (130, 30)
# ---------------------------------------------------------------------------

# USB-C connector
USBC_X, USBC_Y = 30, 35
components.append(('USB_C_Receptacle','J1','USB4125-GF-A',
    'Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal',USBC_X,USBC_Y,'C165948'))
connect('VUSB','USB_C_Receptacle',USBC_X,USBC_Y,'VBUS')
connect('VUSB','USB_C_Receptacle',USBC_X,USBC_Y,'VBUS2')
place_power('GND','USB_C_Receptacle',USBC_X,USBC_Y,'GND',gnd=True)
place_power('GND','USB_C_Receptacle',USBC_X,USBC_Y,'GND2',gnd=True)
# CC resistors will be handled as components below
connect('USB_DP','USB_C_Receptacle',USBC_X,USBC_Y,'D+')
connect('USB_DM','USB_C_Receptacle',USBC_X,USBC_Y,'D-')
nc('USB_C_Receptacle',USBC_X,USBC_Y,'SHIELD')
# CC1 and CC2 get 5.1k to GND (placed as resistors nearby)

# TP4056 LiPo charger
TP_X, TP_Y = 62, 35
components.append(('TP4056','U5','TP4056',
    'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',TP_X,TP_Y,'C16581'))
connect('VUSB','TP4056',TP_X,TP_Y,'VCC')
place_power('GND','TP4056',TP_X,TP_Y,'GND',gnd=True)
connect('VBAT','TP4056',TP_X,TP_Y,'BAT')
connect('CHRG_STAT','TP4056',TP_X,TP_Y,'/CHRG')
connect('STDBY_STAT','TP4056',TP_X,TP_Y,'/STDBY')
place_power('GND','TP4056',TP_X,TP_Y,'TEMP',gnd=True)   # TEMP → GND (NTC bypass)
place_power('VUSB','TP4056',TP_X,TP_Y,'TE')              # TE=high disables timer

# MT3608 Boost Converter (VBAT → 5V)
MT_X, MT_Y = 95, 35
components.append(('MT3608','U6','MT3608',
    'Package_TO_SOT_SMD:SOT-23-6',MT_X,MT_Y,'C84817'))
connect('VBAT','MT3608',MT_X,MT_Y,'IN')
place_power('GND','MT3608',MT_X,MT_Y,'GND',gnd=True)
connect('VCC5V','MT3608',MT_X,MT_Y,'EN')   # EN tied to input via resistor to always-on
connect('MT3608_SW','MT3608',MT_X,MT_Y,'SW')
connect('MT3608_FB','MT3608',MT_X,MT_Y,'FB')
nc('MT3608',MT_X,MT_Y,'NC')

# AMS1117-3.3 LDO (5V → 3.3V)
AM_X, AM_Y = 128, 35
components.append(('AMS1117-3.3','U7','AMS1117-3.3',
    'Package_TO_SOT_SMD:SOT-223-3_TabPin2',AM_X,AM_Y,'C6186'))
connect('VCC5V','AMS1117-3.3',AM_X,AM_Y,'VIN')
place_power('GND','AMS1117-3.3',AM_X,AM_Y,'ADJ_GND',gnd=True)
connect('VCC3V3','AMS1117-3.3',AM_X,AM_Y,'VOUT')
connect('VCC3V3','AMS1117-3.3',AM_X,AM_Y,'VOUT2')

# Battery connector (JST-PH-2)
BAT_X, BAT_Y = 30, 55
components.append(('Conn_1x02','J3','VBAT JST-PH-2',
    'Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical',BAT_X,BAT_Y,'C131337'))
x,y = pin_ep('Conn_1x02',BAT_X,BAT_Y,'Pin1')
labels.append(('VBAT',x,y))
x,y = pin_ep('Conn_1x02',BAT_X,BAT_Y,'Pin2')
pwrs.append(('GND',x,y,270))

# Boost converter inductor L1 (22uH)
L1_X, L1_Y = 108, 28
components.append(('L','L1','22uH',
    'Inductor_SMD:L_0805_2012Metric',L1_X,L1_Y,'C1046'))
# SW → L1 pin1, L1 pin2 → boost rectifier → VCC5V
x,y=pin_ep('L',L1_X,L1_Y,'~')   # top pin (T)
labels.append(('MT3608_SW',x,y))
x,y=pin_ep('L',L1_X,L1_Y,'~')   # hmm both named ~; use top/bottom
# Top of L (pin '~' at top):
tp_x,tp_y = L1_X + all_endpoints['L']['~'][0], L1_Y + all_endpoints['L']['~'][1]
# We need to differentiate top vs bottom - let's just label both
# since build_symbol uses the same name for both, we stored only one entry
# fix: manually compute top/bottom from pin list
# L top: T pin → (0, l_body[1]-PIN_LEN) = (0, -2.032-2.54) = (0,-4.572)
# L bottom: B pin → (0, l_body[3]+PIN_LEN) = (0, 2.032+2.54) = (0, 4.572)
labels.append(('MT3608_SW', L1_X, L1_Y - 4.572))
labels.append(('VBOOST_RAW',L1_X, L1_Y + 4.572))

# Boost rectifier diode
D1_X, D1_Y = 118, 28
components.append(('D_Schottky','D1','SS14',
    'Diode_SMD:D_SOD-123',D1_X,D1_Y,'C2480'))
labels.append(('VBOOST_RAW',D1_X,D1_Y-3.81))
labels.append(('VCC5V',D1_X,D1_Y+3.81))

# Boost converter feedback divider: R_top=750k (SW→FB), R_bot=100k (FB→GND)
# R_top
RT_X, RT_Y = 108, 42
components.append(('R','R1','750k','Resistor_SMD:R_0402_1005Metric',RT_X,RT_Y,'C25022'))
labels.append(('VCC5V',   RT_X, RT_Y - 4.318))   # top: R body top-2.54-1.778=~-4.318
labels.append(('MT3608_FB',RT_X, RT_Y + 4.318))   # bottom
# R_bot
RB_X, RB_Y = 108, 50
components.append(('R','R2','100k','Resistor_SMD:R_0402_1005Metric',RB_X,RB_Y,'C25741'))
labels.append(('MT3608_FB',RB_X, RB_Y - 4.318))
pwrs.append(('GND', RB_X, RB_Y + 4.318, 270))

# TP4056 PROG resistor (R = 1200/Ichrg*1000 = 2k for 500mA)
RP_X, RP_Y = 62, 50
components.append(('R','R3','2k','Resistor_SMD:R_0402_1005Metric',RP_X,RP_Y,'C25879'))
labels.append(('VUSB', RP_X, RP_Y - 4.318))    # Actually PROG pin connects top of resistor
# Actually: PROG pin → 2kΩ → GND
# Let's just use net labels
labels.append(('TP4056_PROG',RP_X, RP_Y - 4.318))
pwrs.append(('GND',RP_X, RP_Y + 4.318, 270))

# CC1 and CC2 resistors for USB-C (5.1k to GND)
RCC1_X, RCC1_Y = 22, 25
components.append(('R','R4','5.1k','Resistor_SMD:R_0402_1005Metric',RCC1_X,RCC1_Y,'C25905'))
labels.append(('USB_CC1', RCC1_X, RCC1_Y - 4.318))
pwrs.append(('GND', RCC1_X, RCC1_Y + 4.318, 270))

RCC2_X, RCC2_Y = 16, 25
components.append(('R','R5','5.1k','Resistor_SMD:R_0402_1005Metric',RCC2_X,RCC2_Y,'C25905'))
labels.append(('USB_CC2', RCC2_X, RCC2_Y - 4.318))
pwrs.append(('GND', RCC2_X, RCC2_Y + 4.318, 270))

# Connect CC1/CC2 from USB-C connector
x,y = pin_ep('USB_C_Receptacle',USBC_X,USBC_Y,'CC1'); labels.append(('USB_CC1',x,y))
x,y = pin_ep('USB_C_Receptacle',USBC_X,USBC_Y,'CC2'); labels.append(('USB_CC2',x,y))

# TP4056 PROG label on component
x,y = pin_ep('TP4056',TP_X,TP_Y,'PROG'); labels.append(('TP4056_PROG',x,y))

# CHRG status LEDs
LED1_X, LED1_Y = 75, 55
components.append(('LED','D2','LED_GREEN','LED_SMD:LED_0402_1005Metric',LED1_X,LED1_Y,'C72043'))
labels.append(('CHRG_STAT',LED1_X,LED1_Y-3.81))
pwrs.append(('GND',LED1_X,LED1_Y+3.81,270))
# Series resistor for LED
RLED_X,RLED_Y = 85, 55
components.append(('R','R6','330','Resistor_SMD:R_0402_1005Metric',RLED_X,RLED_Y,'C25104'))
labels.append(('CHRG_STAT',RLED_X,RLED_Y-4.318))  # from TP4056 /CHRG (open drain)
# Pullup for /CHRG
RPU_X,RPU_Y = 75, 48
components.append(('R','R7','10k','Resistor_SMD:R_0402_1005Metric',RPU_X,RPU_Y,'C25744'))
labels.append(('VCC3V3',RPU_X,RPU_Y-4.318))
labels.append(('CHRG_STAT',RPU_X,RPU_Y+4.318))

# Decoupling caps for power section
decap('VUSB',   USBC_X+5, USBC_Y-8, '10uF', 'C19702')
decap('VUSB',   USBC_X+9, USBC_Y-8, '100nF','C14663')
decap('VBAT',   BAT_X+5,  BAT_Y-8,  '10uF', 'C19702')
decap('VCC5V',  AM_X+8,   AM_Y-8,   '10uF', 'C19702')
decap('VCC5V',  AM_X+12,  AM_Y-8,   '100nF','C14663')
decap('VCC3V3', AM_X+8,   AM_Y+8,   '10uF', 'C19702')
decap('VCC3V3', AM_X+12,  AM_Y+8,   '100nF','C14663')
decap('VCC3V3', AM_X+16,  AM_Y+8,   '100nF','C14663')

# ─── RP2354A ──────────────────────────────────────────────────────────────────
RP_CX, RP_CY = 175, 130
components.append(('RP2354A','U1','RP2354A',
    'Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm',RP_CX,RP_CY,'C41378174'))

# GPIO → LED data lines
for i,gpio in enumerate(['GPIO0','GPIO1','GPIO2','GPIO3']):
    connect(f'LED{i+1}_DATA_3V3','RP2354A',RP_CX,RP_CY,gpio)

# I2C for OLED
connect('I2C_SDA','RP2354A',RP_CX,RP_CY,'GPIO4')
connect('I2C_SCL','RP2354A',RP_CX,RP_CY,'GPIO5')

# SPI for W5500
connect('SPI_MISO','RP2354A',RP_CX,RP_CY,'GPIO16')
connect('SPI_CS',  'RP2354A',RP_CX,RP_CY,'GPIO17')
connect('SPI_SCK', 'RP2354A',RP_CX,RP_CY,'GPIO18')
connect('SPI_MOSI','RP2354A',RP_CX,RP_CY,'GPIO19')
connect('W5500_INT','RP2354A',RP_CX,RP_CY,'GPIO20')
connect('W5500_RST','RP2354A',RP_CX,RP_CY,'GPIO21')

# Buttons
connect('BTN1','RP2354A',RP_CX,RP_CY,'GPIO22')
connect('BTN2','RP2354A',RP_CX,RP_CY,'GPIO23')

# Unused GPIO → NC or label
for g in ['GPIO6','GPIO7','GPIO8','GPIO9','GPIO10','GPIO11','GPIO12','GPIO13',
          'GPIO14','GPIO15','GPIO24','GPIO25','GPIO26','GPIO27','GPIO28','GPIO29']:
    nc('RP2354A',RP_CX,RP_CY,g)

# QSPI is connected to the internal flash die in RP2354A.
# Leave external pads unconnected except QSPI_SS, which is exposed as USB_BOOT.
connect('USB_BOOT', 'RP2354A',RP_CX,RP_CY,'QSPI_SS')
for qpin in ['QSPI_SCLK','QSPI_SD0','QSPI_SD1','QSPI_SD2','QSPI_SD3']:
    nc('RP2354A',RP_CX,RP_CY,qpin)

# USB
connect('USB_DP','RP2354A',RP_CX,RP_CY,'USB_DP')
connect('USB_DM','RP2354A',RP_CX,RP_CY,'USB_DM')

# Crystal 12MHz
connect('RP_XIN', 'RP2354A',RP_CX,RP_CY,'XIN')
connect('RP_XOUT','RP2354A',RP_CX,RP_CY,'XOUT')

# RUN (reset via button)
connect('RP_RUN','RP2354A',RP_CX,RP_CY,'RUN')

# Debug
connect('SWCLK','RP2354A',RP_CX,RP_CY,'SWCLK')
connect('SWDIO','RP2354A',RP_CX,RP_CY,'SWDIO')

# Power
for p in ['IOVDD1','IOVDD2','IOVDD3','IOVDD4','IOVDD5','IOVDD6',
          'USB_OTP_VDD','QSPI_IOVDD','ADC_AVDD','VREG_VIN']:
    place_power('VCC3V3','RP2354A',RP_CX,RP_CY,p)
place_power('GND','RP2354A',RP_CX,RP_CY,'GND',gnd=True)
place_power('GND','RP2354A',RP_CX,RP_CY,'VREG_PGND',gnd=True)

# RP2350 core regulator: internal buck VREG_LX -> 3.3uH -> 1.1V core rail.
connect('VREG_LX','RP2354A',RP_CX,RP_CY,'VREG_LX')
connect('VREG_1V1','RP2354A',RP_CX,RP_CY,'VREG_FB')
for p in ['DVDD1','DVDD2','DVDD3']:
    connect('VREG_1V1','RP2354A',RP_CX,RP_CY,p)

L2_X, L2_Y = RP_CX+25, RP_CY+35
components.append(('L','L2','3.3uH','Inductor_SMD:L_0805_2012Metric',L2_X,L2_Y,'C25923'))
labels.append(('VREG_LX', L2_X, L2_Y - 4.572))
labels.append(('VREG_1V1', L2_X, L2_Y + 4.572))

RVREG_X, RVREG_Y = RP_CX+40, RP_CY+25
components.append(('R','R23','33','Resistor_SMD:R_0402_1005Metric',RVREG_X,RVREG_Y,'C25105'))
labels.append(('VCC3V3', RVREG_X, RVREG_Y - 4.318))
labels.append(('VREG_AVDD', RVREG_X, RVREG_Y + 4.318))
connect('VREG_AVDD','RP2354A',RP_CX,RP_CY,'VREG_AVDD')

for ref,val,net,cx,cy,lcsc in [
    ('C7','4.7uF','VREG_1V1',RP_CX+35,RP_CY+38,'C19712'),
    ('C8','100nF','VREG_AVDD',RP_CX+46,RP_CY+35,'C14663'),
    ('C9','4.7uF','VREG_1V1',RP_CX+42,RP_CY+38,'C19712'),
    ('C10','4.7uF','VREG_1V1',RP_CX+49,RP_CY+38,'C19712'),
]:
    components.append(('C',ref,val,'Capacitor_SMD:C_0402_1005Metric',cx,cy,lcsc))
    labels.append((net,cx,cy-3.048))
    pwrs.append(('GND',cx,cy+3.048,270))

# RP2354A 3.3V decoupling caps
for i in range(7):
    decap('VCC3V3', RP_CX-30+i*6, RP_CY-38, '100nF','C14663')
decap('VCC3V3', RP_CX+15, RP_CY-38, '4.7uF','C19712')

# 12MHz Crystal
Y1_X, Y1_Y = RP_CX-45, RP_CY-50
components.append(('Crystal','Y1','12MHz',
    'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',Y1_X,Y1_Y,'C9002'))
labels.append(('RP_XIN', Y1_X+all_endpoints['Crystal']['XIN'][0],
                          Y1_Y+all_endpoints['Crystal']['XIN'][1]))
labels.append(('RP_XOUT',Y1_X+all_endpoints['Crystal']['XOUT'][0],
                          Y1_Y+all_endpoints['Crystal']['XOUT'][1]))
# Load caps for 12MHz (12pF)
LC1_X,LC1_Y = Y1_X-8, Y1_Y
components.append(('C','C2','12pF','Capacitor_SMD:C_0402_1005Metric',LC1_X,LC1_Y,'C1525'))
labels.append(('RP_XIN', LC1_X, LC1_Y-3.048))
pwrs.append(('GND',LC1_X,LC1_Y+3.048,270))
LC2_X,LC2_Y = Y1_X+8, Y1_Y
components.append(('C','C3','12pF','Capacitor_SMD:C_0402_1005Metric',LC2_X,LC2_Y,'C1525'))
labels.append(('RP_XOUT', LC2_X, LC2_Y-3.048))
pwrs.append(('GND',LC2_X,LC2_Y+3.048,270))

# RUN button + pullup
RUNPU_X, RUNPU_Y = RP_CX-60, RP_CY+15
components.append(('R','R8','10k','Resistor_SMD:R_0402_1005Metric',RUNPU_X,RUNPU_Y,'C25744'))
labels.append(('VCC3V3',RUNPU_X,RUNPU_Y-4.318))
labels.append(('RP_RUN', RUNPU_X,RUNPU_Y+4.318))
SW_RST_X, SW_RST_Y = RP_CX-70, RP_CY+15
components.append(('SW_Push','SW3','RESET',
    'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ',SW_RST_X,SW_RST_Y,'C318884'))
labels.append(('RP_RUN',SW_RST_X+all_endpoints['SW_Push']['A'][0],
                         SW_RST_Y+all_endpoints['SW_Push']['A'][1]))
pwrs.append(('GND',SW_RST_X+all_endpoints['SW_Push']['B'][0],
                    SW_RST_Y+all_endpoints['SW_Push']['B'][1],270))

# BOOTSEL button: pull QSPI_SS low during reset to enter USB/UART boot mode.
RBOOT_X, RBOOT_Y = RP_CX-85, RP_CY+5
components.append(('R','R24','1k','Resistor_SMD:R_0402_1005Metric',RBOOT_X,RBOOT_Y,'C11702'))
labels.append(('USB_BOOT',RBOOT_X,RBOOT_Y-4.318))
labels.append(('USB_BOOT_SW',RBOOT_X,RBOOT_Y+4.318))

SW_BOOT_X, SW_BOOT_Y = RP_CX-85, RP_CY+15
components.append(('SW_Push','SW4','BOOTSEL',
    'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ',SW_BOOT_X,SW_BOOT_Y,'C318884'))
labels.append(('USB_BOOT_SW',SW_BOOT_X+all_endpoints['SW_Push']['A'][0],
                              SW_BOOT_Y+all_endpoints['SW_Push']['A'][1]))
pwrs.append(('GND',SW_BOOT_X+all_endpoints['SW_Push']['B'][0],
                    SW_BOOT_Y+all_endpoints['SW_Push']['B'][1],270))

# USB series resistors (27Ω)
RUSB1_X, RUSB1_Y = USBC_X+15, USBC_Y+10
components.append(('R','R9','27','Resistor_SMD:R_0402_1005Metric',RUSB1_X,RUSB1_Y,'C352446'))
labels.append(('USB_DP', RUSB1_X,RUSB1_Y-4.318))
labels.append(('USB_DP_MCU',RUSB1_X,RUSB1_Y+4.318))
RUSB2_X, RUSB2_Y = USBC_X+21, USBC_Y+10
components.append(('R','R10','27','Resistor_SMD:R_0402_1005Metric',RUSB2_X,RUSB2_Y,'C352446'))
labels.append(('USB_DM', RUSB2_X,RUSB2_Y-4.318))
labels.append(('USB_DM_MCU',RUSB2_X,RUSB2_Y+4.318))
# Connect MCU USB to MCU pins via labels
x,y=pin_ep('RP2354A',RP_CX,RP_CY,'USB_DP'); labels.append(('USB_DP_MCU',x,y))
x,y=pin_ep('RP2354A',RP_CX,RP_CY,'USB_DM'); labels.append(('USB_DM_MCU',x,y))

# ─── W5500 ETHERNET ──────────────────────────────────────────────────────────
W5_X, W5_Y = 255, 130
components.append(('W5500','U3','W5500',
    'Package_QFP:LQFP-48_7x7mm_P0.5mm',W5_X,W5_Y,'C32646'))

# SPI
connect('SPI_MISO','W5500',W5_X,W5_Y,'MISO')
connect('SPI_MOSI','W5500',W5_X,W5_Y,'MOSI')
connect('SPI_SCK', 'W5500',W5_X,W5_Y,'SCLK')
connect('SPI_CS',  'W5500',W5_X,W5_Y,'/SCSn')
connect('W5500_INT','W5500',W5_X,W5_Y,'/INTn')
connect('W5500_RST','W5500',W5_X,W5_Y,'/RSTn')

# PHY connections
connect('ETH_TXP','W5500',W5_X,W5_Y,'TXP')
connect('ETH_TXN','W5500',W5_X,W5_Y,'TXN')
connect('ETH_RXP','W5500',W5_X,W5_Y,'RXP')
connect('ETH_RXN','W5500',W5_X,W5_Y,'RXN')

# 25MHz Crystal
connect('W5_XTAL1','W5500',W5_X,W5_Y,'XTAL1')
connect('W5_XTAL2','W5500',W5_X,W5_Y,'XTAL2')

# EXRES0: 12.4kΩ to GND (sets transmit amplitude)
REXR_X,REXR_Y = W5_X+30, W5_Y+5
components.append(('R','R11','12.4k','Resistor_SMD:R_0402_1005Metric',REXR_X,REXR_Y,'C25502'))
labels.append(('W5500_EXRES0',REXR_X,REXR_Y-4.318))
pwrs.append(('GND',REXR_X,REXR_Y+4.318,270))
connect('W5500_EXRES0','W5500',W5_X,W5_Y,'EXRES0')

# RCLK: 12.4kΩ to GND
RCLK_X,RCLK_Y = W5_X+36, W5_Y+5
components.append(('R','R12','12.4k','Resistor_SMD:R_0402_1005Metric',RCLK_X,RCLK_Y,'C25502'))
labels.append(('W5500_RCLK',RCLK_X,RCLK_Y-4.318))
pwrs.append(('GND',RCLK_X,RCLK_Y+4.318,270))
connect('W5500_RCLK','W5500',W5_X,W5_Y,'RCLK')

# EXRES1: 12.4kΩ to VCC3V3
REXR1_X,REXR1_Y = W5_X+42, W5_Y+5
components.append(('R','R13','12.4k','Resistor_SMD:R_0402_1005Metric',REXR1_X,REXR1_Y,'C25502'))
pwrs.append(('VCC3V3',REXR1_X,REXR1_Y-4.318,0))
labels.append(('W5500_EXRES1',REXR1_X,REXR1_Y+4.318))
connect('W5500_EXRES1','W5500',W5_X,W5_Y,'EXRES1')
connect('W5500_EXRES1','W5500',W5_X,W5_Y,'AVCCRST')  # AVCCRST tied to EXRES1/VCC3V3

# Power
place_power('VCC3V3','W5500',W5_X,W5_Y,'VDDIO')
place_power('VCC3V3','W5500',W5_X,W5_Y,'AVDD')
place_power('VCC3V3','W5500',W5_X,W5_Y,'AVDD2')
place_power('VCC3V3','W5500',W5_X,W5_Y,'VDDIO2')
place_power('GND',   'W5500',W5_X,W5_Y,'GND',gnd=True)
place_power('GND',   'W5500',W5_X,W5_Y,'GND2',gnd=True)
place_power('GND',   'W5500',W5_X,W5_Y,'AGNDB',gnd=True)
place_power('GND',   'W5500',W5_X,W5_Y,'GND3',gnd=True)
place_power('GND',   'W5500',W5_X,W5_Y,'GND4',gnd=True)

# VDD (internal 1.1V): connect 100nF to GND
connect('W5_VDD','W5500',W5_X,W5_Y,'VDD')
WVDD_X,WVDD_Y = W5_X-5, W5_Y-20
components.append(('C','C4','100nF','Capacitor_SMD:C_0402_1005Metric',WVDD_X,WVDD_Y,'C14663'))
labels.append(('W5_VDD',WVDD_X,WVDD_Y-3.048))
pwrs.append(('GND',WVDD_X,WVDD_Y+3.048,270))

# RSVD → NC
for rsvd in ['RSVD1','RSVD2','RSVD3','RSVD4','RSVD5','RSVD6','RSVD7','RSVD8']:
    nc('W5500',W5_X,W5_Y,rsvd)

# W5500 decoupling
for i in range(4):
    decap('VCC3V3', W5_X-25+i*6, W5_Y-22, '100nF','C14663')
decap('VCC3V3', W5_X-5, W5_Y-22, '4.7uF','C19712')

# 25MHz Crystal
Y2_X, Y2_Y = W5_X+30, W5_Y-40
components.append(('Crystal','Y2','25MHz',
    'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',Y2_X,Y2_Y,'C13738'))
labels.append(('W5_XTAL1',Y2_X+all_endpoints['Crystal']['XIN'][0],
                            Y2_Y+all_endpoints['Crystal']['XIN'][1]))
labels.append(('W5_XTAL2',Y2_X+all_endpoints['Crystal']['XOUT'][0],
                            Y2_Y+all_endpoints['Crystal']['XOUT'][1]))
LC3_X,LC3_Y = Y2_X-8, Y2_Y
components.append(('C','C5','18pF','Capacitor_SMD:C_0402_1005Metric',LC3_X,LC3_Y,'C1810'))
labels.append(('W5_XTAL1',LC3_X,LC3_Y-3.048))
pwrs.append(('GND',LC3_X,LC3_Y+3.048,270))
LC4_X,LC4_Y = Y2_X+8, Y2_Y
components.append(('C','C6','18pF','Capacitor_SMD:C_0402_1005Metric',LC4_X,LC4_Y,'C1810'))
labels.append(('W5_XTAL2',LC4_X,LC4_Y-3.048))
pwrs.append(('GND',LC4_X,LC4_Y+3.048,270))

# SPI pullup resistors (10kΩ) on MISO and /SCS
RSPIU_X,RSPIU_Y = RP_CX+30, RP_CY-40
components.append(('R','R14','10k','Resistor_SMD:R_0402_1005Metric',RSPIU_X,RSPIU_Y,'C25744'))
pwrs.append(('VCC3V3',RSPIU_X,RSPIU_Y-4.318,0))
labels.append(('SPI_MISO',RSPIU_X,RSPIU_Y+4.318))
RSPIU2_X,RSPIU2_Y = RSPIU_X+6, RSPIU_Y
components.append(('R','R15','10k','Resistor_SMD:R_0402_1005Metric',RSPIU2_X,RSPIU2_Y,'C25744'))
pwrs.append(('VCC3V3',RSPIU2_X,RSPIU2_Y-4.318,0))
labels.append(('SPI_CS',RSPIU2_X,RSPIU2_Y+4.318))

# W5500 RST pullup
RRSTP_X,RRSTP_Y = RSPIU_X+12, RSPIU_Y
components.append(('R','R16','10k','Resistor_SMD:R_0402_1005Metric',RRSTP_X,RRSTP_Y,'C25744'))
pwrs.append(('VCC3V3',RRSTP_X,RRSTP_Y-4.318,0))
labels.append(('W5500_RST',RRSTP_X,RRSTP_Y+4.318))

# ─── HR911105A RJ45 ──────────────────────────────────────────────────────────
RJ_X, RJ_Y = 310, 130
components.append(('HR911105A','J2','HR911105A',
    'Connector_RJ:RJ45_Hanrun_HR911105A_Horizontal',RJ_X,RJ_Y,'C12074'))
# Magnetics connections (the HR911105A has integrated magnetics)
# TD+/TD- → W5500 TXP/TXN via transformer center-taps at 3V3/2
# The HR911105A has pins: MDI+/-, MDO+/- (to MCU side) and TD+/-,RD+/- (to RJ45 pins)
connect('ETH_TXP','HR911105A',RJ_X,RJ_Y,'MDI+')
connect('ETH_TXN','HR911105A',RJ_X,RJ_Y,'MDI-')
connect('ETH_RXP','HR911105A',RJ_X,RJ_Y,'MDO+')
connect('ETH_RXN','HR911105A',RJ_X,RJ_Y,'MDO-')
place_power('GND','HR911105A',RJ_X,RJ_Y,'GND_LED',gnd=True)
place_power('GND','HR911105A',RJ_X,RJ_Y,'GND2',gnd=True)
# LED power: VCC_LED → 3V3 through resistor
connect('ETH_CT1','HR911105A',RJ_X,RJ_Y,'CT1')
connect('ETH_CT2','HR911105A',RJ_X,RJ_Y,'CT2')
# Center tap bias: 49.9Ω to VCC3V3/2 (or just to VCC3V3 through 49.9Ω each)
RCT_X,RCT_Y = RJ_X-15, RJ_Y-15
components.append(('R','R17','49.9','Resistor_SMD:R_0402_1005Metric',RCT_X,RCT_Y,'C23182'))
pwrs.append(('VCC3V3',RCT_X,RCT_Y-4.318,0))
labels.append(('ETH_CT1',RCT_X,RCT_Y+4.318))
RCT2_X,RCT2_Y = RJ_X-9, RJ_Y-15
components.append(('R','R18','49.9','Resistor_SMD:R_0402_1005Metric',RCT2_X,RCT2_Y,'C23182'))
pwrs.append(('VCC3V3',RCT2_X,RCT2_Y-4.318,0))
labels.append(('ETH_CT2',RCT2_X,RCT2_Y+4.318))
# Shield/LEDs NC
nc('HR911105A',RJ_X,RJ_Y,'SHIELD')
nc('HR911105A',RJ_X,RJ_Y,'LINK_LED')
nc('HR911105A',RJ_X,RJ_Y,'ACT_LED')
# VCC_LED (LED power within connector)
place_power('VCC3V3','HR911105A',RJ_X,RJ_Y,'VCC_LED')
# TD+/TD- are the RJ45 magnetics output pins (external facing) - they're internal
labels.append(('ETH_TXP_RJ', RJ_X+all_endpoints['HR911105A']['TD+'][0]+RJ_X,
                               RJ_Y+all_endpoints['HR911105A']['TD+'][1]+RJ_Y))  # skip, internal

# ─── 74AHCT125 LEVEL SHIFTER ─────────────────────────────────────────────────
LS_X, LS_Y = 120, 175
components.append(('SN74AHCT125','U4','SN74AHCT125',
    'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',LS_X,LS_Y,'C7484'))

# 4 buffers: OE tied low (enabled), inputs from RP2354A, outputs to LED connectors
place_power('GND','SN74AHCT125',LS_X,LS_Y,'/OE_A',gnd=True)
place_power('GND','SN74AHCT125',LS_X,LS_Y,'/OE_B',gnd=True)
place_power('GND','SN74AHCT125',LS_X,LS_Y,'/OE_C',gnd=True)
place_power('GND','SN74AHCT125',LS_X,LS_Y,'/OE_D',gnd=True)

connect('LED1_DATA_3V3','SN74AHCT125',LS_X,LS_Y,'A1')
connect('LED2_DATA_3V3','SN74AHCT125',LS_X,LS_Y,'A2')
connect('LED3_DATA_3V3','SN74AHCT125',LS_X,LS_Y,'A3')
connect('LED4_DATA_3V3','SN74AHCT125',LS_X,LS_Y,'A4')

connect('LED1_DATA_5V','SN74AHCT125',LS_X,LS_Y,'Y1')
connect('LED2_DATA_5V','SN74AHCT125',LS_X,LS_Y,'Y2')
connect('LED3_DATA_5V','SN74AHCT125',LS_X,LS_Y,'Y3')
connect('LED4_DATA_5V','SN74AHCT125',LS_X,LS_Y,'Y4')

place_power('VCC5V','SN74AHCT125',LS_X,LS_Y,'VCC')
place_power('GND',  'SN74AHCT125',LS_X,LS_Y,'GND',gnd=True)
decap('VCC5V',LS_X+12,LS_Y,'100nF','C14663')

# ─── LED OUTPUT CONNECTORS (4×3 pin: GND, DATA, VCC5V) ─────────────────────
LED_Y = 200
for i in range(4):
    lx = 60 + i*18
    ref = f"J{5+i}"
    components.append(('Conn_1x03',ref,f'LED_OUT_{i+1}',
        'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',lx,LED_Y,'C124375'))
    x,y = pin_ep('Conn_1x03',lx,LED_Y,'Pin1'); pwrs.append(('GND',x,y,270))
    x,y = pin_ep('Conn_1x03',lx,LED_Y,'Pin2'); labels.append((f'LED{i+1}_DATA_5V',x,y))
    x,y = pin_ep('Conn_1x03',lx,LED_Y,'Pin3'); labels.append(('VCC5V',x,y))

# ─── OLED CONNECTOR (VCC, GND, SCL, SDA) ────────────────────────────────────
OLED_X, OLED_Y = 30, 160
components.append(('Conn_1x04','J9','OLED_SSD1306',
    'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',OLED_X,OLED_Y,'C124376'))
x,y = pin_ep('Conn_1x04',OLED_X,OLED_Y,'Pin1'); pwrs.append(('VCC3V3',x,y,0))
x,y = pin_ep('Conn_1x04',OLED_X,OLED_Y,'Pin2'); pwrs.append(('GND',x,y,270))
x,y = pin_ep('Conn_1x04',OLED_X,OLED_Y,'Pin3'); labels.append(('I2C_SCL',x,y))
x,y = pin_ep('Conn_1x04',OLED_X,OLED_Y,'Pin4'); labels.append(('I2C_SDA',x,y))

# I2C pullups (4.7kΩ)
RIIC1_X,RIIC1_Y = 30, 148
components.append(('R','R19','4.7k','Resistor_SMD:R_0402_1005Metric',RIIC1_X,RIIC1_Y,'C25900'))
pwrs.append(('VCC3V3',RIIC1_X,RIIC1_Y-4.318,0))
labels.append(('I2C_SCL',RIIC1_X,RIIC1_Y+4.318))
RIIC2_X,RIIC2_Y = 37, 148
components.append(('R','R20','4.7k','Resistor_SMD:R_0402_1005Metric',RIIC2_X,RIIC2_Y,'C25900'))
pwrs.append(('VCC3V3',RIIC2_X,RIIC2_Y-4.318,0))
labels.append(('I2C_SDA',RIIC2_X,RIIC2_Y+4.318))

# ─── USER BUTTONS ────────────────────────────────────────────────────────────
for i,(bx,by) in enumerate([(30,180),(45,180)]):
    ref = f'SW{i+1}'
    components.append(('SW_Push',ref,f'BTN{i+1}',
        'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ',bx,by,'C318884'))
    x,y = pin_ep('SW_Push',bx,by,'A'); labels.append((f'BTN{i+1}',x,y))
    x,y = pin_ep('SW_Push',bx,by,'B'); pwrs.append(('GND',x,y,270))
    # Pullup resistor
    rpux,rpuy = bx, by-12
    rref=f'R{21+i}'
    components.append(('R',rref,'10k','Resistor_SMD:R_0402_1005Metric',rpux,rpuy,'C25744'))
    pwrs.append(('VCC3V3',rpux,rpuy-4.318,0))
    labels.append((f'BTN{i+1}',rpux,rpuy+4.318))

# ─── SWD DEBUG HEADER (2x3) ──────────────────────────────────────────────────
# Use 3-pin connector as minimal SWD
SWD_X, SWD_Y = 155, 180
components.append(('Conn_1x03','J10','SWD_DEBUG',
    'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',SWD_X,SWD_Y,'C124375'))
x,y = pin_ep('Conn_1x03',SWD_X,SWD_Y,'Pin1'); labels.append(('SWCLK',x,y))
x,y = pin_ep('Conn_1x03',SWD_X,SWD_Y,'Pin2'); labels.append(('SWDIO',x,y))
x,y = pin_ep('Conn_1x03',SWD_X,SWD_Y,'Pin3'); pwrs.append(('GND',x,y,270))

# ─── POWER FLAG (required by KiCad ERC) ──────────────────────────────────────
# Power flags tell ERC that power rails are driven
for net,fx,fy in [('VCC3V3',10,10),('VCC5V',20,10),('GND',30,10),('VBAT',40,10),('VUSB',50,10),('VREG_1V1',60,10)]:
    pwrs.append((f'PWR_FLAG',fx,fy,0))
    pwrs.append((net,fx,fy+5,0))

# ---------------------------------------------------------------------------
# Generate schematic file
# ---------------------------------------------------------------------------

lines = []
lines.append(f'(kicad_sch (version 20230121) (generator eeschema)')
lines.append(f'  (paper "A1")')
lines.append(f'  (title_block')
lines.append(f'    (title "ArtNet LED Controller")')
lines.append(f'    (date "2024-01-01")')
lines.append(f'    (rev "1.0")')
lines.append(f'    (company "Open Source")')
lines.append(f'    (comment 1 "RP2354A + W5500 + 4x WS2812 outputs + LiPo charging")')
lines.append(f'  )')
lines.append('')
lines.append('  (lib_symbols')
for sym in lib_symbols:
    lines.append(sym)
lines.append('  )')
lines.append('')

# power symbols
for item in pwrs:
    lines.append(power_sym(*item))

# wires
for w in wires:
    lines.append(wire(*w))

# labels
for item in labels:
    name,x,y = item[0],item[1],item[2]
    angle = item[3] if len(item)>3 else 0
    lines.append(net_label(name,x,y,angle))

# no-connects
for item in noconns:
    lines.append(no_connect(*item))

# components
for c_item in components:
    sym_name,ref,val,fp,cx,cy,lcsc = c_item
    lines.append(comp(sym_name, ref, val, fp, cx, cy, lcsc))

lines.append(')')

out = '\n'.join(lines)
sch_path = DIR / f"{PROJECT}.kicad_sch"
with open(sch_path,'w') as f:
    f.write(out)
print(f"Schematic written: {sch_path} ({len(out):,} bytes, {len(lines)} lines)")

# ---------------------------------------------------------------------------
# Netlist extraction — must run after all components/labels/pwrs are defined
# ---------------------------------------------------------------------------

def build_netlist():
    """Build {ref: {pad_num: net_name}} by matching pin positions to net labels."""
    import json

    # Map schematic position → net name (labels take priority over power syms)
    pos_to_net = {}
    for net, x, y, _angle in pwrs:
        pos_to_net[(round(x, 3), round(y, 3))] = net
    for entry in labels:
        name, x, y = entry[0], entry[1], entry[2]
        pos_to_net[(round(x, 3), round(y, 3))] = name

    netlist = {}
    for sym_name, ref, _val, _fp, cx, cy, _lcsc in components:
        if sym_name not in _sym_pin_defs:
            continue
        body, pins = _sym_pin_defs[sym_name]
        x1, y1, x2, y2 = body
        ref_nets = {}
        for side, off, _name, num, _ptype in pins:
            if side == 'L':
                px, py = x1 - PIN_LEN, off
            elif side == 'R':
                px, py = x2 + PIN_LEN, off
            elif side == 'T':
                px, py = off, y1 - PIN_LEN
            else:  # B
                px, py = off, y2 + PIN_LEN
            # Match pin_ep: abs = (cx+px, cy-py)
            key = (round(cx + px, 3), round(cy - py, 3))
            net = pos_to_net.get(key)
            if net:
                ref_nets[num] = net
        netlist[ref] = ref_nets
    return netlist

import json
netlist = build_netlist()
nl_path = DIR / "netlist.json"
with open(nl_path, 'w') as f:
    json.dump(netlist, f, indent=2)
assigned = sum(len(v) for v in netlist.values())
print(f"Netlist written: {nl_path} ({len(netlist)} refs, {assigned} pin assignments)")
print("Done.")
