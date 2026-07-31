# Open validation gates

- [ ] Select and add explicit hardware, software and documentation licenses
  before describing the repository as reusable open-source hardware.
- [ ] Resolve the three KiCad ERC `lib_symbol_mismatch` warnings by updating
  the embedded TLV9062 units from the KiCad 10 library without changing pins,
  nets or schematic layout.
- [ ] Compile and hardware-in-loop test the RMT and MCP2515 adapters with the
  selected ESP-IDF release.
- [ ] Stack the official XIAO CAN expansion with the intended headers; verify
  clearance and 500 kbit/s traffic on a terminated bus.
- [ ] Resolve the two optional PCB presentation items after the next manual
  routing edit: Edge.Cuts dimension-text placement and backside CMP/TP2
  silkscreen overlap.
- [ ] Measure photocurrent, noise and detection margin across sunlight,
  alignment, vibration, dirt, water, minimum/default/maximum carrier and
  distance; update `config/system.json`.
- [ ] Correlate TP2–TP8 bench waveforms with Python and ngspice.
- [ ] Measure cold-start, Wi-Fi TX and coincident Wi-Fi/LED/CAN rail current
  and droop; update source impedance and inrush parameters.
- [ ] Re-run simulation and compile firmware with the measured parameter set.
- [ ] Review the R4 Gerber/BOM/CPL in JLCPCB, obtain DFM approval for the
  conductive mouse-bite tab and confirm all assembly rotations visually.
