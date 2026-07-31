#!/usr/bin/env python3
"""Verify that KiCad opens the authoritative captured project files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE / "ir_spoke_link.kicad_pro"
SCHEMATIC = HERE / "ir_spoke_link.kicad_sch"
BOARD = HERE / "ir_spoke_link.kicad_pcb"
BOARD_TEMPLATE = HERE / "ir_spoke_link.layout.kicad_pcb"
MANIFEST = HERE / "layout_manifest.json"
LOCKS = (
    HERE / "~ir_spoke_link.kicad_pro.lck",
    HERE / "~ir_spoke_link.kicad_pcb.lck",
)
SCHEMATIC_UUID = "cd4e8c83-0eaa-4789-8c24-0e0e878cde96"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    required = (PROJECT, SCHEMATIC, BOARD, BOARD_TEMPLATE, MANIFEST)
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing authoritative KiCad files: " + ", ".join(missing))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest["pcb_sha256"]
    if sha256(BOARD_TEMPLATE) != expected:
        raise SystemExit("Captured PCB template does not match layout manifest")
    if sha256(BOARD) != expected:
        raise SystemExit(
            "Main PCB differs from the captured layout. Save/close KiCad and "
            "run capture_layout.py intentionally before opening another copy."
        )

    project = json.loads(PROJECT.read_text(encoding="utf-8"))
    top_level = [
        {
            "filename": SCHEMATIC.name,
            "name": SCHEMATIC.stem,
            "uuid": SCHEMATIC_UUID,
        }
    ]
    current = project.setdefault("schematic", {}).get("top_level_sheets")
    if current != top_level:
        if any(path.exists() for path in LOCKS):
            raise SystemExit(
                "KiCad is already open; refusing to rewrite the project entry."
            )
        project["schematic"]["top_level_sheets"] = top_level
        PROJECT.write_text(
            json.dumps(project, indent=2) + "\n", encoding="utf-8"
        )
    print(f"PASS: authoritative KiCad project -> {SCHEMATIC.name}, {BOARD.name}")


if __name__ == "__main__":
    main()
