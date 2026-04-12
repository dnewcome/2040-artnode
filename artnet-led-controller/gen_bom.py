#!/usr/bin/env python3
"""Generates JLCPCB-format BOM CSV for the ArtNet LED Controller."""
from pathlib import Path
import csv

DIR = Path("/Users/dannewcome/sandbox/2040-node/artnet-led-controller")

# (Comment, Designator, Footprint, LCSC, Qty, Description, Type)
BOM = [
    # ── ICs ────────────────────────────────────────────────────────────────────
    ("RP2040",       "U1",           "QFN-56-1EP_7x7mm_P0.4mm",      "C2040",   1, "Dual-core ARM Cortex-M0+ @ 133MHz",          "Basic"),
    ("W25Q16JVSSIQ", "U2",           "SOIC-8_3.9x4.9mm_P1.27mm",     "C97521",  1, "16Mbit SPI NOR Flash for RP2040 boot",       "Extended"),
    ("W5500",        "U3",           "LQFP-48_7x7mm_P0.5mm",         "C32646",  1, "Hardwired TCP/IP Ethernet controller SPI",    "Extended"),
    ("SN74AHCT125",  "U4",           "SOIC-14_3.9x8.7mm_P1.27mm",    "C7484",   1, "Quad buffer 3V3→5V level shifter",           "Basic"),
    ("TP4056",       "U5",           "SOIC-8_3.9x4.9mm_P1.27mm",     "C16581",  1, "1A Li-Ion LiPo charger, USB input",          "Basic"),
    ("MT3608",       "U6",           "SOT-23-6",                      "C84817",  1, "2A boost converter, VBAT→5V",                "Basic"),
    ("AMS1117-3.3",  "U7",           "SOT-223-3_TabPin2",             "C6186",   1, "1A 3.3V LDO regulator",                      "Basic"),

    # ── Connectors ─────────────────────────────────────────────────────────────
    ("USB4125-GF-A",      "J1",      "USB_C_GCT_USB4125",             "C165948", 1, "USB-C receptacle, through-hole + SMD",       "Extended"),
    ("HR911105A",         "J2",      "RJ45_Horizontal_THT",           "C12074",  1, "RJ45 with integrated magnetics + LEDs",      "Extended"),
    ("B2B-PH-K",          "J3",      "JST_PH_2pin_2mm",               "C131337", 1, "2-pin JST-PH battery connector",             "Basic"),
    ("PinHeader_1x04",    "J9",      "PinHeader_2.54mm_1x04",         "C124376", 1, "4-pin OLED (VCC GND SCL SDA)",               "Basic"),
    ("PinHeader_1x03",    "J5,J6,J7,J8","PinHeader_2.54mm_1x03",     "C124375", 4, "LED output connectors (GND DATA VCC5V)",      "Basic"),
    ("PinHeader_1x03",    "J10",     "PinHeader_2.54mm_1x03",         "C124375", 1, "SWD debug header (SWCLK SWDIO GND)",         "Basic"),

    # ── Crystals ────────────────────────────────────────────────────────────────
    ("12MHz 3225",        "Y1",      "Crystal_SMD_3225-4Pin",         "C9002",   1, "12MHz crystal for RP2040 XOSC, ±30ppm",      "Basic"),
    ("25MHz 3225",        "Y2",      "Crystal_SMD_3225-4Pin",         "C13738",  1, "25MHz crystal for W5500 PHY, ±30ppm",        "Basic"),

    # ── Passive – Inductors ──────────────────────────────────────────────────────
    ("22uH",              "L1",      "L_0805_2012Metric",             "C1046",   1, "22uH 2A inductor for MT3608 boost",          "Basic"),

    # ── Passive – Resistors 0402 ────────────────────────────────────────────────
    ("750k",     "R1",  "R_0402", "C25022",  1, "MT3608 FB divider top (Vout≈5.1V)"),
    ("100k",     "R2",  "R_0402", "C25741",  1, "MT3608 FB divider bottom"),
    ("2k",       "R3",  "R_0402", "C25879",  1, "TP4056 PROG: sets charge current 500mA"),
    ("5.1k",     "R4,R5","R_0402","C25905",  2, "USB-C CC1/CC2 pull-down (5V/3A sink)"),
    ("330",      "R6",  "R_0402", "C25104",  1, "Charge LED current limit"),
    ("10k",      "R7,R8,R14,R15,R16,R19,R20,R21,R22","R_0402","C25744",9,"Pull-up: CHRG,RUN,SPI,I2C,BTN"),
    ("27",       "R9,R10","R_0402","C352446", 2, "USB D+/D- series termination"),
    ("12.4k",    "R11,R12","R_0402","C25502", 2, "W5500 EXRES0/RCLK per datasheet"),
    ("12.4k",    "R13","R_0402",   "C25502",  1, "W5500 EXRES1"),
    ("4.7k",     "R19,R20","R_0402","C25900", 2, "I2C SDA/SCL pull-up"),
    ("49.9",     "R17,R18","R_0402","C23182", 2, "Ethernet center-tap bias (49.9Ω)"),

    # ── Passive – Capacitors ─────────────────────────────────────────────────────
    ("100nF 0402 X5R", "C1,C2,C3,C4,C5,C6,C32,C35,C37,C38,C39,C40,C41,C42,C44,C45,C46,C47,C49",
                          "C_0402", "C14663",  19, "100nF 0402 bypass/load caps"),
    ("12pF 0402 C0G", "C2,C3",  "C_0402",  "C1525",   2, "12MHz crystal load caps"),
    ("18pF 0402 C0G", "C5,C6",  "C_0402",  "C1810",   2, "25MHz crystal load caps"),
    ("1uF 0402 X5R",  "C43",    "C_0402",  "C52923",  1, "RP2040 bulk bypass"),
    ("4.7uF 0402 X5R","C48",    "C_0402",  "C19712",  1, "W5500 bulk bypass"),
    ("10uF 0805 X5R", "C31,C33,C34,C36","C_0805","C19702",4,"10uF bulk on all power rails"),

    # ── Discrete ─────────────────────────────────────────────────────────────────
    ("SS14 SOD-123",   "D1",  "D_SOD-123",           "C2480",   1, "40V/1A Schottky, power OR-ing"),
    ("LED 0402 Green", "D2",  "LED_0402_1005Metric",  "C72043",  1, "Charge status LED (green)"),

    # ── Switches ─────────────────────────────────────────────────────────────────
    ("KSC741J",  "SW1,SW2,SW3","SW_Push_SMD",          "C318884", 3, "Tactile switch: BTN1, BTN2, RESET"),
]

# Write JLCPCB format BOM
fields = ["Comment","Designator","Footprint","LCSC Part #","Qty","Description","JLCPCB Part Type"]
bom_path = DIR / "jlcpcb-bom.csv"
with open(bom_path, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(fields)
    for row in BOM:
        # pad to 7 columns
        r = list(row)
        while len(r) < 7:
            r.append("")
        w.writerow(r)

print(f"BOM written: {bom_path}")

# Print summary
total_qty = sum(int(r[4]) for r in BOM if str(r[4]).isdigit())
basic  = [r for r in BOM if len(r)>6 and r[6]=="Basic"]
ext    = [r for r in BOM if len(r)>6 and r[6]=="Extended"]
print(f"\nTotal unique line items: {len(BOM)}")
print(f"JLCPCB Basic parts:    {len(basic)}")
print(f"JLCPCB Extended parts: {len(ext)}")
print(f"\nPart numbers for verification:")
for r in BOM:
    if len(r) > 3 and r[3]:
        print(f"  {r[0]:25s} {r[3]}")
