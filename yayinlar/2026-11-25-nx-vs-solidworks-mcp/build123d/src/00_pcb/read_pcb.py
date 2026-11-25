import sys, json
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopLoc import TopLoc_Location
p = sys.argv[1]
doc = TDocStd_Document(TCollection_ExtendedString("doc"))
r = STEPCAFControl_Reader(); r.SetNameMode(True); r.ReadFile(p); r.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
def name(l):
    n = TDataStd_Name()
    return n.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), n) else "?"
out=[]
def walk(lab, loc, depth):
    comps = TDF_LabelSequence()
    if st.IsAssembly_s(lab):
        st.GetComponents_s(lab, comps)
        for i in range(1, comps.Length()+1):
            c = comps.Value(i)
            ref = TDF_Label() if False else None
            from OCP.TDF import TDF_Label
            ref = TDF_Label(); st.GetReferredShape_s(c, ref)
            l2 = loc.Multiplied(st.GetLocation_s(c))
            walk(ref, l2, depth+1)
    else:
        shp = st.GetShape_s(lab).Moved(loc)
        b = Bnd_Box(); BRepBndLib.Add_s(shp, b, False)
        x0,y0,z0,x1,y1,z1 = b.Get()
        t = loc.Transformation().TranslationPart()
        out.append(dict(name=name(lab), origin=[round(t.X(),3),round(t.Y(),3),round(t.Z(),3)], bbox=[round(v,3) for v in (x0,y0,z0,x1,y1,z1)]))
free = TDF_LabelSequence(); st.GetFreeShapes(free)
for i in range(1, free.Length()+1): walk(free.Value(i), TopLoc_Location(), 0)
json.dump(out, open(sys.argv[2],"w"), indent=1)
for o in out: print(f"{o['name'][:40]:40s} org {o['origin']} bbox {o['bbox']}")
