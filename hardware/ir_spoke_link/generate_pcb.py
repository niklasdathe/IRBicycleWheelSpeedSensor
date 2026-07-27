#!/usr/bin/env python3
"""Generate the placed XIAO carrier PCB for the custom receiver."""

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


def load(lib, name, ref, value, lcsc, x, y, rot=0):
    fp = pcbnew.FootprintLoad(str(LIBROOT / f"{lib}.pretty"), name)
    if fp is None:
        raise RuntimeError(f"Footprint not found: {lib}:{name}")
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(v(x, y))
    fp.SetOrientationDegrees(rot)
    if hasattr(fp, "SetProperty"):
        fp.SetProperty("LCSC", lcsc)
    board.Add(fp)
    return fp


def local(name, ref, value, lcsc, x, y, rot=0):
    fp = pcbnew.FootprintLoad(str(HERE / "IR_Spoke_Link.pretty"), name)
    if fp is None:
        raise RuntimeError(f"Local footprint not found: {name}")
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(v(x, y))
    fp.SetOrientationDegrees(rot)
    if hasattr(fp, "SetProperty"):
        fp.SetProperty("LCSC", lcsc)
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


# XIAO header geometry with a 4 mm connector tongue below the module.
for args in [(0, 0, 21.5, 0), (21.5, 0, 21.5, 22), (21.5, 22, 0, 22), (0, 22, 0, 0)]:
    edge(*args)

fps = {}
fps["J1"] = load("Connector_PinSocket_2.54mm", "PinSocket_1x07_P2.54mm_Vertical", "J1", "XIAO_LEFT", "DNI", 3.13, 1.38)
fps["J2"] = load("Connector_PinSocket_2.54mm", "PinSocket_1x07_P2.54mm_Vertical", "J2", "XIAO_RIGHT", "DNI", 18.37, 1.38)

# Optical detector at the upper edge; AFE parts flow left-to-right below it.
fps["D2"] = local("VEMD10940F_SideView", "D2", "VEMD10940FX01", "C7104273", 10.75, 1.5)
fps["U1"] = load("Package_TO_SOT_SMD", "SOT-23-8", "U1", "TLV9062IDDFR", "C2867884", 9.0, 5.0, 90)
fps["U2"] = load("Package_TO_SOT_SMD", "SOT-353_SC-70-5", "U2", "TLV7011DCKR", "C193688", 15.5, 5.0, 90)
fps["J3"] = load("Connector_JST", "JST_GH_BM02B-GHS-TBT_1x02-1MP_P1.25mm_Vertical", "J3", "TX CABLE", "C161690", 13.0, 18.5, 180)
fps["Q1"] = load("Package_TO_SOT_SMD", "SOT-23", "Q1", "S8050", "C2146", 7.0, 20.0, 90)

def r(ref, value, lcsc, x, y, rot=0, size="0402"):
    return load("Resistor_SMD", f"R_{size}_1005Metric" if size == "0402" else "R_0603_1608Metric",
                ref, value, lcsc, x, y, rot)


def c(ref, value, lcsc, x, y, rot=0, size="0402"):
    return load("Capacitor_SMD", f"C_{size}_1005Metric" if size == "0402" else "C_0603_1608Metric",
                ref, value, lcsc, x, y, rot)


fps["R2"] = r("R2", "1k", "C11702", 7.0, 17.0, 90)
fps["R3"] = r("R3", "10k", "C25744", 6.0, 3.0, 90)
fps["R4"] = r("R4", "10k", "C25744", 6.0, 6.0, 90)
fps["C1"] = c("C1", "1u", "C15849", 6.0, 9.0, 90, "0603")
fps["R5"] = r("R5", "33k", "C25779", 8.0, 11.5)
fps["C2"] = c("C2", "120p", "C1548", 11.0, 11.5)
fps["C3"] = c("C3", "1n", "C1523", 13.5, 11.5)
fps["R6"] = r("R6", "16k", "C25770", 15.5, 11.5)
fps["R7"] = r("R7", "10k", "C25744", 8.0, 13.5)
fps["R8"] = r("R8", "100k", "C25741", 10.5, 13.5)
fps["C4"] = c("C4", "27p", "C1573", 13.0, 13.5)
fps["R9"] = r("R9", "10k", "C25744", 15.5, 13.5)
fps["R10"] = r("R10", "1M", "C26083", 16.0, 8.0, 90)
fps["R11"] = r("R11", "100R", "C25076", 19.0, 19.5)
fps["C5"] = c("C5", "100n", "C1525", 8.0, 15.3)
fps["C6"] = c("C6", "100n", "C1525", 10.0, 15.3)

net_names = [
    "GND", "+3V3", "VREF", "TX_CARRIER_GPIO1", "RX_RMT_GPIO2", "Q_BASE",
    "+3V3_LED", "LED_K_SWITCHED", "PD_ANODE", "NC_MECHANICAL", "TIA_OUT",
    "BP_IN", "BP_NEG", "BANDPASS", "COMP_PLUS", "COMP_OUT", "+5V_USB",
    "XIAO_D2", "XIAO_D3", "XIAO_D4", "XIAO_D5", "XIAO_D6",
    "XIAO_D10", "XIAO_D9", "XIAO_D8", "XIAO_D7",
]
nets = {}
for name in net_names:
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    nets[name] = net


def assign(ref, mapping):
    for pad_no, net_name in mapping.items():
        pad = fps[ref].FindPadByNumber(str(pad_no))
        if pad is None:
            raise RuntimeError(f"{ref}.{pad_no} absent")
        pad.SetNet(nets[net_name])


assign("J1", {1:"TX_CARRIER_GPIO1",2:"RX_RMT_GPIO2",3:"XIAO_D2",4:"XIAO_D3",5:"XIAO_D4",6:"XIAO_D5",7:"XIAO_D6"})
assign("J2", {1:"XIAO_D10",2:"XIAO_D9",3:"XIAO_D8",4:"XIAO_D7",5:"+3V3",6:"GND",7:"+5V_USB"})
assign("D2", {1:"+3V3",2:"NC_MECHANICAL",3:"PD_ANODE"})
assign("U1", {1:"TIA_OUT",2:"PD_ANODE",3:"VREF",4:"GND",5:"BP_IN",6:"BP_NEG",7:"BANDPASS",8:"+3V3"})
assign("U2", {1:"COMP_OUT",2:"GND",3:"COMP_PLUS",4:"VREF",5:"+3V3"})
assign("J3", {1:"+3V3_LED",2:"LED_K_SWITCHED"})
assign("Q1", {1:"Q_BASE",2:"LED_K_SWITCHED",3:"GND"})
assign("R2", {1:"TX_CARRIER_GPIO1",2:"Q_BASE"})
assign("R3", {1:"+3V3",2:"VREF"}); assign("R4", {1:"VREF",2:"GND"}); assign("C1", {1:"VREF",2:"GND"})
assign("R5", {1:"TIA_OUT",2:"PD_ANODE"}); assign("C2", {1:"TIA_OUT",2:"PD_ANODE"})
assign("C3", {1:"TIA_OUT",2:"BP_IN"}); assign("R6", {1:"BP_IN",2:"VREF"})
assign("R7", {1:"BP_NEG",2:"VREF"}); assign("R8", {1:"BANDPASS",2:"BP_NEG"}); assign("C4", {1:"BANDPASS",2:"BP_NEG"})
assign("R9", {1:"BANDPASS",2:"COMP_PLUS"}); assign("R10", {1:"COMP_OUT",2:"COMP_PLUS"})
assign("R11", {1:"COMP_OUT",2:"RX_RMT_GPIO2"}); assign("C5", {1:"+3V3",2:"GND"}); assign("C6", {1:"+3V3",2:"GND"})

for fp in fps.values():
    fp.Reference().SetLayer(pcbnew.F_Fab)
    fp.Value().SetLayer(pcbnew.F_Fab)
for ref in fps:
    for graphic in fps[ref].GraphicalItems():
        if graphic.GetLayer() == pcbnew.F_SilkS:
            graphic.SetLayer(pcbnew.F_Fab)

pcbnew.SaveBoard(str(OUT), board)
print(OUT)
