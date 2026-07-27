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

Sources are recorded in `docs/sources.md`. Always re-run JLCPCB online DFM and
re-check live component stock immediately before ordering.
