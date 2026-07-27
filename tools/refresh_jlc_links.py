#!/usr/bin/env python3
"""Refresh the auditable LCSC/JLCPCB metadata snapshot used by the project."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOMS = (
    ROOT / "hardware/ir_spoke_link/bom_jlcpcb.csv",
    ROOT / "hardware/remote_emitter/bom_jlcpcb.csv",
    ROOT / "hardware/cable_bom.csv",
)
OUTPUT = ROOT / "hardware/jlcpcb_parts_snapshot.json"


def cli_path() -> str:
    found = shutil.which("jlcpcb")
    if found:
        return found
    fallback = (
        Path(os.environ["APPDATA"])
        / "Python/Python314/Scripts/jlcpcb.exe"
    )
    if fallback.is_file():
        return str(fallback)
    raise SystemExit("jlcpcb CLI not found")


def part_numbers() -> list[str]:
    result: set[str] = set()
    for path in BOMS:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                number = row.get("LCSC Part Number", "").strip()
                if number.startswith("C") and number[1:].isdigit():
                    result.add(number)
    return sorted(result, key=lambda value: int(value[1:]))


def main() -> None:
    executable = cli_path()
    parts = []
    for number in part_numbers():
        process = subprocess.run(
            [executable, "--json", "part", "get", number],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={
                **os.environ,
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
            },
        )
        if process.returncode:
            parts.append({"lcsc": number, "error": process.stderr.strip()})
            continue
        payload = json.loads(process.stdout)
        payload["lcsc"] = number
        parts.append(payload)
    snapshot = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": "JLCPCB Parts API via jlcpcb CLI",
        "preference": "Basic when electrically compatible; otherwise Extended",
        "boms": [str(path.relative_to(ROOT)) for path in BOMS],
        "parts": parts,
    }
    OUTPUT.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"{len(parts)} parts -> {OUTPUT}")


if __name__ == "__main__":
    main()
