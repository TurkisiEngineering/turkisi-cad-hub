"""Independent QA of the exported files (build123d + trimesh), not trusting SolidCraft's own numbers."""
import glob
import json
import os
import sys

import numpy as np
import trimesh
from build123d import import_step
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

OUT = sys.argv[1]
rep = {}

asm = import_step(f"{OUT}/mouse_assembly_with_pcb.step")
def leaves(s, acc):
    ch = list(getattr(s, "children", []) or [])
    if not ch:
        acc.append(s)
    for c in ch:
        leaves(c, acc)
    return acc
L = leaves(asm, [])
by = {}
for s in L:
    by.setdefault(s.label, []).append(s)
rep["step_top_children"] = [c.label for c in asm.children]
rep["step_leaf_count"] = len(L)

def get(name):
    if name in by:
        return by[name][0]
    raise KeyError(name)

def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return round(d.Value(), 3)

KEY = ("SW_Tactile", "Alps_EC10E", "PixArt", "PinHeader", "pcb_girdi_PCB", "SOT-223", "SOIC", "QFN")
pcb_parts = [s for s in L if (s.label or "").startswith(KEY) and s.volume > 5]
if not pcb_parts and "PCB" in by:
    pcb_parts = [s for s in by["PCB"][0].solids() if s.volume > 3]
rep["pcb_solids_checked"] = len(pcb_parts)
def min_to_pcb(part):
    best = (1e9, None)
    for p in pcb_parts:
        bb1, bb2 = part.bounding_box(), p.bounding_box()
        # quick reject if boxes are far apart
        gap = max(bb1.min.X - bb2.max.X, bb2.min.X - bb1.max.X, bb1.min.Y - bb2.max.Y, bb2.min.Y - bb1.max.Y,
                  bb1.min.Z - bb2.max.Z, bb2.min.Z - bb1.max.Z, 0)
        if gap > best[0]:
            continue
        d = dist(part, p)
        if d < best[0]:
            c = p.center()
            best = (d, [round(c.X, 1), round(c.Y, 1), round(c.Z, 1)])
    return best

pairs = [("ButtonL", "TopShell"), ("ButtonR", "TopShell"), ("ButtonL", "BottomShell"), ("ButtonL", "Wheel"),
         ("ButtonR", "Wheel"), ("Wheel", "BottomShell"), ("Wheel", "TopShell"), ("DPIButton", "TopShell"),
         ("SideBtnF", "TopShell"), ("SideBtnF", "BottomShell"), ("SideBtnR", "TopShell"), ("SideBtnR", "BottomShell"),
         ("TopShell", "BottomShell"), ("WheelPin", "BottomShell"), ("ButtonL", "ButtonR")]
rep["min_distance_mm"] = {f"{a}~{b}": dist(get(a), get(b)) for a, b in pairs}
rep["min_distance_to_pcb_mm"] = {p: min_to_pcb(get(p)) for p in
                                 ("BottomShell", "TopShell", "ButtonL", "ButtonR", "DPIButton", "SideBtnF", "SideBtnR", "Wheel", "WheelPin")}

# STLs: watertight, volume, bed contact
st = {}
for f in sorted(glob.glob(f"{OUT}/stl/*.stl")):
    m = trimesh.load(f)
    zmin = m.bounds[0][2]
    tri_bed = m.triangles_center[:, 2] < zmin + 0.02
    down = m.face_normals[:, 2] < -0.99
    bed_area = float(m.area_faces[tri_bed & down].sum())
    st[os.path.basename(f)] = dict(watertight=bool(m.is_watertight), volume_cm3=round(m.volume / 1000, 2),
                                   bbox=[round(v, 1) for v in (m.extents)], zmin=round(zmin, 3),
                                   bed_contact_mm2=round(bed_area, 1), triangles=len(m.faces))
rep["stl"] = st

# wall thickness by inward ray casting (shell parts)
def thickness(path, n=1500, seed=1):
    m = trimesh.load(path)
    rng = np.random.default_rng(seed)
    pts, fi = trimesh.sample.sample_surface(m, n, seed=seed)
    nrm = m.face_normals[fi]
    origins = pts - nrm * 1e-3
    loc, idx_ray, _ = m.ray.intersects_location(origins, -nrm, multiple_hits=False)
    d = np.full(n, np.nan)
    d[idx_ray] = np.linalg.norm(loc - origins[idx_ray], axis=1)
    d = d[~np.isnan(d)]
    return dict(p1=round(float(np.percentile(d, 1)), 2), p5=round(float(np.percentile(d, 5)), 2),
                median=round(float(np.median(d)), 2))
rep["thickness_mm"] = {os.path.basename(f): thickness(f) for f in
                       (f"{OUT}/stl/01_bottom_shell.stl", f"{OUT}/stl/02_top_shell.stl", f"{OUT}/stl/03_button_left.stl")}
json.dump(rep, open(f"{OUT}/qa_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1))
print("labels", sorted(set(s.label for s in L))[:12])
