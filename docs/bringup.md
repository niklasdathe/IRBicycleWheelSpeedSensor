# Bring-up and test

## Equipment

- current-limited 5 V USB supply with current logging;
- oscilloscope with short ground spring;
- optical fixture with adjustable emitter/receiver spacing and alignment;
- rotating wheel or controlled spoke target;
- sunlight or calibrated high-irradiance source;
- optional terminated CAN bus and official XIAO CAN expansion.

Do not probe the photodiode summing node `PD_ANODE`; probe capacitance changes
the TIA response.

## Testpoints

| TP | Net | Expected observation |
|---|---|---|
| TP1 | GND | probe reference |
| TP2 | +3V3 | startup and transient droop |
| TP3 | VREF | approximately 1.65 V after startup |
| TP4 | TX_CARRIER_GPIO1 | selected carrier, 50% duty |
| TP5 | TIA_OUT | photodiode current around VREF with headroom |
| TP6 | BANDPASS | AC carrier with DC/slow ambient removed |
| TP7 | COMP_OUT | restored digital carrier; quiet during blockage |
| TP8 | RX_RMT_GPIO2 | comparator signal after GPIO isolation |

## Sequence

### 1. Unpowered inspection

- Verify D1 anode/cathode and D2 photodiode polarity against the schematic and
  datasheets.
- Check the conductive tab, mouse bites, harness pin 1/2 continuity and absence
  of shorts.
- Confirm connector and XIAO header alignment before stacking.

### 2. Current-limited power-up

- Start without CAN and with a conservative current limit.
- Record cold-start, idle and carrier-on current.
- Verify TP2 and TP3 before enabling optical operation.
- Compare current and rail droop with the power traces in the local simulator.

### 3. Electrical signal correlation

- Set the default configuration.
- Capture TP4-TP8 in one acquisition with a complete blockage.
- Export the local-simulator waveform for the same carrier, speed, spoke width
  and distance.
- Compare frequency, duty, DC headroom, band-pass amplitude, hysteresis
  transitions and blockage width.
- Store measured deltas and update `config/system.json` only from repeatable
  data.

### 4. Optical margin

Sweep at least:

- 25 kHz, 38 kHz and 50 kHz;
- minimum, nominal and maximum mounting distance;
- alignment and vibration extremes;
- shade, direct sunlight and changing shadows;
- clean, dirty and wet optical surfaces;
- slow rotation through the 80 km/h stress condition.

For each point, record TP5/TP6 amplitude, false events, missed events and RMT
blockage-width margin.

### 5. Adaptive algorithm

- Run wheels or targets with different spoke counts across 16-48.
- Record inferred count, confidence convergence time and LUT residuals.
- Introduce bounded speed changes and individual interval irregularities.
- Verify continuous recovery after an outlier or temporary blockage.
- Document the expected ambiguity for a perfectly uniform spoke pattern.

### 6. Power and optional CAN

- Capture cold-start and Wi-Fi TX peak current.
- Repeat with coincident carrier, Wi-Fi and CPU activity.
- Stack the official CAN expansion, check D0/D1 versus D6-D10 pin separation,
  then repeat with a terminated 500 kbit/s bus and dominant traffic.
- Verify regulator temperature, 3.3 V droop and CAN error counters.

## Acceptance evidence

Record raw waveforms, configuration JSON, firmware revision, board revision,
fixture geometry, environmental condition and pass/fail result. Map each record
to the relevant test ID in
[the verification matrix](../requirements/verification_matrix.md).

The current open physical gates are maintained in [TODO.md](../TODO.md).
Successful bench correlation should replace assumptions in the model; it must
not merely be noted in prose.
