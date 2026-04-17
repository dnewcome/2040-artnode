# ArtNet LED Controller — Schematic & Layout Plan

## Goal
Produce a clean, readable multi-sheet KiCad schematic with netlist export,
then route a 4-layer PCB (F.Cu signal, In1.Cu VCC, In2.Cu GND, B.Cu signal).

## Current State
- Multi-sheet schematic generator (`gen_schematic.py`) produces:
  - Root sheet with 4 sub-sheet references
  - `power.kicad_sch` — USB-C, TP4056, MT3608, AMS1117, battery
  - `mcu.kicad_sch` — RP2354A, crystal, reset/boot, core regulator, decoupling
  - `ethernet.kicad_sch` — W5500, RJ45, crystal, bias resistors, pullups
  - `led_io.kicad_sch` — 74AHCT125, LED connectors, OLED, buttons, SWD
- `netlist.json` generated with 80 refs, 265 pin assignments
- KiCad project file created

## Next Steps

### 1. Validate schematic
- [ ] Open in KiCad 9, verify all sheets render correctly
- [ ] Run ERC via `kicad-cli sch erc` and fix any errors
- [ ] Cross-check netlist.json against original design

### 2. Evaluate Circuitron for PCB layout
Circuitron (https://github.com/Shaurya-Sethi/circuitron) is an agentic PCB
design accelerator that converts natural language → SKiDL → KiCad schematic + PCB.

**What it offers:**
- Multi-agent pipeline: planner → part finder → code gen → validation → ERC → output
- RAG-backed SKiDL code generation with KiCad library lookups
- Iterative error correction loop
- Outputs native KiCad `.kicad_pcb` files

**Requirements (heavy):**
- Python 3.10+, Docker
- OpenAI API key (with credits + org verification for reasoning models)
- Supabase account (RAG storage)
- Neo4j database (knowledge graph)
- Pydantic Logfire account

**Integration options:**
- A: Use Circuitron end-to-end — feed it our design requirements, let it generate
  schematic + PCB from scratch. Risk: may not match our existing component choices.
- B: Use Circuitron for layout only — feed it our existing netlist/schematic and
  let it handle placement + routing. More useful but may need adaptation.
- C: Cherry-pick ideas — borrow the SKiDL + Docker KiCad CLI validation loop
  without the full OpenAI agent stack. Could integrate with our existing generator.

### 3. PCB layout & routing
- [ ] Generate board outline + stackup
- [ ] Place components (group by functional block)
- [ ] Fill inner GND/VCC planes
- [ ] Route signals on F.Cu / B.Cu
- [ ] Run DRC via `kicad-cli pcb drc`
- [ ] Generate Gerbers for JLCPCB

## Tools
- KiCad 9 (schematic + PCB)
- `kicad-cli` (headless ERC, DRC, netlist/Gerber export)
- Freerouting CLI (signal autorouting with --skip-nets for power)
- Circuitron (evaluate for AI-assisted layout)
- gen_schematic.py (our multi-sheet generator)
