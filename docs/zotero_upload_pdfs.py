#!/usr/bin/env python3
"""Create Zotero datasheet records and upload local PDF bytes as attachments."""

from __future__ import annotations

import json
from pathlib import Path
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent
records = [
    {
        "title": "VSMB1940X01 Datasheet (PDF)",
        "date": "2025",
        "url": "https://www.vishay.com/docs/81933/vsmb1940.pdf",
        "path": ROOT / "datasheets" / "VSMB1940X01.pdf",
    },
    {"title": "VEMD10940FX01 Photodiode Datasheet (PDF)", "date": "2025-10-28",
     "url": "https://www.vishay.com/docs/84217/vemd10940fx01.pdf",
     "path": ROOT / "datasheets" / "VEMD10940FX01.pdf"},
    {"title": "TLV9062 RRIO Operational Amplifier Datasheet (PDF)", "date": "2025",
     "url": "https://www.ti.com/lit/ds/symlink/tlv9062.pdf",
     "path": ROOT / "datasheets" / "TLV9062.pdf", "author": "Texas Instruments"},
    {"title": "TLV7011 Nanopower Comparator Datasheet (PDF)", "date": "2025",
     "url": "https://www.ti.com/lit/ds/symlink/tlv7011.pdf",
     "path": ROOT / "datasheets" / "TLV7011.pdf", "author": "Texas Instruments"},
    {"title": "JST GH Connector Series Datasheet (PDF)", "date": "2026",
     "url": "https://www.jst-mfg.com/product/pdf/eng/eGH.pdf",
     "path": ROOT / "datasheets" / "JST_GH.pdf", "author": "JST"},
    {"title": "ESP32-S3 Technical Reference Manual (PDF)", "date": "2026",
     "url": "https://documentation.espressif.com/esp32-s3_technical_reference_manual_en.pdf",
     "path": ROOT / "datasheets" / "ESP32-S3_TRM.pdf", "author": "Espressif Systems"},
]

with urllib.request.urlopen(
    "http://127.0.0.1:23119/api/users/0/collections/MANPYY9A/items?limit=100",
    timeout=30,
) as response:
    existing_titles = {entry["data"].get("title", "") for entry in json.load(response)}

for record in records:
    if record["title"] in existing_titles:
        print(record["title"], "SKIP existing")
        continue
    session_id = str(uuid.uuid4())
    parent_id = str(uuid.uuid4())
    item = {
        "id": parent_id,
        "itemType": "document",
        "title": record["title"],
        "creators": [{"firstName": "", "lastName": record.get("author", "Vishay Semiconductors"), "creatorType": "author"}],
        "date": record["date"],
        "publisher": record.get("author", "Vishay"),
        "url": record["url"],
        "tags": [{"tag": "IR Spoke Link"}, {"tag": "datasheet"}],
    }
    body = json.dumps({
        "items": [item],
        "uri": record["url"],
        "sessionID": session_id,
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:23119/connector/saveItems",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Zotero-Connector-API-Version": "3",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        if response.status != 201:
            raise RuntimeError(f"saveItems failed: {response.status}")

    pdf = record["path"].read_bytes()
    metadata = json.dumps({
        "sessionID": session_id,
        "parentItemID": parent_id,
        "title": record["path"].name,
        "url": record["url"],
    })
    req = urllib.request.Request(
        "http://127.0.0.1:23119/connector/saveAttachment",
        data=pdf,
        headers={
            "Content-Type": "application/pdf",
            "Content-Length": str(len(pdf)),
            "X-Metadata": metadata,
            "X-Zotero-Connector-API-Version": "3",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        print(record["title"], response.status)
