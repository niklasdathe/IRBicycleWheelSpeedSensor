#!/usr/bin/env python3
"""Compare KiCad's exported schematic netlist with canonical connectivity.

The schematic generator, PCB generator and SPICE generator all consume
hardware/connectivity.json.  This independent check asks KiCad itself which
pins are connected after symbol transforms and fails on any disagreement.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "hardware" / "connectivity.json"
SCHEMATIC = ROOT / "hardware" / "ir_spoke_link" / "ir_spoke_link.kicad_sch"
KICAD_CLI = Path(r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe")

SHORT_TO_CANONICAL = {
    "TX_CARRIER": "TX_CARRIER_GPIO1",
    "RMT_RX": "RX_RMT_GPIO2",
    "LED_K": "LED_K_SWITCHED",
    "D10": "XIAO_D10",
    "D9": "XIAO_D9",
    "D8": "XIAO_D8",
    "D7": "XIAO_D7",
    "D6": "XIAO_D6",
    "D5": "XIAO_D5",
    "D4": "XIAO_D4",
    "D3": "XIAO_D3",
    "D2_GPIO": "XIAO_D2",
}


def normalize_net(name: str) -> str:
    name = name.removeprefix("/")
    return SHORT_TO_CANONICAL.get(name, name)


def export_netlist(output: Path) -> None:
    if not KICAD_CLI.is_file():
        raise FileNotFoundError(f"KiCad CLI not found at {KICAD_CLI}")
    subprocess.run(
        [
            str(KICAD_CLI),
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "--output",
            str(output),
            str(SCHEMATIC),
        ],
        cwd=ROOT,
        check=True,
    )


def load_actual(netlist: Path) -> dict[tuple[str, str], str]:
    root = ET.parse(netlist).getroot()
    actual: dict[tuple[str, str], str] = {}
    for net in root.findall("./nets/net"):
        name = normalize_net(net.attrib["name"])
        if name.startswith("unconnected-"):
            continue
        for node in net.findall("node"):
            endpoint = (node.attrib["ref"], node.attrib["pin"])
            if endpoint in actual:
                raise ValueError(f"KiCad endpoint appears twice: {endpoint}")
            actual[endpoint] = name
    return actual


def expected_endpoints() -> dict[tuple[str, str], str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected: dict[tuple[str, str], str] = {}
    for board in manifest["boards"].values():
        for ref, pins in board["components"].items():
            for pin, net in pins.items():
                if net.startswith("XIAO_D") or net in {
                    "+5V_USB", "NC_MECHANICAL"
                }:
                    continue
                expected[(ref, pin)] = net
    return expected


def validate() -> str:
    with tempfile.TemporaryDirectory(prefix="ir-spoke-netlist-") as temp:
        netlist = Path(temp) / "ir_spoke_link.net.xml"
        export_netlist(netlist)
        actual = load_actual(netlist)
    expected = expected_endpoints()
    errors = []
    for endpoint, expected_net in sorted(expected.items()):
        actual_net = actual.get(endpoint)
        if actual_net != expected_net:
            errors.append(
                f"{endpoint[0]}.{endpoint[1]} expected {expected_net}, "
                f"KiCad exported {actual_net!r}"
            )
    unexpected = sorted(
        (endpoint, net)
        for endpoint, net in actual.items()
        if endpoint[0] in {
            ref
            for board in json.loads(
                MANIFEST.read_text(encoding="utf-8")
            )["boards"].values()
            for ref in board["components"]
        }
        and endpoint not in expected
        and not net.startswith("XIAO_D")
        and net not in {"+5V_USB", "NC_MECHANICAL"}
    )
    if unexpected:
        errors.extend(
            f"{ref}.{pin} unexpectedly connected to {net}"
            for (ref, pin), net in unexpected
        )
    if errors:
        raise SystemExit(
            "KiCad schematic netlist disagrees with "
            "hardware/connectivity.json:\n  - " + "\n  - ".join(errors)
        )
    endpoint_digest = hashlib.sha256(
        json.dumps(
            sorted(
                (ref, pin, net)
                for (ref, pin), net in actual.items()
                if (ref, pin) in expected
            ),
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    print(
        f"PASS: {len(expected)} schematic pin/net assignments match "
        "canonical connectivity"
    )
    return endpoint_digest


def main() -> None:
    validate()


if __name__ == "__main__":
    main()
