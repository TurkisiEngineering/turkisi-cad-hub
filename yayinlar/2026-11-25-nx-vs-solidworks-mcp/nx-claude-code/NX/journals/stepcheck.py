"""Read the delivered assembly STEP back with OCP/XCAF: leaf instances, names, solids, volumes."""
import json, sys
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TCollection import TCollection_ExtendedString
from OCP.TopLoc import TopLoc_Location
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

p = sys.argv[1]
doc = TDocStd_Document(TCollection_ExtendedString("d"))
r = STEPCAFControl_Reader(); r.SetNameMode(True)
assert r.ReadFile(p) == 1
r.Transfer(doc)


def name(l):
    a = TDataStd_Name()
    return a.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), a) else "?"


rows = []


def walk(l, loc, inst):
    if XCAFDoc_ShapeTool.IsReference_s(l):
        ref = TDF_Label(); XCAFDoc_ShapeTool.GetReferredShape_s(l, ref)
        walk(ref, loc.Multiplied(XCAFDoc_ShapeTool.GetLocation_s(l)), name(l)); return
    ch = TDF_LabelSequence(); XCAFDoc_ShapeTool.GetComponents_s(l, ch)
    if ch.Length():
        for i in range(1, ch.Length() + 1):
            walk(ch.Value(i), loc, None)
        return
    s = XCAFDoc_ShapeTool.GetShape_s(l)
    ex = TopExp_Explorer(s, TopAbs_SOLID); n = 0; v = 0.0
    while ex.More():
        g = GProp_GProps(); BRepGProp.VolumeProperties_s(ex.Current(), g); v += g.Mass(); n += 1; ex.Next()
    rows.append({"instance": inst, "product": name(l), "solids": n, "volume": round(v, 2)})


roots = TDF_LabelSequence(); XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()).GetFreeShapes(roots)
for i in range(1, roots.Length() + 1):
    print("root:", name(roots.Value(i)))
    walk(roots.Value(i), TopLoc_Location(), None)
for x in rows:
    print(x)
json.dump(rows, open(sys.argv[2], "w"), indent=1)
