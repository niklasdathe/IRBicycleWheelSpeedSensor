#!/usr/bin/env python3
"""Verify expected pad sets, net assignment and metadata on both PCBs."""

from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "ir_spoke_link/ir_spoke_link.kicad_pcb": {
        "J1": set("1234567"), "J2": set("1234567"), "J3": {"1","2","MP"},
        "D2": {"1","2","3"}, "U1": set("12345678"), "U2": set("12345"),
        "Q1": set("123"), "R2": {"1","2"}, "R3": {"1","2"}, "R4": {"1","2"},
        "R5": {"1","2"}, "R6": {"1","2"}, "R7": {"1","2"}, "R8": {"1","2"},
        "R9": {"1","2"}, "R10": {"1","2"}, "R11": {"1","2"},
        "C1": {"1","2"}, "C2": {"1","2"}, "C3": {"1","2"}, "C4": {"1","2"},
        "C5": {"1","2"}, "C6": {"1","2"},
    },
    "remote_emitter/remote_emitter.kicad_pcb": {
        "J4": {"1","2","MP"}, "R1": {"1","2"}, "D1": {"1","2"},
    },
}

failures = []
for rel, expected in EXPECTED.items():
    board = pcbnew.LoadBoard(str(ROOT / rel))
    found = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for ref, pads in expected.items():
        if ref not in found:
            failures.append(f"{rel}: missing footprint {ref}")
            continue
        actual = {pad.GetNumber() for pad in found[ref].Pads()}
        if actual != pads:
            failures.append(f"{rel}: {ref} pads {sorted(actual)} != {sorted(pads)}")
        for pad in found[ref].Pads():
            if pad.GetNumber() != "MP" and not pad.GetNetname():
                failures.append(f"{rel}: {ref}.{pad.GetNumber()} has no net")
        if ref not in ("J1", "J2") and hasattr(found[ref], "GetProperty"):
            if not found[ref].GetProperty("LCSC"):
                failures.append(f"{rel}: {ref} lacks LCSC property")

if failures:
    raise SystemExit("\n".join(failures))
print(f"PASS: {sum(len(x) for x in EXPECTED.values())} footprints; pad sets, nets and LCSC metadata verified")
