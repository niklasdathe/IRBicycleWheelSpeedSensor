#!/usr/bin/env python3
"""Refresh the auditable LCSC/JLCPCB metadata snapshot used by the project."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOMS = (
    ROOT / "hardware/ir_spoke_link/bom_jlcpcb.csv",
    ROOT / "hardware/cable_bom.csv",
)
OUTPUT = ROOT / "hardware/jlcpcb_parts_snapshot.json"


def cli_command() -> list[str]:
    # Invoke the module through the same interpreter as this script.  The
    # Windows console-script shim may point at a stale interpreter and fail
    # even though the package is installed in the active Python user site.
    candidates = [
        Path(r"C:\Python314\python.exe"),
        Path(sys.executable),
    ]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        probe = subprocess.run(
            [str(candidate), "-c", "import jlcpcb.cli"],
            check=False,
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            return [
                str(candidate),
                "-c",
                "from jlcpcb.cli import main; main()",
            ]
    raise SystemExit(
        "No Python interpreter with the jlcpcb package was found"
    )


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
    command = cli_command()
    parts = []
    for number in part_numbers():
        process = subprocess.run(
            [*command, "--json", "part", "get", number],
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
            raise SystemExit(
                f"JLCPCB lookup failed for {number}: "
                f"{process.stderr.strip() or process.stdout.strip()}"
            )
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
