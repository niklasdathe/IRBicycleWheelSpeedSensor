#!/usr/bin/env python3
"""Verify footprint completeness, metadata, mechanics and canonical wiring."""

import json
import math
import hashlib
from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parent
CONNECTIVITY = json.loads((ROOT / "connectivity.json").read_text(encoding="utf-8"))
CATALOG = json.loads(
    (ROOT / "component_catalog.json").read_text(encoding="utf-8")
)
EXPECTED = {
    "ir_spoke_link/ir_spoke_link.kicad_pcb": {
        "J1": set("1234567"), "J2": set("1234567"), "J3": {"1","2","MP"},
        "D2": {"1","2","3"}, "U1": set("12345678"), "U2": set("12345"),
        "Q1": set("123"), "R2": {"1","2"}, "R3": {"1","2"}, "R4": {"1","2"},
        "R5": {"1","2"}, "R6": {"1","2"}, "R7": {"1","2"}, "R8": {"1","2"},
        "R9": {"1","2"}, "R10": {"1","2"}, "R11": {"1","2"},
        "C1": {"1","2"}, "C2": {"1","2"}, "C3": {"1","2"}, "C4": {"1","2"},
        "C5": {"1","2"}, "C6": {"1","2"},
        "TP1": {"1"}, "TP2": {"1"}, "TP3": {"1"}, "TP4": {"1"},
        "TP5": {"1"}, "TP6": {"1"}, "TP7": {"1"}, "TP8": {"1"},
        "J4": {"1","2","MP"}, "R1": {"1","2"}, "D1": {"1","2"},
        "MH1": {"1"}, "MH2": {"1"},
        "NT1": {"1","2"}, "NT2": {"1","2"},
        "MB1": {""}, "MB2": {""}, "MB3": {""}, "MB4": {""}, "MB5": {""},
        "G***": set(),
    },
}
BOARD_NAMES = {
    "ir_spoke_link/ir_spoke_link.kicad_pcb": "main",
}
EXPECTED_ROTATIONS = {
    "main": {
        "U1": 0, "U2": 270, "J3": 0, "J4": 180, "D1": 0, "D2": 0,
    },
}

failures = []
PANEL_REFS = {"NT1", "NT2", "MB1", "MB2", "MB3", "MB4", "MB5"}
GRAPHIC_REFS = {"G***"}
for rel, expected in EXPECTED.items():
    board_path = ROOT / rel
    board = pcbnew.LoadBoard(str(board_path))
    found = {fp.GetReference(): fp for fp in board.GetFootprints()}
    board_name = BOARD_NAMES[rel]
    catalog = CATALOG[board_name]
    for reference, expected_angle in EXPECTED_ROTATIONS[board_name].items():
        footprint = found.get(reference)
        if footprint is None:
            failures.append(f"{rel}: missing rotation-audited {reference}")
            continue
        actual_angle = round(footprint.GetOrientationDegrees()) % 360
        if actual_angle != expected_angle:
            failures.append(
                f"{rel}: {reference} physical rotation {actual_angle} != "
                f"{expected_angle}; JLC corrections belong only in the CPL"
            )
    polarity_expectations = {
        "D1": {"1": "LED_K_REMOTE", "2": "LED_A"},
    }
    if board_name == "main":
        polarity_expectations["D2"] = {
            "1": "+3V3",
            "2": "NC_MECHANICAL",
            "3": "PD_ANODE",
        }
    for reference, expected_nets in polarity_expectations.items():
        footprint = found.get(reference)
        if footprint is None:
            failures.append(f"{rel}: missing polarity-audited {reference}")
            continue
        actual_nets = {
            pad.GetNumber(): pad.GetNetname() for pad in footprint.Pads()
        }
        if actual_nets != expected_nets:
            failures.append(
                f"{rel}: {reference} polarity map {actual_nets} != "
                f"{expected_nets}"
            )
    if set(found) != set(expected):
        failures.append(
            f"{rel}: footprint set {sorted(found)} != {sorted(expected)}"
        )
    for ref, pads in expected.items():
        if ref not in found:
            failures.append(f"{rel}: missing footprint {ref}")
            continue
        footprint = found[ref]
        actual = {pad.GetNumber() for pad in found[ref].Pads()}
        if actual != pads:
            failures.append(f"{rel}: {ref} pads {sorted(actual)} != {sorted(pads)}")
        connectivity_board = (
            "remote" if ref in CONNECTIVITY["boards"]["remote"]["components"]
            else "main"
        )
        for pad in found[ref].Pads():
            if (
                ref not in {"MH1", "MH2"} | PANEL_REFS
                and pad.GetNumber() != "MP"
                and not pad.GetNetname()
            ):
                failures.append(f"{rel}: {ref}.{pad.GetNumber()} has no net")
            expected_net = CONNECTIVITY["boards"][connectivity_board][
                "components"
            ].get(ref, {}).get(pad.GetNumber())
            if expected_net and pad.GetNetname() != expected_net:
                failures.append(
                    f"{rel}: {ref}.{pad.GetNumber()} net "
                    f"{pad.GetNetname()} != canonical {expected_net}"
                )
        if ref in PANEL_REFS:
            # Board-only, DNI panelization features are deliberately absent
            # from the schematic, BOM, placement file and component catalog.
            continue
        if ref in GRAPHIC_REFS:
            if actual:
                failures.append(f"{rel}: {ref} board graphic has pads")
            if not list(footprint.GraphicalItems()):
                failures.append(
                    f"{rel}: {ref} board graphic has no graphic primitives"
                )
            continue
        catalog_entry = (
            CATALOG["remote"].get(ref)
            if ref in CATALOG["remote"]
            else catalog.get(ref)
        )
        if ref in {"MH1", "MH2"}:
            catalog_entry = {
                "Datasheet": "Mechanical mounting feature; DNI",
                "Description":
                    "M2.5 plated mounting hole, 2.7 mm drill with top/bottom pad",
                "Manufacturer": "Mechanical",
                "MPN": "M2.5 plated mounting hole",
                "LCSC": "DNI",
                "JLCPCB": "DNI",
            }
        for field_name in (
            "Datasheet", "Description", "Manufacturer", "MPN", "LCSC",
            "JLCPCB",
        ):
            if not footprint.HasField(field_name):
                failures.append(f"{rel}: {ref} lacks {field_name} field")
                continue
            actual_value = footprint.GetField(field_name).GetText().strip()
            expected_value = catalog_entry[field_name]
            if not actual_value:
                failures.append(f"{rel}: {ref} has empty {field_name} field")
            elif actual_value != expected_value:
                failures.append(
                    f"{rel}: {ref} {field_name} {actual_value!r} != "
                    f"catalog {expected_value!r}"
                )
        datasheet = catalog_entry["Datasheet"].replace(
            "${KIPRJMOD}", str(board_path.parent)
        )
        if ref not in {"MH1", "MH2"} and not Path(datasheet).resolve().is_file():
            failures.append(
                f"{rel}: {ref} datasheet path does not exist: {datasheet}"
            )

        graphics = list(footprint.GraphicalItems())
        courtyard_layers = {pcbnew.F_CrtYd, pcbnew.B_CrtYd}
        if not any(item.GetLayer() in courtyard_layers for item in graphics):
            failures.append(f"{rel}: {ref} lacks courtyard geometry")

        # A bare PCB test pad intentionally has no body or 3D model. All
        # assembled footprints must additionally have fabrication and 3D data.
        if not ref.startswith("TP") and ref not in {"MH1", "MH2"}:
            if not any(item.GetLayer() == pcbnew.F_Fab for item in graphics):
                failures.append(f"{rel}: {ref} lacks F.Fab geometry")
            models = list(footprint.Models())
            if not models:
                failures.append(f"{rel}: {ref} lacks a 3D model")
            for model in models:
                model_path = model.m_Filename
                replacements = {
                    "${KIPRJMOD}": str(board_path.parent),
                    "${KICAD10_3DMODEL_DIR}":
                        r"C:\Program Files\KiCad\10.0\share\kicad\3dmodels",
                    "${KICAD9_3DMODEL_DIR}":
                        r"C:\Program Files\KiCad\10.0\share\kicad\3dmodels",
                }
                for variable, value in replacements.items():
                    model_path = model_path.replace(variable, value)
                if not Path(model_path).resolve().is_file():
                    failures.append(
                        f"{rel}: {ref} unresolved 3D model "
                        f"{model.m_Filename}"
                    )

    if board_name == "main":
        edge_items = [
            drawing for drawing in board.GetDrawings()
            if drawing.GetLayer() == pcbnew.Edge_Cuts
            and isinstance(drawing, pcbnew.PCB_SHAPE)
        ]
        outline_points = []
        for item in edge_items:
            outline_points.extend((item.GetStart(), item.GetEnd()))
            if item.GetShape() == pcbnew.SHAPE_T_ARC:
                outline_points.append(item.GetArcMid())
        x_values = [pcbnew.ToMM(point.x) for point in outline_points]
        y_values = [pcbnew.ToMM(point.y) for point in outline_points]
        min_x, min_y = min(x_values), min(y_values)
        main_left, main_top = 138.525, 96.450

        j1 = found["J1"].GetPosition()
        j2 = found["J2"].GetPosition()
        x1, y1 = pcbnew.ToMM(j1.x), pcbnew.ToMM(j1.y)
        x2, y2 = pcbnew.ToMM(j2.x), pcbnew.ToMM(j2.y)
        for label, actual_value, expected_value in (
            ("J1 x", x1, main_left + 1.28),
            ("J1 y", y1, main_top + 3.08),
            ("J2 x", x2, main_left + 16.52),
            ("J2 y", y2, main_top + 3.08),
            ("header row separation", x2 - x1, 15.24),
        ):
            if not math.isclose(
                actual_value, expected_value, abs_tol=0.005
            ):
                failures.append(
                    f"{rel}: {label} {actual_value:.3f} mm != "
                    f"{expected_value:.3f} mm"
                )
        segments = [
            item for item in edge_items
            if item.GetShape() == pcbnew.SHAPE_T_SEGMENT
        ]
        arcs = [
            item for item in edge_items
            if item.GetShape() == pcbnew.SHAPE_T_ARC
        ]
        if len(segments) != 12 or len(arcs) != 8:
            failures.append(
                f"{rel}: breakaway outline needs 12 segments and 8 arcs; "
                f"found {len(segments)} and {len(arcs)}"
            )
        for arc in arcs:
            radius = pcbnew.ToMM(arc.GetRadius())
            if not math.isclose(radius, 1.905, abs_tol=0.01):
                failures.append(
                    f"{rel}: corner radius {radius:.3f} mm != 1.905 mm"
                )
        dimensions = (
            max(x_values) - min(x_values),
            max(y_values) - min(y_values),
        )
        if not (
            math.isclose(dimensions[0], 21.0, abs_tol=0.01)
            and math.isclose(dimensions[1], 37.9, abs_tol=0.01)
        ):
            failures.append(
                f"{rel}: outline is {dimensions[0]:.3f} x "
                f"{dimensions[1]:.3f} mm, expected 21.0 x 37.9 mm"
            )
        main_dimensions = (17.8, 21.4)
        main_right = main_left + main_dimensions[0]
        main_bottom = main_top + main_dimensions[1]
        receiver_points = []
        transmitter_points = []
        for item in edge_items:
            points = [item.GetStart(), item.GetEnd()]
            if item.GetShape() == pcbnew.SHAPE_T_ARC:
                points.append(item.GetArcMid())
            point_y = [pcbnew.ToMM(point.y) for point in points]
            if max(point_y) <= main_bottom + 0.005:
                receiver_points.extend(points)
            if min(point_y) >= 119.350 - 0.005:
                transmitter_points.extend(points)
        receiver_bounds = (
            min(pcbnew.ToMM(point.x) for point in receiver_points),
            min(pcbnew.ToMM(point.y) for point in receiver_points),
            max(pcbnew.ToMM(point.x) for point in receiver_points),
            max(pcbnew.ToMM(point.y) for point in receiver_points),
        )
        transmitter_bounds = (
            min(pcbnew.ToMM(point.x) for point in transmitter_points),
            min(pcbnew.ToMM(point.y) for point in transmitter_points),
            max(pcbnew.ToMM(point.x) for point in transmitter_points),
            max(pcbnew.ToMM(point.y) for point in transmitter_points),
        )
        if not all(
            math.isclose(actual, expected, abs_tol=0.005)
            for actual, expected in zip(
                receiver_bounds,
                (main_left, main_top, main_right, main_bottom),
            )
        ):
            failures.append(
                f"{rel}: receiver bounds {receiver_bounds} != "
                "(138.525, 96.450, 156.325, 117.850) mm"
            )
        if not all(
            math.isclose(actual, expected, abs_tol=0.005)
            for actual, expected in zip(
                transmitter_bounds,
                (136.925, 119.350, 157.925, 134.350),
            )
        ):
            failures.append(
                f"{rel}: transmitter bounds {transmitter_bounds} != "
                "(136.925, 119.350, 157.925, 134.350) mm"
            )
        for label, actual_value, expected_value in (
            ("receiver left", main_left, 138.525),
            ("receiver right", main_right, 156.325),
            ("receiver top", main_top, 96.450),
            ("receiver bottom", main_bottom, 117.850),
        ):
            if not math.isclose(actual_value, expected_value, abs_tol=0.005):
                failures.append(
                    f"{rel}: {label} {actual_value:.3f} != "
                    f"{expected_value:.3f} mm"
                )

        tracks = [
            item for item in board.GetTracks()
            if not isinstance(item, pcbnew.PCB_VIA)
        ]
        vias = [
            item for item in board.GetTracks()
            if isinstance(item, pcbnew.PCB_VIA)
        ]
        if len(tracks) != 197 or len(vias) != 12:
            failures.append(
                f"{rel}: expected 197 user-routed segments and 12 vias; found "
                f"{len(tracks)} and {len(vias)}"
            )
        for track in tracks:
            width = pcbnew.ToMM(track.GetWidth())
            if not any(
                math.isclose(width, expected, abs_tol=0.001)
                for expected in (0.20, 0.25)
            ):
                failures.append(
                    f"{rel}: track width {width:.3f} mm is not "
                    "0.200/0.250 mm"
                )
            if track.GetLayer() not in (pcbnew.F_Cu, pcbnew.B_Cu):
                failures.append(
                    f"{rel}: routed segment is on non-copper layer "
                    f"{track.GetLayerName()}"
                )
            if not track.GetNetname():
                failures.append(f"{rel}: routed segment has no net")
        for via in vias:
            diameter = pcbnew.ToMM(via.GetWidth(pcbnew.F_Cu))
            drill = pcbnew.ToMM(via.GetDrillValue())
            if not (
                math.isclose(diameter, 0.60, abs_tol=0.001)
                and math.isclose(drill, 0.30, abs_tol=0.001)
            ):
                failures.append(
                    f"{rel}: via {diameter:.3f}/{drill:.3f} mm != "
                    "0.600/0.300 mm"
                )
            if not via.GetNetname():
                failures.append(f"{rel}: via has no net")

        zones = list(board.Zones())
        if len(zones) != 1:
            failures.append(
                f"{rel}: expected one B.Cu GND zone; "
                f"found {len(zones)}"
            )
        else:
            zone = next((z for z in zones if z.GetNetname() == "GND"), None)
            if zone is None or not zone.GetLayerSet().Contains(pcbnew.B_Cu):
                failures.append(
                    f"{rel}: copper zone must include B.Cu/GND"
                )
            elif not zone.IsFilled():
                failures.append(f"{rel}: B.Cu GND zone is not filled")
            if zone is not None and not math.isclose(
                pcbnew.ToMM(zone.GetLocalClearance()), 0.50, abs_tol=0.001
            ):
                failures.append(
                    f"{rel}: zone clearance "
                    f"{pcbnew.ToMM(zone.GetLocalClearance()):.3f} mm != "
                    "0.500 mm"
                )
        break_y = 118.600
        for index, expected_x in enumerate(
            (144.175, 145.675, 147.175, 148.675, 150.175), start=1
        ):
            hole = found[f"MB{index}"]
            pos = hole.GetPosition()
            drill = next(iter(hole.Pads())).GetDrillSize()
            if not (
                math.isclose(pcbnew.ToMM(pos.x), expected_x, abs_tol=0.005)
                and math.isclose(
                    pcbnew.ToMM(pos.y), break_y, abs_tol=0.005
                )
                and math.isclose(
                    pcbnew.ToMM(drill.x), 0.50, abs_tol=0.005
                )
            ):
                failures.append(
                    f"{rel}: MB{index} is not the expected 0.5 mm "
                    "breakaway perforation"
                )
        expected_ties = {
            "NT1": {"LED_K_SWITCHED", "LED_K_REMOTE"},
            "NT2": {"+3V3", "+3V3_LED"},
        }
        for reference, expected_nets in expected_ties.items():
            tie = found[reference]
            actual_nets = {pad.GetNetname() for pad in tie.Pads()}
            if (
                actual_nets != expected_nets
                or not math.isclose(
                    pcbnew.ToMM(tie.GetPosition().y),
                    break_y,
                    abs_tol=0.005,
                )
            ):
                failures.append(
                    f"{rel}: {reference} does not bridge "
                    f"{sorted(expected_nets)} at the break line"
                )
        led = found["D1"].GetPosition()
        led_x, led_y = pcbnew.ToMM(led.x), pcbnew.ToMM(led.y)
        for ref, expected_x in (("MH1", 140.000), ("MH2", 154.925)):
            hole = found[ref]
            pos = hole.GetPosition()
            if not (
                math.isclose(pcbnew.ToMM(pos.x), expected_x, abs_tol=0.01)
                and math.isclose(
                    pcbnew.ToMM(pos.y), 131.250, abs_tol=0.01
                )
                and math.isclose(
                    pcbnew.ToMM(next(iter(hole.Pads())).GetDrillSize().x),
                    2.7, abs_tol=0.01,
                )
            ):
                failures.append(
                    f"{rel}: {ref} is not the expected 2.7 mm M2.5 hole"
                )

        manifest_path = board_path.parent / "layout_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(board_path.read_bytes()).hexdigest()
        if digest != manifest["pcb_sha256"]:
            failures.append(
                f"{rel}: PCB differs from captured routed layout template"
            )
        preferences_path = board_path.with_suffix(".kicad_prl")
        preferences = json.loads(preferences_path.read_text(encoding="utf-8"))
        visible_layers = preferences["board"]["visible_layers"]
        # The final byte contains F.CrtYd/B.CrtYd visibility bits in KiCad 10.
        if not visible_layers.endswith("ffffff7f"):
            failures.append(
                f"{rel}: front/back courtyard layers are not both visible"
            )

if failures:
    raise SystemExit("\n".join(failures))
print(
    f"PASS: {sum(len(x) for x in EXPECTED.values())} footprints; "
    "pads, nets, local datasheets, descriptions, 3D models and XIAO mechanics "
    "verified"
)
