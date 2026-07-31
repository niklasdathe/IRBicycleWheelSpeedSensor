#!/usr/bin/env python3
"""Verify the immutable ordered-hardware bundle and its nested JLC archives."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    manifest = json.loads((ROOT / "project_manifest.json").read_text(encoding="utf-8"))
    version = manifest["ordered_hardware_version"]
    product = f"IR_Spoke_Sensor_{version}_2L"
    release_dir = ROOT / manifest["canonical"]["jlc_export"]
    package = release_dir / f"{product}_ORDER_PACKAGE.zip"

    with zipfile.ZipFile(package) as archive:
        members = {item.filename: archive.read(item) for item in archive.infolist()}

    checksum_name = f"{product}_SHA256SUMS.txt"
    checksums = {}
    for line in members[checksum_name].decode("ascii").splitlines():
        expected, name = line.split(None, 1)
        checksums[name.strip()] = expected
    for name, expected in checksums.items():
        if name not in members:
            raise SystemExit(f"Release checksum target missing from package: {name}")
        actual = digest(members[name])
        if actual != expected:
            raise SystemExit(f"Release checksum mismatch for {name}")

    gerber_name = f"{product}_GERBER.zip"
    with zipfile.ZipFile(io.BytesIO(members[gerber_name])) as gerbers:
        if len(gerbers.infolist()) != 11:
            raise SystemExit("Hardware release must contain 11 Gerber/drill/job files")

    pcba_name = f"{product}_PCBA.zip"
    with zipfile.ZipFile(io.BytesIO(members[pcba_name])) as pcba:
        expected_pcba = {
            f"{product}_BOM.csv",
            f"{product}_CPL.csv",
            f"{product}_ORDER.json",
        }
        if {item.filename for item in pcba.infolist()} != expected_pcba:
            raise SystemExit("PCBA archive must contain exactly BOM, CPL and order JSON")

    order = json.loads(members[f"{product}_ORDER.json"].decode("utf-8-sig"))
    if order["hardware_version"] != version or order["cad_revision"] != manifest["revision"]:
        raise SystemExit("Order metadata version does not match the project manifest")
    drc = members[f"{product}_DRC.rpt"].decode("utf-8-sig")
    if "** Found 0 DRC violations **" not in drc or "** Found 0 unconnected pads **" not in drc:
        raise SystemExit("Release DRC evidence is not fabrication-ready")

    print(
        f"PASS: ordered hardware {version} package, checksums, Gerbers, BOM, "
        "CPL and DRC evidence verified"
    )


if __name__ == "__main__":
    main()
