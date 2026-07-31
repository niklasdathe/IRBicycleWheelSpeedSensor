import importlib.util
import csv
import hashlib
import json
import math
import re
import sqlite3
import unittest
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config/system.json").read_text())
DS = json.loads((ROOT / "docs/datasheet_values.json").read_text())
SIM_SPEC = importlib.util.spec_from_file_location(
    "ir_spoke_sim", ROOT / "simulation/ir_spoke_sim.py"
)
SIM_MODULE = importlib.util.module_from_spec(SIM_SPEC)
SIM_SPEC.loader.exec_module(SIM_MODULE)
SIM = SIM_MODULE.simulate()
SIM["robustness"] = SIM_MODULE.robustness_sweep(1000)


class TestSystem(unittest.TestCase):
    def test_requirements_are_unique_and_linked_to_verification(self):
        requirements = yaml.safe_load(
            (ROOT / "requirements/requirements.yaml").read_text(
                encoding="utf-8"
            )
        )["requirements"]
        requirement_ids = [item["id"] for item in requirements]
        self.assertEqual(len(requirement_ids), len(set(requirement_ids)))
        matrix = (
            ROOT / "requirements/verification_matrix.md"
        ).read_text(encoding="utf-8")
        matrix_ids = set(re.findall(r"\|\s*(T-[A-Z]+-\d+)\s*\|", matrix))
        for item in requirements:
            self.assertIn(item["verification"], matrix_ids, item["id"])

    def test_documentation_has_task_entry_points_and_explicit_status(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        docs_index = (
            ROOT / "docs/README.md"
        ).read_text(encoding="utf-8")
        for token in (
            "Hardware V0.1",
            "physical validation is still open",
            "System overview",
            "Getting started",
            "Development workflow",
            "Manufacturing",
            "Bring-up and test",
            "Source of truth",
            "No project license has been selected",
        ):
            self.assertIn(token, readme)
        for page in (
            "system_overview.md",
            "getting_started.md",
            "development.md",
            "manufacturing.md",
            "bringup.md",
            "reference_projects.md",
        ):
            self.assertIn(page, docs_index)
            self.assertTrue((ROOT / "docs" / page).is_file())

    def test_interactive_bom_is_synced_to_the_authoritative_pcb(self):
        manifest = json.loads(
            (ROOT / "docs/interactive_bom.json").read_text(encoding="utf-8")
        )

        def digest(relative: str) -> str:
            return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()

        def text_digest(relative: str) -> str:
            content = (ROOT / relative).read_text(encoding="utf-8")
            return hashlib.sha256(content.encode("utf-8")).hexdigest()

        self.assertEqual(manifest["generator_version"], "v2.11.2")
        self.assertEqual(
            manifest["generator_commit"],
            "de7fad7ead9b73cea7eb17afa02c6ce9ce17a6ab",
        )
        self.assertEqual(manifest["source_sha256"], digest(manifest["source"]))
        self.assertEqual(
            manifest["output_sha256"], text_digest(manifest["output"])
        )
        page = (ROOT / manifest["output"]).read_text(encoding="utf-8")
        for token in ("Manufacturer", "MPN", "LCSC", "JLCPCB", "Netlist"):
            self.assertIn(token, page)
        launcher = (ROOT / "Open-IR-Spoke-Sensor.cmd").read_text()
        self.assertIn("interactive_bom.py", launcher)
        self.assertIn("--watch --serve --open", launcher)

    def test_datasheet_values_cross_validate_manifest(self):
        o, a, p = CFG["optical"], CFG["analog_frontend"], CFG["power"]
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
        self.assertTrue(DS["VEMD10940FX01"]["daylight_blocking_filter"])
        self.assertEqual(
            p["esp32_wifi_tx_peak_ma"],
            DS["ESP32_S3_POWER"]["wifi_tx_peak_ma_80211b_21dbm"],
        )
        self.assertEqual(
            p["opamp_quiescent_ua_per_amplifier_typ"],
            DS["TLV9062"]["quiescent_current_ua_per_amplifier_typ"],
        )
        self.assertEqual(
            p["comparator_quiescent_ua_typ"],
            DS["TLV7011"]["quiescent_current_ua_typ"],
        )
        self.assertEqual(
            p["xiao_3v3_regulator_capacity_ma"],
            DS["ESP32_S3_POWER"]["xiao_3v3_output_current_ma"],
        )
        can = CFG["can"]
        self.assertEqual(
            can["controller_oscillator_hz"],
            DS["SEEED_XIAO_CAN"]["oscillator_hz"],
        )
        self.assertEqual(
            p["can_controller_active_ma_max"],
            DS["MCP2515"]["active_current_ma_max"],
        )
        self.assertEqual(
            p["can_transceiver_recessive_ma_max"],
            DS["SN65HVD230"]["recessive_supply_current_ma_max"],
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

    def test_every_transient_has_centered_blockage_and_extended_traces(self):
        for duration_ms in (2, 6, 12, 40):
            result = SIM_MODULE.simulate(parameters={"duration_ms": duration_ms})
            self.assertTrue(result["derived"]["center_blockage_visible"])
            time = np.asarray(result["traces"]["time_ms"])
            path = np.asarray(result["traces"]["transmission"])
            blocked_time = time[path < 0.5]
            self.assertTrue(blocked_time.size)
            self.assertAlmostEqual(
                float(np.mean(blocked_time)), duration_ms / 2, delta=0.15
            )
            for trace in (
                "irradiance_w_m2", "photodiode_ua", "tia_v",
                "ac_coupled_v", "bandpass_v", "threshold_v",
                "comparator_ideal", "comparator",
                "rmt_carrier_present", "blocked_digital",
            ):
                self.assertEqual(len(result["traces"][trace]), len(time))

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
        self.assertIn("rmt_new_copy_encoder", rmt)
        self.assertIn("rmt_rx_register_event_callbacks", rmt)
        self.assertIn("config->rmt_resolution_hz", rmt)
        self.assertIn("config->rmt_mem_block_symbols", rmt)
        self.assertIn("config->rmt_tx_queue_depth", rmt)
        self.assertIn("config->rx_demod_duty", rmt)
        self.assertIn("ticks_to_us", rmt)
        self.assertIn("cursor_us", rmt)
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

    def test_optional_xiao_can_has_no_pin_conflicts_and_fits_power_budget(self):
        can = CFG["can"]
        ir_pins = {CFG["esp32"]["tx_gpio"], CFG["esp32"]["rx_gpio"]}
        can_pins = {
            can["int_gpio_d6"], can["cs_gpio_d7"], can["sck_gpio_d8"],
            can["miso_gpio_d9"], can["mosi_gpio_d10"],
        }
        self.assertTrue(ir_pins.isdisjoint(can_pins))
        self.assertLessEqual(
            can["spi_clock_hz"],
            DS["MCP2515"]["spi_clock_hz_max_at_3v3_16mhz"],
        )
        result = SIM_MODULE.simulate(parameters={
            "can_enabled": 1,
            "can_bus_activity_duty": 1.0,
        })
        self.assertTrue(result["derived"]["within_xiao_3v3_capacity"])
        self.assertTrue(
            result["derived"]["within_esp32_recommended_supply_capacity"]
        )
        self.assertGreater(result["derived"]["can_current_ma_peak"], 0)
        adapter = (
            ROOT / "firmware/main/ir_spoke_can_mcp2515_adapter.c"
        ).read_text()
        self.assertIn("spi_bus_initialize", adapter)
        self.assertIn("_Static_assert", adapter)

    def test_no_integrated_receiver_in_bom(self):
        bom = (ROOT / "hardware/ir_spoke_link/bom_jlcpcb.csv").read_text()
        self.assertNotRegex(bom, r"TSOP57|integrated 38")
        for mpn in ("VEMD10940FX01", "TLV9062IDDFR", "TLV7011DCKR"):
            self.assertIn(mpn, bom)

    def test_panel_and_jlc_export_are_versioned_and_fail_closed(self):
        layout = json.loads(
            (ROOT / "hardware/ir_spoke_link/layout_manifest.json").read_text()
        )
        self.assertTrue(layout["required_drc"]["fabrication_ready"])
        self.assertEqual(layout["required_drc"]["violations"], 0)
        self.assertEqual(layout["required_drc"]["unconnected_pads"], 0)
        self.assertEqual(
            layout["footprint_rotations_deg"],
            {"U1": 0, "U2": 270, "J3": 0, "J4": 180, "D1": 0, "D2": 0},
        )
        self.assertEqual(
            layout["jlc_rotation_offsets_deg"],
            {"U1": 90, "U2": 90, "J3": 180, "J4": 180, "D1": 180, "D2": 0},
        )
        project = json.loads((ROOT / "project_manifest.json").read_text())
        export_dir = ROOT / project["canonical"]["jlc_export"]
        product = f"IR_Spoke_Sensor_{project['hardware_version']}_2L"
        with (export_dir / f"{product}_CPL.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            rotations = {
                row["Designator"]: float(row["Rotation"])
                for row in csv.DictReader(stream)
            }
        self.assertEqual(
            {ref: rotations[ref] for ref in ("U1", "U2", "J3", "J4", "D1", "D2")},
            {"U1": 90.0, "U2": 0.0, "J3": 180.0, "J4": 0.0, "D1": 180.0, "D2": 0.0},
        )
        export = (ROOT / "hardware/export_jlc.ps1").read_text()
        for token in (
            "IR_Spoke_Sensor_${Revision}_2L",
            "breakaway_tab_mm",
            "mouse_bite",
            "temporary_links",
            "Found 0 DRC violations",
            "Found 0 unconnected pads",
            "generate_jlc_assembly.py",
            "ORDER_PACKAGE.zip",
            "SHA256SUMS.txt",
        ):
            self.assertIn(token, export)

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
        connectivity = (
            ROOT / "simulation/generated_connectivity.inc"
        ).read_text()
        self.assertIn(".param IPHOTO_SIGNAL=", generated)
        self.assertIn(".include generated_connectivity.inc", netlist)
        self.assertIn("BPHOTO +3V3 PD_ANODE", connectivity)
        self.assertIn("RHARNESS_K LED_K_SWITCHED LED_K_REMOTE", connectivity)
        self.assertIn("RHARNESS_3V3 +3V3 +3V3_LED", connectivity)
        self.assertIn("BESP +3V3 GND", connectivity)
        self.assertIn("V3V3 +3V3 GND {VSUP}", connectivity)
        self.assertIn("V(+3V3_LED,LED_A)>0.039", netlist)
        self.assertIn(".param SUPPLY_RISE=", generated)
        self.assertNotRegex(netlist, r"\.param IPHOTO_SIGNAL=")
        self.assertIn("TRAN_STOP/2-SPOKE_BLOCK/2", netlist)

    def test_canonical_connectivity_drives_simulation_and_probes(self):
        manifest = json.loads(
            (ROOT / "hardware/connectivity.json").read_text()
        )
        main = manifest["boards"]["main"]["components"]
        remote = manifest["boards"]["remote"]["components"]
        self.assertEqual(main["J2"]["5"], main["J3"]["2"])
        self.assertEqual(main["J3"]["2"], "+3V3")
        self.assertEqual(main["Q1"]["2"], main["J3"]["1"])
        self.assertEqual(remote["J4"]["1"], remote["D1"]["1"])
        self.assertNotEqual(main["J3"]["1"], remote["J4"]["1"])
        self.assertNotEqual(main["J3"]["2"], remote["J4"]["2"])
        probe_nets = {
            pins["1"] for ref, pins in main.items() if ref.startswith("TP")
        }
        self.assertTrue(
            set(manifest["simulation"]["probe_nets"]) <= probe_nets
        )
        self.assertNotIn("PD_ANODE", probe_nets)
        generated = (
            ROOT / "simulation/generated_connectivity.inc"
        ).read_text()
        self.assertIn(
            f"CONNECTIVITY_SHA256={SIM['derived']['connectivity_sha256']}",
            generated,
        )

    def test_kicad_native_netlist_matches_canonical_connectivity(self):
        spec = importlib.util.spec_from_file_location(
            "validate_kicad_netlist",
            ROOT / "tools/validate_kicad_netlist.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.validate()

    def test_power_budget_and_transient_traces(self):
        d = SIM["derived"]
        self.assertTrue(d["within_xiao_3v3_capacity"])
        self.assertTrue(d["within_esp32_recommended_supply_capacity"])
        self.assertLess(d["gpio_source_current_utilization"], 0.1)
        self.assertLess(d["xiao_regulator_peak_utilization"], 0.7)
        self.assertGreater(d["system_current_ma_peak_estimate"], 380)
        self.assertGreater(d["system_current_ma_steady_average"], 80)
        for trace in (
            "led_current_ma", "esp32_current_ma", "afe_current_ma",
            "can_current_ma", "system_current_ma", "supply_voltage_v",
            "system_power_mw",
        ):
            self.assertEqual(
                len(SIM["traces"][trace]),
                len(SIM["traces"]["time_ms"]),
            )

    def test_konnect_database_matches_expected_schema_and_scope(self):
        manifest = json.loads(
            (ROOT / "hardware/konnect_database_manifest.json").read_text()
        )
        database = Path(manifest["database_path"])
        self.assertTrue(database.is_file())
        self.assertIn("subset", manifest["scope"])
        with sqlite3.connect(database) as connection:
            self.assertEqual(
                connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(components)")
            }
            self.assertTrue({
                "LCSC", "MFR_Part", "Package", "Manufacturer", "Library_Type",
                "Description", "Price", "Stock", "Category",
            }.issubset(columns))
            count = connection.execute(
                "SELECT COUNT(*) FROM components"
            ).fetchone()[0]
            self.assertEqual(count, manifest["rows"])
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM components WHERE Stock > 0"
                ).fetchone()[0],
                count,
            )
            library_counts = dict(connection.execute(
                "SELECT Library_Type, COUNT(*) FROM components GROUP BY Library_Type"
            ))
            self.assertEqual(library_counts, {
                "Basic": manifest["basic_rows"],
                "Extended": manifest["extended_rows"],
            })
            self.assertEqual(
                connection.execute(
                    "SELECT Library_Type FROM components WHERE LCSC='C2146'"
                ).fetchone()[0],
                "Basic",
            )
            self.assertEqual(
                connection.execute(
                    "SELECT Library_Type FROM components WHERE LCSC='C7104273'"
                ).fetchone()[0],
                "Extended",
            )

    def test_technical_html_documents_implemented_chain(self):
        page = (
            ROOT / "local_simulator/technical.html"
        ).read_text(encoding="utf-8")
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
            "197 segments",
            "392.27 mA",
            "460.27 mA",
            "MCP2515",
            "7.5 × 1.5 mm conductive tab",
            "70/70 pin-net matches",
            "daylight-blocking",
            "ESP-IDF target compile",
        ):
            self.assertIn(token, page)


if __name__ == "__main__":
    unittest.main()
