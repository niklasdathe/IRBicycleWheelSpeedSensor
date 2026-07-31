#!/usr/bin/env python3
"""Build a Konnect-compatible SQLite cache from the live-verified project BOM.

Konnect's current downloader points at a retired URL. This intentionally builds
a small, auditable project database rather than pretending it is the full JLC
catalog. Run refresh_jlc_links.py first to refresh stock and metadata.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "hardware" / "jlcpcb_parts_snapshot.json"
MANIFEST = ROOT / "hardware" / "konnect_database_manifest.json"
BOM_FILES = (
    ROOT / "hardware" / "ir_spoke_link" / "bom_jlcpcb.csv",
)


def verified_jlc_library_types() -> dict[str, str]:
    """Return the JLC Basic/Extended classification audited in each PCB BOM."""
    result: dict[str, str] = {}
    for path in BOM_FILES:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                code = row.get("LCSC Part Number", "").strip()
                library = row.get("JLCPCB Library", "").strip()
                if code.startswith("C") and library in ("Basic", "Extended"):
                    result[code] = library
    return result


def main() -> None:
    default_path = Path(os.environ["APPDATA"]) / "konnect" / "jlcpcb.db"
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=default_path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    source = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    parts = source["parts"]
    invalid = [
        part.get("lcsc", "<unknown>")
        for part in parts
        if part.get("error")
        or not (part.get("component_code") or part.get("lcsc"))
        or int(part.get("stock_count") or 0) <= 0
    ]
    if invalid:
        raise SystemExit(
            "Refusing to build Konnect DB from failed, incomplete or "
            "out-of-stock records: " + ", ".join(invalid)
        )
    audited_libraries = verified_jlc_library_types()
    with tempfile.NamedTemporaryFile(
        prefix="jlcpcb-", suffix=".db", dir=output.parent, delete=False
    ) as temporary:
        temp_path = Path(temporary.name)
    try:
        db = sqlite3.connect(temp_path)
        db.executescript(
            """
            PRAGMA journal_mode=DELETE;
            CREATE TABLE components (
                LCSC TEXT PRIMARY KEY,
                MFR_Part TEXT NOT NULL,
                Package TEXT NOT NULL,
                Solder_Joint TEXT NOT NULL DEFAULT '',
                Manufacturer TEXT NOT NULL,
                Library_Type TEXT NOT NULL,
                Description TEXT NOT NULL,
                Datasheet TEXT NOT NULL DEFAULT '',
                Price REAL NOT NULL DEFAULT 0,
                Stock INTEGER NOT NULL DEFAULT 0,
                Category TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX idx_components_mfr ON components(MFR_Part);
            CREATE INDEX idx_components_description ON components(Description);
            CREATE INDEX idx_components_library_stock
                ON components(Library_Type, Stock);
            CREATE TABLE konnect_cache_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        rows = []
        for part in parts:
            code = part.get("component_code") or part.get("lcsc") or ""
            # Cable-only catalog items are outside PCBA placement. Keep them
            # searchable but conservatively classify them as Extended.
            library = audited_libraries.get(code, "Extended")
            rows.append(
                (
                    code,
                    part.get("component_model_en") or "",
                    part.get("component_specification_en") or "",
                    part.get("component_brand_en") or "",
                    library,
                    part.get("describe") or part.get("erp_component_name") or "",
                    part.get("data_manual_url") or "",
                    float(part.get("initial_price") or 0),
                    int(part.get("stock_count") or 0),
                    part.get("first_sort_name") or "",
                )
            )
        db.executemany(
            """
            INSERT INTO components
                (LCSC, MFR_Part, Package, Manufacturer, Library_Type,
                 Description, Datasheet, Price, Stock, Category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        metadata = {
            "scope": "IR Spoke Sensor BOM subset",
            "source": source["source"],
            "source_generated_utc": source["generated_utc"],
            "built_utc": datetime.now(timezone.utc).isoformat(),
            "row_count": str(len(rows)),
            "schema": "Konnect components v0.1",
            "library_classification": "verified JLCPCB Library fields in PCB BOMs",
        }
        db.executemany(
            "INSERT INTO konnect_cache_metadata(key, value) VALUES (?, ?)",
            metadata.items(),
        )
        db.execute("PRAGMA user_version=1")
        db.commit()
        db.close()
        os.replace(temp_path, output)
    finally:
        temp_path.unlink(missing_ok=True)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = {
        "database_path": str(output),
        "scope": "project BOM subset; not the complete JLCPCB catalog",
        "rows": len(parts),
        "basic_rows": sum(row[4] == "Basic" for row in rows),
        "extended_rows": sum(row[4] == "Extended" for row in rows),
        "sha256": digest,
        "source_snapshot": str(SNAPSHOT.relative_to(ROOT)),
        "source_generated_utc": source["generated_utc"],
        "konnect_schema_reference":
            "mixelpixx/Konnect crates/konnect-core/src/tools/integration.rs",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
