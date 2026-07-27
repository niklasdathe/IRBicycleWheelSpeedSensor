# Simulation

`ir_spoke_sim.py` is the linked system model. It reads
`../config/system.json` and writes the exact dataset consumed by the HTML
visualization to `../public/simulation.json`.

`ir_spoke_link.cir` is the ngspice/KiCad-compatible circuit model. It includes
the remote LED and cable resistance, VEMD10940FX01 photocurrent/capacitance,
TLV9062 finite-bandwidth TIA and active band-pass, TLV7011 hysteretic
comparator and ESP32 input network.

Run:

```powershell
python simulation/ir_spoke_sim.py
ngspice simulation/ir_spoke_link.cir
```

The model has no proprietary integrated receiver behavior. Optical coupling
and sunlight/noise remain environmental assumptions and therefore require a
prototype test before the system can be treated as safety-related.
