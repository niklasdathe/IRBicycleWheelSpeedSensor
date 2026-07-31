# Development workflow

## Rule: change the owner, not a consumer

| Concern | Authoritative input | Generated or checked consumers |
|---|---|---|
| Timing, optical, analog and power values | `config/system.json` | C headers, SPICE parameters, Python/UI defaults |
| Pins and nets | `hardware/connectivity.json` | KiCad audit and SPICE connectivity include |
| Parts and fields | `hardware/component_catalog.json` | schematic/PCB fields, BOM, footprint and Konnect data |
| Requirements | `requirements/requirements.yaml` | verification matrix and tests |
| Manual CAD state | live KiCad files | captured layout templates and hashes |

Never edit a generated consumer to override its source.

## Parameter change

1. Edit `config/system.json`.
2. Run `py -3.14 tools/generate_constants.py`.
3. Exercise the value in the local simulator.
4. Add or update a requirement/test if acceptance behavior changed.
5. Run `tests/run_all.ps1`.

The runtime carrier remains validated from 25-50 kHz. The generated header
provides compile-time defaults and limits; it does not replace runtime
validation.

## Firmware boundaries

`firmware/components/ir_spoke_core` is portable C99 with caller-owned state and
no heap, RTOS or ESP-IDF dependency:

| Module | Interface responsibility |
|---|---|
| `ir_spoke_config` | Validate runtime carrier and detector configuration |
| `ir_spoke_geometry` | Convert wheel geometry and speed to timing |
| `ir_spoke_detector` | Qualify blockage widths and track link state |
| `ir_spoke_pattern` | Infer count/confidence and adapt the interval LUT |
| `ir_spoke_pipeline` | Compose detector and learner without hardware access |
| `ir_spoke_can` | Encode fixed telemetry independently of transport |

`firmware/main` owns ESP-IDF RMT and optional MCP2515/SPI integration. Hardware
callbacks translate peripheral events into the portable interfaces; portable
modules do not call ESP-IDF.

## Connectivity change

1. Edit `hardware/connectivity.json`.
2. Update the schematic/PCB manually if the physical design changes.
3. Run `py -3.14 tools/generate_connectivity.py`.
4. Run `py -3.14 tools/validate_kicad_netlist.py`.
5. Run the full suite.

Simulation refuses to start when its topology hash is stale. The native KiCad
netlist, PCB pad nets and generated SPICE topology must all match.

## CAD change

The route is user-authored and protected. Generators may restore it but must
never route.

1. Open through `Open-IR-Spoke-Sensor.cmd`.
2. Make the manual schematic, placement or routing edit.
3. Save and close every KiCad editor.
4. Run:

   ```powershell
   py -3.14 hardware\ir_spoke_link\capture_layout.py
   ```

5. Review the PDF/PCB visually and run the complete suite.

6. Regenerate the README image from the captured board:

   ```powershell
   py -3.14 tools\readme_pcb_render.py --generate
   ```

`layout_manifest.json` records schematic, PCB, logical routing, raw route text,
preferences, rotations, DRC requirements and endpoint count. A component move
does not authorize automated rerouting.

The render manifest beside the PNG records both the PCB and image hashes. CI
fails when the README still shows an older captured PCB.

## Acceptance checklist

- [ ] The authoritative source changed.
- [ ] Generated files were regenerated, not manually patched.
- [ ] Relevant requirement and test still express the intended behavior.
- [ ] `tests/run_all.ps1` passes.
- [ ] CAD hashes changed only when an intentional manual CAD edit occurred.
- [ ] Physical claims remain marked unverified until measured.
- [ ] Manufacturing changes pass the [manufacturing checklist](manufacturing.md).

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the concise repository policy.
