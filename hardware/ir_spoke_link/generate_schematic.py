#!/usr/bin/env python3
"""Generate a clean, block-organized system schematic for the IR sensor."""

from pathlib import Path
import kicad_sch_api as ksa

HERE = Path(__file__).resolve().parent
OUT = HERE / "ir_spoke_link.kicad_sch"
sch = ksa.create_schematic("IR Spoke Sensor")


def add(lib_id, ref, value, pos, footprint, rotation=0, unit=1, **fields):
    return sch.components.add(
        lib_id=lib_id, reference=ref, value=value, position=pos,
        footprint=footprint, rotation=rotation, unit=unit, **fields
    )


def heading(text, x, y):
    sch.add_text(text, (x, y), size=1.6, bold=True)


def note(text, x, y):
    sch.add_text(text, (x, y), size=0.9, italic=True)


# ---------------------------------------------------------------------------
# Host / control
heading("1  ESP32-S3 HOST / RMT", 26, 24)
add("Connector_Generic:Conn_01x07", "J1", "XIAO LEFT", (30, 46),
    "Connector_PinSocket_2.54mm:PinSocket_1x07_P2.54mm_Vertical", LCSC="DNI")
add("Connector_Generic:Conn_01x07", "J2", "XIAO RIGHT", (30, 72),
    "Connector_PinSocket_2.54mm:PinSocket_1x07_P2.54mm_Vertical", LCSC="DNI")
add("power:PWR_FLAG", "#FLG01", "PWR_FLAG", (44, 70), "")
add("power:PWR_FLAG", "#FLG02", "PWR_FLAG", (54, 70), "")
note("GPIO1: runtime carrier TX  |  GPIO2: comparator carrier into RMT RX", 25, 91)

# ---------------------------------------------------------------------------
# Remote transmitter and cable boundary
heading("2  DRIVER / LOCKING HARNESS", 78, 24)
add("Device:R", "R2", "1k", (74, 44), "Resistor_SMD:R_0402_1005Metric",
    rotation=90, LCSC="C11702")
add("Transistor_BJT:Q_NPN_BCE", "Q1", "S8050 J3Y", (91, 44),
    "Package_TO_SOT_SMD:SOT-23", LCSC="C2146")
add("Connector_Generic:Conn_01x02", "J3", "JST GH MAIN", (111, 44),
    "Connector_JST:JST_GH_BM02B-GHS-TBT_1x02-1MP_P1.25mm_Vertical",
    LCSC="C161690", Datasheet="https://www.jst-mfg.com/product/pdf/eng/eGH.pdf")
note("600 mm AWG28 pair / GHR-02V-S / SSHL-002T-P0.2", 69, 58)

heading("3  REMOTE EMITTER PCB", 145, 24)
add("Connector_Generic:Conn_01x02", "J4", "JST GH LED", (143, 44),
    "Connector_JST:JST_GH_BM02B-GHS-TBT_1x02-1MP_P1.25mm_Vertical",
    LCSC="C161690")
add("Device:R", "R1", "39R", (165, 40), "Resistor_SMD:R_0603_1608Metric",
    rotation=90, LCSC="C23154")
add("Device:LED", "D1", "VSMB1940X01", (188, 44),
    "LED_SMD:LED_0805_2012Metric", LCSC="C3151600",
    Datasheet="https://www.vishay.com/docs/81933/vsmb1940.pdf")
note("Emitter faces D2 across spoke plane", 145, 58)

# ---------------------------------------------------------------------------
# Reference and detector
heading("4  VREF / PHOTODIODE / TIA", 32, 106)
add("Device:R", "R3", "10k", (28, 124), "Resistor_SMD:R_0402_1005Metric",
    rotation=90, LCSC="C25744")
add("Device:R", "R4", "10k", (28, 140), "Resistor_SMD:R_0402_1005Metric",
    rotation=90, LCSC="C25744")
add("Device:C", "C1", "1u", (43, 140), "Capacitor_SMD:C_0603_1608Metric",
    LCSC="C15849")
add("Connector_Generic:Conn_01x03", "D2", "VEMD10940FX01", (58, 128),
    "IR_Spoke_Link:VEMD10940F_SideView", LCSC="C7104273",
    Datasheet="https://www.vishay.com/docs/84217/vemd10940fx01.pdf")
u1a = add("Amplifier_Operational:TLV9062", "U1", "TLV9062IDDFR", (84, 128),
    "Package_TO_SOT_SMD:SOT-23-8", unit=1, LCSC="C2867884",
    Datasheet="https://www.ti.com/lit/ds/symlink/tlv9062.pdf")
add("Device:R", "R5", "33k", (84, 114), "Resistor_SMD:R_0402_1005Metric",
    LCSC="C25779")
add("Device:C", "C2", "120p C0G", (99, 114), "Capacitor_SMD:C_0402_1005Metric",
    LCSC="C1548")
note("D2 pins: 1 cathode, 2 mechanical NC, 3 anode", 51, 148)

# ---------------------------------------------------------------------------
# Active band-pass
heading("5  10 kHz-60 kHz ACTIVE BAND-PASS", 125, 106)
add("Device:C", "C3", "1n C0G", (112, 128), "Capacitor_SMD:C_0402_1005Metric",
    LCSC="C1523")
add("Device:R", "R6", "16k", (120, 142), "Resistor_SMD:R_0402_1005Metric",
    LCSC="C25770")
u1b = add("Amplifier_Operational:TLV9062", "U1", "TLV9062IDDFR", (139, 128),
    "Package_TO_SOT_SMD:SOT-23-8", unit=2, LCSC="C2867884")
u1p = add("Amplifier_Operational:TLV9062", "U1", "TLV9062IDDFR", (139, 151),
    "Package_TO_SOT_SMD:SOT-23-8", unit=3, LCSC="C2867884")
add("Device:R", "R7", "10k", (139, 142), "Resistor_SMD:R_0402_1005Metric",
    LCSC="C25744")
add("Device:R", "R8", "560k", (151, 114), "Resistor_SMD:R_0402_1005Metric",
    LCSC="C132339")
add("Device:C", "C4", "4.7p C0G", (165, 114), "Capacitor_SMD:C_0402_1005Metric",
    LCSC="C1569")

# ---------------------------------------------------------------------------
# Comparator and GPIO
heading("6  SCHMITT DECISION / RMT INPUT", 190, 106)
add("Device:R", "R9", "10k", (174, 128), "Resistor_SMD:R_0402_1005Metric",
    LCSC="C25744")
add("Comparator:LMV331", "U2", "TLV7011DCKR", (194, 128),
    "Package_TO_SOT_SMD:SOT-353_SC-70-5", LCSC="C193688",
    Datasheet="https://www.ti.com/lit/ds/symlink/tlv7011.pdf")
add("Device:R", "R10", "1M", (194, 114), "Resistor_SMD:R_0402_1005Metric",
    LCSC="C26083")
add("Device:R", "R11", "100R", (214, 128), "Resistor_SMD:R_0402_1005Metric",
    LCSC="C25076")
add("Device:C", "C5", "100n X7R", (182, 151), "Capacitor_SMD:C_0402_1005Metric",
    LCSC="C1525")
add("Device:C", "C6", "100n X7R", (205, 151), "Capacitor_SMD:C_0402_1005Metric",
    LCSC="C1525")
note("36.9 mV hysteresis typ.; RMT RX removes selected carrier", 171, 163)

pin_nets = {
    ("J1", "1"): "TX_CARRIER_GPIO1", ("J1", "2"): "RX_RMT_GPIO2",
    ("J1", "3"): "XIAO_D2", ("J1", "4"): "XIAO_D3", ("J1", "5"): "XIAO_D4",
    ("J1", "6"): "XIAO_D5", ("J1", "7"): "XIAO_D6",
    ("J2", "1"): "XIAO_D10", ("J2", "2"): "XIAO_D9", ("J2", "3"): "XIAO_D8",
    ("J2", "4"): "XIAO_D7", ("J2", "5"): "+3V3", ("J2", "6"): "GND",
    ("J2", "7"): "+5V_USB",
    ("#FLG01", "1"): "+3V3", ("#FLG02", "1"): "GND",
    ("R2", "1"): "TX_CARRIER_GPIO1", ("R2", "2"): "Q_BASE",
    ("Q1", "1"): "Q_BASE", ("Q1", "2"): "LED_K_SWITCHED", ("Q1", "3"): "GND",
    ("J3", "1"): "+3V3_LED", ("J3", "2"): "LED_K_SWITCHED",
    ("J4", "1"): "+3V3_LED", ("J4", "2"): "LED_K_SWITCHED",
    ("R1", "1"): "+3V3_LED", ("R1", "2"): "LED_A",
    ("D1", "1"): "LED_K_SWITCHED", ("D1", "2"): "LED_A",
    ("R3", "1"): "+3V3", ("R3", "2"): "VREF",
    ("R4", "1"): "VREF", ("R4", "2"): "GND",
    ("C1", "1"): "VREF", ("C1", "2"): "GND",
    ("D2", "1"): "+3V3", ("D2", "2"): "NC_MECHANICAL", ("D2", "3"): "PD_ANODE",
    ("R5", "1"): "TIA_OUT", ("R5", "2"): "PD_ANODE",
    ("C2", "1"): "TIA_OUT", ("C2", "2"): "PD_ANODE",
    ("C3", "1"): "TIA_OUT", ("C3", "2"): "BP_IN",
    ("R6", "1"): "BP_IN", ("R6", "2"): "VREF",
    ("R7", "1"): "BP_NEG", ("R7", "2"): "VREF",
    ("R8", "1"): "BANDPASS", ("R8", "2"): "BP_NEG",
    ("C4", "1"): "BANDPASS", ("C4", "2"): "BP_NEG",
    ("R9", "1"): "BANDPASS", ("R9", "2"): "COMP_PLUS",
    ("U2", "1"): "COMP_OUT", ("U2", "2"): "GND", ("U2", "3"): "COMP_PLUS",
    ("U2", "4"): "VREF", ("U2", "5"): "+3V3",
    ("R10", "1"): "COMP_OUT", ("R10", "2"): "COMP_PLUS",
    ("R11", "1"): "COMP_OUT", ("R11", "2"): "RX_RMT_GPIO2",
    ("C5", "1"): "+3V3", ("C5", "2"): "GND",
    ("C6", "1"): "+3V3", ("C6", "2"): "GND",
}

short_names = {
    "TX_CARRIER_GPIO1": "TX_CARRIER",
    "RX_RMT_GPIO2": "RMT_RX",
    "LED_K_SWITCHED": "LED_K",
    "NC_MECHANICAL": "NC_MECH",
    "XIAO_D10": "D10", "XIAO_D9": "D9", "XIAO_D8": "D8",
    "XIAO_D7": "D7", "XIAO_D6": "D6", "XIAO_D5": "D5",
    "XIAO_D4": "D4", "XIAO_D3": "D3", "XIAO_D2": "D2_GPIO",
}

for (ref, pin), net in pin_nets.items():
    sch.add_label(short_names.get(net, net), pin=(ref, pin), size=0.58)

for component, mapping in [
    (u1a, {"1": "TIA_OUT", "2": "PD_ANODE", "3": "VREF"}),
    (u1b, {"5": "BP_IN", "6": "BP_NEG", "7": "BANDPASS"}),
    (u1p, {"4": "GND", "8": "+3V3"}),
]:
    for pin, net in mapping.items():
        sch.add_label(short_names.get(net, net),
                      position=component.get_pin_position(pin), size=0.58)

sch.add_text(
    "SYSTEM NOTES\n"
    "- RMT TX carrier is runtime-selectable from 25 kHz to 50 kHz.\n"
    "- The discrete AFE rejects DC sunlight; the Schmitt stage restores logic.\n"
    "- RMT RX carrier removal yields blockage intervals for the adaptive LUT.\n"
    "- J3/J4 are the harness boundary; J4/R1/D1 are on the remote PCB.",
    (25, 177), size=0.95
)
sch.save(str(OUT))
print(OUT)
