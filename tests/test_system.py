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


class TestSystem(unittest.TestCase):
    def test_datasheet_values_cross_validate_manifest(self):
        o, a = CFG["optical"], CFG["analog_frontend"]
        self.assertEqual(o["led_peak_nm"], DS["VSMB1940X01"]["peak_wavelength_nm_typ"])
        self.assertEqual(o["emitter_radiant_intensity_mw_sr_at_100ma_typ"], DS["VSMB1940X01"]["radiant_intensity_mw_sr_at_100ma_typ"])
        self.assertEqual(o["photodiode_capacitance_pf_typ"], DS["VEMD10940FX01"]["capacitance_pf_at_0v_typ"])
        self.assertEqual(a["opamp_gbw_hz_typ"], DS["TLV9062"]["gbw_hz_typ"])
        self.assertEqual(a["comparator_delay_ns_typ"], DS["TLV7011"]["propagation_delay_ns_typ"])
        for values in DS.values():
            self.assertTrue((ROOT / values["source"]).is_file())

    def test_led_current_and_cable_drop(self):
        tx = CFG["transmitter"]
        current_a = (tx["supply_v"] - tx["led_vf_v_typ"] - tx["driver_vce_sat_v_typ"]) / tx["led_series_ohm"]
        self.assertLessEqual(current_a * 1000, 50)
        self.assertLess(current_a * 1000, DS["VSMB1940X01"]["continuous_forward_current_ma_max"])
        loop_r = 2 * tx["cable_length_mm"] / 1000 * tx["cable_conductor_ohm_per_m"] + 2 * tx["connector_contact_ohm_max"]
        self.assertLess(current_a * loop_r, 0.025)

    def test_stress_blockage_within_capture_window(self):
        w, e = CFG["wheel"], CFG["esp32"]
        hz = (w["stress_speed_kmh"] / 3.6) / (math.pi * w["effective_diameter_m"])
        blocked_us = (w["spoke_width_mm"] / 1000) / (2 * math.pi * hz * w["beam_radius_m"]) * 1e6
        self.assertGreater(blocked_us, e["minimum_blocked_us"])
        self.assertLess(blocked_us, e["maximum_blocked_us"])

    def test_installed_filter_poles_bracket_carrier(self):
        a, f = CFG["analog_frontend"], CFG["optical"]["carrier_hz"]
        tia = 1 / (2 * math.pi * a["tia_feedback_ohm"] * a["tia_feedback_pf"] * 1e-12)
        hp = 1 / (2 * math.pi * a["ac_bias_ohm"] * a["ac_coupling_nf"] * 1e-9)
        lp = 1 / (2 * math.pi * a["gain_feedback_ohm"] * a["gain_feedback_pf"] * 1e-12)
        self.assertLess(hp, f)
        self.assertGreater(lp, f)
        self.assertLess(abs(tia / f - 1), 0.15)

    def test_transient_detection_and_headroom(self):
        d = SIM["derived"]
        self.assertGreater(d["tia_min_v"], 0.1)
        self.assertLess(d["tia_max_v"], CFG["analog_frontend"]["supply_v"] - 0.1)
        self.assertGreater(d["bandpass_peak_to_peak_v"], d["comparator_hysteresis_mv_typ"] / 1000)
        trace = np.asarray(SIM["traces"]["blocked_digital"], dtype=int)
        time = np.asarray(SIM["traces"]["time_ms"])
        edges = np.flatnonzero(np.diff(trace))
        widths = []
        for a, b in zip(edges, edges[1:]):
            if trace[a + 1] == 1:
                widths.append((time[b] - time[a]) * 1000)
        self.assertGreaterEqual(len(widths), 4)
        self.assertTrue(all(CFG["esp32"]["minimum_blocked_us"] <= x <= CFG["esp32"]["maximum_blocked_us"] for x in widths))

    def test_generated_firmware_and_adaptive_features(self):
        generated = (ROOT / "firmware/include/ir_spoke_generated.h").read_text()
        code = (ROOT / "firmware/include/spoke_learner.h").read_text()
        rmt = (ROOT / "firmware/esp32s3_rmt_example.cpp").read_text()
        self.assertRegex(generated, rf"kCarrierHz = {CFG['optical']['carrier_hz']}")
        for token in ("interval_lut_", "kLearningRate", "infer_count", "kOutlierSigma"):
            self.assertIn(token, code)
        self.assertIn("rmt_apply_carrier(*rx", rmt)
        self.assertNotIn("mcpwm_new_capture", rmt)

    def test_no_integrated_receiver_in_bom(self):
        bom = (ROOT / "hardware/ir_spoke_link/bom_jlcpcb.csv").read_text()
        self.assertNotRegex(bom, r"TSOP57|integrated 38")
        for mpn in ("VEMD10940FX01", "TLV9062IDDFR", "TLV7011DCKR"):
            self.assertIn(mpn, bom)

    def test_technical_html_documents_implemented_chain(self):
        page = (ROOT / "public/technical.html").read_text(encoding="utf-8")
        HTMLParser().feed(page)
        for token in (
            "38 kHz", "VEMD10940FX01", "TLV9062", "TLV7011",
            "RMT RX", "MCPWM", "16…48", "41 connections not routed",
            "ESP-IDF build and RMT receive loop",
        ):
            self.assertIn(token, page)


if __name__ == "__main__":
    unittest.main()
