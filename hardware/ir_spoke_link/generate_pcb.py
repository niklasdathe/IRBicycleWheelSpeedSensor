#!/usr/bin/env python3
"""Restore the verified, manually routed KiCad carrier PCB template."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "ir_spoke_link.layout.kicad_pcb"
PREFERENCES_TEMPLATE = HERE / "ir_spoke_link.layout.kicad_prl"
OUT = HERE / "ir_spoke_link.kicad_pcb"
PREFERENCES = HERE / "ir_spoke_link.kicad_prl"
MANIFEST = HERE / "layout_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        text=True,
        encoding="utf-8",
    ).strip()


if not all(path.is_file() for path in (
    TEMPLATE, PREFERENCES_TEMPLATE, MANIFEST
)):
    raise SystemExit(
        "Captured PCB layout is missing. Run capture_layout.py after saving "
        "and closing KiCad."
    )
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
if sha256(TEMPLATE) != manifest["pcb_sha256"]:
    raise SystemExit("Captured PCB template hash does not match manifest")
if sha256(PREFERENCES_TEMPLATE) != manifest["preferences_sha256"]:
    raise SystemExit("Captured PCB preferences hash does not match manifest")
if routing_signature(TEMPLATE) != manifest["routing_sha256"]:
    raise SystemExit("Captured PCB routing does not match manifest")
if route_text_signature(TEMPLATE) != manifest["route_text_sha256"]:
    raise SystemExit("Captured raw segment/via/arc text does not match manifest")

temporary = OUT.with_suffix(".kicad_pcb.tmp")
shutil.copyfile(TEMPLATE, temporary)
os.replace(temporary, OUT)
preferences_temporary = PREFERENCES.with_suffix(".kicad_prl.tmp")
shutil.copyfile(PREFERENCES_TEMPLATE, preferences_temporary)
os.replace(preferences_temporary, PREFERENCES)
if sha256(OUT) != manifest["pcb_sha256"]:
    raise SystemExit("Generated PCB is not byte-identical to routed template")
if routing_signature(OUT) != manifest["routing_sha256"]:
    raise SystemExit("Generated PCB routing does not match manifest")
if route_text_signature(OUT) != manifest["route_text_sha256"]:
    raise SystemExit("Generated raw segment/via/arc text does not match manifest")
print(OUT)
