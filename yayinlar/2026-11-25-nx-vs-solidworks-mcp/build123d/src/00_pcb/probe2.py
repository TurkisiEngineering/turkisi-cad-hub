# Face-level probe: board top-face wires; faces of one switch, encoder, header, sensor body.
import sys
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
from OCP.TopAbs import TopAbs_FACE, TopAbs_WIRE, TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp

doc = TDocStd_Document(TCollection_ExtendedString("doc"))
r = STEPCAFControl_Reader(); r.SetNameMode(True); r.ReadFile(sys.argv[1]); r.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
def name(l):
    n = TDataStd_Name(); return n.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), n) else "?"
def bb(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b, False); return [round(v, 3) for v in b.Get()]
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
TN = {0: "Plane", 1: "Cyl", 2: "Cone", 3: "Sph", 4: "Tor", 5: "Bez", 6: "BSp"}
CN = {0: "Line", 1: "Circ", 2: "Ell", 6: "BSp", 7: "Bez"}

def faces(s):
    e = TopExp_Explorer(s, TopAbs_FACE)
    while e.More():
        yield TopoDS.Face_s(e.Current()); e.Next()

def area(f):
    g = GProp_GProps(); BRepGProp.SurfaceProperties_s(f, g); return g.Mass()

def dump_faces(nm, s):
    print(f"\n=== {nm} {bb(s)}")
    for f in faces(s):
        a = BRepAdaptor_Surface(f); t = a.GetType()
        extra = ""
        if t == GeomAbs_Cylinder:
            c = a.Cylinder(); l = c.Axis().Location(); d = c.Axis().Direction()
            extra = f"r={c.Radius():.3f} ax=({l.X():.2f},{l.Y():.2f},{l.Z():.2f}) d=({d.X():.0f},{d.Y():.0f},{d.Z():.0f})"
        elif t == GeomAbs_Plane:
            d = a.Plane().Axis().Direction(); extra = f"n=({d.X():.2f},{d.Y():.2f},{d.Z():.2f})"
        print(f"  {TN.get(t,t):5s} A={area(f):7.2f} {bb(f)} {extra}")

for nm, shp in leaves:
    if nm.startswith("pcb_girdi"):
        print("BOARD")
        for f in faces(shp):
            a = BRepAdaptor_Surface(f)
            if a.GetType() == GeomAbs_Plane and abs(a.Plane().Axis().Direction().Z()) > 0.99 and bb(f)[2] > 1.0:
                print(" top face area", round(area(f), 2), bb(f))
                ow = BRepTools.OuterWire_s(f)
                e = TopExp_Explorer(f, TopAbs_WIRE); k = 0
                while e.More():
                    w = TopoDS.Wire_s(e.Current()); wb = bb(w)
                    big = (wb[3]-wb[0]) > 3 or (wb[4]-wb[1]) > 3
                    if w.IsSame(ow) or big:
                        print("  wire", "OUTER" if w.IsSame(ow) else "inner", wb)
                        ee = TopExp_Explorer(w, TopAbs_EDGE)
                        while ee.More():
                            ed = TopoDS.Edge_s(ee.Current()); c = BRepAdaptor_Curve(ed)
                            p0 = c.Value(c.FirstParameter()); p1 = c.Value(c.LastParameter())
                            ex = ""
                            if c.GetType() == 1:
                                ci = c.Circle(); ex = f" R={ci.Radius():.3f} c=({ci.Location().X():.3f},{ci.Location().Y():.3f})"
                            print(f"    {CN.get(c.GetType(), c.GetType())} ({p0.X():.3f},{p0.Y():.3f})->({p1.X():.3f},{p1.Y():.3f}){ex}")
                            ee.Next()
                    k += 1; e.Next()
                print("  n wires", k)
done = set()
for nm, shp in leaves:
    if (nm.startswith("SW_Tactile") and bb(shp)[0] > 55) or nm.startswith("SW_Tactile") and bb(shp)[0] < 17 and bb(shp)[1] < -60 \
       or nm.startswith("Alps") or nm.startswith("PinHeader"):
        dump_faces(nm, shp)
