# Simulation

`ir_spoke_sim.py` is the linked system model. It reads
`../config/system.json` and writes the exact dataset consumed by the HTML
visualization to `../public/simulation.json`.

`ir_spoke_link.cir` is the ngspice/KiCad-compatible behavioral circuit model.
It includes the LED current path, spoke transmission mask, a narrow-band
receiver approximation, envelope detector, hysteretic active-low output and
the ESP32 input network.

Run:

```powershell
python simulation/ir_spoke_sim.py
ngspice simulation/ir_spoke_link.cir
```

The integrated Vishay receiver contains proprietary AGC and demodulator
details. The model therefore uses datasheet-level timing and a conservative
envelope/hysteresis approximation. Prototype testing in direct sun remains a
required design gate.
