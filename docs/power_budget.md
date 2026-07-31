# Power budget

## Modeled 3.3 V rail

| Load | Default scenario |
|---|---:|
| ESP32-S3 + XIAO board, averaged | 60.35 mA |
| IR LED, 45.02 mA peak at 50% duty | 22.51 mA |
| S8050 base drive, 2.50 mA peak at 50% duty | 1.25 mA |
| TLV9062, TLV7011 and VREF divider | 1.246 mA |
| Optional XIAO CAN board | 0 mA (disabled by default) |
| Total steady average | 85.36 mA |
| Total coincident peak estimate | 392.27 mA |
| 3.3 V steady power | 281.69 mW |
| Estimated regulator input at 90% efficiency | 312.99 mW |

The ESP32 scenario uses the datasheet's 42.3 mA WAITI and 54.6 mA
single-core values at 160 MHz, a configurable 10% CPU-active fraction, and a
configurable 5% Wi-Fi TX fraction. The peak aligns the 340 mA 802.11b/21 dBm
case with LED, base, AFE, VREF and local-bypass startup currents.

The estimated peak is 78.5% of Espressif's 500 mA minimum recommended supply
capacity and 56.0% of Seeed's stated 700 mA XIAO 3V3 output capacity. GPIO1
sources 2.5 mA peak, 6.25% of the ESP32-S3 datasheet's 40 mA typical source
test point. These comparisons pass for the modeled scenario.

## Optional official XIAO CAN expansion

The CAN option uses the board's MCP2515 and SN65HVD230. The conservative
enabled model includes 10 mA MCP2515 active current, 17 mA transceiver
recessive current, 8 mA board-LED allowance and an additional estimated
33 mA while driving a dominant, 60-ohm-terminated bus.

| CAN case | CAN load | System average | Coincident peak |
|---|---:|---:|---:|
| Enabled, 10% dominant duty | 38.3 mA average / 68 mA peak | 123.66 mA | 460.27 mA |
| Enabled, 100% dominant stress | 68 mA | 153.36 mA | 460.27 mA |

The stress peak uses 92.1% of the 500 mA ESP32-S3 supply recommendation and
65.8% of the stated 700 mA XIAO 3V3 capacity. It passes the configured limits,
but the 39.7 mA margin to 500 mA is small enough that the CAN+Wi-Fi+LED
coincident case must be measured before release.

## Transients and limits

`simulation/ir_spoke_sim.py` exposes `led_current_ma`,
`esp32_current_ma`, `afe_current_ma`, `can_current_ma`, `system_current_ma` and
`supply_voltage_v` and `system_power_mw`. It includes:

- carrier-cycle LED and transistor-base current;
- a centered Wi-Fi current burst;
- event-related CPU activity;
- 200 nF local bypass charging during the configured supply rise;
- VREF capacitor charging through the 10 kOhm divider;
- comparator/GPIO capacitive edge current.

The model does not claim the XIAO module's complete USB-plug-in inrush because
the onboard regulator, bulk capacitance, source impedance and cable are not
characterized here. Verify the assembled board with a current probe or shunt,
including Wi-Fi TX, cold power-up and worst supply cable, before release.

Primary values: `docs/datasheets/ESP32-S3_Datasheet.pdf`,
`docs/datasheets/TLV9062.pdf`, `docs/datasheets/TLV7011.pdf`.
