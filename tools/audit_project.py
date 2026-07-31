#!/usr/bin/env python3
"""Fail when canonical project links are missing or stale paths return."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "project_manifest.json"
FORBIDDEN_PATHS = (
    ".openai",
    ".vinext",
    ".wrangler",
    "app",
    "db",
    "dist",
    "drizzle",
    "examples",
    "node_modules",
    "public",
    "worker",
    "hardware/remote_emitter",
    "hardware/ir_spoke_link/production",
    "hardware/ir_spoke_link/ir_spoke_link.layout.kicad_pro",
    "hardware/ir_spoke_link/ir_spoke_link.net.xml",
    "simulation/models/TI_TLV9062_PSpice_RevE",
    "simulation/models/TI_TLV9062_TINA_RevC",
    "simulation/models/TI_TLV9062_TINA_RevC.zip",
    "simulation/output",
)
FORBIDDEN_REFERENCES = (
    "hardware/remote_emitter",
    "public/technical.html",
    "public/simulation.json",
    "simulation/output",
    "ir_spoke_link/production",
    "integrate_right_angle_connectors.py",
    "apply_user_requested_rotations.py",
)
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*]\(([^)]+)\)")


def iter_paths(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from iter_paths(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_paths(nested)
    elif isinstance(value, str):
        yield value


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing = [
        path for path in iter_paths({
            "canonical": manifest["canonical"],
            "generators": manifest["generators"],
            "checks": manifest["checks"],
            "maintenance": manifest["maintenance"],
        })
        if not (ROOT / path).exists()
    ]

    leftovers = [
        path for path in FORBIDDEN_PATHS if (ROOT / path).exists()
    ]
    stale = []
    broken_links = []
    scanned_suffixes = {
        ".c", ".cmd", ".h", ".html", ".json", ".md", ".ps1", ".py",
        ".yaml",
    }
    ignored = {ROOT / "tools" / "audit_project.py"}
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.lower() not in scanned_suffixes
            or path in ignored
            or any(part in {".git", "build", "tmp"} for part in path.parts)
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in FORBIDDEN_REFERENCES:
            if token in text:
                stale.append(f"{path.relative_to(ROOT)} -> {token}")

        if path.suffix.lower() == ".md":
            for raw_target in MARKDOWN_LINK.findall(text):
                target = raw_target.strip()
                if target.startswith("<") and target.endswith(">"):
                    target = target[1:-1]
                if (
                    not target
                    or target.startswith("#")
                    or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target)
                ):
                    continue
                relative = unquote(target.split("#", 1)[0])
                resolved = (path.parent / relative).resolve()
                try:
                    resolved.relative_to(ROOT.resolve())
                except ValueError:
                    broken_links.append(
                        f"{path.relative_to(ROOT)} -> outside project: {target}"
                    )
                    continue
                if not resolved.exists():
                    broken_links.append(
                        f"{path.relative_to(ROOT)} -> {target}"
                    )

    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    unindexed_docs = [
        str(path.relative_to(ROOT))
        for path in sorted((ROOT / "docs").glob("*.md"))
        if path.name != "README.md" and path.name not in docs_index
    ]

    zotero = json.loads(
        (ROOT / "docs" / "zotero_links.json").read_text(encoding="utf-8")
    )
    for key, item in zotero["items"].items():
        for field in ("local_pdf", "official_design"):
            if field in item and not (ROOT / item[field]).is_file():
                missing.append(f"zotero:{key}:{item[field]}")

    if missing or leftovers or stale or broken_links or unindexed_docs:
        lines = []
        if missing:
            lines.append("Missing canonical links:\n  " + "\n  ".join(missing))
        if leftovers:
            lines.append("Redundant paths remain:\n  " + "\n  ".join(leftovers))
        if stale:
            lines.append("Stale references:\n  " + "\n  ".join(stale))
        if broken_links:
            lines.append(
                "Broken relative Markdown links:\n  "
                + "\n  ".join(broken_links)
            )
        if unindexed_docs:
            lines.append(
                "Documentation pages missing from docs/README.md:\n  "
                + "\n  ".join(unindexed_docs)
            )
        raise SystemExit("\n".join(lines))

    print(
        "PASS: canonical manifest, Zotero paths, Markdown links, documentation "
        "index and stale-reference audit"
    )


if __name__ == "__main__":
    main()
