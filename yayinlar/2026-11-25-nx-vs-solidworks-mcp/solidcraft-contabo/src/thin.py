import sys, numpy as np, trimesh
from build123d import import_step
# thin-wall map on the assembled (mouse-frame) parts: export each part from the STEP as mesh
asm = import_step(sys.argv[1])
for ch in asm.children:
    if ch.label not in ("TopShell", "ButtonL", "BottomShell"):
        continue
    v, f = ch.tessellate(0.02, 0.2)
    m = trimesh.Trimesh(np.array([[p.X, p.Y, p.Z] for p in v]), np.array(f), process=True)
    n = 6000
    pts, fi = trimesh.sample.sample_surface(m, n, seed=3)
    nrm = m.face_normals[fi]
    o = pts - nrm * 1e-3
    loc, idx, _ = m.ray.intersects_location(o, -nrm, multiple_hits=False)
    d = np.linalg.norm(loc - o[idx], axis=1)
    P = pts[idx]
    thin = d < 1.3
    print(ch.label, "samples", len(d), "thin<1.3:", int(thin.sum()))
    # cluster thin points coarsely
    if thin.any():
        q = np.round(P[thin] / 6) * 6
        u, c = np.unique(q, axis=0, return_counts=True)
        order = np.argsort(-c)[:12]
        for k in order:
            sel = np.all(np.round(P[thin] / 6) * 6 == u[k], axis=1)
            print("   near", u[k], "n", c[k], "min d %.2f" % d[thin][sel].min())
