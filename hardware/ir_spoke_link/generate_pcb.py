#!/usr/bin/env python3
"""Place the reviewed circuit on a XIAO-sized carrier board.

Run with KiCad's bundled Python 3.11:
  & "C:\Program Files\KiCad\10.0\bin\python.exe" generate_pcb.py
"""

from pathlib import Path
import pcbnew

HERE = Path(__file__).resolve().parent
LIBROOT = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
OUT = HERE / "ir_spoke_link.kicad_pcb"

board = pcbnew.BOARD()
board.GetDesignSettings().SetCopperLayerCount(2)
board.GetDesignSettings().m_TrackMinWidth = pcbnew.FromMM(0.15)
board.GetDesignSettings().m_ViasMinSize = pcbnew.FromMM(0.60)
board.GetDesignSettings().m_MinThroughDrill = pcbnew.FromMM(0.30)


def v(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def load(lib, name, ref, value, x, y, rot=0):
    fp = pcbnew.FootprintLoad(str(LIBROOT / f"{lib}.pretty"), name)
    if fp is None:
        raise RuntimeError(f"Footprint not found: {lib}:{name}")
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(v(x, y))
    fp.SetOrientationDegrees(rot)
    board.Add(fp)
    return fp


def load_local(name, ref, value, x, y, rot=0):
    fp = pcbnew.FootprintLoad(str(HERE / "IR_Spoke_Link.pretty"), name)
    if fp is None:
        raise RuntimeError(f"Local footprint not found: {name}")
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(v(x, y))
    fp.SetOrientationDegrees(rot)
    board.Add(fp)
    return fp


def edge(x1, y1, x2, y2):
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
    shape.SetStart(v(x1, y1))
    shape.SetEnd(v(x2, y2))
    shape.SetLayer(pcbnew.Edge_Cuts)
    shape.SetWidth(pcbnew.FromMM(0.1))
    board.Add(shape)


# 21.5 x 18.0 mm carrier; XIAO header geometry remains exact while the
# additional 0.25 mm rim restores conservative copper-to-edge clearance.
edge(0, 0, 21.5, 0)
edge(21.5, 0, 21.5, 18.0)
edge(21.5, 18.0, 0, 18.0)
edge(0, 18.0, 0, 0)

fps = {}
fps["J1"] = load("Connector_PinSocket_2.54mm", "PinSocket_1x07_P2.54mm_Vertical", "J1", "XIAO_LEFT", 3.13, 1.38)
fps["J2"] = load("Connector_PinSocket_2.54mm", "PinSocket_1x07_P2.54mm_Vertical", "J2", "XIAO_RIGHT", 18.37, 1.38)

# Receiver faces the top board edge; emitter faces the bottom edge.
fps["U1"] = load_local("TSOP57_Belobog_4x4mm", "U1", "TSOP57438TT1", 10.75, 3.35, 180)
fps["D1"] = load("LED_SMD", "LED_0805_2012Metric", "D1", "VSMB1940X01", 10.75, 16.55)
fps["Q1"] = load("Package_TO_SOT_SMD", "SOT-23", "Q1", "S8050", 7.0, 15.1, 90)
fps["R1"] = load("Resistor_SMD", "R_0603_1608Metric", "R1", "39R", 11.4, 14.0, 90)
fps["R2"] = load("Resistor_SMD", "R_0402_1005Metric", "R2", "1k", 5.9, 11.5, 90)
fps["R3"] = load("Resistor_SMD", "R_0402_1005Metric", "R3", "100R", 13.7, 6.0, 90)
fps["R4"] = load("Resistor_SMD", "R_0402_1005Metric", "R4", "10k", 7.8, 6.0, 90)
fps["R5"] = load("Resistor_SMD", "R_0402_1005Metric", "R5", "100R", 5.9, 8.6, 90)
fps["C1"] = load("Capacitor_SMD", "C_0402_1005Metric", "C1", "100n", 14.2, 12.2, 90)
fps["C2"] = load("Capacitor_SMD", "C_0603_1608Metric", "C2", "4.7u", 15.4, 8.6, 90)
fps["C3"] = load("Capacitor_SMD", "C_0402_1005Metric", "C3", "100n", 13.7, 8.6, 90)
fps["C4"] = load("Capacitor_SMD", "C_0402_1005Metric", "C4", "47p", 7.9, 8.6, 90)

nets = {}
for name in [
    "GND", "+3V3", "TX_CARRIER_GPIO1", "RX_RMT_GPIO2", "Q_BASE", "LED_K",
    "LED_A", "RX_VS_FILTERED", "RX_RAW_ACTIVE_LOW", "+5V_USB",
    "XIAO_D2_GPIO3", "XIAO_D3_GPIO4", "XIAO_D4_GPIO5", "XIAO_D5_GPIO6",
    "XIAO_D6_GPIO43", "XIAO_D10_GPIO9", "XIAO_D9_GPIO8", "XIAO_D8_GPIO7",
    "XIAO_D7_GPIO44"
]:
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    nets[name] = net


def assign(ref, mapping):
    fp = fps[ref]
    for pad_no, net_name in mapping.items():
        pad = fp.FindPadByNumber(str(pad_no))
        if pad is None:
            raise RuntimeError(f"{ref}.{pad_no} absent")
        pad.SetNet(nets[net_name])


assign("J1", {1:"TX_CARRIER_GPIO1",2:"RX_RMT_GPIO2",3:"XIAO_D2_GPIO3",4:"XIAO_D3_GPIO4",5:"XIAO_D4_GPIO5",6:"XIAO_D5_GPIO6",7:"XIAO_D6_GPIO43"})
assign("J2", {1:"XIAO_D10_GPIO9",2:"XIAO_D9_GPIO8",3:"XIAO_D8_GPIO7",4:"XIAO_D7_GPIO44",5:"+3V3",6:"GND",7:"+5V_USB"})
assign("R2", {1:"TX_CARRIER_GPIO1",2:"Q_BASE"})
assign("Q1", {1:"Q_BASE",2:"LED_K",3:"GND"})
assign("D1", {1:"LED_K",2:"LED_A"})
assign("R1", {1:"+3V3",2:"LED_A"})
assign("C1", {1:"+3V3",2:"GND"})
assign("U1", {1:"RX_RAW_ACTIVE_LOW",2:"GND",3:"GND",4:"RX_VS_FILTERED",5:"RX_VS_FILTERED",6:"GND",7:"GND",8:"GND"})
assign("R3", {1:"+3V3",2:"RX_VS_FILTERED"})
assign("C2", {1:"RX_VS_FILTERED",2:"GND"})
assign("C3", {1:"RX_VS_FILTERED",2:"GND"})
assign("R4", {1:"+3V3",2:"RX_RAW_ACTIVE_LOW"})
assign("R5", {1:"RX_RAW_ACTIVE_LOW",2:"RX_RMT_GPIO2"})
assign("C4", {1:"RX_RMT_GPIO2",2:"GND"})

# Keep the tiny carrier legible; fabrication references remain available on
# F.Fab and in BOM/CPL outputs.
for fp in fps.values():
    fp.Reference().SetLayer(pcbnew.F_Fab)
    fp.Value().SetLayer(pcbnew.F_Fab)
for ref in ("J1", "J2"):
    for graphic in fps[ref].GraphicalItems():
        if graphic.GetLayer() == pcbnew.F_SilkS:
            graphic.SetLayer(pcbnew.F_Fab)

# Helpful fabrication labels.  Keep these on F.Fab so the compact component
# placement is not compromised by silkscreen-to-mask clearance.
for text, x, y, size in [
    ("IR SPOKE LINK", 10.75, 10.35, 0.85),
    ("XIAO S3", 10.75, 11.35, 0.8),
]:
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(v(x, y))
    item.SetTextSize(v(size, size))
    item.SetTextThickness(pcbnew.FromMM(0.12))
    item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    item.SetLayer(pcbnew.F_Fab)
    board.Add(item)

pcbnew.SaveBoard(str(OUT), board)
print(OUT)
