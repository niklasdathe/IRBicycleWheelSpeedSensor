# Manufacturing

## Current release candidate

| Field | Value |
|---|---|
| Product/revision | IR Spoke Sensor R4 |
| Layers | 2 |
| Material | FR-4 |
| Thickness | 1.6 mm |
| Copper | 1 oz |
| Panel size | 21 x 37.9 mm |
| Receiver finished size | 17.8 x 21.4 mm |
| Emitter finished size | 21 x 15 mm |
| Separation | One 7.5 x 1.5 mm conductive mouse-bite tab |
| Assembly side | Top |

The tab intentionally carries `3V3` and `LED_K` for pre-snap testing. Snapping
severs both traces. The two boards then reconnect through J3/J4 and the JST-GH
harness.

## Generate the JLC package

```powershell
powershell -ExecutionPolicy Bypass -File hardware\export_jlc.ps1 -Revision R4
```

The export is fail-closed: captured-layout restoration and footprint audit run
first, and no manufacturing files are accepted unless DRC reports 0 violations
and 0 unconnected pads.

Authoritative output:

`hardware/jlc_export/IR_Spoke_Sensor_R4_2L/`

| Upload/review artifact | File |
|---|---|
| PCB fabrication | `IR_Spoke_Sensor_R4_2L_GERBER.zip` |
| BOM + CPL + order metadata | `IR_Spoke_Sensor_R4_2L_PCBA.zip` |
| Bill of materials | `IR_Spoke_Sensor_R4_2L_BOM.csv` |
| Component placement | `IR_Spoke_Sensor_R4_2L_CPL.csv` |
| Order parameters | `IR_Spoke_Sensor_R4_2L_ORDER.json` |
| DRC evidence | `IR_Spoke_Sensor_R4_2L_DRC.rpt` |
| Non-production courtyard reference | `IR_Spoke_Sensor_R4_2L_COURTYARD_REFERENCE.zip` |
| Interactive placement guide | [`docs/interactive_bom.html`](interactive_bom.html) |

Do not upload the courtyard reference archive as production Gerbers.

## Assembly conventions

KiCad physical orientation and JLC placement rotation are separate. R4 applies
CPL-only offsets without rotating footprints or changing tracks:

| Ref | Physical KiCad | CPL offset | Final JLC rotation |
|---|---:|---:|---:|
| U1 | 0° | 90° | 90° |
| U2 | 270° | 90° | 0° |
| J3 | 0° | 180° | 180° |
| J4 | 180° | 180° | 0° |
| D1 IR emitter | 0° | 180° | 180° |
| D2 photodiode | 0° | 0° | 0° |

The detailed polarity evidence is in
[JLC diode orientation](jlc_diode_orientation.md). Automated offsets do not
prove the third-party preview renderer; inspect the preview.

## JLC review checklist

- [ ] Upload the R4 Gerber archive and confirm a two-layer 1.6 mm board.
- [ ] Confirm the overall outline and four rounded corners on each finished
      board.
- [ ] Confirm the mouse-bite tab is a single breakaway and no V-groove exists.
- [ ] Request engineering review of the two intentional routed tab traces.
- [ ] Confirm both M2.5 emitter holes are excluded from assembly.
- [ ] Upload BOM/CPL and resolve every reference without substitutions.
- [ ] Visually verify D1/D2 polarity and U1/U2/J3/J4 orientation.
- [ ] Confirm J3/J4 are low side-entry JST-GH parts over their board cutouts.
- [ ] Keep front/back courtyards out of production layers.
- [ ] Record JLC DFM approval and preview screenshots as release evidence.

## Procurement and Konnect

`hardware/component_catalog.json` is the canonical part table.
`hardware/ir_spoke_link/bom_jlcpcb.csv` feeds the scoped Konnect SQLite cache
and the JLC export. Basic/extended classification and consolidation notes are
in [JLC basic-part review](../hardware/jlc_basic_consolidation.md).

For Konnect configuration and database limits, use
[Konnect and JLCPCB](konnect_jlcpcb.md).

## Release gate

R4 is ready for a manufacturer preview, not for an unreviewed production
order. Manual JLC preview approval, DFM approval of the conductive tab and the
physical tests in [Bring-up and test](bringup.md) remain open.
