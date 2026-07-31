# Debug nodes and threshold policy

| Test point | Net | Correlated transient | Use |
|---|---|---|---|
| TP1 | GND | reference | probe ground |
| TP2 | +3V3 | supply/current setup | rail droop and startup |
| TP3 | VREF | threshold reference | 1.65 V startup/noise |
| TP4 | TX_CARRIER_GPIO1 | `carrier` | RMT TX and base drive |
| TP5 | TIA_OUT | `tia_v` | ambient headroom and optical current |
| TP6 | BANDPASS | `bandpass_v` | carrier amplitude and filter response |
| TP7 | COMP_OUT | `comparator` | analog decision |
| TP8 | RX_RMT_GPIO2 | RMT input | GPIO isolation and hardware demodulation input |

The 1 mm pads are on the main PCB underside and excluded from BOM and
placement output. Do not probe `PD_ANODE`: ordinary probe capacitance changes
the TIA noise gain and bandwidth. Use a short ground spring at TP5/TP6.

## Potentiometer decision

A threshold potentiometer is not fitted. Distance changes the AC carrier
amplitude; shifting the comparator center away from VREF does not directly
correct that amplitude and reduces asymmetric headroom. A trimmer also adds
area, vibration sensitivity, contact drift and manual calibration, conflicting
with continuous adaptive operation.

The installed 10 kOhm input / 1 MOhm feedback network produces approximately
37.2 mV total typical hysteresis including TLV7011 internal hysteresis. Bench
work should first measure TP5 and TP6 across distance, sunlight and alignment.
If decision margin is insufficient, change fixed gain/hysteresis values and
regenerate simulation/firmware. An optional DNP trimmer footprint should only
be added after those measurements show a need; it is not a production control.

The VEMD10940FX01 has an optical daylight-blocking filter matched to
830-950 nm emitters. It is not a sunlight eliminator: sunlight still contains
940 nm energy. Reverse bias preserves speed; TIA headroom handles DC ambient,
the AC band-pass rejects DC/slow changes, and carrier-loss timing supplies the
remaining discrimination. Direct-sun testing remains mandatory.

