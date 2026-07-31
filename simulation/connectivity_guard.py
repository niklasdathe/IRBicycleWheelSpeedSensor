"""Fail simulation when generated SPICE topology is stale or invalid."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from generate_connectivity import (  # noqa: E402
    OUTPUT_PATH,
    canonical_manifest,
    validate_manifest,
)
from validate_kicad_netlist import (  # noqa: E402
    MANIFEST as KICAD_MANIFEST_PATH,
    SCHEMATIC,
    validate as validate_kicad_netlist,
)

_validated_key: tuple[int, int, int] | None = None


def validate_simulation_connectivity() -> str:
    global _validated_key
    manifest, digest = canonical_manifest()
    validate_manifest(manifest)
    if not OUTPUT_PATH.is_file():
        raise RuntimeError(
            "generated SPICE connectivity is missing; run "
            "tools/generate_connectivity.py"
        )
    generated = OUTPUT_PATH.read_text(encoding="utf-8")
    if f"CONNECTIVITY_SHA256={digest}" not in generated:
        raise RuntimeError(
            "SPICE connectivity is stale relative to hardware/connectivity.json"
        )
    key = (
        KICAD_MANIFEST_PATH.stat().st_mtime_ns,
        SCHEMATIC.stat().st_mtime_ns,
        OUTPUT_PATH.stat().st_mtime_ns,
    )
    if key != _validated_key:
        endpoint_digest = validate_kicad_netlist()
        if f"KICAD_ENDPOINT_SHA256={endpoint_digest}" not in generated:
            raise RuntimeError(
                "SPICE connectivity is stale relative to KiCad's native "
                "schematic endpoint netlist"
            )
        _validated_key = key
    return digest
