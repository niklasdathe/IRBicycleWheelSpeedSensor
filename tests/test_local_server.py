import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulation"))
from local_server import Handler  # noqa: E402


class TestLocalSimulationApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def get_json(self, path):
        with urllib.request.urlopen(self.url + path) as response:
            return json.load(response)

    def post_json(self, path, payload):
        request = urllib.request.Request(
            self.url + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def test_static_ui_and_technical_reference_are_served(self):
        for path, token in (
            ("/", "IR Spoke Sensor / physical transient"),
            ("/technical.html", "technical reference"),
        ):
            with urllib.request.urlopen(self.url + path) as response:
                page = response.read().decode("utf-8")
            self.assertIn(token, page)

    def test_defaults_cover_runtime_and_adaptive_config(self):
        defaults = self.get_json("/api/defaults")
        keys = set(defaults["values"])
        self.assertTrue({
            "tx_gpio", "rx_gpio", "carrier_hz", "carrier_duty",
            "rmt_resolution_hz", "rmt_mem_block_symbols",
            "rmt_tx_queue_depth", "rx_demod_ratio", "rx_demod_duty",
            "rx_glitch_filter_us", "minimum_blocked_us",
            "maximum_blocked_us", "link_loss_timeout_us",
            "lut_bins", "learning_rate", "spoke_count_confidence_events",
            "outlier_sigma", "esp32_cpu_active_duty",
            "esp32_wifi_tx_duty", "supply_rise_us",
            "regulator_efficiency", "can_enabled",
            "can_bus_activity_duty",
        }.issubset(keys))

    def test_simulation_and_code_generation_share_values(self):
        defaults = self.get_json("/api/defaults")["values"]
        defaults.update({"carrier_hz": 42500, "rx_demod_ratio": 0.7,
                         "duration_ms": 6})
        simulation = self.post_json("/api/simulate", defaults)
        generated = self.post_json("/api/generate-code", defaults)
        self.assertEqual(simulation["derived"]["carrier_hz"], 42500)
        self.assertAlmostEqual(simulation["derived"]["rx_demod_hz"], 29750)
        self.assertTrue(simulation["derived"]["center_blockage_visible"])
        self.assertTrue(simulation["derived"]["within_xiao_3v3_capacity"])
        self.assertIn(".carrier_hz = 42500u", generated["code"])
        self.assertIn(".rmt_mem_block_symbols = 64u", generated["code"])
        self.assertIn(".rmt_tx_queue_depth = 2u", generated["code"])
        self.assertIn(".rx_demod_ratio = 0.7f", generated["code"])
        self.assertAlmostEqual(
            generated["derived"]["blocked_us"],
            simulation["derived"]["blocked_us"],
        )

    def test_invalid_rmt_relationship_is_rejected(self):
        defaults = self.get_json("/api/defaults")["values"]
        defaults["rx_gpio"] = defaults["tx_gpio"]
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post_json("/api/generate-code", defaults)
        self.assertEqual(caught.exception.code, 400)
        with caught.exception as response:
            error = json.load(response)
        self.assertIn("must be different", error["error"])

    def test_changed_physical_and_power_values_change_real_traces(self):
        defaults = self.get_json("/api/defaults")["values"]
        baseline = self.post_json("/api/simulate", defaults)
        changed_values = dict(defaults)
        changed_values.update({
            "distance_mm": 80,
            "esp32_wifi_tx_duty": 0.2,
            "supply_rise_us": 1200,
            "can_enabled": 1,
            "can_bus_activity_duty": 0.5,
        })
        changed = self.post_json("/api/simulate", changed_values)
        self.assertLess(
            changed["derived"]["signal_photocurrent_ua_nominal"],
            baseline["derived"]["signal_photocurrent_ua_nominal"],
        )
        self.assertGreater(
            changed["derived"]["system_current_ma_steady_average"],
            baseline["derived"]["system_current_ma_steady_average"],
        )
        self.assertNotEqual(
            changed["traces"]["bandpass_v"],
            baseline["traces"]["bandpass_v"],
        )
        self.assertNotEqual(
            changed["traces"]["supply_voltage_v"],
            baseline["traces"]["supply_voltage_v"],
        )
        self.assertGreater(
            max(changed["traces"]["can_current_ma"]),
            max(baseline["traces"]["can_current_ma"]),
        )


if __name__ == "__main__":
    unittest.main()
