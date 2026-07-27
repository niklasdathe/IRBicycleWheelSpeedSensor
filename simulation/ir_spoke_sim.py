#!/usr/bin/env python3
"""Numerical, component-valued model of the custom IR analog front end.

The model deliberately exposes every stage: optical flux, photodiode current,
TIA, active band-pass, Schmitt comparator and RMT carrier removal.  It shares
its only editable parameter source with firmware and SPICE: config/system.json.
"""

from __future__ import annotations

import csv
import argparse
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


def simulate(duration_s: float = 0.024, sample_rate_hz: int = 2_000_000,
             carrier_hz: float | None = None) -> dict:
    wheel = CFG["wheel"]
    optical = CFG["optical"]
    afe = CFG["analog_frontend"]
    tx = CFG["transmitter"]
    esp = CFG["esp32"]
    carrier_hz = float(carrier_hz or optical["carrier_hz_default"])
    if not optical["carrier_hz_min"] <= carrier_hz <= optical["carrier_hz_max"]:
        raise ValueError("carrier_hz outside analog-compatible configured range")

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
    phase_carrier = np.mod(t * carrier_hz, 1.0)
    carrier = (phase_carrier < optical["carrier_duty"]).astype(float)

    spoke_phase = np.mod(t + 0.15 * spoke_period_s, spoke_period_s)
    transmission = np.where(
        spoke_phase >= blocked_s, 1.0, wheel["residual_transmission_blocked"]
    )

    cable_loop_ohm = (
        2 * tx["cable_length_mm"] * 1e-3 * tx["cable_conductor_ohm_per_m"]
        + 2 * tx["connector_contact_ohm_max"]
    )
    led_ma = (
        tx["supply_v"] - tx["led_vf_v_typ"] - tx["driver_vce_sat_v_typ"]
    ) / (tx["led_series_ohm"] + cable_loop_ohm) * 1000
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
        0.0, optical["environmental_noise_rms_ua"] * 1e-6, t.size
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
        photo_current_a * afe["tia_feedback_ohm"], dt, tia_tau,
        float(photo_current_a[0] * afe["tia_feedback_ohm"])
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

    rx_demod_hz = carrier_hz * esp["rx_demod_frequency_ratio"]
    demod_hold_us = 1e6 / rx_demod_hz
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
            "carrier_hz": carrier_hz,
            "rx_demod_hz": rx_demod_hz,
            "carrier_cycles_per_blockage": blocked_s * carrier_hz,
            "irradiance_w_m2_nominal": irradiance_w_m2,
            "signal_photocurrent_ua_nominal": signal_photo_a * 1e6,
            "tia_pole_hz": tia_pole_hz,
            "bandpass_highpass_hz": hp_hz,
            "bandpass_lowpass_hz": gain_lp_hz,
            "bandpass_peak_to_peak_v": float(np.ptp(
                bandpass_v[int(2e-3 * sample_rate_hz):])),
            "comparator_hysteresis_mv_typ": comparator_hyst_mv,
            "tia_min_v": float(np.min(tia_v)),
            "tia_max_v": float(np.max(tia_v)),
            "detected_blocked_fraction": float(np.mean(blocked_digital)),
            "speed_margin_to_stress": wheel["stress_speed_kmh"] / wheel["max_speed_kmh"],
            "cable_loop_resistance_ohm": cable_loop_ohm,
        },
        "traces": traces,
    }


def robustness_sweep(samples: int = 1000, seed: int = 0x51A1) -> dict:
    """Tolerance/environment sweep using datasheet limits where specified."""
    o, a, tx = CFG["optical"], CFG["analog_frontend"], CFG["transmitter"]
    rng = np.random.default_rng(seed)
    failures = 0
    margins = []
    headrooms = []
    for _ in range(samples):
        carrier = rng.uniform(o["carrier_hz_min"], o["carrier_hz_max"])
        supply = rng.uniform(3.0, 3.6)
        vf = rng.triangular(1.15, 1.35, 1.60)
        cable = (2 * tx["cable_length_mm"] * 1e-3 *
                 tx["cable_conductor_ohm_per_m"] +
                 2 * tx["connector_contact_ohm_max"])
        vce_sat = rng.uniform(0.08, 0.60)
        led_a = max(0.0, (supply - vf - vce_sat) /
                    (tx["led_series_ohm"] + cable))
        radiant_100 = rng.triangular(
            o["emitter_radiant_intensity_mw_sr_at_100ma_min"],
            o["emitter_radiant_intensity_mw_sr_at_100ma_typ"],
            12.0)
        detector_ua_at_10wm2 = rng.triangular(2.0, 3.0, 4.0)
        alignment = rng.uniform(0.25, 0.85)
        irradiance = radiant_100 * 1e-3 * led_a / 0.1
        irradiance = irradiance / (o["emitter_receiver_distance_mm"] * 1e-3) ** 2
        photo_peak = (
            irradiance
            * alignment
            / 10
            * detector_ua_at_10wm2
            * 1e-6
        )
        rf = a["tia_feedback_ohm"] * rng.uniform(0.99, 1.01)
        cf = a["tia_feedback_pf"] * rng.uniform(0.95, 1.05) * 1e-12
        rac = a["ac_bias_ohm"] * rng.uniform(0.99, 1.01)
        cac = a["ac_coupling_nf"] * rng.uniform(0.95, 1.05) * 1e-9
        rg = a["gain_ground_ohm"] * rng.uniform(0.99, 1.01)
        rfg = a["gain_feedback_ohm"] * rng.uniform(0.99, 1.01)
        cfg = a["gain_feedback_pf"] * rng.uniform(0.95, 1.05) * 1e-12
        w = 2 * math.pi * carrier
        tia_mag = rf / math.sqrt(1 + (w * rf * cf) ** 2)
        hp_mag = w * rac * cac / math.sqrt(1 + (w * rac * cac) ** 2)
        zf = rfg / complex(1, w * rfg * cfg)
        gain_mag = abs(1 + zf / rg)
        fundamental_peak = 2 / math.pi * photo_peak
        signal_peak_v = fundamental_peak * tia_mag * hp_mag * gain_mag
        ext_hyst = supply * a["comparator_input_ohm"] / a["comparator_feedback_ohm"]
        required_peak_v = 0.5 * (ext_hyst + rng.uniform(0.0012, 0.014)) + 0.008
        margin = signal_peak_v / required_peak_v if required_peak_v else 0
        ambient_a = rng.uniform(0, 35e-6)
        low_output = a["vref_v"] - ambient_a * rf - photo_peak * rf
        headroom = min(low_output - 0.06, supply - 0.06 - low_output)
        margins.append(margin)
        headrooms.append(headroom)
        if margin < 1.0 or headroom < 0.1:
            failures += 1
    return {
        "samples": samples,
        "failures": failures,
        "pass_fraction": 1 - failures / samples,
        "decision_margin_ratio_p01": float(np.quantile(margins, 0.01)),
        "decision_margin_ratio_median": float(np.median(margins)),
        "tia_headroom_v_p01": float(np.quantile(headrooms, 0.01)),
        "assumptions": {
            "alignment_factor_range": [0.25, 0.85],
            "ambient_photocurrent_ua_range": [0, 35],
            "supply_v_range": [3.0, 3.6],
            "driver_vce_sat_v_range": [0.08, 0.60],
            "emitter_radiant_intensity_mw_sr_range": [3, 12],
            "photodiode_current_ua_at_10wm2_range": [2, 4],
            "passive_resistor_tolerance": "1%",
            "passive_capacitor_tolerance": "5%",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--carrier-hz", type=float)
    parser.add_argument("--monte-carlo", type=int, default=1000)
    args = parser.parse_args()
    result = simulate(carrier_hz=args.carrier_hz)
    result["robustness"] = robustness_sweep(args.monte_carlo)
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
