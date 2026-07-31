#!/usr/bin/env python3
"""Local HTTP UI/API backed directly by the physical Python transient model."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ir_spoke_sim import CFG, ROOT, simulate

UI_DIR = ROOT / "local_simulator"


def control_schema() -> list[dict[str, Any]]:
    w, o, e, p, c = (
        CFG["wheel"], CFG["optical"], CFG["esp32"], CFG["power"], CFG["can"]
    )
    return [
        {"key": "speed_kmh", "label": "Speed", "unit": "km/h", "group": "Geometry",
         "default": w["max_speed_kmh"], "min": 1, "max": w["stress_speed_kmh"], "step": 1},
        {"key": "spoke_count", "label": "Actual spokes", "unit": "", "group": "Geometry",
         "default": w["spoke_count_design"], "min": w["spoke_count_min"],
         "max": w["spoke_count_max"], "step": 1},
        {"key": "spoke_width_mm", "label": "Spoke width", "unit": "mm", "group": "Geometry",
         "default": w["spoke_width_mm"], "min": 1, "max": 4, "step": 0.1},
        {"key": "wheel_diameter_m", "label": "Wheel diameter", "unit": "m", "group": "Geometry",
         "default": w["effective_diameter_m"], "min": 0.3, "max": 0.9, "step": 0.001},
        {"key": "beam_radius_m", "label": "Beam radius", "unit": "m", "group": "Geometry",
         "default": w["beam_radius_m"], "min": 0.08, "max": 0.34, "step": 0.005},
        {"key": "duration_ms", "label": "Transient window", "unit": "ms", "group": "Geometry",
         "default": 2, "min": 2, "max": 40, "step": 1},
        {"key": "carrier_hz", "label": "TX carrier", "unit": "Hz", "group": "Optical link",
         "default": o["carrier_hz_default"], "min": o["carrier_hz_min"],
         "max": o["carrier_hz_max"], "step": 250},
        {"key": "carrier_duty", "label": "TX duty", "unit": "", "group": "Optical link",
         "default": o["carrier_duty"], "min": 0.2, "max": 0.8, "step": 0.01},
        {"key": "distance_mm", "label": "Emitter distance", "unit": "mm", "group": "Optical link",
         "default": o["emitter_receiver_distance_mm"], "min": 10, "max": 120, "step": 1},
        {"key": "alignment_factor", "label": "Alignment factor", "unit": "", "group": "Optical link",
         "default": o["alignment_factor_nominal"], "min": 0.1, "max": 1, "step": 0.01},
        {"key": "ambient_photocurrent_ua", "label": "Ambient current", "unit": "uA",
         "group": "Optical link", "default": o["ambient_photocurrent_ua"],
         "min": 0, "max": 40, "step": 0.5},
        {"key": "environmental_noise_rms_ua", "label": "Interference RMS", "unit": "uA",
         "group": "Optical link", "default": o["environmental_noise_rms_ua"],
         "min": 0, "max": 0.02, "step": 0.0005},
        {"key": "residual_transmission_blocked", "label": "Blocked transmission", "unit": "",
         "group": "Optical link", "default": w["residual_transmission_blocked"],
         "min": 0, "max": 0.5, "step": 0.01},
        {"key": "esp32_cpu_active_duty", "label": "CPU active duty", "unit": "",
         "group": "Power scenario", "default": p["esp32_cpu_active_duty"],
         "min": 0, "max": 1, "step": 0.01},
        {"key": "esp32_wifi_tx_duty", "label": "Wi-Fi TX duty", "unit": "",
         "group": "Power scenario", "default": p["esp32_wifi_tx_duty"],
         "min": 0, "max": 0.5, "step": 0.01},
        {"key": "supply_rise_us", "label": "3V3 rise time", "unit": "us",
         "group": "Power scenario", "default": p["supply_rise_us"],
         "min": 100, "max": 5000, "step": 100},
        {"key": "regulator_efficiency", "label": "Regulator efficiency", "unit": "",
         "group": "Power scenario", "default": p["regulator_efficiency_estimate"],
         "min": 0.7, "max": 1, "step": 0.01},
        {"key": "can_enabled", "label": "XIAO CAN enabled", "unit": "0/1",
         "group": "Power scenario", "default": int(c["enabled_default"]),
         "min": 0, "max": 1, "step": 1},
        {"key": "can_bus_activity_duty", "label": "CAN dominant duty", "unit": "",
         "group": "Power scenario", "default": c["bus_activity_duty_default"],
         "min": 0, "max": 1, "step": 0.01},
        {"key": "tx_gpio", "label": "TX GPIO", "unit": "", "group": "ESP-IDF RMT",
         "default": e["tx_gpio"], "min": 0, "max": 48, "step": 1},
        {"key": "rx_gpio", "label": "RX GPIO", "unit": "", "group": "ESP-IDF RMT",
         "default": e["rx_gpio"], "min": 0, "max": 48, "step": 1},
        {"key": "rmt_resolution_hz", "label": "RMT resolution", "unit": "Hz",
         "group": "ESP-IDF RMT", "default": e["rmt_resolution_hz"],
         "min": 400000, "max": 4000000, "step": 100000},
        {"key": "rmt_mem_block_symbols", "label": "Channel memory", "unit": "symbols",
         "group": "ESP-IDF RMT", "default": e["rmt_mem_block_symbols"],
         "min": 48, "max": 512, "step": 16},
        {"key": "rmt_tx_queue_depth", "label": "TX queue depth", "unit": "",
         "group": "ESP-IDF RMT", "default": e["rmt_tx_queue_depth"],
         "min": 1, "max": 8, "step": 1},
        {"key": "rx_demod_ratio", "label": "RX / TX frequency", "unit": "",
         "group": "ESP-IDF RMT", "default": e["rx_demod_frequency_ratio"],
         "min": 0.5, "max": 0.9, "step": 0.01},
        {"key": "rx_demod_duty", "label": "RX demod duty", "unit": "",
         "group": "ESP-IDF RMT", "default": e["rx_demod_duty"],
         "min": 0.2, "max": 0.8, "step": 0.01},
        {"key": "rx_glitch_filter_us", "label": "RX minimum pulse", "unit": "us",
         "group": "ESP-IDF RMT", "default": e["rx_glitch_filter_us"],
         "min": 1, "max": 9, "step": 1},
        {"key": "minimum_blocked_us", "label": "Minimum blockage", "unit": "us",
         "group": "ESP-IDF RMT", "default": e["minimum_blocked_us"],
         "min": 20, "max": 250, "step": 5},
        {"key": "maximum_blocked_us", "label": "Maximum blockage", "unit": "us",
         "group": "ESP-IDF RMT", "default": e["maximum_blocked_us"],
         "min": 250, "max": 1500, "step": 10},
        {"key": "link_loss_timeout_us", "label": "Link-loss timeout", "unit": "us",
         "group": "ESP-IDF RMT", "default": e["link_loss_timeout_us"],
         "min": 2000, "max": 30000, "step": 500},
        {"key": "spoke_count_min", "label": "Auto-count minimum", "unit": "",
         "group": "Adaptive map", "default": w["spoke_count_min"], "min": 8, "max": 32, "step": 1},
        {"key": "spoke_count_max", "label": "Auto-count maximum", "unit": "",
         "group": "Adaptive map", "default": w["spoke_count_max"], "min": 24, "max": 64, "step": 1},
        {"key": "lut_bins", "label": "Spacing LUT bins", "unit": "",
         "group": "Adaptive map", "default": e["lut_bins"], "min": 16, "max": 256, "step": 8},
        {"key": "learning_rate", "label": "Learning rate", "unit": "",
         "group": "Adaptive map", "default": e["learning_rate"], "min": 0.01, "max": 0.3, "step": 0.01},
        {"key": "spoke_count_confidence_events", "label": "Count confidence", "unit": "events",
         "group": "Adaptive map", "default": e["spoke_count_confidence_events"],
         "min": 32, "max": 512, "step": 16},
        {"key": "outlier_sigma", "label": "Outlier gate", "unit": "sigma",
         "group": "Adaptive map", "default": e["outlier_sigma"], "min": 1.5, "max": 6, "step": 0.1},
    ]


def defaults_payload() -> dict[str, Any]:
    controls = control_schema()
    return {
        "controls": controls,
        "values": {item["key"]: item["default"] for item in controls},
        "source": "config/system.json",
        "model": "simulation/ir_spoke_sim.py",
    }


def validate_code_parameters(values: dict[str, Any]) -> None:
    """Reject combinations that cannot produce a valid ESP-IDF configuration."""
    carrier_hz = float(values["carrier_hz"])
    resolution_hz = float(values["rmt_resolution_hz"])
    glitch_filter_us = float(values["rx_glitch_filter_us"])
    blockage_min_us = float(values["minimum_blocked_us"])
    blockage_max_us = float(values["maximum_blocked_us"])
    link_loss_timeout_us = float(values["link_loss_timeout_us"])

    if int(values["tx_gpio"]) == int(values["rx_gpio"]):
        raise ValueError("TX and RX GPIO must be different")
    if resolution_hz < 8.0 * carrier_hz:
        raise ValueError("RMT resolution must be at least 8x the carrier frequency")
    if not 48 <= int(values["rmt_mem_block_symbols"]) <= 512:
        raise ValueError("RMT channel memory must be between 48 and 512 symbols")
    if not 1 <= int(values["rmt_tx_queue_depth"]) <= 8:
        raise ValueError("RMT TX queue depth must be between 1 and 8")
    if glitch_filter_us * carrier_hz >= 500_000.0:
        raise ValueError("RX minimum pulse must be shorter than half a carrier period")
    if not blockage_min_us < blockage_max_us < link_loss_timeout_us:
        raise ValueError(
            "Timing must satisfy minimum blockage < maximum blockage < link-loss timeout"
        )
    if int(values["spoke_count_min"]) >= int(values["spoke_count_max"]):
        raise ValueError("Auto-count minimum must be smaller than its maximum")


def generated_config_header(values: dict[str, Any], result: dict[str, Any]) -> str:
    def iv(key: str) -> int:
        return int(round(float(values[key])))

    def fv(key: str) -> str:
        return f"{float(values[key]):.9g}f"

    d = result["derived"]
    return f"""/* Generated by the local physical model. Review before committing. */
#pragma once
#include "ir_spoke_config.h"

#define IR_SPOKE_EXPERIMENT_WHEEL_DIAMETER_M {fv("wheel_diameter_m")}
#define IR_SPOKE_EXPERIMENT_BEAM_RADIUS_M {fv("beam_radius_m")}
#define IR_SPOKE_EXPERIMENT_COUNT_MIN {iv("spoke_count_min")}u
#define IR_SPOKE_EXPERIMENT_COUNT_MAX {iv("spoke_count_max")}u
#define IR_SPOKE_EXPERIMENT_LUT_BINS {iv("lut_bins")}u
#define IR_SPOKE_EXPERIMENT_LEARNING_RATE {fv("learning_rate")}
#define IR_SPOKE_EXPERIMENT_CONFIDENCE_EVENTS {iv("spoke_count_confidence_events")}u
#define IR_SPOKE_EXPERIMENT_OUTLIER_SIGMA {fv("outlier_sigma")}
#define IR_SPOKE_EXPERIMENT_CPU_ACTIVE_DUTY {fv("esp32_cpu_active_duty")}
#define IR_SPOKE_EXPERIMENT_WIFI_TX_DUTY {fv("esp32_wifi_tx_duty")}
#define IR_SPOKE_EXPERIMENT_SUPPLY_RISE_US {iv("supply_rise_us")}u
#define IR_SPOKE_EXPERIMENT_REGULATOR_EFFICIENCY {fv("regulator_efficiency")}
#define IR_SPOKE_EXPERIMENT_CAN_ENABLED {iv("can_enabled")}
#define IR_SPOKE_EXPERIMENT_CAN_ACTIVITY_DUTY {fv("can_bus_activity_duty")}

static inline ir_spoke_runtime_config_t ir_spoke_experiment_config(void) {{
    return (ir_spoke_runtime_config_t){{
        .tx_gpio = {iv("tx_gpio")},
        .rx_gpio = {iv("rx_gpio")},
        .carrier_hz = {iv("carrier_hz")}u,
        .carrier_duty = {fv("carrier_duty")},
        .rmt_resolution_hz = {iv("rmt_resolution_hz")}u,
        .rmt_mem_block_symbols = {iv("rmt_mem_block_symbols")}u,
        .rmt_tx_queue_depth = {iv("rmt_tx_queue_depth")}u,
        .rx_demod_ratio = {fv("rx_demod_ratio")},
        .rx_demod_duty = {fv("rx_demod_duty")},
        .rx_glitch_filter_us = {iv("rx_glitch_filter_us")}u,
        .blockage_min_us = {iv("minimum_blocked_us")}u,
        .blockage_max_us = {iv("maximum_blocked_us")}u,
        .link_loss_us = {iv("link_loss_timeout_us")}u,
    }};
}}

/* Model result: blockage={d["blocked_us"]:.2f} us,
   carrier cycles={d["carrier_cycles_per_blockage"]:.2f},
   nominal photocurrent={d["signal_photocurrent_ua_nominal"]:.4f} uA. */
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "IRSpokeLocal/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[local-sim] {self.address_string()} {fmt % args}")

    def send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, payload: Any) -> None:
        self.send_bytes(
            status,
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/defaults":
            self.send_json(200, defaults_payload())
            return
        path = "index.html" if self.path in ("/", "/index.html") else self.path.lstrip("/")
        target = (UI_DIR / path).resolve()
        if UI_DIR.resolve() not in target.parents and target != UI_DIR.resolve():
            self.send_json(403, {"error": "invalid path"})
            return
        if not target.is_file():
            self.send_json(404, {"error": "not found"})
            return
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_bytes(200, target.read_bytes(), f"{mime}; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
            values = json.loads(self.rfile.read(length) or b"{}")
            defaults = defaults_payload()["values"]
            unknown = sorted(set(values) - set(defaults))
            if unknown:
                raise ValueError(f"unknown parameters: {', '.join(unknown)}")
            merged = defaults | values
            validate_code_parameters(merged)
            result = simulate(parameters=merged)
            if self.path == "/api/simulate":
                self.send_json(200, result)
            elif self.path == "/api/generate-code":
                self.send_json(200, {
                    "filename": "ir_spoke_experiment_config.h",
                    "code": generated_config_header(merged, result),
                    "derived": result["derived"],
                })
            else:
                self.send_json(404, {"error": "not found"})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception as exc:  # keep model failures visible in the UI
            self.send_json(500, {"error": f"{type(exc).__name__}: {exc}"})


def main() -> None:
    address = ("127.0.0.1", 8765)
    print(f"IR Spoke physical simulator: http://{address[0]}:{address[1]}/")
    ThreadingHTTPServer(address, Handler).serve_forever()


if __name__ == "__main__":
    main()
