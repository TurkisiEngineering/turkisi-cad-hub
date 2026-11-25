"""RV01 lead review - exact BRep checks on one delivered STEP (A1, A5, A16 for top_shell), fine re-tessellation.
usage: python rv01_step.py <part> [<step path>]   -> 05_review/mesh/<part>.stl + 05_review/mesh/<part>_step.json
"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *
import master as ML

PARTS = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work\03_parts")
OUT = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work\05_review\mesh")
name = sys.argv[1]
step = Path(sys.argv[2]) if len(sys.argv) > 2 else PARTS / name / f"{name}.step"
t0 = time.time()
shp = import_step(str(step))
sols = shp.solids()
res = dict(part=name, step=str(step), n_solids=len(sols), valid=bool(shp.is_valid),
           volume=round(sum(s.volume for s in sols), 2), t_import=round(time.time() - t0, 1))
print(name, res, flush=True)
tol = 0.01
export_stl(shp, str(OUT / f"{name}.stl"), tolerance=tol, angular_tolerance=0.08)
res["stl_tol"] = tol

if name == "top_shell":   # A16: downward planar faces and their Z
    down = []
    for f in shp.faces():
        try:
            if f.geom_type in (GeomType.PLANE, "PLANE"):
                n = f.normal_at(f.center())
                if n.Z < -0.999:
                    down.append((round(f.center().Z, 4), round(f.area, 2)))
        except Exception:
            pass
    down.sort()
    res["down_planes"] = down[:40]

# A5 exact: part & each PCB solid with overlapping bbox
pcb = ML.load_pcb()
bb = shp.bounding_box()
vols = []
for i, s in enumerate(pcb.solids()):
    sb = s.bounding_box()
    if sb.min.X > bb.max.X or sb.max.X < bb.min.X or sb.min.Y > bb.max.Y or sb.max.Y < bb.min.Y \
            or sb.min.Z > bb.max.Z + 0.1 or sb.max.Z < bb.min.Z - 0.1:
        continue
    try:
        c = shp & s
        v = sum(q.volume for q in c.solids()) if c is not None else 0.0
    except Exception as e:
        v = f"ERR {e}"
    vols.append((i, v if isinstance(v, str) else round(v, 5)))
res["A5_tested"] = len(vols)
num = [v for _, v in vols if not isinstance(v, str)]
res["A5_maxvol"] = max(num) if num else None
res["A5_hits"] = [(i, v) for i, v in vols if isinstance(v, str) or v > 1e-4]
res["t_total"] = round(time.time() - t0, 1)
json.dump(res, open(OUT / f"{name}_step.json", "w"), indent=1)
print(json.dumps(res), flush=True)
