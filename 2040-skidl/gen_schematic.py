#!/usr/bin/env python3
"""
ArtNet LED Controller — SKiDL Schematic Generator
RP2354A + W5500 + 4x WS2812 outputs + LiPo charging

Generates KiCad netlist and schematic via SKiDL.
"""

import os
os.environ['KICAD9_SYMBOL_DIR'] = '/usr/share/kicad/symbols'

from skidl import *

# Suppress noisy warnings
import warnings
warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Custom RP2354A (not in KiCad libs yet)
# ---------------------------------------------------------------------------
rp2354a_pins = {
    # GPIO
    'GPIO0': 2, 'GPIO1': 3, 'GPIO2': 4, 'GPIO3': 5,
    'GPIO4': 7, 'GPIO5': 8, 'GPIO6': 9, 'GPIO7': 10,
    'GPIO8': 12, 'GPIO9': 13, 'GPIO10': 14, 'GPIO11': 15,
    'GPIO12': 16, 'GPIO13': 17, 'GPIO14': 18, 'GPIO15': 19,
    'GPIO16': 27, 'GPIO17': 28, 'GPIO18': 29, 'GPIO19': 31,
    'GPIO20': 32, 'GPIO21': 33, 'GPIO22': 34, 'GPIO23': 35,
    'GPIO24': 36, 'GPIO25': 37, 'GPIO26': 40, 'GPIO27': 41,
    'GPIO28': 42, 'GPIO29': 43,
    # Crystal
    'XIN': 21, 'XOUT': 22,
    # USB
    'USB_DP': 52, 'USB_DM': 51,
    # System
    'RUN': 26, 'SWCLK': 24, 'SWDIO': 25,
    # QSPI
    'QSPI_SS': 60, 'QSPI_SCLK': 56,
    'QSPI_SD0': 57, 'QSPI_SD1': 59,
    'QSPI_SD2': 58, 'QSPI_SD3': 55,
    # Power (IO)
    'IOVDD1': 1, 'IOVDD2': 11, 'IOVDD3': 20,
    'IOVDD4': 30, 'IOVDD5': 38, 'IOVDD6': 45,
    'USB_OTP_VDD': 53, 'QSPI_IOVDD': 54,
    'ADC_AVDD': 44, 'VREG_AVDD': 46, 'VREG_VIN': 49,
    # Power (core)
    'DVDD1': 6, 'DVDD2': 23, 'DVDD3': 39,
    'GND': 61, 'VREG_PGND': 47,
    'VREG_LX': 48, 'VREG_FB': 50,
}

RP2354A = Part(
    name='RP2354A',
    dest=TEMPLATE,
    tool=SKIDL,
    pins=[Pin(num=str(num), name=name, func=Pin.types.BIDIR)
          for name, num in rp2354a_pins.items()],
    footprint='Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm',
    ref_prefix='U',
)
# Fix pin functions
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
# Power nets
# ---------------------------------------------------------------------------
vusb = Net('VUSB')
vbat = Net('VBAT')
vcc5v = Net('VCC5V')
vcc3v3 = Net('VCC3V3')
gnd = Net('GND')

# Internal / local nets
usb_dp = Net('USB_DP')
usb_dm = Net('USB_DM')
usb_dp_mcu = Net('USB_DP_MCU')
usb_dm_mcu = Net('USB_DM_MCU')
usb_cc1 = Net('USB_CC1')
usb_cc2 = Net('USB_CC2')

# ---------------------------------------------------------------------------
# POWER SECTION
# ---------------------------------------------------------------------------

# USB-C connector (6-pin simplified)
J1 = Part('Connector', 'USB_C_Receptacle',
          footprint='Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal',
          value='USB4125-GF-A')
J1['A4, A9, B4, B9'] += vusb     # VBUS pins
J1['A1, A12, B1, B12'] += gnd    # GND pins
J1['A6, B6'] += usb_dp           # D+
J1['A7, B7'] += usb_dm           # D-
J1['A5'] += usb_cc1              # CC1
J1['B5'] += usb_cc2              # CC2
J1['S1'] += NC                   # Shield

# CC resistors (5.1k to GND for USB-C sink detection)
R4 = Part('Device', 'R', value='5.1k', footprint='Resistor_SMD:R_0402_1005Metric')
R4[1] += usb_cc1
R4[2] += gnd

R5 = Part('Device', 'R', value='5.1k', footprint='Resistor_SMD:R_0402_1005Metric')
R5[1] += usb_cc2
R5[2] += gnd

# USB series resistors (27 ohm)
R9 = Part('Device', 'R', value='27', footprint='Resistor_SMD:R_0402_1005Metric')
R9[1] += usb_dp
R9[2] += usb_dp_mcu

R10 = Part('Device', 'R', value='27', footprint='Resistor_SMD:R_0402_1005Metric')
R10[1] += usb_dm
R10[2] += usb_dm_mcu

# TP4056 LiPo Charger
U5 = Part('Battery_Management', 'TP4056-42-ESOP8',
          footprint='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
          value='TP4056')
tp_prog = Net('TP4056_PROG')
chrg_stat = Net('CHRG_STAT')
stdby_stat = Net('STDBY_STAT')
U5['V_{CC}'] += vusb            # pin 4
U5['GND'] += gnd                # pin 3
U5['BAT'] += vbat               # pin 5
U5['~{CHRG}'] += chrg_stat      # pin 7
U5['~{STDBY}'] += stdby_stat    # pin 6
U5['TEMP'] += gnd               # NTC bypass — tie to GND
U5['CE'] += vusb                # Chip enable
U5['PROG'] += tp_prog           # charge current programming
U5['EPAD'] += gnd               # Exposed pad

# PROG resistor (2k for 500mA charge current)
R3 = Part('Device', 'R', value='2k', footprint='Resistor_SMD:R_0402_1005Metric')
R3[1] += tp_prog
R3[2] += gnd

# Charge status LED
D2 = Part('Device', 'LED', value='LED_GREEN', footprint='LED_SMD:LED_0402_1005Metric')
D2[1] += chrg_stat  # K/A depends on symbol, fix as needed
D2[2] += gnd

R6 = Part('Device', 'R', value='330', footprint='Resistor_SMD:R_0402_1005Metric')
R6[1] += chrg_stat
R6[2] += gnd

R7 = Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
R7[1] += vcc3v3
R7[2] += chrg_stat

# Battery connector (JST-PH 2-pin)
J3 = Part('Connector_Generic', 'Conn_01x02',
          footprint='Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical',
          value='JST-PH-2')
J3[1] += vbat
J3[2] += gnd

# MT3608 Boost Converter (VBAT -> 5V)
mt_sw = Net('MT3608_SW')
mt_fb = Net('MT3608_FB')
vboost_raw = Net('VBOOST_RAW')

U6 = Part('Regulator_Switching', 'MT3608',
          footprint='Package_TO_SOT_SMD:SOT-23-6',
          value='MT3608')
U6['IN'] += vbat               # pin 5
U6['GND'] += gnd               # pin 2
U6['EN'] += vbat                # Enable — tie to input
U6['SW'] += mt_sw               # pin 1
U6['FB'] += mt_fb               # pin 3
U6['NC'] += NC                  # pin 6

# Boost inductor
L1 = Part('Device', 'L', value='22uH', footprint='Inductor_SMD:L_0805_2012Metric')
L1[1] += mt_sw
L1[2] += vboost_raw

# Boost rectifier diode (Schottky)
D1 = Part('Device', 'D_Schottky', value='SS14', footprint='Diode_SMD:D_SOD-123')
D1[1] += vboost_raw   # Anode side
D1[2] += vcc5v         # Cathode -> 5V output

# Feedback divider (sets output to ~5V)
R1 = Part('Device', 'R', value='750k', footprint='Resistor_SMD:R_0402_1005Metric')
R1[1] += vcc5v
R1[2] += mt_fb

R2 = Part('Device', 'R', value='100k', footprint='Resistor_SMD:R_0402_1005Metric')
R2[1] += mt_fb
R2[2] += gnd

# AMS1117-3.3 LDO (5V -> 3.3V)
U7 = Part('Regulator_Linear', 'AMS1117-3.3',
          footprint='Package_TO_SOT_SMD:SOT-223-3_TabPin2',
          value='AMS1117-3.3')
U7['VI'] += vcc5v               # pin 3
U7['GND'] += gnd                # pin 1
U7['VO'] += vcc3v3              # pin 2

# Power decoupling caps
def decap(net, value='100nF', fp='Capacitor_SMD:C_0402_1005Metric'):
    c = Part('Device', 'C', value=value, footprint=fp)
    c[1] += net
    c[2] += gnd
    return c

# VUSB decoupling
decap(vusb, '10uF')
decap(vusb, '100nF')

# VBAT decoupling
decap(vbat, '10uF')

# VCC5V decoupling
decap(vcc5v, '10uF')
decap(vcc5v, '100nF')

# VCC3V3 decoupling (near LDO)
decap(vcc3v3, '10uF')
decap(vcc3v3, '100nF')
decap(vcc3v3, '100nF')


# ---------------------------------------------------------------------------
# MCU SECTION — RP2354A
# ---------------------------------------------------------------------------
U1 = RP2354A()
U1.ref = 'U1'
U1.value = 'RP2354A'

# SPI nets (for W5500)
spi_miso = Net('SPI_MISO')
spi_mosi = Net('SPI_MOSI')
spi_sck = Net('SPI_SCK')
spi_cs = Net('SPI_CS')
w5500_int = Net('W5500_INT')
w5500_rst = Net('W5500_RST')

# I2C nets (for OLED)
i2c_sda = Net('I2C_SDA')
i2c_scl = Net('I2C_SCL')

# Button nets
btn1 = Net('BTN1')
btn2 = Net('BTN2')

# LED data nets (3.3V side, before level shifter)
led1_data = Net('LED1_DATA_3V3')
led2_data = Net('LED2_DATA_3V3')
led3_data = Net('LED3_DATA_3V3')
led4_data = Net('LED4_DATA_3V3')

# SWD
swclk = Net('SWCLK')
swdio = Net('SWDIO')

# MCU crystal nets
rp_xin = Net('RP_XIN')
rp_xout = Net('RP_XOUT')

# Core regulator nets
vreg_lx = Net('VREG_LX')
vreg_1v1 = Net('VREG_1V1')
vreg_avdd = Net('VREG_AVDD')

# USB boot
usb_boot = Net('USB_BOOT')
usb_boot_sw = Net('USB_BOOT_SW')

# Run/reset
rp_run = Net('RP_RUN')

# GPIO connections
U1['GPIO0'] += led1_data
U1['GPIO1'] += led2_data
U1['GPIO2'] += led3_data
U1['GPIO3'] += led4_data
U1['GPIO4'] += i2c_sda
U1['GPIO5'] += i2c_scl

# SPI for W5500
U1['GPIO16'] += spi_miso
U1['GPIO17'] += spi_cs
U1['GPIO18'] += spi_sck
U1['GPIO19'] += spi_mosi
U1['GPIO20'] += w5500_int
U1['GPIO21'] += w5500_rst

# Buttons
U1['GPIO22'] += btn1
U1['GPIO23'] += btn2

# Unused GPIOs -> NC
for g in ['GPIO6','GPIO7','GPIO8','GPIO9','GPIO10','GPIO11','GPIO12','GPIO13',
          'GPIO14','GPIO15','GPIO24','GPIO25','GPIO26','GPIO27','GPIO28','GPIO29']:
    U1[g] += NC

# QSPI
U1['QSPI_SS'] += usb_boot
for qpin in ['QSPI_SCLK','QSPI_SD0','QSPI_SD1','QSPI_SD2','QSPI_SD3']:
    U1[qpin] += NC

# USB
U1['USB_DP'] += usb_dp_mcu
U1['USB_DM'] += usb_dm_mcu

# Crystal
U1['XIN'] += rp_xin
U1['XOUT'] += rp_xout

# System
U1['RUN'] += rp_run
U1['SWCLK'] += swclk
U1['SWDIO'] += swdio

# Power pins (all IOVDDx -> VCC3V3)
for p in ['IOVDD1','IOVDD2','IOVDD3','IOVDD4','IOVDD5','IOVDD6',
          'USB_OTP_VDD','QSPI_IOVDD','ADC_AVDD','VREG_VIN']:
    U1[p] += vcc3v3
U1['GND'] += gnd
U1['VREG_PGND'] += gnd
U1['VREG_AVDD'] += vreg_avdd

# Core regulator
U1['VREG_LX'] += vreg_lx
U1['VREG_FB'] += vreg_1v1
for p in ['DVDD1', 'DVDD2', 'DVDD3']:
    U1[p] += vreg_1v1

# VREG inductor (LX -> 1V1 core)
L2 = Part('Device', 'L', value='3.3uH', footprint='Inductor_SMD:L_0805_2012Metric')
L2[1] += vreg_lx
L2[2] += vreg_1v1

# VREG_AVDD filter resistor
R23 = Part('Device', 'R', value='33', footprint='Resistor_SMD:R_0402_1005Metric')
R23[1] += vcc3v3
R23[2] += vreg_avdd

# Core regulator caps
decap(vreg_1v1, '4.7uF')
decap(vreg_avdd, '100nF')
decap(vreg_1v1, '4.7uF')
decap(vreg_1v1, '4.7uF')

# 3.3V decoupling (8 caps around MCU)
for _ in range(7):
    decap(vcc3v3, '100nF')
decap(vcc3v3, '4.7uF')

# 12MHz Crystal
Y1 = Part('Device', 'Crystal', value='12MHz',
          footprint='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm')
Y1[1] += rp_xin
Y1[2] += rp_xout

# Crystal load caps
C2 = Part('Device', 'C', value='12pF', footprint='Capacitor_SMD:C_0402_1005Metric')
C2[1] += rp_xin
C2[2] += gnd

C3 = Part('Device', 'C', value='12pF', footprint='Capacitor_SMD:C_0402_1005Metric')
C3[1] += rp_xout
C3[2] += gnd

# Reset button + pullup
R8 = Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
R8[1] += vcc3v3
R8[2] += rp_run

SW3 = Part('Switch', 'SW_Push', value='RESET',
           footprint='Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ')
SW3[1] += rp_run
SW3[2] += gnd

# Boot button
R24 = Part('Device', 'R', value='1k', footprint='Resistor_SMD:R_0402_1005Metric')
R24[1] += usb_boot
R24[2] += usb_boot_sw

SW4 = Part('Switch', 'SW_Push', value='BOOTSEL',
           footprint='Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ')
SW4[1] += usb_boot_sw
SW4[2] += gnd


# ---------------------------------------------------------------------------
# ETHERNET SECTION — W5500 + RJ45
# ---------------------------------------------------------------------------
U3 = Part('Interface_Ethernet', 'W5500',
          footprint='Package_QFP:LQFP-48_7x7mm_P0.5mm',
          value='W5500')

# PHY nets
eth_txp = Net('ETH_TXP')
eth_txn = Net('ETH_TXN')
eth_rxp = Net('ETH_RXP')
eth_rxn = Net('ETH_RXN')

# W5500 crystal nets
w5_xtal1 = Net('W5_XTAL1')
w5_xtal2 = Net('W5_XTAL2')

# Bias nets
w5_exres0 = Net('W5500_EXRES0')
w5_exres1 = Net('W5500_EXRES1')
w5_rclk = Net('W5500_RCLK')
w5_vdd = Net('W5_VDD')

# SPI connections
U3['MISO'] += spi_miso
U3['MOSI'] += spi_mosi
U3['SCLK'] += spi_sck
U3['~{SCS}'] += spi_cs
U3['~{INT}'] += w5500_int
U3['~{RST}'] += w5500_rst

# PHY connections
U3['TXP'] += eth_txp
U3['TXN'] += eth_txn
U3['RXP'] += eth_rxp
U3['RXN'] += eth_rxn

# Crystal
U3['XI/CLKIN'] += w5_xtal1
U3['XO'] += w5_xtal2

# Bias/reference pins
U3['EXRES1'] += w5_exres1
U3['1V2O'] += w5_vdd

# PMODE pins — set to all-capable mode (tie to GND for auto-negotiation)
U3['PMODE0'] += gnd
U3['PMODE1'] += gnd
U3['PMODE2'] += gnd

# LED pins (directly driven, active low — just NC for now)
U3['LINKLED'] += NC
U3['ACTLED'] += NC
U3['SPDLED'] += NC
U3['DUPLED'] += NC

# Power pins
U3['AVDD'] += vcc3v3
U3['VDD'] += w5_vdd
U3['VBG'] += NC  # Internal bandgap reference — leave unconnected
U3['TOCAP'] += NC  # Internal — typically has a cap to GND
U3['GND'] += gnd
U3['AGND'] += gnd

# Handle remaining NC and RSVD pins
U3['RSVD'] += NC
U3['DNC'] += NC
U3['NC'] += NC

# Bias resistors
R11 = Part('Device', 'R', value='12.4k', footprint='Resistor_SMD:R_0402_1005Metric')
R11[1] += w5_exres1
R11[2] += gnd

# SPI/RST pullups
R14 = Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
R14[1] += vcc3v3
R14[2] += spi_miso

R15 = Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
R15[1] += vcc3v3
R15[2] += spi_cs

R16 = Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
R16[1] += vcc3v3
R16[2] += w5500_rst

# W5500 decoupling (4x 100nF + 1x 4.7uF)
for _ in range(4):
    decap(vcc3v3, '100nF')
decap(vcc3v3, '4.7uF')

# W5500 VDD (internal 1.2V) decoupling
decap(w5_vdd, '100nF')

# 25MHz Crystal for W5500
Y2 = Part('Device', 'Crystal', value='25MHz',
          footprint='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm')
Y2[1] += w5_xtal1
Y2[2] += w5_xtal2

# Crystal load caps
C5 = Part('Device', 'C', value='18pF', footprint='Capacitor_SMD:C_0402_1005Metric')
C5[1] += w5_xtal1
C5[2] += gnd

C6 = Part('Device', 'C', value='18pF', footprint='Capacitor_SMD:C_0402_1005Metric')
C6[1] += w5_xtal2
C6[2] += gnd

# RJ45 with magnetics (HR911105A)
J2 = Part('Connector', 'RJ45_Hanrun_HR911105A_Horizontal',
          footprint='Connector_RJ:RJ45_Hanrun_HR911105A_Horizontal',
          value='HR911105A')

# Center tap nets
eth_ct1 = Net('ETH_CT1')
eth_ct2 = Net('ETH_CT2')

J2['TD+'] += eth_txp
J2['TD-'] += eth_txn
J2['RD+'] += eth_rxp
J2['RD-'] += eth_rxn
J2['TCT'] += eth_ct1
J2['RCT'] += eth_ct2
J2['NC'] += NC
J2['SH'] += gnd

# Center tap bias (49.9 ohm to VCC3V3)
R17 = Part('Device', 'R', value='49.9', footprint='Resistor_SMD:R_0402_1005Metric')
R17[1] += vcc3v3
R17[2] += eth_ct1

R18 = Part('Device', 'R', value='49.9', footprint='Resistor_SMD:R_0402_1005Metric')
R18[1] += vcc3v3
R18[2] += eth_ct2


# ---------------------------------------------------------------------------
# LED & IO SECTION
# ---------------------------------------------------------------------------

# 74AHCT125 Level Shifter (3.3V -> 5V for WS2812)
U4 = Part('74xx', '74AHCT125',
          footprint='Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
          value='SN74AHCT125')

# LED data nets (5V side, after level shifter)
led1_data_5v = Net('LED1_DATA_5V')
led2_data_5v = Net('LED2_DATA_5V')
led3_data_5v = Net('LED3_DATA_5V')
led4_data_5v = Net('LED4_DATA_5V')

# The 74AHCT125 pin names are just "~" (unnamed), so use pin numbers
# Pin layout: 1=/OE_A, 2=A1, 3=Y1, 4=/OE_B, 5=A2, 6=Y2,
#             7=GND, 8=Y3, 9=/OE_C, 10=A3, 11=Y4, 12=/OE_D, 13=A4, 14=VCC
# OE pins tied low (active)
U4[1] += gnd     # /OE_A
U4[4] += gnd     # /OE_B
U4[9] += gnd     # /OE_C
U4[12] += gnd    # /OE_D

# Inputs (from MCU, 3.3V)
U4[2] += led1_data    # A1
U4[5] += led2_data    # A2
U4[10] += led3_data   # A3
U4[13] += led4_data   # A4

# Outputs (to LED strips, 5V)
U4[3] += led1_data_5v   # Y1
U4[6] += led2_data_5v   # Y2
U4[8] += led3_data_5v   # Y3
U4[11] += led4_data_5v  # Y4

# Power
U4[14] += vcc5v    # VCC
U4[7] += gnd       # GND

# Decoupling for level shifter
decap(vcc5v, '100nF')

# LED output connectors (3-pin: GND, DATA, VCC5V)
for i in range(4):
    j = Part('Connector_Generic', 'Conn_01x03',
             footprint='Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
             value=f'LED_OUT_{i+1}')
    j.ref = f'J{5+i}'
    j[1] += gnd
    j[2] += [led1_data_5v, led2_data_5v, led3_data_5v, led4_data_5v][i]
    j[3] += vcc5v

# OLED display connector (I2C, 4-pin: VCC, GND, SCL, SDA)
J9 = Part('Connector_Generic', 'Conn_01x04',
          footprint='Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
          value='OLED_SSD1306')
J9[1] += vcc3v3
J9[2] += gnd
J9[3] += i2c_scl
J9[4] += i2c_sda

# I2C pullups
R19 = Part('Device', 'R', value='4.7k', footprint='Resistor_SMD:R_0402_1005Metric')
R19[1] += vcc3v3
R19[2] += i2c_scl

R20 = Part('Device', 'R', value='4.7k', footprint='Resistor_SMD:R_0402_1005Metric')
R20[1] += vcc3v3
R20[2] += i2c_sda

# User buttons (active low with pullup)
for i, (sw_net, ref_r) in enumerate([(btn1, 'R21'), (btn2, 'R22')]):
    sw = Part('Switch', 'SW_Push', value=f'BTN{i+1}',
              footprint='Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ')
    sw.ref = f'SW{i+1}'
    sw[1] += sw_net
    sw[2] += gnd
    # Pullup
    r = Part('Device', 'R', value='10k', footprint='Resistor_SMD:R_0402_1005Metric')
    r.ref = ref_r
    r[1] += vcc3v3
    r[2] += sw_net

# SWD debug header (3-pin: SWCLK, SWDIO, GND)
J10 = Part('Connector_Generic', 'Conn_01x03',
           footprint='Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
           value='SWD_DEBUG')
J10[1] += swclk
J10[2] += swdio
J10[3] += gnd


# ---------------------------------------------------------------------------
# Generate netlist
# ---------------------------------------------------------------------------
generate_netlist()
print("\nNetlist generated: gen_schematic.net")

try:
    generate_schematic()
    print("Schematic generated!")
except Exception as e:
    print(f"Schematic generation failed: {e}")
    print("(The .net netlist file can still be imported into KiCad)")

print("\nDone!")
