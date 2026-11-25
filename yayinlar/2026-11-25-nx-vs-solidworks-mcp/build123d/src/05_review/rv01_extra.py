"""RV01 extras: exact lip gap at the mesh-minimum points, A21 skate edge distance and A25 underside chamfer in world XY."""
import sys, json
import numpy as np, trimesh
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\05_review")
import rvlib as R
from shapely.geometry import Polygon, Point
from shapely.ops import polygonize, unary_union
B = R.load("bottom_shell"); BC = R.Caster(B)
out = {}
def outline(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    segs = [s.vertices[e.points][:, :2] for e in s.entities]
    polys = list(polygonize([tuple(map(tuple, q)) for q in segs]))
    return max(polys, key=lambda p: Polygon(p.exterior).area)
o_lo = Polygon(outline(B, -5.39).exterior); o_hi = Polygon(outline(B, -4.9).exterior)
out["A25_B_inset"] = round((o_hi.area - o_lo.area) / o_hi.exterior.length, 3)
o = Polygon(outline(B, -5.3).exterior)
rec = []
for x in np.arange(8, 71.5, 0.25):
    for y in np.arange(-124, -4, 0.25):
        z = BC.vhits(x + 1.3e-5, y + 0.7e-5)
        if len(z) and abs(z[0] + 5.05) < 0.02:
            rec.append((x, y))
rec = np.array(rec)
for nm, (y0, y1) in {"front": (-15, -6), "sensor_ring": (-70, -44), "rear": (-105, -90)}.items():
    q = rec[(rec[:, 1] > y0) & (rec[:, 1] < y1) & (rec[:, 0] > 15) & (rec[:, 0] < 64)]
    out[f"A21_edge_{nm}"] = round(min(o.exterior.distance(Point(a, b)) for a, b in q), 2)
print(out, flush=True)
# exact lip gap
from build123d import import_step, Vertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
T = import_step(r"C:\Users\marya\Desktop\Mouse for PCB\work\03_parts\top_shell\top_shell.step")
Bs = import_step(r"C:\Users\marya\Desktop\Mouse for PCB\work\03_parts\bottom_shell\bottom_shell.step")
Tm = trimesh.load(r"C:\Users\marya\Desktop\Mouse for PCB\work\03_parts\top_shell\top_shell.stl")
pts, _ = R.samples(B, 0.2); lp = pts[pts[:, 2] > 1.05]
cp, d, _ = trimesh.proximity.closest_point(Tm, lp)
idx = np.argsort(d)[:12]
def ex(S, p):
    q = BRepExtrema_DistShapeShape(S.wrapped, Vertex(*p).wrapped); q.Perform(); return q.Value(), q.PointOnShape1(1)
rows = []
for i in idx:
    dB, pB = ex(Bs, lp[i])
    pb = np.array([pB.X(), pB.Y(), pB.Z()])
    dT, _ = ex(T, pb)
    rows.append(dict(p=lp[i].round(2).tolist(), mesh_gap=round(float(d[i]), 3), exact_gap=round(dT, 3), mesh_err_B=round(dB, 3)))
    print(rows[-1], flush=True)
out["LIP_exact"] = rows
json.dump(out, open(r"C:\Users\marya\Desktop\Mouse for PCB\work\05_review\rv01_extra.json", "w"), indent=1)
