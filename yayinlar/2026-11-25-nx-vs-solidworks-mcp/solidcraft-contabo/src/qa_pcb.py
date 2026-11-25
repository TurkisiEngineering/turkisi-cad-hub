"""Part-to-PCB clearances on meshes: dense surface samples of each part, exact point-to-mesh distance
to every PCB solid nearby. Adds `min_distance_to_pcb_mm` to qa_report.json."""
import json
import sys

import numpy as np
import trimesh
from build123d import import_step

OUT = sys.argv[1]
asm = import_step(f"{OUT}/mouse_assembly_with_pcb.step")
parts = {c.label: c for c in asm.children if c.label != "PCB"}
pcb = [c for c in asm.children if c.label == "PCB"][0]

def mesh(shape, tol=0.02):
    v, f = shape.tessellate(tol, 0.15)
    return trimesh.Trimesh(np.array([[p.X, p.Y, p.Z] for p in v]), np.array(f), process=True)

pcb_solids = [s for s in pcb.solids()]
pcb_meshes = [(s, mesh(s)) for s in pcb_solids]
res = {}
for name, part in parts.items():
    m = mesh(part)
    pts, _ = trimesh.sample.sample_surface_even(m, int(m.area * 12), seed=2)
    pts = np.vstack([pts, m.vertices])
    best = (1e9, None)
    for s, pm in pcb_meshes:
        lo, hi = pm.bounds[0] - 4, pm.bounds[1] + 4
        sel = np.all((pts >= lo) & (pts <= hi), axis=1)
        if not sel.any():
            continue
        _, d, _ = trimesh.proximity.closest_point(pm, pts[sel])
        k = float(d.min())
        if k < best[0]:
            c = s.center()
            best = (round(k, 2), [round(c.X, 1), round(c.Y, 1), round(c.Z, 1)])
    res[name] = best
    print(name, best, flush=True)
rep = json.load(open(f"{OUT}/qa_report.json"))
rep["min_distance_to_pcb_mm"] = res
rep["min_distance_to_pcb_note"] = "mesh based (point-to-mesh, chord 0.02 mm); value, centre of the nearest PCB solid"
json.dump(rep, open(f"{OUT}/qa_report.json", "w"), indent=1)
