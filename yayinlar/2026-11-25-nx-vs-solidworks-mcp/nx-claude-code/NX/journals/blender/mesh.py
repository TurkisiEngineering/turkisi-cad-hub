"""Tessellate the delivered assembly STEP finely into one STL per render group (assembly position, mm).

Mechanical parts -> one STL per instance. The PCB product (69 solids) is split into material groups by
matching each solid's bounding box to intake/pcb_flat_bodies.json (same frame).
usage: python mesh.py <mouse_assembly.step> <pcb_flat_bodies.json> <out_dir>
"""
import json, os, sys
from collections import defaultdict
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TCollection import TCollection_ExtendedString
from OCP.TopLoc import TopLoc_Location
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopoDS import TopoDS_Compound, TopoDS_Builder
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

step, bodies_json, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
BODIES = json.load(open(bodies_json))

doc = TDocStd_Document(TCollection_ExtendedString("d"))
r = STEPCAFControl_Reader(); r.SetNameMode(True)
assert r.ReadFile(step) == 1
r.Transfer(doc)


def name(l):
    a = TDataStd_Name()
    return a.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), a) else "?"


def pcb_group(nm):
    if nm == "PCB": return "pcb_board"
    if nm.startswith("SW"): return "pcb_switch"
    if nm.startswith("Encoder"): return "pcb_encoder"
    if nm == "U2_0": return "pcb_sensor"
    if nm.startswith("U2_"): return "pcb_pins"
    if nm.startswith("USB"): return "pcb_header"
    if nm.startswith("U") or nm.startswith("D"): return "pcb_ic"
    if nm.startswith("Y"): return "pcb_crystal"
    if nm.startswith("USB"): return "pcb_header"
    return "pcb_passive"        # C*, R*


def match(bb):
    best, bd = None, 1e9
    for b in BODIES:
        d = sum((x - y) ** 2 for x, y in zip(bb, b["bb"]))
        if d < bd: best, bd = b["name"], d
    return best, bd


groups = defaultdict(list)
log = []


def walk(l, loc, inst):
    if XCAFDoc_ShapeTool.IsReference_s(l):
        ref = TDF_Label(); XCAFDoc_ShapeTool.GetReferredShape_s(l, ref)
        walk(ref, loc.Multiplied(XCAFDoc_ShapeTool.GetLocation_s(l)), name(l)); return
    ch = TDF_LabelSequence(); XCAFDoc_ShapeTool.GetComponents_s(l, ch)
    if ch.Length():
        for i in range(1, ch.Length() + 1):
            walk(ch.Value(i), loc, None)
        return
    s = XCAFDoc_ShapeTool.GetShape_s(l).Moved(loc)
    ex = TopExp_Explorer(s, TopAbs_SOLID)
    while ex.More():
        so = ex.Current()
        if inst == "PCB":
            bx = Bnd_Box(); BRepBndLib.AddOptimal_s(so, bx, False, False)
            bb = bx.Get()
            nm, d = match(bb)
            g = pcb_group(nm)
            log.append((nm, g, round(d, 4)))
        else:
            g = inst.lower()
        groups[g].append(so)
        ex.Next()


roots = TDF_LabelSequence(); XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()).GetFreeShapes(roots)
for i in range(1, roots.Length() + 1):
    walk(roots.Value(i), TopLoc_Location(), None)

w = StlAPI_Writer(); w.ASCIIMode = False
summary = {}
for g, sols in groups.items():
    cc = TopoDS_Compound(); bl = TopoDS_Builder(); bl.MakeCompound(cc)
    for so in sols: bl.Add(cc, so)
    fine = not g.startswith("pcb_") or g in ("pcb_board", "pcb_encoder", "pcb_switch", "pcb_sensor")
    BRepMesh_IncrementalMesh(cc, 0.006 if fine else 0.02, False, 0.12 if fine else 0.3, True)
    p = os.path.join(out, g + ".stl")
    w.Write(cc, p)
    summary[g] = len(sols)
print(json.dumps(summary, indent=1))
print("worst PCB match d2:", max(x[2] for x in log))
json.dump({"groups": summary, "pcb_match": log}, open(os.path.join(out, "mesh_log.json"), "w"), indent=1)
