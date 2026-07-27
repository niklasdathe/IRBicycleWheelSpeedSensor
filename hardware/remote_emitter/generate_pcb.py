#!/usr/bin/env python3
"""Generate the small remote IR LED board connected by the JST-GH cable."""

from pathlib import Path
import pcbnew

HERE = Path(__file__).resolve().parent
LIBROOT = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
OUT = HERE / "remote_emitter.kicad_pcb"
board = pcbnew.BOARD()
board.GetDesignSettings().SetCopperLayerCount(2)
board.GetDesignSettings().m_TrackMinWidth = pcbnew.FromMM(0.20)

def v(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))

def load(lib, name, ref, value, lcsc, x, y, rot=0):
    fp = pcbnew.FootprintLoad(str(LIBROOT / f"{lib}.pretty"), name)
    if fp is None: raise RuntimeError(f"Missing {lib}:{name}")
    fp.SetReference(ref); fp.SetValue(value); fp.SetPosition(v(x, y)); fp.SetOrientationDegrees(rot)
    if hasattr(fp, "SetProperty"): fp.SetProperty("LCSC", lcsc)
    board.Add(fp); return fp

def edge(x1,y1,x2,y2):
    s=pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(v(x1,y1)); s.SetEnd(v(x2,y2))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1)); board.Add(s)

for a in [(0,0,14,0),(14,0,14,12),(14,12,0,12),(0,12,0,0)]: edge(*a)
j4=load("Connector_JST","JST_GH_BM02B-GHS-TBT_1x02-1MP_P1.25mm_Vertical","J4","JST GH LED","C161690",5.5,3.5)
r1=load("Resistor_SMD","R_0603_1608Metric","R1","39R","C23154",11.5,7.0,90)
d1=load("LED_SMD","LED_0805_2012Metric","D1","VSMB1940X01","C3151600",5.5,10.5)
nets={}
for name in ("+3V3_LED","LED_A","LED_K_SWITCHED"):
    n=pcbnew.NETINFO_ITEM(board,name); board.Add(n); nets[name]=n
for fp,m in [(j4,{1:"+3V3_LED",2:"LED_K_SWITCHED"}),(r1,{1:"+3V3_LED",2:"LED_A"}),(d1,{1:"LED_K_SWITCHED",2:"LED_A"})]:
    for p,n in m.items(): fp.FindPadByNumber(str(p)).SetNet(nets[n])

def track(a,b,net,width=0.30,layer=pcbnew.F_Cu):
    s=pcbnew.PCB_TRACK(board); s.SetStart(a); s.SetEnd(b); s.SetLayer(layer); s.SetWidth(pcbnew.FromMM(width)); s.SetNet(net); board.Add(s)

def path(points, net, layer=pcbnew.F_Cu):
    for a,b in zip(points,points[1:]): track(v(*a) if isinstance(a,tuple) else a, v(*b) if isinstance(b,tuple) else b, net, layer=layer)

def via(point, net):
    x = v(*point)
    p = pcbnew.PCB_VIA(board); p.SetPosition(x); p.SetWidth(pcbnew.FromMM(0.6)); p.SetDrill(pcbnew.FromMM(0.3)); p.SetNet(net); board.Add(p)

p_j1=j4.FindPadByNumber("1").GetPosition(); p_j2=j4.FindPadByNumber("2").GetPosition()
p_r1=r1.FindPadByNumber("1").GetPosition(); p_r2=r1.FindPadByNumber("2").GetPosition()
p_d1=d1.FindPadByNumber("1").GetPosition(); p_d2=d1.FindPadByNumber("2").GetPosition()
path([p_j1,(3.0,5.8),(3.0,7.825),p_r1],nets["+3V3_LED"])
path([p_r2,(12.5,6.175),(12.5,10.5),p_d2],nets["LED_A"])
path([p_j2,(6.125,6.5)],nets["LED_K_SWITCHED"])
via((6.125,6.5),nets["LED_K_SWITCHED"])
path([(6.125,6.5),(3.5,8.0),(3.5,10.0),(4.56,10.0)],nets["LED_K_SWITCHED"],pcbnew.B_Cu)
via((4.56,10.0),nets["LED_K_SWITCHED"])
path([(4.56,10.0),p_d1],nets["LED_K_SWITCHED"])
for fp in (j4,r1,d1):
    fp.Reference().SetLayer(pcbnew.F_Fab); fp.Value().SetLayer(pcbnew.F_Fab)
    for graphic in fp.GraphicalItems():
        if graphic.GetLayer()==pcbnew.F_SilkS: graphic.SetLayer(pcbnew.F_Fab)
pcbnew.SaveBoard(str(OUT),board)
print(OUT)
