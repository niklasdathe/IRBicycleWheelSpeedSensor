#!/usr/bin/env python3
"""Capture the current KiCad-authored schematic and routed PCB as templates."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KICAD_CLI = Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")
SCHEMATIC = HERE / "ir_spoke_link.kicad_sch"
BOARD = HERE / "ir_spoke_link.kicad_pcb"
PREFERENCES = HERE / "ir_spoke_link.kicad_prl"
SCHEMATIC_TEMPLATE = HERE / "ir_spoke_link.layout.kicad_sch"
BOARD_TEMPLATE = HERE / "ir_spoke_link.layout.kicad_pcb"
PREFERENCES_TEMPLATE = HERE / "ir_spoke_link.layout.kicad_prl"
MANIFEST = HERE / "layout_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_checked(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def routing_signature(path: Path) -> str:
    code = (
        "import sys, pcbnew; "
        f"sys.path.insert(0, {str(HERE)!r}); "
        "from layout_integrity import routing_signature; "
        f"print(routing_signature(pcbnew.LoadBoard({str(path)!r})))"
    )
    return subprocess.check_output(
        [
            r"C:\Program Files\KiCad\10.0\bin\python.exe",
            "-c",
            code,
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).strip()


def route_text_signature(path: Path) -> str:
    code = (
        "import sys,pathlib; "
        f"sys.path.insert(0, {str(HERE)!r}); "
        "from layout_integrity import route_text_signature; "
        f"print(route_text_signature(pathlib.Path({str(path)!r})"
        ".read_text(encoding='utf-8')))"
    )
    return subprocess.check_output(
        [
            r"C:\Program Files\KiCad\10.0\bin\python.exe",
            "-c",
            code,
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).strip()


def main() -> None:
    locks = [
        path
        for path in (
            HERE / "~ir_spoke_link.kicad_sch.lck",
            HERE / "~ir_spoke_link.kicad_pcb.lck",
            HERE / "~ir_spoke_link.layout.kicad_sch.lck",
            HERE / "~ir_spoke_link.layout.kicad_pcb.lck",
        )
        if path.exists()
    ]
    if locks:
        raise SystemExit(
            "Close KiCad editors before capturing layout: "
            + ", ".join(path.name for path in locks)
        )

    route = routing_signature(BOARD)
    route_text = route_text_signature(BOARD)

    with tempfile.TemporaryDirectory(prefix="ir-spoke-capture-") as temp:
        temp_path = Path(temp)
        drc = temp_path / "drc.rpt"
        erc = temp_path / "erc.rpt"
        run_checked([
            str(KICAD_CLI), "pcb", "drc", "--refill-zones",
            "--output", str(drc), str(BOARD),
        ])
        drc_text = drc.read_text(encoding="utf-8")
        violation_match = re.search(
            r"\*\* Found (\d+) DRC violations \*\*", drc_text
        )
        unconnected_match = re.search(
            r"\*\* Found (\d+) unconnected pads \*\*", drc_text
        )
        if not violation_match or not unconnected_match:
            raise SystemExit("PCB capture refused: unrecognized DRC report")
        violation_count = int(violation_match.group(1))
        unconnected_count = int(unconnected_match.group(1))
        hard_fail_types = (
            "[shorting_items]", "[clearance]", "[hole_clearance]",
            "[copper_edge_clearance]", "[courtyards_overlap]",
        )
        if any(kind in drc_text for kind in hard_fail_types):
            raise SystemExit(
                "PCB capture refused: electrical/mechanical DRC errors remain"
            )
        if violation_count != 0 or unconnected_count != 0:
            raise SystemExit("PCB capture refused: DRC or unrouted items remain")

        run_checked([
            str(KICAD_CLI), "sch", "erc",
            "--output", str(erc), str(SCHEMATIC),
        ])
        erc_text = erc.read_text(encoding="utf-8")
        if "Errors 0" not in erc_text:
            raise SystemExit("Schematic capture refused: ERC errors remain")

    run_checked([sys.executable, str(ROOT / "tools/validate_kicad_netlist.py")])

    shutil.copy2(SCHEMATIC, SCHEMATIC_TEMPLATE)
    shutil.copy2(BOARD, BOARD_TEMPLATE)
    shutil.copy2(PREFERENCES, PREFERENCES_TEMPLATE)
    manifest = {
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "source": "manually arranged KiCad 10 schematic and routed PCB",
        "schematic_sha256": sha256(SCHEMATIC_TEMPLATE),
        "pcb_sha256": sha256(BOARD_TEMPLATE),
        "routing_sha256": route,
        "route_text_sha256": route_text,
        "preferences_sha256": sha256(PREFERENCES_TEMPLATE),
        "footprint_rotations_deg": {
            "U1": 0,
            "U2": 270,
            "J3": 0,
            "J4": 180,
            "D1": 0,
            "D2": 0,
        },
        "jlc_rotation_offsets_deg": {
            "U1": 90,
            "U2": 90,
            "J3": 180,
            "J4": 180,
            "D1": 180,
            "D2": 0,
        },
        "required_drc": {
            "violations": violation_count,
            "unconnected_pads": unconnected_count,
            "fabrication_ready": (
                violation_count == 0 and unconnected_count == 0
            ),
            "capture_mode": "fabrication_ready",
        },
        "required_schematic_net_endpoints": 70,
    }
    MANIFEST.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
