#!/usr/bin/env python3
"""Generate and verify the README PCB render from the authoritative board."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "ir_spoke_link" / "ir_spoke_link.kicad_pcb"
OUTPUT = ROOT / "docs" / "images" / "ir_spoke_sensor_panel_r4_top.png"
MANIFEST = OUTPUT.with_suffix(".json")
WIDTH = 1200
HEIGHT = 1800
IMAGE_WIDTH = 1176
IMAGE_HEIGHT = 1768
RENDER_OPTIONS = (
    "--width", str(WIDTH),
    "--height", str(HEIGHT),
    "--side", "top",
    "--background", "opaque",
    "--quality", "high",
    "--preset", "follow_pcb_editor",
    "--floor",
    "--zoom", "0.95",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise SystemExit(f"README render is not a valid PNG: {path}")
    return struct.unpack(">II", header[16:24])


def find_kicad_cli() -> str:
    candidates = (
        os.environ.get("KICAD_CLI"),
        shutil.which("kicad-cli"),
        r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise SystemExit("KiCad CLI not found; set KICAD_CLI or add it to PATH")


def expected_metadata() -> dict[str, object]:
    return {
        "schema_version": 1,
        "generator": "KiCad CLI pcb render",
        "source": PCB.relative_to(ROOT).as_posix(),
        "source_sha256": sha256(PCB),
        "output": OUTPUT.relative_to(ROOT).as_posix(),
        "output_sha256": sha256(OUTPUT),
        "render_width": WIDTH,
        "render_height": HEIGHT,
        "image_width": IMAGE_WIDTH,
        "image_height": IMAGE_HEIGHT,
        "options": list(RENDER_OPTIONS),
    }


def generate() -> None:
    command = [
        find_kicad_cli(),
        "pcb", "render",
        "--output", str(OUTPUT),
        *RENDER_OPTIONS,
        str(PCB),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    if image_size(OUTPUT) != (IMAGE_WIDTH, IMAGE_HEIGHT):
        raise SystemExit("KiCad produced a README render with unexpected dimensions")
    metadata = expected_metadata()
    MANIFEST.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: README PCB render generated from {metadata['source_sha256'][:12]}")


def check() -> None:
    if not OUTPUT.is_file() or not MANIFEST.is_file():
        raise SystemExit("README PCB render or its sync manifest is missing")
    if image_size(OUTPUT) != (IMAGE_WIDTH, IMAGE_HEIGHT):
        raise SystemExit(
            f"README PCB render must be {IMAGE_WIDTH} x {IMAGE_HEIGHT} px"
        )
    recorded = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = expected_metadata()
    mismatches = {
        key: {"recorded": recorded.get(key), "actual": value}
        for key, value in expected.items()
        if recorded.get(key) != value
    }
    if mismatches:
        raise SystemExit(
            "README PCB render is stale:\n" + json.dumps(mismatches, indent=2)
        )
    print("PASS: README PCB render matches the current KiCad PCB")


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--generate", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.generate:
        generate()
    else:
        check()


if __name__ == "__main__":
    main()
