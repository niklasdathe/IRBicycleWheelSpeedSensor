#!/usr/bin/env python3
"""Save the primary design references and their PDFs through Zotero Connector."""

from __future__ import annotations

import json
import urllib.request
import uuid

items = [
    {
        "itemType": "document",
        "title": "VSMB1940X01 — High Speed Infrared Emitting Diode, 940 nm",
        "creators": [{"firstName": "", "lastName": "Vishay Semiconductors", "creatorType": "author"}],
        "date": "2026",
        "publisher": "Vishay",
        "url": "https://www.vishay.com/en/product/81933/",
        "tags": [{"tag": "IR Spoke Link"}, {"tag": "datasheet"}, {"tag": "940 nm"}],
        "attachments": [{
            "title": "VSMB1940X01 datasheet",
            "url": "https://www.vishay.com/docs/81933/vsmb1940.pdf",
            "mimeType": "application/pdf"
        }]
    },
    {
        "itemType": "document",
        "title": "TSOP572 / TSOP574 — IR Receiver Modules for Remote Control Systems",
        "creators": [{"firstName": "", "lastName": "Vishay Semiconductors", "creatorType": "author"}],
        "date": "2022-11-24",
        "publisher": "Vishay",
        "url": "https://www.vishay.com/en/product/82434/",
        "tags": [{"tag": "IR Spoke Link"}, {"tag": "datasheet"}, {"tag": "38 kHz"}, {"tag": "AGC4"}],
        "attachments": [{
            "title": "TSOP572 / TSOP574 datasheet",
            "url": "https://www.vishay.com/docs/82434/tsop572.pdf",
            "mimeType": "application/pdf"
        }]
    },
    {
        "itemType": "webpage",
        "title": "JLCPCB PCB Manufacturing & Assembly Capabilities",
        "creators": [{"firstName": "", "lastName": "JLCPCB", "creatorType": "author"}],
        "date": "2026",
        "websiteTitle": "JLCPCB",
        "url": "https://jlcpcb.com/capabilities/pcb-capabilities/",
        "tags": [{"tag": "IR Spoke Link"}, {"tag": "PCB design rules"}, {"tag": "JLCPCB"}],
        "attachments": []
    },
    {
        "itemType": "webpage",
        "title": "JLCPCB PCB Assembly FAQs — Basic and Extended Components",
        "creators": [{"firstName": "", "lastName": "JLCPCB", "creatorType": "author"}],
        "date": "2025-11-24",
        "websiteTitle": "JLCPCB",
        "url": "https://jlcpcb.com/help/article/pcb-assembly-faqs",
        "tags": [{"tag": "IR Spoke Link"}, {"tag": "PCBA"}, {"tag": "JLCPCB"}],
        "attachments": []
    }
]

payload = json.dumps({"items": items, "sessionID": str(uuid.uuid4())}).encode()
request = urllib.request.Request(
    "http://127.0.0.1:23119/connector/saveItems",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=60) as response:
    print(response.status)
    print(response.read().decode("utf-8", errors="replace"))
