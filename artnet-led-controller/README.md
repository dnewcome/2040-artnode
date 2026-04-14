# ArtNet LED Controller

RP2354A-based ArtNet node with 4× WS2812/SK6812 serial outputs, W5500 Ethernet, USB-C LiPo charging, and SSD1306 OLED display header.

---

## Board Specifications

| Parameter | Value |
|---|---|
| MCU | Raspberry Pi RP2354A (dual-core Cortex-M33 / Hazard3 RISC-V, 150MHz) |
| Network | WIZnet W5500 hardwired TCP/IP + ArtNet (Ethernet) |
| LED outputs | 4× single-wire serial (WS2812B / SK6812 / NeoPixel compatible) |
| Max pixels | 1024 (256/universe × 4 universes at 30fps) |
| Flash | 2MB flash-in-package inside RP2354A |
| OLED | I²C header for SSD1306 128×64 |
| Buttons | 2× user + 1× reset + 1× BOOTSEL |
| Charging | TP4056 @ 500mA, USB-C input (5V/3A CC resistors) |
| Battery | Single-cell Li-Ion/LiPo via JST-PH 2-pin |
| 5V rail | MT3608 boost converter (VBAT → 5.1V) |
| 3.3V rail | AMS1117-3.3 LDO (VCC5V → 3.3V, 800mA) |
| Board | 100mm × 70mm, 2-layer FR4, ENIG |

---

## Power Architecture

```
USB-C (5V/3A) ──────────────────────────────────────────┐
                                                         │
                 ┌── TP4056 (500mA charge) ──────────────┤
                 │                                       │
Li-Ion Battery ──┘                                       │
         │                                               │
         └── MT3608 (boost → 5.1V) ── D1 (SS14) ── 5V Bus
                                                         │
                                              AMS1117-3.3 (LDO)
                                                         │
                                                      3.3V Bus
```

- When USB-C is connected: TP4056 charges the battery; boost converter runs from battery simultaneously
- When on battery only: boost converter maintains 5V rail
- D1 (Schottky) prevents USB 5V from back-feeding if simultaneously present
- LED pixel power is **external** — the board provides only the control signal and a 5V pass-through on each LED connector

> **Power budget for LED pixels:**  
> WS2812B at full white: 60mA/pixel × 1024 = 61.4A @ 5V — this **must** come from external PSUs  
> connected directly to your LED strips. The board draws ~300mA for its own electronics.

---

## Pinout — RP2354A

| GPIO | Function | Notes |
|---|---|---|
| GPIO0 | LED1_DATA | → SN74AHCT125 → 5V level |
| GPIO1 | LED2_DATA | → SN74AHCT125 → 5V level |
| GPIO2 | LED3_DATA | → SN74AHCT125 → 5V level |
| GPIO3 | LED4_DATA | → SN74AHCT125 → 5V level |
| GPIO4 | I2C0_SDA | OLED display |
| GPIO5 | I2C0_SCL | OLED display |
| GPIO16 | SPI0_MISO | W5500 |
| GPIO17 | SPI0_CS | W5500 chip select |
| GPIO18 | SPI0_SCK | W5500 |
| GPIO19 | SPI0_MOSI | W5500 |
| GPIO20 | W5500_INT | Active low interrupt |
| GPIO21 | W5500_RST | Active low reset |
| GPIO22 | BTN1 | Active low, 10k pullup |
| GPIO23 | BTN2 | Active low, 10k pullup |
| QSPI_SS | USB_BOOT | SW4 BOOTSEL, hold low during reset |
| QSPI | Internal flash | Integrated 2MB flash-in-package |
| USB | USB | Native USB (programming / serial) |
| SWCLK/SWDIO | SWD | Debug header J10 |

---

## LED Output Connectors (J5–J8)

Each connector is a 3-pin 2.54mm header:

| Pin | Signal |
|---|---|
| 1 | GND |
| 2 | DATA (5V level, from SN74AHCT125) |
| 3 | VCC5V (board 5V rail, ~300mA total available — for short LED test strips only) |

For production use with 1024 pixels, inject external 5V power directly into your LED strips and use only Pin 2 (DATA) and Pin 1 (GND) from this connector.

---

## OLED Connector (J9)

4-pin 2.54mm header:

| Pin | Signal |
|---|---|
| 1 | VCC (3.3V) |
| 2 | GND |
| 3 | SCL |
| 4 | SDA |

Compatible with common SSD1306 I²C OLED modules (128×64, 0.96").

---

## KiCad Workflow

### Opening the project

```
File → Open Project → artnet-led-controller.kicad_pro
```

The schematic (`artnet-led-controller.kicad_sch`) contains all symbols defined inline — no external library dependencies.

### Importing schematic into PCB

1. Open `artnet-led-controller.kicad_pcb`
2. **Tools → Update PCB from Schematic** (F8)
3. Click **Update PCB** — this assigns nets to all footprint pads

### Routing

The PCB has all components placed on a 100×70mm board. GND copper pours are defined on both layers. To complete routing:

```
Route → Interactive Router Settings → set to "Follow Mouse"
Route → Route All Tracks (freerouter)
```

Or use the **FreeRouting** plugin:  
`PCB Editor → Tools → External Plugins → FreeRouting`

**Recommended design rules (JLCPCB 2-layer):**

| Rule | Value |
|---|---|
| Min track width | 0.2mm |
| Min clearance | 0.2mm |
| Min via drill | 0.3mm |
| Min via pad | 0.6mm |
| Copper-to-edge | 0.3mm |

**Critical routing notes:**
- Route USB D+/D- as a matched-length differential pair, 27Ω series resistors close to USB-C connector
- Route Ethernet TX+/TX- and RX+/RX- as differential pairs (0.2mm/0.2mm gap)
- Keep 25MHz crystal traces (Y2) short and shielded with GND vias
- Keep 12MHz crystal traces (Y1) short and shielded with GND vias
- RP2354A decoupling and internal regulator parts must follow Raspberry Pi RP2350 layout guidance
- TP4056 PROG resistor (R3) must be within 10mm of the PROG pin

---

## JLCPCB Order Instructions

### Gerber export

1. **File → Fabrication Outputs → Gerbers (.gbr)**
2. Select layers: F.Cu, B.Cu, F.SilkS, B.SilkS, F.Mask, B.Mask, Edge.Cuts
3. **Fabrication Outputs → Drill Files (.drl)**

### JLCPCB order settings

| Setting | Value |
|---|---|
| Layers | 2 |
| PCB thickness | 1.6mm |
| Surface finish | ENIG (required for fine-pitch QFN/LQFP pads) |
| Copper weight | 1oz |
| Min hole size | 0.3mm |
| Solder mask | Green (or your preference) |

### SMT assembly

Upload `jlcpcb-bom.csv` and the Pick & Place file (generated from KiCad):  
**Fabrication Outputs → Component Placement (.pos)**

The BOM uses LCSC part numbers. All extended parts incur a one-time $3 setup fee per unique part number (at time of writing). The design uses:

- **Basic parts**: passives, connectors, charger, regulator, switches, crystals, level shifter
- **Extended parts**: RP2354A (C41378174), W5500 (C32646), USB4125-GF-A (C165948), HR911105A (C12074)

The RP2354A uses the QFN-60 7mm × 7mm footprint.

---

## Firmware

The RP2354A targets RP2350-compatible firmware using:

- [pico-sdk](https://github.com/raspberrypi/pico-sdk)
- [Ethernet library for Raspberry Pi Pico-class boards + W5500](https://github.com/earlephilhower/arduino-pico) when the selected release supports RP2350
- [MicroPython + W5500 nic driver](https://micropython.org) using an RP2350 build

ArtNet reception via W5500: UDP port 6454, standard ArtDMX packets.

LED protocol via PIO: RP2354A PIO state machines on GPIO0–3 for parallel WS2812B output (800kHz, single-wire).

Programming: hold SW4 BOOTSEL while pressing/releasing SW3 RESET. The RP2354A appears as a USB boot device. SWD debug via J10.

---

## Schematic Regeneration

All design files are generated by Python scripts. To regenerate:

```bash
python3 gen_project.py   # .kicad_pro
python3 gen_schematic.py # .kicad_sch  
python3 gen_pcb.py       # .kicad_pcb (component placement)
python3 gen_bom.py       # jlcpcb-bom.csv
```

---

## Design Notes

- **Integrated flash**: RP2354A contains the 2MB boot flash in-package, so U2/W25Q16JV and its QSPI routing were removed.
- **QSPI_SS / USB_BOOT**: Connected to SW4 BOOTSEL through R24 (1k). The remaining QSPI pads are left unconnected externally because they are shared with the internal flash die.
- **W5500 VDD pin**: The W5500 generates its own 1.2V core from AVDD internally. The VDD pin is an output — connect only a 100nF bypass cap (C4).
- **RP2354A core regulator**: Uses L2 (3.3µH) and C7/C9/C10 on the internal 1.1V rail, with R23/C8 filtering VREG_AVDD.
- **TP4056 TE pin**: Tied high (to VCC) to disable the safety timer — suitable when charging from USB-C which provides reliable 5V.
- **MT3608 current limit**: The 22µH inductor (L1) supports up to 2A peak. At 3.7V→5.1V the duty cycle is ~27%, continuous current ~600mA safely.
