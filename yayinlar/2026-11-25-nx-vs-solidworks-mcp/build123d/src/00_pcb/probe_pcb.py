# Probe the PCB STEP: sub-solids of key components, board cylinders, board outline section.
# usage: python probe_pcb.py <step> <out_json>
import sys, json, math
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopLoc import TopLoc_Location
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_EDGE, TopAbs_SHELL
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Line, GeomAbs_Circle
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

p = sys.argv[1]
doc = TDocStd_Document(TCollection_ExtendedString("doc"))
r = STEPCAFControl_Reader(); r.SetNameMode(True); r.ReadFile(p); r.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

def name(l):
    n = TDataStd_Name()
    return n.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), n) else "?"

def bb(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b, False)
    return [round(v, 3) for v in b.Get()]

leaves = []
def walk(lab, loc):
    if st.IsAssembly_s(lab):
        comps = TDF_LabelSequence(); st.GetComponents_s(lab, comps)
        for i in range(1, comps.Length() + 1):
            c = comps.Value(i); ref = TDF_Label(); st.GetReferredShape_s(c, ref)
            walk(ref, loc.Multiplied(st.GetLocation_s(c)))
    else:
        leaves.append((name(lab), st.GetShape_s(lab).Moved(loc)))
free = TDF_LabelSequence(); st.GetFreeShapes(free)
for i in range(1, free.Length() + 1): walk(free.Value(i), TopLoc_Location())

def solids(s):
    out = []
    e = TopExp_Explorer(s, TopAbs_SOLID)
    while e.More():
        out.append(TopoDS.Solid_s(e.Current())); e.Next()
    if not out:
        e = TopExp_Explorer(s, TopAbs_SHELL)
        while e.More():
            out.append(e.Current()); e.Next()
    return out

def vol(s):
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(s, g); return g.Mass()

def cyls(s, maxr=10):
    res = []
    e = TopExp_Explorer(s, TopAbs_FACE)
    while e.More():
        f = TopoDS.Face_s(e.Current()); a = BRepAdaptor_Surface(f)
        if a.GetType() == GeomAbs_Cylinder:
            c = a.Cylinder(); ax = c.Axis(); l = ax.Location(); d = ax.Direction()
            if c.Radius() <= maxr:
                res.append(dict(r=round(c.Radius(), 4), p=[round(l.X(), 3), round(l.Y(), 3), round(l.Z(), 3)],
                                d=[round(d.X(), 3), round(d.Y(), 3), round(d.Z(), 3)], bbox=bb(f)))
        e.Next()
    return res

out = dict(components=[], board=None)
key = ("SW_Tactile", "Alps_EC10E", "PixArt", "PinHeader")
for nm, shp in leaves:
    if nm.startswith("pcb_girdi"):
        sl = solids(shp)
        out["board"] = dict(name=nm, nsolids=len(sl), solids=[dict(bbox=bb(s), vol=round(vol(s), 2)) for s in sl],
                            cyl=cyls(shp, 50))
        continue
    if any(nm.startswith(k) for k in key):
        sl = solids(shp)
        ent = dict(name=nm, bbox=bb(shp), solids=[])
        for s in sl:
            ent["solids"].append(dict(bbox=bb(s), vol=round(vol(s), 3), cyl=cyls(s, 5)))
        out["components"].append(ent)
json.dump(out, open(sys.argv[2], "w"), indent=1)

print("BOARD solids", out["board"]["nsolids"], out["board"]["solids"][:5])
# unique cylinders through the board
seen = {}
for c in out["board"]["cyl"]:
    k = (round(c["p"][0], 2), round(c["p"][1], 2), c["r"])
    seen.setdefault(k, c)
print("board cylinders (unique xy,r):", len(seen))
for k in sorted(seen, key=lambda k: (-k[2], k[0])):
    print("  ", k, seen[k]["bbox"][2], seen[k]["bbox"][5])
for c in out["components"]:
    print("\n==", c["name"], c["bbox"], "nsolids", len(c["solids"]))
    for s in c["solids"]:
        cy = [(x["r"], x["p"], x["d"]) for x in s["cyl"]][:3]
        print("   ", s["bbox"], s["vol"], cy)
