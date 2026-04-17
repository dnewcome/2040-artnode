#!/usr/bin/env python3
"""
ArtNet LED Controller — SKiDL Schematic Generator
RP2354A + W5500 + 4x WS2812 outputs + LiPo charging

Uses @subcircuit for each functional block so generate_svg()
produces readable per-block diagrams.
"""

import os
os.environ['KICAD9_SYMBOL_DIR'] = '/usr/share/kicad/symbols'

from skidl import *

import warnings
warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Custom RP2354A (not in KiCad libs yet)
# ---------------------------------------------------------------------------
rp2354a_pins = {
    'GPIO0': 2, 'GPIO1': 3, 'GPIO2': 4, 'GPIO3': 5,
    'GPIO4': 7, 'GPIO5': 8, 'GPIO6': 9, 'GPIO7': 10,
    'GPIO8': 12, 'GPIO9': 13, 'GPIO10': 14, 'GPIO11': 15,
    'GPIO12': 16, 'GPIO13': 17, 'GPIO14': 18, 'GPIO15': 19,
    'GPIO16': 27, 'GPIO17': 28, 'GPIO18': 29, 'GPIO19': 31,
    'GPIO20': 32, 'GPIO21': 33, 'GPIO22': 34, 'GPIO23': 35,
    'GPIO24': 36, 'GPIO25': 37, 'GPIO26': 40, 'GPIO27': 41,
    'GPIO28': 42, 'GPIO29': 43,
    'XIN': 21, 'XOUT': 22,
    'USB_DP': 52, 'USB_DM': 51,
    'RUN': 26, 'SWCLK': 24, 'SWDIO': 25,
    'QSPI_SS': 60, 'QSPI_SCLK': 56,
    'QSPI_SD0': 57, 'QSPI_SD1': 59,
    'QSPI_SD2': 58, 'QSPI_SD3': 55,
    'IOVDD1': 1, 'IOVDD2': 11, 'IOVDD3': 20,
    'IOVDD4': 30, 'IOVDD5': 38, 'IOVDD6': 45,
    'USB_OTP_VDD': 53, 'QSPI_IOVDD': 54,
    'ADC_AVDD': 44, 'VREG_AVDD': 46, 'VREG_VIN': 49,
    'DVDD1': 6, 'DVDD2': 23, 'DVDD3': 39,
    'GND': 61, 'VREG_PGND': 47,
    'VREG_LX': 48, 'VREG_FB': 50,
}

RP2354A = Part(
    name='RP2354A', dest=TEMPLATE, tool=SKIDL,
    pins=[Pin(num=str(num), name=name, func=Pin.types.BIDIR)
          for name, num in rp2354a_pins.items()],
    footprint='Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm',
    ref_prefix='U',
)
for p in RP2354A.pins:
    if 'VDD' in p.name or 'VIN' in p.name or 'AVDD' in p.name:
        p.func = Pin.types.PWRIN
    elif p.name in ('GND', 'VREG_PGND'):
        p.func = Pin.types.PWRIN
    elif p.name == 'VREG_LX':
        p.func = Pin.types.PWROUT
    elif p.name == 'VREG_FB':
        p.func = Pin.types.INPUT
    elif p.name in ('XIN', 'RUN', 'SWCLK'):
        p.func = Pin.types.INPUT
    elif p.name == 'XOUT':
        p.func = Pin.types.OUTPUT


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def decap(net, gnd, value='100nF'):
    c = Part('Device', 'C', value=value, footprint='Capacitor_SMD:C_0402_1005Metric')
    c[1] += net
    c[2] += gnd


# =========================================================================
# SUBCIRCUIT: USB-C Input
# =========================================================================
@subcircuit
def usb_input(vusb, gnd, usb_dp, usb_dm):
    """USB-C connector with CC resistors."""
    J1 = Part('Connector', 'USB_C_Receptacle',
              footprint='Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal',
              value='USB4125-GF-A')
    J1['A4, A9, B4, B9'] += vusb
    J1['A1, A12, B1, B12'] += gnd
    J1['A6, B6'] += usb_dp
    J1['A7, B7'] += usb_dm

    cc1, cc2 = Net('CC1'), Net('CC2')
    J1['A5'] += cc1
    J1['B5'] += cc2
    J1['S1'] += NC

    # 5.1k CC resistors for USB-C sink
    for cc in [cc1, cc2]:
        r = Part('Device', 'R', value='5.1k', footprint='Resistor_SMD:R_0402_1005Metric')
        r[1] += cc
        r[2] += gnd

    # USB series resistors (27 ohm) not here — they go in the MCU subcircuit
    decap(vusb, gnd, '10uF')
    decap(vusb, gnd, '100nF')


# =========================================================================
# SUBCIRCUIT: TP4056 LiPo Charger
# =========================================================================
@subcircuit
def lipo_charger(vusb, vbat, vcc3v3, gnd):
    """TP4056 charger with status LED and battery connector."""
    U = Part('Battery_Management', 'TP4056-42-ESOP8',
             footprint='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', value='TP4056')

    prog = Net('PROG')
    chrg = Net('CHRG_STAT')

    U['V_{CC}'] += vusb
    U['GND'] += gnd
    U['BAT'] += vbat
    U['~{CHRG}'] += chrg
    U['~{STDBY}'] += NC
    U['TEMP'] += gnd        # NTC bypass
    U['CE'] += vusb
    U['PROG'] += prog
    U['EPAD'] += gnd

    # PROG resistor (2k = 500mA)
    r_prog = Part('Device', 'R', value='2k', footprint='Resistor_SMD:R_0402_1005Metric')
    r_prog[1] += prog
    r_prog[2] += gnd

    # Charge LED + current limit
    led = Part('Device', 'LED', value='GREEN', footprint='LED_SMD:LED_0402_1005Metric')
    r_led = Part('Device', 'R', value='330', footprint='Resistor_SMD:R_0402_1005Metric')
    led[1] += chrg
    led[2] += gnd
    r_led[1] += chrg
    r_led[2] += gnd

    # Pullup for open-drain status
    r_pu = Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
    r_pu[1] += vcc3v3
    r_pu[2] += chrg

    # Battery connector
    J = Part('Connector_Generic', 'Conn_01x02',
             footprint='Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical',
             value='JST-PH-2')
    J[1] += vbat
    J[2] += gnd

    decap(vbat, gnd, '10uF')


# =========================================================================
# SUBCIRCUIT: MT3608 Boost (VBAT -> 5V)
# =========================================================================
@subcircuit
def boost_converter(vbat, vcc5v, gnd):
    """MT3608 boost converter with inductor, diode, and feedback divider."""
    U = Part('Regulator_Switching', 'MT3608',
             footprint='Package_TO_SOT_SMD:SOT-23-6', value='MT3608')

    sw = Net('SW')
    fb = Net('FB')
    vraw = Net('VBOOST_RAW')

    U['IN'] += vbat
    U['GND'] += gnd
    U['EN'] += vbat          # always enabled
    U['SW'] += sw
    U['FB'] += fb
    U['NC'] += NC

    # Inductor
    L = Part('Device', 'L', value='22uH', footprint='Inductor_SMD:L_0805_2012Metric')
    L[1] += sw
    L[2] += vraw

    # Schottky rectifier
    D = Part('Device', 'D_Schottky', value='SS14', footprint='Diode_SMD:D_SOD-123')
    D[1] += vraw
    D[2] += vcc5v

    # Feedback divider (750k/100k -> ~5V)
    r_top = Part('Device', 'R', value='750k', footprint='Resistor_SMD:R_0402_1005Metric')
    r_bot = Part('Device', 'R', value='100k', footprint='Resistor_SMD:R_0402_1005Metric')
    r_top[1] += vcc5v
    r_top[2] += fb
    r_bot[1] += fb
    r_bot[2] += gnd


# =========================================================================
# SUBCIRCUIT: AMS1117-3.3 LDO (5V -> 3.3V)
# =========================================================================
@subcircuit
def ldo_3v3(vcc5v, vcc3v3, gnd):
    """AMS1117-3.3 with input/output decoupling."""
    U = Part('Regulator_Linear', 'AMS1117-3.3',
             footprint='Package_TO_SOT_SMD:SOT-223-3_TabPin2', value='AMS1117-3.3')
    U['VI'] += vcc5v
    U['GND'] += gnd
    U['VO'] += vcc3v3

    decap(vcc5v, gnd, '10uF')
    decap(vcc5v, gnd, '100nF')
    decap(vcc3v3, gnd, '10uF')
    decap(vcc3v3, gnd, '100nF')
    decap(vcc3v3, gnd, '100nF')


# =========================================================================
# SUBCIRCUIT: RP2354A MCU
# =========================================================================
@subcircuit
def mcu_rp2354a(vcc3v3, gnd, usb_dp_mcu, usb_dm_mcu,
                spi_miso, spi_mosi, spi_sck, spi_cs,
                w5500_int, w5500_rst,
                i2c_sda, i2c_scl,
                led_data,  # list of 4 nets
                btn1, btn2, swclk, swdio):
    """RP2354A with crystal, VREG, reset/boot, decoupling."""
    U = RP2354A()
    U.value = 'RP2354A'

    # LED data: GPIO0-3
    for i in range(4):
        U[f'GPIO{i}'] += led_data[i]

    # I2C: GPIO4-5
    U['GPIO4'] += i2c_sda
    U['GPIO5'] += i2c_scl

    # SPI: GPIO16-19
    U['GPIO16'] += spi_miso
    U['GPIO17'] += spi_cs
    U['GPIO18'] += spi_sck
    U['GPIO19'] += spi_mosi
    U['GPIO20'] += w5500_int
    U['GPIO21'] += w5500_rst

    # Buttons: GPIO22-23
    U['GPIO22'] += btn1
    U['GPIO23'] += btn2

    # Unused GPIOs
    for g in ['GPIO6','GPIO7','GPIO8','GPIO9','GPIO10','GPIO11','GPIO12','GPIO13',
              'GPIO14','GPIO15','GPIO24','GPIO25','GPIO26','GPIO27','GPIO28','GPIO29']:
        U[g] += NC

    # QSPI
    usb_boot = Net('USB_BOOT')
    U['QSPI_SS'] += usb_boot
    for qpin in ['QSPI_SCLK','QSPI_SD0','QSPI_SD1','QSPI_SD2','QSPI_SD3']:
        U[qpin] += NC

    # USB
    U['USB_DP'] += usb_dp_mcu
    U['USB_DM'] += usb_dm_mcu

    # Crystal (12MHz)
    xin, xout = Net('XIN'), Net('XOUT')
    U['XIN'] += xin
    U['XOUT'] += xout

    Y = Part('Device', 'Crystal', value='12MHz',
             footprint='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm')
    Y[1] += xin
    Y[2] += xout

    # Crystal load caps
    for x in [xin, xout]:
        c = Part('Device', 'C', value='12pF', footprint='Capacitor_SMD:C_0402_1005Metric')
        c[1] += x
        c[2] += gnd

    # System
    rp_run = Net('RUN')
    U['RUN'] += rp_run
    U['SWCLK'] += swclk
    U['SWDIO'] += swdio

    # IO power -> VCC3V3
    for p in ['IOVDD1','IOVDD2','IOVDD3','IOVDD4','IOVDD5','IOVDD6',
              'USB_OTP_VDD','QSPI_IOVDD','ADC_AVDD','VREG_VIN']:
        U[p] += vcc3v3
    U['GND'] += gnd
    U['VREG_PGND'] += gnd

    # Core voltage regulator
    vreg_lx = Net('VREG_LX')
    vreg_1v1 = Net('VREG_1V1')
    vreg_avdd = Net('VREG_AVDD')

    U['VREG_LX'] += vreg_lx
    U['VREG_FB'] += vreg_1v1
    U['VREG_AVDD'] += vreg_avdd
    for p in ['DVDD1', 'DVDD2', 'DVDD3']:
        U[p] += vreg_1v1

    # VREG inductor
    L = Part('Device', 'L', value='3.3uH', footprint='Inductor_SMD:L_0805_2012Metric')
    L[1] += vreg_lx
    L[2] += vreg_1v1

    # VREG_AVDD filter
    r_avdd = Part('Device', 'R', value='33', footprint='Resistor_SMD:R_0402_1005Metric')
    r_avdd[1] += vcc3v3
    r_avdd[2] += vreg_avdd

    # Core caps
    decap(vreg_1v1, gnd, '4.7uF')
    decap(vreg_1v1, gnd, '4.7uF')
    decap(vreg_1v1, gnd, '4.7uF')
    decap(vreg_avdd, gnd, '100nF')

    # IO decoupling (8 caps)
    for _ in range(7):
        decap(vcc3v3, gnd, '100nF')
    decap(vcc3v3, gnd, '4.7uF')

    # Reset button + pullup
    r_rst = Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
    r_rst[1] += vcc3v3
    r_rst[2] += rp_run

    sw_rst = Part('Switch', 'SW_Push', value='RESET',
                  footprint='Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ')
    sw_rst[1] += rp_run
    sw_rst[2] += gnd

    # Boot button
    boot_sw = Net('BOOT_SW')
    r_boot = Part('Device', 'R', value='1k', footprint='Resistor_SMD:R_0402_1005Metric')
    r_boot[1] += usb_boot
    r_boot[2] += boot_sw

    sw_boot = Part('Switch', 'SW_Push', value='BOOTSEL',
                   footprint='Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ')
    sw_boot[1] += boot_sw
    sw_boot[2] += gnd

    # USB series resistors
    for dp, net in [(usb_dp_mcu, usb_dp_mcu)]:
        pass  # series resistors are in the USB input subcircuit's domain
    # Actually, let's add USB series resistors here since they're MCU-side
    # (They connect USB_DP/DM raw to USB_DP/DM_MCU)
    # These are already connected at the top level, skip here.


# =========================================================================
# SUBCIRCUIT: W5500 Ethernet
# =========================================================================
@subcircuit
def ethernet_w5500(vcc3v3, gnd,
                   spi_miso, spi_mosi, spi_sck, spi_cs,
                   w5500_int, w5500_rst,
                   eth_txp, eth_txn, eth_rxp, eth_rxn):
    """W5500 + 25MHz crystal + bias resistors + decoupling."""
    U = Part('Interface_Ethernet', 'W5500',
             footprint='Package_QFP:LQFP-48_7x7mm_P0.5mm', value='W5500')

    # SPI
    U['MISO'] += spi_miso
    U['MOSI'] += spi_mosi
    U['SCLK'] += spi_sck
    U['~{SCS}'] += spi_cs
    U['~{INT}'] += w5500_int
    U['~{RST}'] += w5500_rst

    # PHY
    U['TXP'] += eth_txp
    U['TXN'] += eth_txn
    U['RXP'] += eth_rxp
    U['RXN'] += eth_rxn

    # Crystal (25MHz)
    xtal1, xtal2 = Net('XTAL1'), Net('XTAL2')
    U['XI/CLKIN'] += xtal1
    U['XO'] += xtal2

    Y = Part('Device', 'Crystal', value='25MHz',
             footprint='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm')
    Y[1] += xtal1
    Y[2] += xtal2

    for x in [xtal1, xtal2]:
        c = Part('Device', 'C', value='18pF', footprint='Capacitor_SMD:C_0402_1005Metric')
        c[1] += x
        c[2] += gnd

    # Bias resistor (EXRES1)
    w5_exres1 = Net('EXRES1')
    U['EXRES1'] += w5_exres1
    r_bias = Part('Device', 'R', value='12.4k', footprint='Resistor_SMD:R_0402_1005Metric')
    r_bias[1] += w5_exres1
    r_bias[2] += gnd

    # Internal 1.2V
    w5_vdd = Net('W5_VDD')
    U['1V2O'] += w5_vdd
    U['VDD'] += w5_vdd
    decap(w5_vdd, gnd, '100nF')

    # PMODE (auto-negotiation)
    U['PMODE0'] += gnd
    U['PMODE1'] += gnd
    U['PMODE2'] += gnd

    # LED / misc NC
    U['LINKLED'] += NC
    U['ACTLED'] += NC
    U['SPDLED'] += NC
    U['DUPLED'] += NC
    U['VBG'] += NC
    U['TOCAP'] += NC
    U['RSVD'] += NC
    U['DNC'] += NC
    U['NC'] += NC

    # Power
    U['AVDD'] += vcc3v3
    U['GND'] += gnd
    U['AGND'] += gnd

    # Pullups on SPI/RST
    for net in [spi_miso, spi_cs, w5500_rst]:
        r = Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
        r[1] += vcc3v3
        r[2] += net

    # Decoupling
    for _ in range(4):
        decap(vcc3v3, gnd, '100nF')
    decap(vcc3v3, gnd, '4.7uF')


# =========================================================================
# SUBCIRCUIT: RJ45 Magjack
# =========================================================================
@subcircuit
def rj45_magjack(vcc3v3, gnd, eth_txp, eth_txn, eth_rxp, eth_rxn):
    """HR911105A with center-tap bias resistors."""
    J = Part('Connector', 'RJ45_Hanrun_HR911105A_Horizontal',
             footprint='Connector_RJ:RJ45_Hanrun_HR911105A_Horizontal',
             value='HR911105A')

    ct1, ct2 = Net('CT1'), Net('CT2')

    J['TD+'] += eth_txp
    J['TD-'] += eth_txn
    J['RD+'] += eth_rxp
    J['RD-'] += eth_rxn
    J['TCT'] += ct1
    J['RCT'] += ct2
    J['NC'] += NC
    J['SH'] += gnd

    # Center tap bias (49.9 ohm)
    for ct in [ct1, ct2]:
        r = Part('Device', 'R', value='49.9', footprint='Resistor_SMD:R_0402_1005Metric')
        r[1] += vcc3v3
        r[2] += ct


# =========================================================================
# SUBCIRCUIT: Level Shifter + LED Outputs
# =========================================================================
@subcircuit
def led_outputs(vcc5v, vcc3v3, gnd, led_data_3v3):
    """74AHCT125 level shifter (3.3V->5V) + 4x WS2812 connectors."""
    U = Part('74xx', '74AHCT125',
             footprint='Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
             value='SN74AHCT125')

    # OE tied low (active)
    U[1] += gnd   # /OE_A
    U[4] += gnd   # /OE_B
    U[9] += gnd   # /OE_C
    U[12] += gnd  # /OE_D

    # Inputs from MCU (3.3V)
    U[2] += led_data_3v3[0]
    U[5] += led_data_3v3[1]
    U[10] += led_data_3v3[2]
    U[13] += led_data_3v3[3]

    # Outputs (5V) to connectors
    led_5v = [Net(f'LED{i+1}_5V') for i in range(4)]
    U[3] += led_5v[0]
    U[6] += led_5v[1]
    U[8] += led_5v[2]
    U[11] += led_5v[3]

    U[14] += vcc5v
    U[7] += gnd
    decap(vcc5v, gnd, '100nF')

    # 4x LED output connectors (GND, DATA, VCC5V)
    for i in range(4):
        j = Part('Connector_Generic', 'Conn_01x03',
                 footprint='Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
                 value=f'LED_OUT_{i+1}')
        j[1] += gnd
        j[2] += led_5v[i]
        j[3] += vcc5v


# =========================================================================
# SUBCIRCUIT: OLED + I2C
# =========================================================================
@subcircuit
def oled_i2c(vcc3v3, gnd, i2c_sda, i2c_scl):
    """OLED display connector + I2C pullups."""
    J = Part('Connector_Generic', 'Conn_01x04',
             footprint='Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
             value='OLED_SSD1306')
    J[1] += vcc3v3
    J[2] += gnd
    J[3] += i2c_scl
    J[4] += i2c_sda

    # Pullups
    for net in [i2c_scl, i2c_sda]:
        r = Part('Device', 'R', value='4.7k', footprint='Resistor_SMD:R_0402_1005Metric')
        r[1] += vcc3v3
        r[2] += net


# =========================================================================
# SUBCIRCUIT: User Buttons + SWD
# =========================================================================
@subcircuit
def buttons_swd(vcc3v3, gnd, btn1, btn2, swclk, swdio):
    """Two user buttons with pullups + SWD debug header."""
    for btn_net, name in [(btn1, 'BTN1'), (btn2, 'BTN2')]:
        sw = Part('Switch', 'SW_Push', value=name,
                  footprint='Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ')
        sw[1] += btn_net
        sw[2] += gnd

        r = Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
        r[1] += vcc3v3
        r[2] += btn_net

    # SWD header
    J = Part('Connector_Generic', 'Conn_01x03',
             footprint='Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
             value='SWD_DEBUG')
    J[1] += swclk
    J[2] += swdio
    J[3] += gnd


# =========================================================================
# TOP LEVEL — Wire subcircuits together
# =========================================================================

# Power rails
vusb = Net('VUSB')
vbat = Net('VBAT')
vcc5v = Net('VCC5V')
vcc3v3 = Net('VCC3V3')
gnd = Net('GND')

# Inter-block buses
spi = Bus('SPI', 4)        # MISO, MOSI, SCK, CS
spi[0].name = 'SPI_MISO'
spi[1].name = 'SPI_MOSI'
spi[2].name = 'SPI_SCK'
spi[3].name = 'SPI_CS'

w5500_ctl = Bus('W5500_CTL', 2)  # INT, RST
w5500_ctl[0].name = 'W5500_INT'
w5500_ctl[1].name = 'W5500_RST'

i2c = Bus('I2C', 2)        # SDA, SCL
i2c[0].name = 'I2C_SDA'
i2c[1].name = 'I2C_SCL'

led_data = Bus('LED_DATA', 4)
for i in range(4):
    led_data[i].name = f'LED{i+1}_DATA'

eth = Bus('ETH', 4)        # TXP, TXN, RXP, RXN
eth[0].name = 'ETH_TXP'
eth[1].name = 'ETH_TXN'
eth[2].name = 'ETH_RXP'
eth[3].name = 'ETH_RXN'

btn1 = Net('BTN1')
btn2 = Net('BTN2')
swclk = Net('SWCLK')
swdio = Net('SWDIO')

usb_dp = Net('USB_DP')
usb_dm = Net('USB_DM')
usb_dp_mcu = Net('USB_DP_MCU')
usb_dm_mcu = Net('USB_DM_MCU')

# USB series resistors (bridge between USB connector and MCU)
for raw, mcu in [(usb_dp, usb_dp_mcu), (usb_dm, usb_dm_mcu)]:
    r = Part('Device', 'R', value='27', footprint='Resistor_SMD:R_0402_1005Metric')
    r[1] += raw
    r[2] += mcu

# --- Instantiate subcircuits ---
usb_input(vusb, gnd, usb_dp, usb_dm)
lipo_charger(vusb, vbat, vcc3v3, gnd)
boost_converter(vbat, vcc5v, gnd)
ldo_3v3(vcc5v, vcc3v3, gnd)

mcu_rp2354a(vcc3v3, gnd, usb_dp_mcu, usb_dm_mcu,
            spi[0], spi[1], spi[2], spi[3],
            w5500_ctl[0], w5500_ctl[1],
            i2c[0], i2c[1],
            [led_data[i] for i in range(4)],
            btn1, btn2, swclk, swdio)

ethernet_w5500(vcc3v3, gnd,
               spi[0], spi[1], spi[2], spi[3],
               w5500_ctl[0], w5500_ctl[1],
               eth[0], eth[1], eth[2], eth[3])

rj45_magjack(vcc3v3, gnd, eth[0], eth[1], eth[2], eth[3])

led_outputs(vcc5v, vcc3v3, gnd, [led_data[i] for i in range(4)])

oled_i2c(vcc3v3, gnd, i2c[0], i2c[1])

buttons_swd(vcc3v3, gnd, btn1, btn2, swclk, swdio)


# ---------------------------------------------------------------------------
# Generate outputs
# ---------------------------------------------------------------------------
generate_netlist()
print("\nNetlist generated: gen_schematic.net")

generate_svg()
print("SVG schematic generated: gen_schematic.svg")

print("\nDone!")
