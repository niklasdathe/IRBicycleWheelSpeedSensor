import importlib.util
import csv
import json
import math
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config/system.json").read_text())
DS = json.loads((ROOT / "docs/datasheet_values.json").read_text())
SIM = json.loads((ROOT / "simulation/output/simulation.json").read_text())
SIM_SPEC = importlib.util.spec_from_file_location(
    "ir_spoke_sim", ROOT / "simulation/ir_spoke_sim.py"
)
SIM_MODULE = importlib.util.module_from_spec(SIM_SPEC)
SIM_SPEC.loader.exec_module(SIM_MODULE)


class TestSystem(unittest.TestCase):
    def test_datasheet_values_cross_validate_manifest(self):
        o, a = CFG["optical"], CFG["analog_frontend"]
        self.assertEqual(o["led_peak_nm"], DS["VSMB1940X01"]["peak_wavelength_nm_typ"])
        self.assertEqual(
            o["emitter_radiant_intensity_mw_sr_at_100ma_typ"],
            DS["VSMB1940X01"]["radiant_intensity_mw_sr_at_100ma_typ"],
        )
        self.assertEqual(
            o["photodiode_capacitance_pf_typ"],
            DS["VEMD10940FX01"]["capacitance_pf_at_0v_typ"],
        )
        self.assertEqual(a["opamp_gbw_hz_typ"], DS["TLV9062"]["gbw_hz_typ"])
        self.assertEqual(
            a["opamp_voltage_noise_nv_sqrt_hz_typ"],
            DS["TLV9062"]["input_voltage_noise_nv_rt_hz_at_10khz_typ"],
        )
        self.assertEqual(
            a["comparator_delay_ns_typ"],
            DS["TLV7011"]["propagation_delay_ns_typ"],
        )
        for values in DS.values():
            self.assertTrue((ROOT / values["source"]).is_file())

    def test_led_current_and_cable_drop(self):
        tx = CFG["transmitter"]
        loop_r = (
            2
            * tx["cable_length_mm"]
            / 1000
            * tx["cable_conductor_ohm_per_m"]
            + 2 * tx["connector_contact_ohm_max"]
        )
        current_a = (
            tx["supply_v"] - tx["led_vf_v_typ"] - tx["driver_vce_sat_v_typ"]
        ) / (tx["led_series_ohm"] + loop_r)
        self.assertLessEqual(current_a * 1000, 50)
        self.assertLess(
            current_a * 1000,
            DS["VSMB1940X01"]["continuous_forward_current_ma_max"],
        )
        self.assertLess(current_a * loop_r, 0.025)

    def test_stress_blockage_within_capture_window(self):
        w, e = CFG["wheel"], CFG["esp32"]
        hz = (w["stress_speed_kmh"] / 3.6) / (
            math.pi * w["effective_diameter_m"]
        )
        blocked_us = (
            (w["spoke_width_mm"] / 1000)
            / (2 * math.pi * hz * w["beam_radius_m"])
            * 1e6
        )
        self.assertGreater(blocked_us, e["minimum_blocked_us"])
        self.assertLess(blocked_us, e["maximum_blocked_us"])

    def test_runtime_carrier_range_and_installed_filter_response(self):
        a, o = CFG["analog_frontend"], CFG["optical"]
        tia = 1 / (
            2 * math.pi * a["tia_feedback_ohm"] * a["tia_feedback_pf"] * 1e-12
        )
        hp = 1 / (
            2 * math.pi * a["ac_bias_ohm"] * a["ac_coupling_nf"] * 1e-9
        )
        lp = 1 / (
            2
            * math.pi
            * a["gain_feedback_ohm"]
            * a["gain_feedback_pf"]
            * 1e-12
        )
        self.assertEqual(o["carrier_hz_default"], 38000)
        self.assertLess(o["carrier_hz_min"], o["carrier_hz_default"])
        self.assertGreater(o["carrier_hz_max"], o["carrier_hz_default"])
        for frequency in (
            o["carrier_hz_min"],
            o["carrier_hz_default"],
            o["carrier_hz_max"],
        ):
            response = (
                1 / math.sqrt(1 + (frequency / tia) ** 2)
                * (frequency / hp)
                / math.sqrt(1 + (frequency / hp) ** 2)
                * 1
                / math.sqrt(1 + (frequency / lp) ** 2)
            )
            self.assertGreater(response, 0.25)

    def test_transient_at_carrier_range_edges(self):
        for frequency in (
            CFG["optical"]["carrier_hz_min"],
            CFG["optical"]["carrier_hz_max"],
        ):
            result = SIM_MODULE.simulate(duration_s=0.012, carrier_hz=frequency)
            self.assertEqual(result["derived"]["carrier_hz"], frequency)
            self.assertGreater(
                result["derived"]["bandpass_peak_to_peak_v"],
                result["derived"]["comparator_hysteresis_mv_typ"] / 1000,
            )

    def test_transient_detection_headroom_and_robustness(self):
        d = SIM["derived"]
        self.assertGreater(d["tia_min_v"], 0.1)
        self.assertLess(
            d["tia_max_v"], CFG["analog_frontend"]["supply_v"] - 0.1
        )
        self.assertGreater(
            d["bandpass_peak_to_peak_v"],
            d["comparator_hysteresis_mv_typ"] / 1000,
        )
        trace = np.asarray(SIM["traces"]["blocked_digital"], dtype=int)
        time = np.asarray(SIM["traces"]["time_ms"])
        edges = np.flatnonzero(np.diff(trace))
        widths = [
            (time[b] - time[a]) * 1000
            for a, b in zip(edges, edges[1:])
            if trace[a + 1] == 1
        ]
        qualified = [
            x
            for x in widths
            if CFG["esp32"]["minimum_blocked_us"]
            <= x
            <= CFG["esp32"]["maximum_blocked_us"]
        ]
        self.assertGreaterEqual(len(qualified), 4)
        self.assertGreaterEqual(SIM["robustness"]["pass_fraction"], 0.99)
        self.assertGreaterEqual(
            SIM["robustness"]["decision_margin_ratio_p01"], 1.0
        )

    def test_generated_firmware_and_adaptive_features(self):
        generated = (ROOT / "firmware/include/ir_spoke_generated.h").read_text()
        generated_c = (
            ROOT
            / "firmware/components/ir_spoke_core/include/ir_spoke_generated_c.h"
        ).read_text()
        code = (
            ROOT / "firmware/components/ir_spoke_core/ir_spoke_pattern.c"
        ).read_text()
        rmt = (ROOT / "firmware/main/ir_spoke_rmt_adapter.c").read_text()
        self.assertRegex(
            generated,
            rf"kDefaultCarrierHz = {CFG['optical']['carrier_hz_default']}",
        )
        self.assertIn("IR_SPOKE_MIN_CARRIER_HZ", generated_c)
        self.assertIn("IR_SPOKE_MAX_CARRIER_HZ", generated_c)
        for token in (
            "interval_lut",
            "IR_SPOKE_LEARNING_RATE",
            "infer_count",
            "IR_SPOKE_OUTLIER_SIGMA",
        ):
            self.assertIn(token, code)
        self.assertIn(".frequency_hz = config->carrier_hz", rmt)
        self.assertIn("rmt_apply_carrier(rx_channel", rmt)
        self.assertIn("rmt_transmit(tx_channel", rmt)
        self.assertNotIn("mcpwm_new_capture", rmt)

    def test_portable_c_module_boundaries(self):
        core = ROOT / "firmware/components/ir_spoke_core"
        for module in ("config", "geometry", "detector", "pattern", "pipeline"):
            self.assertTrue((core / f"ir_spoke_{module}.c").is_file())
            self.assertTrue(
                (core / "include" / f"ir_spoke_{module}.h").is_file()
            )
        source = "\n".join(p.read_text() for p in core.glob("*.c"))
        self.assertNotRegex(source, r"\b(malloc|calloc|realloc|free)\s*\(")
        self.assertNotIn("freertos/", source.lower())
        self.assertNotIn("driver/rmt", source.lower())

    def test_no_integrated_receiver_in_bom(self):
        bom = (ROOT / "hardware/ir_spoke_link/bom_jlcpcb.csv").read_text()
        self.assertNotRegex(bom, r"TSOP57|integrated 38")
        for mpn in ("VEMD10940FX01", "TLV9062IDDFR", "TLV7011DCKR"):
            self.assertIn(mpn, bom)

    def test_live_jlc_snapshot_covers_all_procured_parts(self):
        snapshot = json.loads(
            (ROOT / "hardware/jlcpcb_parts_snapshot.json").read_text()
        )
        live = {part["lcsc"]: part for part in snapshot["parts"]}
        self.assertTrue(live)
        self.assertFalse(any("error" in part for part in live.values()))
        expected = set()
        for relative in (
            "hardware/ir_spoke_link/bom_jlcpcb.csv",
            "hardware/remote_emitter/bom_jlcpcb.csv",
            "hardware/cable_bom.csv",
        ):
            with (ROOT / relative).open(newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    number = row.get("LCSC Part Number", "")
                    if re.fullmatch(r"C\d+", number):
                        expected.add(number)
        self.assertEqual(expected, set(live))
        self.assertTrue(all(part["stock_count"] > 0 for part in live.values()))

    def test_spice_uses_generated_optical_current_and_correct_direction(self):
        netlist = (ROOT / "simulation/ir_spoke_link.cir").read_text()
        generated = (ROOT / "simulation/generated_params.inc").read_text()
        self.assertIn(".param IPHOTO_SIGNAL=", generated)
        self.assertIn("BPHOTO PD_K PD_A", netlist)
        self.assertNotRegex(netlist, r"\.param IPHOTO_SIGNAL=")

    def test_technical_html_documents_implemented_chain(self):
        page = (ROOT / "public/technical.html").read_text(encoding="utf-8")
        HTMLParser().feed(page)
        for token in (
            "25–50 kHz",
            "38 kHz default",
            "VEMD10940FX01",
            "TLV9062",
            "TLV7011",
            "RMT RX",
            "MCPWM",
            "16–48",
            "41 open connections",
            "ESP-IDF target compile",
        ):
            self.assertIn(token, page)


if __name__ == "__main__":
    unittest.main()
