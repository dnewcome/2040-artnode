# Changes

## RP2354A Redesign

- Replaced the original `RP2040` MCU with `RP2354A` on U1.
- Updated U1 to use `QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm`.
- Removed the external `W25Q16JVSSIQ` / U2 boot flash from the schematic, PCB placement, BOM, and documentation.
- Updated the BOM to use `RP2354A` as JLCPCB/LCSC part `C41378174`.
- Added RP2354A internal core regulator support:
  - `L2` 3.3uH inductor
  - `C7`, `C9`, `C10` 4.7uF capacitors on the 1.1V core rail
  - `R23` / `C8` VREG_AVDD filter
- Added a dedicated `SW4` BOOTSEL button.
- Added `R24` 1k in series between `QSPI_SS` / `USB_BOOT` and the BOOTSEL switch, following Raspberry Pi RP2350 hardware guidance.
- Left the remaining QSPI pads unconnected externally because RP2354A includes 2MB flash-in-package.
- Fixed the generator output paths to use the local script directory instead of the previous hard-coded `/Users/...` path.
- Fixed generated KiCad file compatibility:
  - Replaced invalid schematic pin type `bidir` with KiCad's `bidirectional`.
  - Replaced bare schematic `hide` flags with `(hide yes)`.
  - Removed the generated PCB semicolon comment that KiCad 9 refused to parse.
  - Removed the generated PCB inline `net_settings` block that KiCad 9 refused to load.
- Fixed generated PCB footprint visibility:
  - The PCB generator now embeds full KiCad library footprint geometry instead of empty footprint shells.
  - The generated board now contains real pads and footprint drawing primitives.
  - Updated unavailable/less-specific footprint names to available KiCad library footprints:
    - `J1`: `Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal`
    - `J2`: `Connector_RJ:RJ45_Hanrun_HR911105A_Horizontal`
    - `SW1`-`SW4`: `Button_Switch_SMD:SW_Push_1P1T_NO_CK_KSC7xxJ`
  - Stripped KiCad-9-only footprint metadata from embedded footprint bodies for better compatibility with the KiCad 7-era project format.
- Added the missing schematic representation for existing `D1` so schematic, PCB, and BOM references agree.
- Regenerated:
  - `artnet-led-controller/artnet-led-controller.kicad_sch`
  - `artnet-led-controller/artnet-led-controller.kicad_pcb`
  - `artnet-led-controller/jlcpcb-bom.csv`
  - `artnet-led-controller/artnet-led-controller.kicad_pro`

## Documentation

- Updated the root `README.md` for the RP2354A design.
- Updated `artnet-led-controller/README.md` for:
  - RP2354A MCU and integrated flash
  - New BOOTSEL flow
  - Removed external flash
  - New RP2354A regulator parts
  - Updated JLCPCB extended parts list

## Verification

- Ran all generators successfully:
  - `python3 gen_schematic.py`
  - `python3 gen_pcb.py`
  - `python3 gen_bom.py`
  - `python3 gen_project.py`
- Checked schematic vs PCB reference designators:
  - No schematic references missing PCB footprints.
  - No PCB references missing schematic symbols.
- Scanned for stale `RP2040`, `C2040`, `C97521`, `QSPI_SS_N`, `VREG_VOUT`, `TESTEN`, and `TBD` references.
  - Only one intentional README note remains, explaining that the old `W25Q16JV` flash was removed.
- Confirmed KiCad 9.0.3 can load the generated files:
  - `kicad-cli sch export netlist artnet-led-controller.kicad_sch -o /tmp/artnet-fixed.net`
  - `kicad-cli pcb export drill artnet-led-controller.kicad_pcb -o /tmp/artnet-drill-fixed`
- Confirmed the regenerated PCB contains visible footprint geometry:
  - 84 footprint blocks
  - 343 pads
  - 956 footprint drawing lines
- Ran KiCad CLI checks:
  - `kicad-cli sch erc artnet-led-controller.kicad_sch --format report -o /tmp/artnet-erc.rpt`
    - Completed and reported 337 ERC violations. The current generated schematic still has many off-grid/pin-not-connected/library warnings from the generator style.
  - `kicad-cli pcb drc artnet-led-controller.kicad_pcb --format report -o /tmp/artnet-drc.rpt`
    - Completed and reported 186 DRC violations with 0 unconnected items. The visible report entries are primarily silkscreen overlaps caused by dense generated placement and footprint reference text.
