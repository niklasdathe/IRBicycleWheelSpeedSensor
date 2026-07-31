#!/usr/bin/env python3
"""Stable hashes for user-authored KiCad routing."""

from __future__ import annotations

import hashlib
import json

import pcbnew


def routing_signature(board: pcbnew.BOARD) -> str:
    items = []
    for track in board.GetTracks():
        if isinstance(track, pcbnew.PCB_VIA):
            position = track.GetPosition()
            items.append((
                "via",
                round(pcbnew.ToMM(position.x), 4),
                round(pcbnew.ToMM(position.y), 4),
                round(pcbnew.ToMM(track.GetDrillValue()), 4),
                track.GetNetname(),
            ))
        else:
            start, end = track.GetStart(), track.GetEnd()
            items.append((
                "seg",
                round(pcbnew.ToMM(start.x), 4),
                round(pcbnew.ToMM(start.y), 4),
                round(pcbnew.ToMM(end.x), 4),
                round(pcbnew.ToMM(end.y), 4),
                round(pcbnew.ToMM(track.GetWidth()), 4),
                track.GetLayerName(),
                track.GetNetname(),
            ))
    return hashlib.sha256(
        json.dumps(sorted(items)).encode("utf-8")
    ).hexdigest()


def route_text_signature(text: str) -> str:
    blocks = []
    for expression in ("segment", "via", "arc"):
        prefix = f"\n\t({expression}\n"
        cursor = 0
        while True:
            start = text.find(prefix, cursor)
            if start < 0:
                break
            start += 1
            depth = 0
            quoted = False
            escaped = False
            end = start
            while end < len(text):
                character = text[end]
                if quoted:
                    if escaped:
                        escaped = False
                    elif character == "\\":
                        escaped = True
                    elif character == '"':
                        quoted = False
                else:
                    if character == '"':
                        quoted = True
                    elif character == "(":
                        depth += 1
                    elif character == ")":
                        depth -= 1
                        if depth == 0:
                            end += 1
                            break
                end += 1
            blocks.append(text[start:end])
            cursor = end
    if not blocks:
        raise ValueError("No routed segment, via or arc expressions found")
    return hashlib.sha256(
        "\n".join(sorted(blocks)).encode("utf-8")
    ).hexdigest()
