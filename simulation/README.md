# Simulation

`ir_spoke_sim.py` is the linked system model. It reads
`../config/system.json`. The local API imports the model directly; command-line
runs write disposable evidence to `../build/simulation/`.

`ir_spoke_link.cir` is the ngspice/KiCad-compatible circuit model. It includes
the remote LED and cable resistance, VEMD10940FX01 photocurrent/capacitance,
TLV9062 finite-bandwidth TIA and active band-pass, TLV7011 hysteretic
comparator, ESP32 load, optional XIAO CAN load and input network. Its physical nets are generated from
`hardware/connectivity.json`. Both batch and local simulations fail when the
generated topology hash is stale.

The fast TLV9062 model in `models/TLV9062_typ_ngspice.lib` uses the
datasheet-typical 100 dB open-loop gain, 10 MHz GBW and 40 mV light-load output
headroom. TI's original PSpice Rev. E ZIP is retained for short sign-off
cases; its switch-heavy model is intentionally not used for the interactive
wheel transient.
`validate_ngspice.py` runs the complete circuit and bounds TIA, band-pass,
blockage-demodulation and current results against the Python reference.

`local_server.py` serves `http://127.0.0.1:8765/`. The HTML contains no
second electrical model: `/api/simulate` calls `ir_spoke_sim.simulate()`
directly. Every window is phase-aligned to contain a complete spoke blockage.
Reset reloads `config/system.json`; code export runs the same transient and
returns a C header containing the selected RMT and adaptive-map values.

Current/power traces separate LED, ESP32, AFE and optional CAN loads and include carrier
edges, a Wi-Fi TX burst, configurable CPU activity, VREF startup and local
decoupling inrush. The local UI exposes CAN enable and dominant-bus duty and
uses the same values when generating the experiment header. See
`docs/power_budget.md` for assumptions and limitations.

Run:

```powershell
py -3.14 simulation/ir_spoke_sim.py
py -3.14 simulation/validate_ngspice.py
py -3.14 tools/validate_kicad_netlist.py
py -3.14 simulation/local_server.py
```

The numerical noise source combines ambient/dark-current shot noise, TIA
feedback-resistor Johnson noise, op-amp current noise, an input-referred
approximation of op-amp voltage noise, and the separately adjustable
environmental interference term. The model has no proprietary integrated
receiver behavior. Beam profile, contamination, sunlight spectra and
mechanical alignment still require prototype tests before release.
