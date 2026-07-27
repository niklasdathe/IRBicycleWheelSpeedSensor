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
        "date": "2026",
        "url": "https://www.vishay.com/docs/81933/vsmb1940.pdf",
        "path": ROOT / "datasheets" / "VSMB1940X01.pdf",
    },
    {
        "title": "TSOP572 / TSOP574 Datasheet (PDF)",
        "date": "2022-11-24",
        "url": "https://www.vishay.com/docs/82434/tsop572.pdf",
        "path": ROOT / "datasheets" / "TSOP572_TSOP574.pdf",
    },
]

for record in records:
    session_id = str(uuid.uuid4())
    parent_id = str(uuid.uuid4())
    item = {
        "id": parent_id,
        "itemType": "document",
        "title": record["title"],
        "creators": [{"firstName": "", "lastName": "Vishay Semiconductors", "creatorType": "author"}],
        "date": record["date"],
        "publisher": "Vishay",
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
