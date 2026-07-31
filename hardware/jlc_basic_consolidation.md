# JLCPCB part-class and consolidation audit

Checked 2026-07-28 against the JLCPCB Parts API snapshot in
`hardware/jlcpcb_parts_snapshot.json`.

| Group | Result |
|---|---|
| Basic retained | Q1; R2, R3, R4, R5, R7, R9, R10, R11; C1, C3, C5, C6 |
| Extended retained for analog value/dielectric | R6 16 kOhm, R8 560 kOhm, C2 120 pF C0G, C4 4.7 pF C0G |
| Extended retained for electrical/optical behavior | D1, D2, U1, U2 |
| Extended retained for mechanics | J3 and J4, consolidated to one identical JST-GH part |
| Extended retained for LED current | R1 39 Ohm; no exact in-stock Basic result was returned |

The active devices are model inputs, not generic placeholders. Replacing
TLV9062, TLV7011, VEMD10940FX01 or VSMB1940X01 requires a new
datasheet-value extraction, tolerance sweep, transient simulation and optical
alignment review. J3/J4 and their cable parts are already consolidated.

The current placed panel has 24 placements in 20 grouped BOM rows. Common
passives and Q1 are Basic. Header sockets, M2.5 holes and test pads are DNI.
