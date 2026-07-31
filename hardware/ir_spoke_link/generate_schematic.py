#!/usr/bin/env python3
"""Restore the verified, manually arranged KiCad schematic template."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "ir_spoke_link.layout.kicad_sch"
OUT = HERE / "ir_spoke_link.kicad_sch"
MANIFEST = HERE / "layout_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if not TEMPLATE.is_file() or not MANIFEST.is_file():
    raise SystemExit(
        "Captured schematic layout is missing. Run capture_layout.py after "
        "saving and closing KiCad."
    )
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
if sha256(TEMPLATE) != manifest["schematic_sha256"]:
    raise SystemExit("Captured schematic template hash does not match manifest")

temporary = OUT.with_suffix(".kicad_sch.tmp")
shutil.copyfile(TEMPLATE, temporary)
os.replace(temporary, OUT)
if sha256(OUT) != manifest["schematic_sha256"]:
    raise SystemExit("Generated schematic is not byte-identical to template")
print(OUT)
