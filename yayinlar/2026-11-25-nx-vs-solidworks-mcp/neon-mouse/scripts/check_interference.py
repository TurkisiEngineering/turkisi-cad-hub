"""Fast exact interference & clearance audit for all mouse mechanical parts + PCB.
Uses bounding-box prefilter + BRepExtrema_DistShapeShape + solid-by-solid boolean Common only on overlapping pairs.
"""
import os, sys, json
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopoDS import TopoDS
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common

def load_solids(path):
    r = STEPControl_Reader()
    assert r.ReadFile(path) == 1, f"Failed to read {path}"
    r.TransferRoots()
    sh = r.OneShape()
    out = []
    exp = TopExp_Explorer(sh, TopAbs_SOLID)
    while exp.More():
        s = TopoDS.Solid_s(exp.Current())
        bb = Bnd_Box()
        BRepBndLib.AddOptimal_s(s, bb)
        p = GProp_GProps()
        BRepGProp.VolumeProperties_s(s, p)
        out.append((s, bb.Get(), p.Mass()))
        exp.Next()
    return out

def bb_overlap(a, b, tol=1e-4):
    return not (a[3] < b[0] - tol or b[3] < a[0] - tol or
                a[4] < b[1] - tol or b[4] < a[1] - tol or
                a[5] < b[2] - tol or b[5] < a[2] - tol)

def shape_vol(sh):
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(sh, p)
    return p.Mass()

def shape_bb(sh):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(sh, b)
    return [round(v, 2) for v in b.Get()]

stp_dir = sys.argv[1]
pcb_path = sys.argv[2]

parts = {}
parts["PCB"] = load_solids(pcb_path)
for n in ["mouse_base", "mouse_top_shell", "mouse_scroll_wheel", "mouse_dpi_button", "mouse_thumb_fwd", "mouse_thumb_back", "mouse_skates"]:
    p = os.path.join(stp_dir, n + ".step")
    if os.path.exists(p):
        parts[n] = load_solids(p)

print("=== PART SUMMARY ===")
for name, sols in parts.items():
    tv = sum(v for _, _, v in sols)
    if name == "PCB":
        print(f"  {name:20s}: {len(sols):2d} solids, total vol={tv:9.2f} mm3")
    else:
        for idx, (_, bb, v) in enumerate(sols):
            print(f"  {name:20s}[{idx}]: vol={v:9.2f} mm3  bbox={[round(x,2) for x in bb]}")

print("\n=== PAIRWISE INTERFERENCE & CLEARANCE CHECK ===")
keys = list(parts.keys())
issues = []
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        na, nb = keys[i], keys[j]
        min_d = 999.0
        inter_vol = 0.0
        inter_hits = []
        for ia, (sa, bba, _) in enumerate(parts[na]):
            for ib, (sb, bbb, _) in enumerate(parts[nb]):
                # Quick bbox distance lower bound
                dx = max(bba[0] - bbb[3], bbb[0] - bba[3], 0.0)
                dy = max(bba[1] - bbb[4], bbb[1] - bba[4], 0.0)
                dz = max(bba[2] - bbb[5], bbb[2] - bba[5], 0.0)
                lb = (dx*dx + dy*dy + dz*dz) ** 0.5
                if lb > min_d and not bb_overlap(bba, bbb):
                    continue
                ext = BRepExtrema_DistShapeShape(sa, sb)
                ext.Perform()
                d = ext.Value() if ext.IsDone() else 999.0
                if d < min_d:
                    min_d = d
                if d < 1e-4 and bb_overlap(bba, bbb):
                    c = BRepAlgoAPI_Common(sa, sb)
                    c.Build()
                    if c.IsDone():
                        iv = shape_vol(c.Shape())
                        if iv > 1e-3:
                            inter_vol += iv
                            inter_hits.append((ia, ib, round(iv, 3), shape_bb(c.Shape())))
        status = "INTERFERENCE!" if inter_vol > 0.01 else ("TOUCH" if min_d < 0.005 else "CLEAR")
        print(f"  {na:20s} x {nb:20s}: min_dist={min_d:7.4f} mm | inter={inter_vol:8.3f} mm3  [{status}]")
        for hit in inter_hits:
            print(f"      -> solid {na}[{hit[0]}] x {nb}[{hit[1]}]: vol={hit[2]} mm3 bbox={hit[3]}")
            issues.append((na, nb, hit))

print(f"\nTotal interference pairs: {len(issues)}")
