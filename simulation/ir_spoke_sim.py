#!/usr/bin/env python3
"""Numerical, component-valued model of the custom IR analog front end.

The model deliberately exposes every stage: optical flux, photodiode current,
TIA, active band-pass, Schmitt comparator and RMT carrier removal.  It shares
its only editable parameter source with firmware and SPICE: config/system.json.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "system.json").read_text(encoding="utf-8"))


def rc_lowpass(x: np.ndarray, dt: float, tau: float, initial: float = 0.0) -> np.ndarray:
    alpha = dt / (tau + dt)
    y = np.empty_like(x)
    acc = initial
    for i, value in enumerate(x):
        acc += alpha * (value - acc)
        y[i] = acc
    return y


def rc_highpass(x: np.ndarray, dt: float, tau: float) -> np.ndarray:
    baseline = rc_lowpass(x, dt, tau, float(x[0]))
    return x - baseline


def rmt_carrier_remove(digital_carrier: np.ndarray, sample_rate_hz: int, hold_us: float) -> np.ndarray:
    """Retriggerable hardware-demodulator approximation.

    Each comparator transition representing carrier energy extends the clear
    state. Missing carrier for hold_us becomes a spoke blockage.
    """
    hold_samples = max(1, round(hold_us * 1e-6 * sample_rate_hz))
    out = np.zeros(digital_carrier.size, dtype=np.uint8)
    countdown = 0
    previous = int(digital_carrier[0])
    for i, value in enumerate(digital_carrier):
        current = int(value)
        if current != previous:
            countdown = hold_samples
        elif countdown:
            countdown -= 1
        out[i] = 1 if countdown else 0
        previous = current
    return out


def simulate(duration_s: float = 0.024, sample_rate_hz: int = 2_000_000) -> dict:
    wheel = CFG["wheel"]
    optical = CFG["optical"]
    afe = CFG["analog_frontend"]
    tx = CFG["transmitter"]
    esp = CFG["esp32"]

    speed_mps = wheel["max_speed_kmh"] / 3.6
    circumference = math.pi * wheel["effective_diameter_m"]
    wheel_hz = speed_mps / circumference
    omega = 2 * math.pi * wheel_hz
    spoke_hz = wheel_hz * wheel["spoke_count_design"]
    tangential_speed = omega * wheel["beam_radius_m"]
    blocked_s = (wheel["spoke_width_mm"] / 1000) / tangential_speed
    spoke_period_s = 1 / spoke_hz
    clear_s = spoke_period_s - blocked_s

    dt = 1 / sample_rate_hz
    t = np.arange(0, duration_s, dt)
    phase_carrier = np.mod(t * optical["carrier_hz"], 1.0)
    carrier = (phase_carrier < optical["carrier_duty"]).astype(float)

    spoke_phase = np.mod(t + 0.15 * spoke_period_s, spoke_period_s)
    transmission = np.where(
        spoke_phase >= blocked_s, 1.0, wheel["residual_transmission_blocked"]
    )

    led_ma = (
        tx["supply_v"] - tx["led_vf_v_typ"] - tx["driver_vce_sat_v_typ"]
    ) / tx["led_series_ohm"] * 1000
    intensity_w_sr = (
        optical["emitter_radiant_intensity_mw_sr_at_100ma_typ"]
        * 1e-3
        * led_ma
        / 100
    )
    distance_m = optical["emitter_receiver_distance_mm"] * 1e-3
    irradiance_w_m2 = (
        intensity_w_sr
        / distance_m**2
        * optical["alignment_factor_nominal"]
    )
    signal_photo_a = (
        irradiance_w_m2
        / 10.0
        * optical["photodiode_reverse_light_current_ua_at_10wm2_typ"]
        * 1e-6
    )

    rng = np.random.default_rng(0xB1C1E)
    noise_a = rng.normal(
        0.0, optical["signal_noise_rms_ua"] * 1e-6, t.size
    )
    photo_current_a = (
        optical["ambient_photocurrent_ua"] * 1e-6
        + signal_photo_a * carrier * transmission
        + noise_a
    )

    # TIA small-signal response. DC ambient is retained to verify output
    # headroom; the following AC coupling removes it before high gain.
    tia_tau = afe["tia_feedback_ohm"] * afe["tia_feedback_pf"] * 1e-12
    tia_delta_v = -rc_lowpass(
        photo_current_a * afe["tia_feedback_ohm"], dt, tia_tau
    )
    tia_v = afe["vref_v"] + tia_delta_v

    hp_tau = afe["ac_bias_ohm"] * afe["ac_coupling_nf"] * 1e-9
    ac_v = rc_highpass(tia_v, dt, hp_tau)
    gain = 1 + afe["gain_feedback_ohm"] / afe["gain_ground_ohm"]
    gain_tau = afe["gain_feedback_ohm"] * afe["gain_feedback_pf"] * 1e-12
    bandpass_v = afe["vref_v"] + rc_lowpass(ac_v * gain, dt, gain_tau)
    bandpass_v = np.clip(bandpass_v, 0.04, afe["supply_v"] - 0.04)

    # Explicit external feedback plus the comparator's specified typical
    # internal hysteresis. The threshold changes with the output state.
    comparator = np.zeros(t.size, dtype=np.uint8)
    state = 0
    r_input = afe["comparator_input_ohm"]
    r_feedback = afe["comparator_feedback_ohm"]
    hysteresis_v = (
        afe["supply_v"] * r_input / (r_input + r_feedback)
        + afe["comparator_internal_hysteresis_mv_typ"] * 1e-3
    )
    threshold_trace = np.empty_like(t)
    for i, signal_v in enumerate(bandpass_v):
        threshold = afe["vref_v"] + (-0.5 if state else 0.5) * hysteresis_v
        if state == 0 and signal_v > threshold:
            state = 1
        elif state == 1 and signal_v < threshold:
            state = 0
        comparator[i] = state
        threshold_trace[i] = threshold

    demod_hold_us = 1e6 / esp["rx_demod_frequency_hz"]
    clear_digital = rmt_carrier_remove(comparator, sample_rate_hz, demod_hold_us)
    blocked_digital = 1 - clear_digital

    tia_pole_hz = 1 / (2 * math.pi * tia_tau)
    hp_hz = 1 / (2 * math.pi * hp_tau)
    gain_lp_hz = 1 / (2 * math.pi * gain_tau)
    comparator_hyst_mv = (
        hysteresis_v * 1000
    )

    stride = max(1, sample_rate_hz // 200_000)
    sl = slice(None, None, stride)
    traces = {
        "time_ms": np.round(t[sl] * 1000, 6).tolist(),
        "carrier": carrier[sl].astype(int).tolist(),
        "transmission": np.round(transmission[sl], 4).tolist(),
        "photodiode_ua": np.round(photo_current_a[sl] * 1e6, 5).tolist(),
        "tia_v": np.round(tia_v[sl], 5).tolist(),
        "bandpass_v": np.round(bandpass_v[sl], 5).tolist(),
        "threshold_v": np.round(threshold_trace[sl], 5).tolist(),
        "comparator": comparator[sl].astype(int).tolist(),
        "digital_active_low": (1 - blocked_digital[sl]).astype(int).tolist(),
        "blocked_digital": blocked_digital[sl].astype(int).tolist(),
    }
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
            "led_current_ma_calculated": led_ma,
            "carrier_cycles_per_blockage": blocked_s * optical["carrier_hz"],
            "irradiance_w_m2_nominal": irradiance_w_m2,
            "signal_photocurrent_ua_nominal": signal_photo_a * 1e6,
            "tia_pole_hz": tia_pole_hz,
            "bandpass_highpass_hz": hp_hz,
            "bandpass_lowpass_hz": gain_lp_hz,
            "bandpass_peak_to_peak_v": float(np.ptp(bandpass_v)),
            "comparator_hysteresis_mv_typ": comparator_hyst_mv,
            "tia_min_v": float(np.min(tia_v)),
            "tia_max_v": float(np.max(tia_v)),
            "detected_blocked_fraction": float(np.mean(blocked_digital)),
            "speed_margin_to_stress": wheel["stress_speed_kmh"] / wheel["max_speed_kmh"],
        },
        "traces": traces,
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
        writer.writerow(traces)
        writer.writerows(zip(*(traces[name] for name in traces)))
    print(json.dumps(result["derived"], indent=2))


if __name__ == "__main__":
    main()
