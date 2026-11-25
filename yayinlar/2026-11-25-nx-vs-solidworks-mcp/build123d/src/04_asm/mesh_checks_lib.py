r"""WP-I mesh helpers + loaded meshes (used by mesh_checks.py, asm_order.py). Was: WP-I step 3 (cadgenbench venv): mesh clearances, motion travel, assembly sweeps.
<venv>\python mesh_checks.py  -> mesh_checks.json"""
import json, math, sys
from pathlib import Path
import numpy as np, trimesh, open3d as o3d

ASM = Path(__file__).resolve().parent; MESH = ASM / "mesh"
POSE = json.load(open(ASM / "poses.json"))
PSOL = json.load(open(ASM / "pcb_solids.json"))
PARTS = ["bottom_shell", "top_shell", "button_L", "button_R", "wheel_body", "axle_pin", "wheel_yoke",
         "dpi_button", "side_btn_fwd", "side_btn_back"]
MOVING = {"button_L", "button_R", "wheel_body", "axle_pin", "wheel_yoke", "dpi_button", "side_btn_fwd", "side_btn_back"}
M = {n: trimesh.load(MESH / f"{n}.stl") for n in PARTS}
MP = {n: trimesh.load(MESH / f"{n}_pose.stl") for n in ["button_L", "button_R", "wheel_body", "axle_pin",
                                                         "side_btn_fwd", "side_btn_back", "dpi_button"]}
PCB = {f"pcb{d['idx']:02d}:{d['label']}": trimesh.load(MESH / f"pcb_{d['idx']:02d}.stl") for d in PSOL}
# switch solids include plunger + leads: split into a body box (Z 1.595..6.595) and a plunger box (6.595..7.595)
PL = {"SW_mainL": ((20.32, -23.53), (2.9, 1.2)), "SW_mainR": ((58.42, -23.53), (2.9, 1.2)),
      "SW_middle": ((50.80, -27.975), (2.9, 1.2)), "SW_dpi": ((40.04, -43.18), (1.2, 2.9)),
      "SW_side_fwd": ((20.99, -50.80), (1.2, 2.9)), "SW_side_back": ((20.99, -68.58), (1.2, 2.9))}
for k in list(PCB):
    lab = k.split(":", 1)[1]
    if lab.startswith("SW_") and lab.endswith("_body"):
        sw = lab[:-5]; b = PCB.pop(k).bounds
        body = trimesh.creation.box(bounds=[[b[0][0], b[0][1], 1.595], [b[1][0], b[1][1], 6.595]])
        (cx, cy), (sx, sy) = PL[sw]
        pl = trimesh.creation.box(bounds=[[cx - sx / 2, cy - sy / 2, 6.595], [cx + sx / 2, cy + sy / 2, 7.595]])
        for m in (body, pl):     # subdivide for vertex sampling density
            pass
        PCB[k.split(":")[0] + ":" + sw + "_body"] = body
        PCB[k.split(":")[0] + "p:" + sw + "_plunger"] = pl
OUT = {}


def zhit(mesh, x, y, z0=-10.0, up=True):
    sc = scene([mesh]); d = (0, 0, 1) if up else (0, 0, -1)
    r = np.array([[x, y, z0, *d]], np.float32)
    t = float(sc.cast_rays(o3d.core.Tensor(r))["t_hit"].numpy()[0])
    return z0 + t if up else z0 - t


_SC = {}
def scene(meshes):
    key = tuple(id(m) for m in meshes)
    if key in _SC: return _SC[key]
    sc = o3d.t.geometry.RaycastingScene(); _SC[key] = sc
    for m in meshes:
        sc.add_triangles(o3d.core.Tensor(np.asarray(m.vertices, np.float32)),
                         o3d.core.Tensor(np.asarray(m.faces, np.uint32)))
    return sc

_SM = {}


def samples(m, n=60000):
    if (id(m), n) in _SM: return _SM[(id(m), n)]
    _SM[(id(m), n)] = _samples(m, n); return _SM[(id(m), n)]


def _samples(m, n):
    p, _ = trimesh.sample.sample_surface_even(m, n) if len(m.faces) > 50 else (m.vertices, None)
    return np.vstack([m.vertices, p]).astype(np.float32)


def mindist(a, b):
    """min distance between meshes a, b (vertices+surface samples both ways) and the closest point."""
    best = (1e9, None)
    for x, y in ((a, b), (b, a)):
        sc = scene([y]); P = samples(x)
        lo, hi = y.bounds[0] - 3.0, y.bounds[1] + 3.0
        P = P[np.all((P >= lo) & (P <= hi), axis=1)]
        if len(P) == 0: continue
        d = sc.compute_distance(o3d.core.Tensor(P)).numpy()
        i = int(np.argmin(d))
        if d[i] < best[0]: best = (float(d[i]), P[i].round(2).tolist())
    return best


def bbgap(a, b):
    g = np.maximum(a.bounds[0] - b.bounds[1], b.bounds[0] - a.bounds[1])
    return float(np.linalg.norm(np.maximum(g, 0)))


def sweep(moving, fixed, m_dir, S, P_extra=None, ignore=None):
    """moving meshes arrive along m_dir (unit), from final - S*m_dir to final. Returns hits (point, t, which)."""
    m_dir = np.asarray(m_dir, float); m_dir /= np.linalg.norm(m_dir)
    hits = []
    for src, dst, d in ((moving, fixed, -m_dir), (fixed, moving, m_dir)):
        sc = scene(list(dst.values()))
        for name, mesh in src.items():
            P = samples(mesh, 40000).astype(np.float64)
            O = P + d * 0.03
            rays = np.hstack([O, np.tile(d, (len(O), 1))]).astype(np.float32)
            t = sc.cast_rays(o3d.core.Tensor(rays))["t_hit"].numpy()
            ok = np.isfinite(t) & (t < S)
            if ignore is not None: ok &= ~ignore(P)
            for p, tt in zip(P[ok], t[ok]):
                hits.append((p.round(2).tolist(), round(float(tt) + 0.03, 3), name))
    return hits


def summarize(h):
    if not h: return dict(n=0)
    P = np.array([x[0] for x in h]); who = sorted(set(x[2] for x in h))
    return dict(n=len(h), bbox=[P.min(0).round(2).tolist(), P.max(0).round(2).tolist()], sources=who,
                tmin=min(x[1] for x in h), example=h[0])


