#!/usr/bin/env python3
"""Generate JLCPCB BOM/CPL files directly from the captured KiCad panel."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import pcbnew

# JLCPCB defines positive CPL rotation as counter-clockwise.  These offsets
# correct only JLC's tape/reel zero convention; they must never be applied to
# the physical KiCad board.  Identity fields make the rule fail closed if a
# reference is later repurposed.
JLC_ROTATION_RULES = {
    "U1": ("C2867884", "TLV9062IDDFR", 90),
    "U2": ("C193688", "TLV7011DCKR", 90),
    "J3": ("C189893", "SM02B-GHS-TB(LF)(SN)", 180),
    "J4": ("C189893", "SM02B-GHS-TB(LF)(SN)", 180),
    # LCSC C3151600 uses pin 1=A and pin 2=K, opposite KiCad's LED pad
    # convention. Rotate only the assembled D1 by 180 degrees. D2 agrees.
    "D1": ("C3151600", "VSMB1940X01", 180),
    "D2": ("C7104273", "VEMD10940FX01", 0),
}


def normalized_rotation(angle: float) -> float:
    return angle % 360.0


def jlc_rotation(footprint: pcbnew.FOOTPRINT) -> float:
    reference = footprint.GetReference()
    rule = JLC_ROTATION_RULES.get(reference)
    if rule is None:
        return normalized_rotation(footprint.GetOrientationDegrees())
    expected_lcsc, expected_mpn, offset = rule
    lcsc = footprint.GetField("LCSC").GetText().strip()
    mpn = footprint.GetField("MPN").GetText().strip()
    if (lcsc, mpn) != (expected_lcsc, expected_mpn):
        raise SystemExit(
            f"{reference}: JLC rotation rule is for "
            f"{expected_lcsc}/{expected_mpn}, found {lcsc}/{mpn}"
        )
    return normalized_rotation(
        footprint.GetOrientationDegrees() + offset
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("board", type=Path)
    parser.add_argument("--bom", type=Path, required=True)
    parser.add_argument("--cpl", type=Path, required=True)
    args = parser.parse_args()

    board = pcbnew.LoadBoard(str(args.board.resolve()))
    placed = []
    for footprint in board.GetFootprints():
        ref = footprint.GetReference()
        lcsc = (
            footprint.GetField("LCSC").GetText().strip()
            if footprint.HasField("LCSC") else ""
        )
        if not lcsc.startswith("C") or not lcsc[1:].isdigit():
            continue
        if not all(pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD
                   for pad in footprint.Pads()):
            raise SystemExit(f"{ref}: fitted JLC part is not fully SMD")
        placed.append(footprint)

    groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for footprint in placed:
        lcsc = footprint.GetField("LCSC").GetText().strip()
        groups[
            (
                str(footprint.GetValue()),
                str(footprint.GetFPID().GetLibItemName()),
                str(lcsc),
            )
        ].append(footprint.GetReference())

    args.bom.parent.mkdir(parents=True, exist_ok=True)
    with args.bom.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ["Comment", "Designator", "Footprint", "LCSC Part #"]
        )
        for (value, package, lcsc), references in sorted(groups.items()):
            writer.writerow(
                [value, ",".join(sorted(references)), package, lcsc]
            )

    with args.cpl.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
        )
        for footprint in sorted(placed, key=lambda item: item.GetReference()):
            position = footprint.GetPosition()
            writer.writerow([
                footprint.GetReference(),
                f"{pcbnew.ToMM(position.x):.4f}mm",
                f"{pcbnew.ToMM(position.y):.4f}mm",
                "Top" if footprint.GetLayer() == pcbnew.F_Cu else "Bottom",
                f"{jlc_rotation(footprint):.2f}",
            ])

    cpl_refs = {footprint.GetReference() for footprint in placed}
    bom_refs = {
        ref
        for references in groups.values()
        for ref in references
    }
    if cpl_refs != bom_refs:
        raise SystemExit("Generated BOM and CPL designators differ")
    print(
        f"PASS: {len(placed)} placements, {len(groups)} BOM rows; "
        "BOM/CPL designators match"
    )


if __name__ == "__main__":
    main()
