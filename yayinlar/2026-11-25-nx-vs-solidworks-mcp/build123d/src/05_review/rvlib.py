"""RV01 review helpers: mesh loading, vectorised ray casts, gaps, containment. Pure numpy/scipy/trimesh."""
import numpy as np, trimesh
from scipy.spatial import cKDTree
from pathlib import Path

W = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work")
MESH = W / "05_review" / "mesh"
PCBM = W / "00_pcb" / "mesh"


def load(name):
    p = MESH / f"{name}.stl"
    m = trimesh.load(str(p), force="mesh")
    return m


def pcb_groups():
    return {p.stem: trimesh.load(str(p), force="mesh") for p in sorted(PCBM.glob("*.stl"))}


class Caster:
    """Ray caster for one mesh: KD tree on triangle centroids, Moller-Trumbore on candidates."""
    def __init__(self, m):
        self.m = m
        self.tri = m.triangles
        self.c = self.tri.mean(axis=1)
        self.r = np.max(np.linalg.norm(self.tri - self.c[:, None, :], axis=2), axis=1)
        self.rmax = float(self.r.max())
        self.kd = cKDTree(self.c)
        # XY grid for vertical rays
        self.cell = 0.5
        lo = self.tri[:, :, :2].min(axis=1); hi = self.tri[:, :, :2].max(axis=1)
        self.g0 = lo.min(axis=0) - 1
        i0 = np.floor((lo - self.g0) / self.cell).astype(int); i1 = np.floor((hi - self.g0) / self.cell).astype(int)
        nx = i1[:, 0] - i0[:, 0] + 1; ny = i1[:, 1] - i0[:, 1] + 1
        cnt = nx * ny
        tid = np.repeat(np.arange(len(self.tri)), cnt)
        off = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        nyr = np.repeat(ny, cnt)
        ix = np.repeat(i0[:, 0], cnt) + off // nyr; iy = np.repeat(i0[:, 1], cnt) + off % nyr
        key = ix.astype(np.int64) * 100000 + iy
        o = np.argsort(key, kind="stable"); key = key[o]; tid = tid[o]
        uk, st = np.unique(key, return_index=True)
        en = np.append(st[1:], len(key))
        self.grid = {int(k): tid[a:b] for k, a, b in zip(uk, st, en)}

    def vhits(self, x, y):
        """All Z where the vertical line through (x, y) crosses the mesh (sorted)."""
        k = (int(np.floor((x - self.g0[0]) / self.cell)), int(np.floor((y - self.g0[1]) / self.cell)))
        ids = self.grid.get(k[0] * 100000 + k[1])
        if ids is None:
            return np.array([])
        T = self.tri[ids]
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        # barycentric in XY
        v0 = b[:, :2] - a[:, :2]; v1 = c[:, :2] - a[:, :2]; v2 = np.array([x, y]) - a[:, :2]
        den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
        ok = np.abs(den) > 1e-14
        den = np.where(ok, den, 1)
        u = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
        v = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
        e = -1e-9
        sel = ok & (u >= e) & (v >= e) & (u + v <= 1 - e)
        z = a[sel, 2] + u[sel] * (b[sel, 2] - a[sel, 2]) + v[sel] * (c[sel, 2] - a[sel, 2])
        z = np.unique(np.round(z, 6))
        return z

    def inside(self, pts):
        """Parity containment via vertical rays (mesh must be closed)."""
        out = np.zeros(len(pts), bool)
        for i, p in enumerate(pts):
            z = self.vhits(p[0] + 1.3e-5, p[1] + 0.7e-5)
            out[i] = (np.sum(z > p[2]) % 2) == 1
        return out

    def first(self, o, d, maxlen=5.0, eps=1e-4):
        """Distance along unit dir d from origin o to the first hit (<= maxlen), np.inf if none. Vectorised per ray."""
        o = np.atleast_2d(o); d = np.atleast_2d(d)
        res = np.full(len(o), np.inf)
        mids = o + d * maxlen / 2
        cand = self.kd.query_ball_point(mids, maxlen / 2 + self.rmax)
        for i, ids in enumerate(cand):
            if not ids:
                continue
            T = self.tri[ids]
            e1 = T[:, 1] - T[:, 0]; e2 = T[:, 2] - T[:, 0]
            h = np.cross(d[i], e2); a = np.einsum("ij,ij->i", e1, h)
            ok = np.abs(a) > 1e-12
            f = np.where(ok, 1 / np.where(ok, a, 1), 0)
            s = o[i] - T[:, 0]
            u = f * np.einsum("ij,ij->i", s, h)
            q = np.cross(s, e1)
            v = f * (q @ d[i])
            t = f * np.einsum("ij,ij->i", e2, q)
            sel = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > eps) & (t <= maxlen)
            if sel.any():
                res[i] = t[sel].min()
        return res


def samples(m, spacing=0.15, seed=0):
    n = int(m.area / spacing ** 2) + 100
    pts, fi = trimesh.sample.sample_surface(m, n, seed=seed)
    return pts, m.face_normals[fi]


def gap(A_pts, B, B_pts=None, refine=3000, thresh=2.0):
    """min distance from point set A to mesh B (exact point-triangle on the nearest candidates). returns d, point"""
    if B_pts is None:
        B_pts, _ = samples(B, 0.2)
    kd = cKDTree(np.vstack([B_pts, B.vertices]))
    d0, _ = kd.query(A_pts, distance_upper_bound=thresh + 0.5)
    order = np.argsort(d0)[:refine]
    order = order[np.isfinite(d0[order])]
    if len(order) == 0:
        return float(np.min(d0)), None
    cp, d, _ = trimesh.proximity.closest_point(B, A_pts[order])
    j = int(np.argmin(d))
    return float(d[j]), A_pts[order][j]


def penetration(A_pts, B, Bc, B_pts=None, band=1.0):
    """count of A surface points inside B (only those within band of B are tested)."""
    if B_pts is None:
        B_pts, _ = samples(B, 0.2)
    kd = cKDTree(np.vstack([B_pts, B.vertices]))
    d0, _ = kd.query(A_pts, distance_upper_bound=band)
    cand = np.where(np.isfinite(d0))[0]
    if len(cand) == 0:
        return 0, None
    ins = Bc.inside(A_pts[cand])
    if ins.any():
        return int(ins.sum()), A_pts[cand][ins]
    return 0, None


def rot_x(pts, yc, zc, ang):
    p = pts.copy(); y = p[:, 1] - yc; z = p[:, 2] - zc
    c, s = np.cos(ang), np.sin(ang)
    p[:, 1] = yc + c * y - s * z; p[:, 2] = zc + s * y + c * z
    return p


def rot_y(pts, xc, zc, ang):
    """rotation about an axis along Y through (xc, zc); positive ang moves +Z points toward +X."""
    p = pts.copy(); x = p[:, 0] - xc; z = p[:, 2] - zc
    c, s = np.cos(ang), np.sin(ang)
    p[:, 0] = xc + c * x + s * z; p[:, 2] = zc - s * x + c * z
    return p


def mesh_xf(m, f):
    m2 = m.copy(); m2.vertices = f(m2.vertices.copy()); return m2
