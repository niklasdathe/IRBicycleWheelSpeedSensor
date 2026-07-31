#!/usr/bin/env python3
"""Validate independent hardware/software version ownership and release links."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_version(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8").strip()


def main() -> None:
    manifest = json.loads((ROOT / "project_manifest.json").read_text(encoding="utf-8"))
    hardware = read_version("hardware/VERSION")
    software = read_version("firmware/VERSION")
    ordered = manifest["ordered_hardware_version"]
    failures: list[str] = []

    if not re.fullmatch(r"V\d+\.\d+(?:-dev)?", hardware):
        failures.append(f"invalid hardware version: {hardware}")
    if not re.fullmatch(r"SW-V\d+\.\d+\.\d+(?:-dev)?", software):
        failures.append(f"invalid software version: {software}")
    if not re.fullmatch(r"V\d+\.\d+", ordered):
        failures.append(f"invalid ordered hardware version: {ordered}")
    if manifest["hardware_version"] != hardware:
        failures.append("project manifest and hardware/VERSION differ")
    if manifest["software_version"] != software:
        failures.append("project manifest and firmware/VERSION differ")
    if ordered not in manifest["canonical"]["jlc_export"]:
        failures.append("canonical JLC export does not identify ordered hardware")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if hardware.removesuffix("-dev") not in changelog:
        failures.append("current hardware version is absent from CHANGELOG.md")
    if software.removesuffix("-dev") not in changelog:
        failures.append("current software version is absent from CHANGELOG.md")

    if failures:
        raise SystemExit("Versioning check failed:\n  " + "\n  ".join(failures))
    print(
        f"PASS: hardware {hardware}, ordered {ordered}, software {software} "
        "are independently linked"
    )


if __name__ == "__main__":
    main()
