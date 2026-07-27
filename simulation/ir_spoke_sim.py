#!/usr/bin/env python3
"""Linked numerical model for the IR spoke link.

The script reads config/system.json and emits public/simulation.json plus CSV
data used by the web visualizer. It intentionally models the optical channel
and the receiver's band-pass/envelope/hysteresis behavior, not proprietary
internals of the selected Vishay receiver.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "system.json").read_text(encoding="utf-8"))


def simulate(duration_s: float = 0.024, sample_rate_hz: int = 1_000_000) -> dict:
    wheel = CFG["wheel"]
    optical = CFG["optical"]
    electrical = CFG["electrical"]

    speed_mps = wheel["max_speed_kmh"] / 3.6
    circumference = math.pi * wheel["effective_diameter_m"]
    wheel_hz = speed_mps / circumference
    omega = 2 * math.pi * wheel_hz
    spoke_hz = wheel_hz * wheel["spoke_count"]
    tangential_speed = omega * wheel["beam_radius_m"]
    blocked_s = (wheel["spoke_width_mm"] / 1000) / tangential_speed
    spoke_period_s = 1 / spoke_hz
    clear_s = spoke_period_s - blocked_s

    dt = 1 / sample_rate_hz
    t = np.arange(0, duration_s, dt)
    raw_carrier = (np.sin(2 * np.pi * optical["carrier_hz"] * t) >= 0).astype(float)
    burst_on_s = optical["burst_cycles"] / optical["carrier_hz"]
    burst_period_s = burst_on_s + optical["burst_gap_us"] * 1e-6
    burst_gate = (np.mod(t, burst_period_s) < burst_on_s).astype(float)
    carrier = raw_carrier * burst_gate

    phase = np.mod(t + 0.15 * spoke_period_s, spoke_period_s)
    clear = phase >= blocked_s
    transmission = np.where(
        clear, 1.0, wheel["residual_transmission_blocked"]
    )

    rng = np.random.default_rng(0xB1C1E)
    noise = rng.normal(0.0, optical["noise_rms_normalized"], t.size)
    optical_rx = (
        transmission * carrier
        + optical["ambient_normalized"]
        + noise
    )

    # Synchronous magnitude extraction approximates the integrated 38 kHz
    # receiver's narrow band-pass and rejects DC ambient light.
    mixed = (optical_rx - optical["ambient_normalized"]) * (2 * raw_carrier - 1)
    tau = optical["envelope_tau_us"] * 1e-6
    alpha = dt / (tau + dt)
    envelope = np.empty_like(mixed)
    acc = 0.0
    for idx, value in enumerate(np.abs(mixed)):
        acc += alpha * (value - acc)
        envelope[idx] = acc

    digital = np.empty_like(envelope, dtype=np.uint8)
    detected = False
    for idx, value in enumerate(envelope):
        if not detected and value >= optical["receiver_threshold_on"]:
            detected = True
        elif detected and value <= optical["receiver_threshold_off"]:
            detected = False
        digital[idx] = 0 if detected else 1  # receiver output is active-low

    led_current_ma = (
        electrical["supply_v"]
        - electrical["led_vf_v"]
        - electrical["driver_vce_sat_v"]
    ) / electrical["led_series_ohm"] * 1000

    # Downsample only for browser payload. Preserve transition points by
    # sampling at 5 us, still resolving the 38 kHz carrier.
    stride = max(1, sample_rate_hz // 200_000)
    sl = slice(None, None, stride)
    traces = {
        "time_ms": np.round(t[sl] * 1000, 6).tolist(),
        "carrier": carrier[sl].astype(int).tolist(),
        "transmission": np.round(transmission[sl], 4).tolist(),
        "optical_rx": np.round(optical_rx[sl], 4).tolist(),
        "envelope": np.round(envelope[sl], 4).tolist(),
        "digital_active_low": digital[sl].astype(int).tolist()
    }

    high_fraction = float(np.mean(digital))
    return {
        "config": CFG,
        "derived": {
            "circumference_m": circumference,
            "wheel_hz": wheel_hz,
            "wheel_rpm": wheel_hz * 60,
            "spoke_event_hz": spoke_hz,
            "blocked_us": blocked_s * 1e6,
            "clear_us": clear_s * 1e6,
            "blocked_fraction": blocked_s / spoke_period_s,
            "led_current_ma_calculated": led_current_ma,
            "digital_high_fraction": high_fraction,
            "carrier_cycles_per_blockage": blocked_s * optical["carrier_hz"],
            "burst_on_us": burst_on_s * 1e6,
            "burst_period_us": burst_period_s * 1e6,
            "speed_margin_to_stress": wheel["stress_speed_kmh"] / wheel["max_speed_kmh"]
        },
        "traces": traces
    }


def main() -> None:
    result = simulate()
    public = ROOT / "public"
    output = ROOT / "simulation" / "output"
    public.mkdir(exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(result, indent=2)
    (public / "simulation.json").write_text(payload, encoding="utf-8")
    (output / "simulation.json").write_text(payload, encoding="utf-8")

    traces = result["traces"]
    with (output / "waveforms.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        names = list(traces)
        writer.writerow(names)
        writer.writerows(zip(*(traces[name] for name in names)))

    summary = result["derived"]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
