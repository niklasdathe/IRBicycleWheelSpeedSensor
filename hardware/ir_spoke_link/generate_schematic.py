#!/usr/bin/env python3
"""Generate the editable KiCad schematic from the reviewed component set."""

from pathlib import Path

import kicad_sch_api as ksa

HERE = Path(__file__).resolve().parent
OUT = HERE / "ir_spoke_link.kicad_sch"

sch = ksa.create_schematic("IR Spoke Link")


def add(lib_id, ref, value, pos, footprint, rotation=0, **fields):
    return sch.components.add(
        lib_id=lib_id,
        reference=ref,
        value=value,
        position=pos,
        footprint=footprint,
        rotation=rotation,
        **fields,
    )


# XIAO ESP32S3 carrier headers. Pin names are stated in adjacent text/labels.
add(
    "Connector_Generic:Conn_01x07",
    "J1",
    "XIAO_LEFT: D0,D1,D2,D3,D4,D5,D6",
    (35, 72),
    "Connector_PinSocket_2.54mm:PinSocket_1x07_P2.54mm_Vertical",
    LCSC="DNI",
)
add(
    "Connector_Generic:Conn_01x07",
    "J2",
    "XIAO_RIGHT: D10,D9,D8,D7,3V3,GND,5V",
    (35, 110),
    "Connector_PinSocket_2.54mm:PinSocket_1x07_P2.54mm_Vertical",
    LCSC="DNI",
)

# Transmitter.
add(
    "Device:R",
    "R2",
    "1k",
    (70, 72),
    "Resistor_SMD:R_0402_1005Metric",
    rotation=90,
    LCSC="C11702",
)
add(
    "Transistor_BJT:Q_NPN_BCE",
    "Q1",
    "S8050",
    (96, 72),
    "Package_TO_SOT_SMD:SOT-23",
    LCSC="C2146",
)
add(
    "Device:LED",
    "D1",
    "VSMB1940X01 940nm",
    (96, 48),
    "LED_SMD:LED_0805_2012Metric",
    LCSC="C3151600",
    Datasheet="https://www.lcsc.com/product-detail/C3151600.html",
)
add(
    "Device:R",
    "R1",
    "39R 0.1W",
    (96, 34),
    "Resistor_SMD:R_0603_1608Metric",
    LCSC="C23154",
)
add(
    "Device:C",
    "C1",
    "100n X7R",
    (118, 45),
    "Capacitor_SMD:C_0402_1005Metric",
    LCSC="C1525",
)

# Integrated 38 kHz receiver. Belobog pinning:
# pin 1 = OUT; 2,3,6,7,8 = GND; 4,5 = VS.
add(
    "Connector_Generic:Conn_01x08",
    "U1",
    "TSOP57438TT1 38kHz",
    (158, 72),
    "IR_Spoke_Link:TSOP57_Belobog_4x4mm",
    LCSC="C3742825",
    Datasheet="https://www.vishay.com/en/product/82434/",
)
add(
    "Device:R",
    "R3",
    "100R",
    (158, 48),
    "Resistor_SMD:R_0402_1005Metric",
    LCSC="C25076",
)
add(
    "Device:C",
    "C2",
    "4.7u X5R",
    (178, 54),
    "Capacitor_SMD:C_0603_1608Metric",
    LCSC="C19666",
)
add(
    "Device:C",
    "C3",
    "100n X7R",
    (192, 54),
    "Capacitor_SMD:C_0402_1005Metric",
    LCSC="C1525",
)
add(
    "Device:R",
    "R4",
    "10k",
    (178, 83),
    "Resistor_SMD:R_0402_1005Metric",
    LCSC="C25744",
)
add(
    "Device:R",
    "R5",
    "100R",
    (205, 72),
    "Resistor_SMD:R_0402_1005Metric",
    rotation=90,
    LCSC="C25076",
)
add(
    "Device:C",
    "C4",
    "47p C0G",
    (224, 83),
    "Capacitor_SMD:C_0402_1005Metric",
    LCSC="C1671",
)

# Label-based connectivity keeps the schematic legible and produces named
# nets shared with firmware and simulation.
pin_nets = {
    ("J1", "1"): "TX_CARRIER_GPIO1",
    ("J1", "2"): "RX_RMT_GPIO2",
    ("J1", "3"): "XIAO_D2_GPIO3",
    ("J1", "4"): "XIAO_D3_GPIO4",
    ("J1", "5"): "XIAO_D4_GPIO5",
    ("J1", "6"): "XIAO_D5_GPIO6",
    ("J1", "7"): "XIAO_D6_GPIO43",
    ("J2", "1"): "XIAO_D10_GPIO9",
    ("J2", "2"): "XIAO_D9_GPIO8",
    ("J2", "3"): "XIAO_D8_GPIO7",
    ("J2", "4"): "XIAO_D7_GPIO44",
    ("J2", "5"): "+3V3",
    ("J2", "6"): "GND",
    ("J2", "7"): "+5V_USB",
    ("R2", "1"): "TX_CARRIER_GPIO1",
    ("R2", "2"): "Q_BASE",
    ("Q1", "1"): "Q_BASE",
    ("Q1", "2"): "LED_K",
    ("Q1", "3"): "GND",
    ("D1", "1"): "LED_K",
    ("D1", "2"): "LED_A",
    ("R1", "1"): "+3V3",
    ("R1", "2"): "LED_A",
    ("C1", "1"): "+3V3",
    ("C1", "2"): "GND",
    ("U1", "1"): "RX_RAW_ACTIVE_LOW",
    ("U1", "2"): "GND",
    ("U1", "3"): "GND",
    ("U1", "4"): "RX_VS_FILTERED",
    ("U1", "5"): "RX_VS_FILTERED",
    ("U1", "6"): "GND",
    ("U1", "7"): "GND",
    ("U1", "8"): "GND",
    ("R3", "1"): "+3V3",
    ("R3", "2"): "RX_VS_FILTERED",
    ("C2", "1"): "RX_VS_FILTERED",
    ("C2", "2"): "GND",
    ("C3", "1"): "RX_VS_FILTERED",
    ("C3", "2"): "GND",
    ("R4", "1"): "+3V3",
    ("R4", "2"): "RX_RAW_ACTIVE_LOW",
    ("R5", "1"): "RX_RAW_ACTIVE_LOW",
    ("R5", "2"): "RX_RMT_GPIO2",
    ("C4", "1"): "RX_RMT_GPIO2",
    ("C4", "2"): "GND",
}

for (ref, pin), net in pin_nets.items():
    sch.add_label(net, pin=(ref, pin), size=1.0)

sch.save(str(OUT))
print(OUT)
