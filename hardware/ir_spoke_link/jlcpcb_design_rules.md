# JLCPCB manufacturing profile

Conservative 2-layer, 1 oz rules used by this project:

- Track width / clearance: 0.15 / 0.15 mm (fab minimum is 0.10 / 0.10 mm).
- Signal vias: 0.60 mm diameter, 0.30 mm drill.
- Via-to-track: 0.25 mm (fab minimum 0.20 mm).
- Different-net SMD pad clearance: 0.20 mm (fab minimum 0.15 mm).
- Copper-to-board-edge: 0.30 mm.
- Minimum component body-to-edge target: 2.5 mm where the XIAO carrier
  geometry allows; the optical edge-facing parts require explicit DFM review.
- 0402 is the smallest passive footprint used. 0603 is used for the LED current
  resistor to retain pulse-power margin.
- IPC-7351 medium-density courtyards; no via-in-pad.
- Exactly two copper layers, 1.6 mm FR-4 and 1 oz outer copper are encoded in
  the R4 order definition.
- The receiver is 17.8 x 21.4 mm; the transmitter is 21 x 15 mm. Both have
  four 1.905 mm-radius corners.
- One 7.5 x 1.5 mm routed tab joins the boards. Five 0.5 mm NPTH drills at
  1.5 mm pitch form the break line. Two 0.25 mm temporary links cross between
  the drills and are intentionally severed when the tab is snapped.
- The combined customer board is 21 x 37.9 mm and requires online DFM review
  of the mouse-bite tab before ordering.
- BOM, CPL, Gerber job, copper, mask, silkscreen, outline and drill files are
  included by the versioned `IR_Spoke_Sensor_R4_2L` export workflow.

Sources are recorded in `docs/sources.md`. Always re-run JLCPCB online DFM and
re-check live component stock immediately before ordering.
