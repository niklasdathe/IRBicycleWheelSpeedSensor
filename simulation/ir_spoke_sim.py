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
import sys
from pathlib import Path
from typing import Any

import numpy as np

SIMULATION_DIR = Path(__file__).resolve().parent
if str(SIMULATION_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATION_DIR))
from connectivity_guard import validate_simulation_connectivity

ROOT = SIMULATION_DIR.parent
CFG = json.loads((ROOT / "config" / "system.json").read_text(encoding="utf-8"))
ELEMENTARY_CHARGE_C = 1.602176634e-19
BOLTZMANN_J_K = 1.380649e-23
ROOM_TEMPERATURE_K = 298.15


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


def delayed_logic(x: np.ndarray, delay_s: float, sample_rate_hz: int) -> np.ndarray:
    delay_samples = max(0, round(delay_s * sample_rate_hz))
    if not delay_samples:
        return x.copy()
    out = np.empty_like(x)
    out[:delay_samples] = x[0]
    out[delay_samples:] = x[:-delay_samples]
    return out


def simulate(duration_s: float = 0.024, sample_rate_hz: int = 2_000_000,
             carrier_hz: float | None = None,
             parameters: dict[str, Any] | None = None) -> dict:
    connectivity_sha256 = validate_simulation_connectivity()
    wheel = CFG["wheel"]
    optical = CFG["optical"]
    afe = CFG["analog_frontend"]
    tx = CFG["transmitter"]
    esp = CFG["esp32"]
    can = CFG["can"]
    power = CFG["power"]
    requested = {
        "speed_kmh": wheel["max_speed_kmh"],
        "spoke_count": wheel["spoke_count_design"],
        "spoke_width_mm": wheel["spoke_width_mm"],
        "wheel_diameter_m": wheel["effective_diameter_m"],
        "beam_radius_m": wheel["beam_radius_m"],
        "residual_transmission_blocked": wheel["residual_transmission_blocked"],
        "carrier_hz": carrier_hz or optical["carrier_hz_default"],
        "carrier_duty": optical["carrier_duty"],
        "distance_mm": optical["emitter_receiver_distance_mm"],
        "alignment_factor": optical["alignment_factor_nominal"],
        "ambient_photocurrent_ua": optical["ambient_photocurrent_ua"],
        "environmental_noise_rms_ua": optical["environmental_noise_rms_ua"],
        "rx_demod_ratio": esp["rx_demod_frequency_ratio"],
        "rx_demod_duty": esp["rx_demod_duty"],
        "rx_glitch_filter_us": esp["rx_glitch_filter_us"],
        "minimum_blocked_us": esp["minimum_blocked_us"],
        "maximum_blocked_us": esp["maximum_blocked_us"],
        "link_loss_timeout_us": esp["link_loss_timeout_us"],
        "esp32_cpu_active_duty": power["esp32_cpu_active_duty"],
        "esp32_wifi_tx_duty": power["esp32_wifi_tx_duty"],
        "supply_rise_us": power["supply_rise_us"],
        "regulator_efficiency": power["regulator_efficiency_estimate"],
        "can_enabled": can["enabled_default"],
        "can_bus_activity_duty": can["bus_activity_duty_default"],
    }
    if parameters:
        requested.update(parameters)
    carrier_hz = float(requested["carrier_hz"])
    duration_s = float(parameters.get("duration_ms", duration_s * 1000) * 1e-3
                       if parameters else duration_s)
    sample_rate_hz = int(parameters.get("sample_rate_hz", sample_rate_hz)
                         if parameters else sample_rate_hz)
    if not optical["carrier_hz_min"] <= carrier_hz <= optical["carrier_hz_max"]:
        raise ValueError("carrier_hz outside analog-compatible configured range")
    if requested["speed_kmh"] <= 0 or requested["spoke_count"] < 1:
        raise ValueError("speed and spoke count must be positive")
    if duration_s <= 0 or sample_rate_hz < 10 * carrier_hz:
        raise ValueError("duration must be positive and sample rate >= 10x carrier")

    speed_mps = float(requested["speed_kmh"]) / 3.6
    circumference = math.pi * float(requested["wheel_diameter_m"])
    wheel_hz = speed_mps / circumference
    omega = 2 * math.pi * wheel_hz
    spoke_hz = wheel_hz * float(requested["spoke_count"])
    tangential_speed = omega * float(requested["beam_radius_m"])
    blocked_s = (float(requested["spoke_width_mm"]) / 1000) / tangential_speed
    spoke_period_s = 1 / spoke_hz
    clear_s = spoke_period_s - blocked_s

    dt = 1 / sample_rate_hz
    t = np.arange(0, duration_s, dt)
    phase_carrier = np.mod(t * carrier_hz, 1.0)
    carrier = (phase_carrier < float(requested["carrier_duty"])).astype(float)

    # Put a full blockage in the centre of every requested time window. This
    # makes short diagnostic transients useful while retaining the true period.
    centered_start_s = 0.5 * duration_s - 0.5 * blocked_s
    spoke_phase = np.mod(t - centered_start_s, spoke_period_s)
    transmission = np.where(
        spoke_phase >= blocked_s, 1.0,
        float(requested["residual_transmission_blocked"])
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
    distance_m = float(requested["distance_mm"]) * 1e-3
    irradiance_w_m2 = (
        intensity_w_sr
        / distance_m**2
        * float(requested["alignment_factor"])
    )
    signal_photo_a = (
        irradiance_w_m2
        / 10.0
        * optical["photodiode_reverse_light_current_ua_at_10wm2_typ"]
        * 1e-6
    )

    ambient_a = float(requested["ambient_photocurrent_ua"]) * 1e-6
    dark_a = afe["photodiode_dark_current_na_typ"] * 1e-9
    shot_density_a_sqrt_hz = math.sqrt(
        2 * ELEMENTARY_CHARGE_C * (ambient_a + dark_a)
    )
    resistor_density_a_sqrt_hz = math.sqrt(
        4 * BOLTZMANN_J_K * ROOM_TEMPERATURE_K / afe["tia_feedback_ohm"]
    )
    opamp_current_density_a_sqrt_hz = (
        afe["opamp_current_noise_fa_sqrt_hz_typ"] * 1e-15
    )
    opamp_voltage_as_current_density = (
        afe["opamp_voltage_noise_nv_sqrt_hz_typ"] * 1e-9
        / afe["tia_feedback_ohm"]
    )
    physical_input_noise_density = math.sqrt(
        shot_density_a_sqrt_hz**2
        + resistor_density_a_sqrt_hz**2
        + opamp_current_density_a_sqrt_hz**2
        + opamp_voltage_as_current_density**2
    )
    physical_noise_rms_a = physical_input_noise_density * math.sqrt(
        sample_rate_hz / 2
    )
    environmental_noise_rms_a = (
        float(requested["environmental_noise_rms_ua"]) * 1e-6
    )
    total_noise_rms_a = math.hypot(
        physical_noise_rms_a, environmental_noise_rms_a
    )
    rng = np.random.default_rng(0xB1C1E)
    noise_a = rng.normal(0.0, total_noise_rms_a, t.size)
    photo_current_a = (
        ambient_a + dark_a
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
    comparator_ideal = np.zeros(t.size, dtype=np.uint8)
    state = 0
    r_input = afe["comparator_input_ohm"]
    r_feedback = afe["comparator_feedback_ohm"]
    feedback_ratio = r_input / r_feedback
    internal_hysteresis_v = (
        afe["comparator_internal_hysteresis_mv_typ"] * 1e-3
    )
    # Solve the summing node at VREF for each output rail. The thresholds are
    # intentionally asymmetric around the 1.65 V reference because the
    # feedback rail changes between comparator output states.
    rising_threshold_v = (
        afe["vref_v"] * (1.0 + feedback_ratio)
        + 0.5 * internal_hysteresis_v
    )
    falling_threshold_v = (
        afe["vref_v"]
        + (afe["vref_v"] - afe["supply_v"]) * feedback_ratio
        - 0.5 * internal_hysteresis_v
    )
    hysteresis_v = rising_threshold_v - falling_threshold_v
    threshold_trace = np.empty_like(t)
    for i, signal_v in enumerate(bandpass_v):
        threshold = falling_threshold_v if state else rising_threshold_v
        if state == 0 and signal_v > threshold:
            state = 1
        elif state == 1 and signal_v < threshold:
            state = 0
        comparator_ideal[i] = state
        threshold_trace[i] = threshold
    comparator = delayed_logic(
        comparator_ideal,
        afe["comparator_delay_ns_typ"] * 1e-9,
        sample_rate_hz,
    )

    rx_demod_hz = carrier_hz * float(requested["rx_demod_ratio"])
    demod_hold_us = 1e6 / rx_demod_hz
    clear_digital = rmt_carrier_remove(comparator, sample_rate_hz, demod_hold_us)
    blocked_digital = 1 - clear_digital

    # Datasheet-based 3.3 V rail model. CPU and Wi-Fi values are ESP32-S3
    # current-consumption table values; the LED/base and AFE currents are
    # calculated from the installed circuit. A short inrush term represents
    # local bypass charging for the configured supply ramp.
    cpu_duty = float(requested["esp32_cpu_active_duty"])
    wifi_duty = float(requested["esp32_wifi_tx_duty"])
    if not 0 <= cpu_duty <= 1 or not 0 <= wifi_duty <= 1:
        raise ValueError("CPU and Wi-Fi duty cycles must be from zero to one")
    can_enabled = bool(requested["can_enabled"])
    can_bus_duty = float(requested["can_bus_activity_duty"])
    if not 0 <= can_bus_duty <= 1:
        raise ValueError("CAN bus activity duty must be from zero to one")
    cpu_active = np.zeros(t.size, dtype=bool)
    event_edges = np.flatnonzero(np.diff(blocked_digital.astype(int)) != 0) + 1
    if event_edges.size and cpu_duty:
        samples_per_event = max(
            1, round(cpu_duty * t.size / event_edges.size)
        )
        for edge in event_edges:
            cpu_active[edge:min(t.size, edge + samples_per_event)] = True
    wifi_active = np.zeros(t.size, dtype=bool)
    wifi_samples = min(t.size, max(0, round(wifi_duty * t.size)))
    if wifi_samples:
        wifi_start = max(0, (t.size - wifi_samples) // 2)
        wifi_active[wifi_start:wifi_start + wifi_samples] = True
    esp32_current_ma = np.where(
        cpu_active,
        power["esp32_active_single_core_all_peripherals_ma_typ"],
        power["esp32_waiti_all_peripherals_ma_typ"],
    )
    esp32_current_ma[wifi_active] = power["esp32_wifi_tx_peak_ma"]
    esp32_current_ma += power["xiao_board_overhead_ma_estimate"]

    can_dominant = np.zeros(t.size, dtype=bool)
    can_samples = min(
        t.size, max(0, round(can_bus_duty * t.size))
    ) if can_enabled else 0
    if can_samples:
        can_start = max(0, (t.size - can_samples) // 2)
        can_dominant[can_start:can_start + can_samples] = True
    can_idle_ma = (
        power["can_controller_active_ma_max"]
        + power["can_transceiver_recessive_ma_max"]
        + power["can_board_leds_ma_estimate"]
    ) if can_enabled else 0.0
    can_current_ma = np.full(t.size, can_idle_ma)
    can_current_ma[can_dominant] += (
        power["can_dominant_line_drive_ma_estimate"]
    )

    base_peak_ma = max(
        0.0,
        (
            tx["supply_v"] - tx["driver_vbe_v_typ_estimate"]
        ) / tx["base_resistor_ohm"] * 1000,
    )
    led_branch_ma = carrier * led_ma
    base_drive_ma = carrier * base_peak_ma
    vref_divider_ma = afe["supply_v"] / (10_000 + 10_000) * 1000
    afe_static_ma = (
        power["opamp_quiescent_ua_per_amplifier_typ"]
        * power["opamp_amplifier_count"]
        + power["comparator_quiescent_ua_typ"]
    ) / 1000 + vref_divider_ma

    supply_rise_s = float(requested["supply_rise_us"]) * 1e-6
    if supply_rise_s <= 0:
        raise ValueError("supply_rise_us must be positive")
    supply_voltage_v = afe["supply_v"] * np.clip(
        t / supply_rise_s, 0.0, 1.0
    )
    local_bypass_inrush_ma = (
        power["local_decoupling_uf"] * 1e-6
        * afe["supply_v"] / supply_rise_s * 1000
    )
    inrush_ma = np.where(t < supply_rise_s, local_bypass_inrush_ma, 0.0)
    vref_tau_s = 5_000 * 1e-6
    vref_startup_extra_ma = vref_divider_ma * np.exp(-t / vref_tau_s)

    comparator_edges = np.r_[
        False, np.diff(comparator.astype(int)) != 0
    ]
    comparator_dynamic_ma = comparator_edges.astype(float) * (
        0.5
        * power["gpio_and_trace_capacitance_pf_estimate"] * 1e-12
        * afe["supply_v"]
        / dt
        * 1000
    )
    afe_current_ma = (
        afe_static_ma + inrush_ma + vref_startup_extra_ma
        + comparator_dynamic_ma
    )
    system_current_ma = (
        esp32_current_ma + led_branch_ma + base_drive_ma + afe_current_ma
        + can_current_ma
    )
    system_power_mw = system_current_ma * supply_voltage_v

    esp32_compute_average_ma = (
        power["esp32_waiti_all_peripherals_ma_typ"]
        + cpu_duty * (
            power["esp32_active_single_core_all_peripherals_ma_typ"]
            - power["esp32_waiti_all_peripherals_ma_typ"]
        )
    )
    esp32_average_ma = (
        (1 - wifi_duty) * esp32_compute_average_ma
        + wifi_duty * power["esp32_wifi_tx_peak_ma"]
        + power["xiao_board_overhead_ma_estimate"]
    )
    led_average_ma = led_ma * float(requested["carrier_duty"])
    base_average_ma = base_peak_ma * float(requested["carrier_duty"])
    comparator_dynamic_average_ma = (
        power["gpio_and_trace_capacitance_pf_estimate"] * 1e-12
        * afe["supply_v"] * carrier_hz * 1000
    )
    can_average_ma = (
        can_idle_ma
        + (
            power["can_dominant_line_drive_ma_estimate"] * can_bus_duty
            if can_enabled else 0.0
        )
    )
    system_steady_average_ma = (
        esp32_average_ma + led_average_ma + base_average_ma
        + afe_static_ma + comparator_dynamic_average_ma + can_average_ma
    )
    system_peak_estimate_ma = (
        power["esp32_wifi_tx_peak_ma"]
        + power["xiao_board_overhead_ma_estimate"]
        + led_ma + base_peak_ma + afe_static_ma
        + local_bypass_inrush_ma + vref_divider_ma
        + comparator_dynamic_ma.max(initial=0.0)
        + (
            can_idle_ma + power["can_dominant_line_drive_ma_estimate"]
            if can_enabled else 0.0
        )
    )
    regulator_efficiency = float(requested["regulator_efficiency"])
    if not 0 < regulator_efficiency <= 1:
        raise ValueError("regulator_efficiency must be greater than zero and at most one")

    tia_pole_hz = 1 / (2 * math.pi * tia_tau)
    hp_hz = 1 / (2 * math.pi * hp_tau)
    gain_lp_hz = 1 / (2 * math.pi * gain_tau)
    comparator_hyst_mv = (
        hysteresis_v * 1000
    )
    settle_samples = min(
        int(2e-3 * sample_rate_hz),
        max(0, int(0.2 * bandpass_v.size)),
    )

    stride = max(1, sample_rate_hz // 200_000)
    sl = slice(None, None, stride)
    traces = {
        "time_ms": np.round(t[sl] * 1000, 6).tolist(),
        "carrier": carrier[sl].astype(int).tolist(),
        "transmission": np.round(transmission[sl], 4).tolist(),
        "irradiance_w_m2": np.round(
            irradiance_w_m2 * carrier[sl] * transmission[sl], 6
        ).tolist(),
        "photodiode_ua": np.round(photo_current_a[sl] * 1e6, 5).tolist(),
        "tia_v": np.round(tia_v[sl], 5).tolist(),
        "ac_coupled_v": np.round(ac_v[sl], 5).tolist(),
        "bandpass_v": np.round(bandpass_v[sl], 5).tolist(),
        "threshold_v": np.round(threshold_trace[sl], 5).tolist(),
        "comparator_ideal": comparator_ideal[sl].astype(int).tolist(),
        "comparator": comparator[sl].astype(int).tolist(),
        "rmt_carrier_present": clear_digital[sl].astype(int).tolist(),
        "digital_active_low": (1 - blocked_digital[sl]).astype(int).tolist(),
        "blocked_digital": blocked_digital[sl].astype(int).tolist(),
        "led_current_ma": np.round(led_branch_ma[sl], 4).tolist(),
        "esp32_current_ma": np.round(esp32_current_ma[sl], 4).tolist(),
        "afe_current_ma": np.round(afe_current_ma[sl], 4).tolist(),
        "can_current_ma": np.round(can_current_ma[sl], 4).tolist(),
        "system_current_ma": np.round(system_current_ma[sl], 4).tolist(),
        "supply_voltage_v": np.round(supply_voltage_v[sl], 5).tolist(),
        "system_power_mw": np.round(system_power_mw[sl], 4).tolist(),
    }
    return {
        "config": CFG,
        "derived": {
            "connectivity_sha256": connectivity_sha256,
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
            "rx_demod_ratio": float(requested["rx_demod_ratio"]),
            "rx_demod_duty": float(requested["rx_demod_duty"]),
            "carrier_cycles_per_blockage": blocked_s * carrier_hz,
            "irradiance_w_m2_nominal": irradiance_w_m2,
            "signal_photocurrent_ua_nominal": signal_photo_a * 1e6,
            "physical_input_noise_density_pa_sqrt_hz": (
                physical_input_noise_density * 1e12
            ),
            "physical_noise_rms_na_at_sample_nyquist": (
                physical_noise_rms_a * 1e9
            ),
            "environmental_noise_rms_na": environmental_noise_rms_a * 1e9,
            "tia_pole_hz": tia_pole_hz,
            "bandpass_highpass_hz": hp_hz,
            "bandpass_lowpass_hz": gain_lp_hz,
            "bandpass_peak_to_peak_v": float(np.ptp(
                bandpass_v[settle_samples:])),
            "comparator_hysteresis_mv_typ": comparator_hyst_mv,
            "tia_min_v": float(np.min(tia_v)),
            "tia_max_v": float(np.max(tia_v)),
            "detected_blocked_fraction": float(np.mean(blocked_digital)),
            "center_blockage_visible": bool(
                np.any(transmission < 0.5 * (
                    1 + float(requested["residual_transmission_blocked"])
                ))
            ),
            "speed_margin_to_stress": wheel["stress_speed_kmh"] / wheel["max_speed_kmh"],
            "cable_loop_resistance_ohm": cable_loop_ohm,
            "led_current_ma_average": led_average_ma,
            "gpio_base_drive_ma_peak": base_peak_ma,
            "gpio_source_current_utilization": (
                base_peak_ma / power["esp32_gpio_source_current_ma_typ"]
            ),
            "afe_current_ma_static": afe_static_ma,
            "can_enabled": can_enabled,
            "can_current_ma_idle": can_idle_ma,
            "can_current_ma_average": can_average_ma,
            "can_current_ma_peak": (
                can_idle_ma + power["can_dominant_line_drive_ma_estimate"]
                if can_enabled else 0.0
            ),
            "esp32_current_ma_average_scenario": esp32_average_ma,
            "system_current_ma_steady_average": system_steady_average_ma,
            "system_current_ma_peak_estimate": system_peak_estimate_ma,
            "system_power_mw_steady_average": (
                system_steady_average_ma * afe["supply_v"]
            ),
            "system_input_power_mw_estimate": (
                system_steady_average_ma * afe["supply_v"]
                / regulator_efficiency
            ),
            "system_energy_mwh_per_hour": (
                system_steady_average_ma * afe["supply_v"]
                / regulator_efficiency
            ),
            "xiao_regulator_peak_utilization": (
                system_peak_estimate_ma
                / power["xiao_3v3_regulator_capacity_ma"]
            ),
            "esp32_recommended_supply_peak_utilization": (
                system_peak_estimate_ma
                / power["esp32_recommended_supply_capacity_ma"]
            ),
            "within_xiao_3v3_capacity": bool(
                system_peak_estimate_ma
                < power["xiao_3v3_regulator_capacity_ma"]
            ),
            "within_esp32_recommended_supply_capacity": bool(
                system_peak_estimate_ma
                < power["esp32_recommended_supply_capacity_ma"]
            ),
        },
        "parameters": requested | {
            "duration_ms": duration_s * 1000,
            "sample_rate_hz": sample_rate_hz,
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
    output = ROOT / "build" / "simulation"
    output.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2)
    (output / "simulation.json").write_text(payload, encoding="utf-8")
    traces = result["traces"]
    with (output / "waveforms.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(traces)
        writer.writerows(zip(*(traces[name] for name in traces)))
    print(json.dumps(result["derived"], indent=2))


if __name__ == "__main__":
    main()
