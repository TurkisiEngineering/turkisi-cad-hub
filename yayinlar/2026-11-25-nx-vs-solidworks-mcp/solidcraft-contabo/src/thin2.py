import sys, numpy as np, trimesh
from build123d import import_step
asm = import_step(sys.argv[1])
ch = [c for c in asm.children if c.label == "TopShell"][0]
v, f = ch.tessellate(0.01, 0.1)
m = trimesh.Trimesh(np.array([[p.X, p.Y, p.Z] for p in v]), np.array(f), process=True)
pts, fi = trimesh.sample.sample_surface(m, 40000, seed=5)
keep = pts[:, 1] < -50
pts, fi = pts[keep], fi[keep]
nrm = m.face_normals[fi]
o = pts - nrm * 1e-3
loc, idx, _ = m.ray.intersects_location(o, -nrm, multiple_hits=False)
d = np.linalg.norm(loc - o[idx], axis=1)
P, N = pts[idx], nrm[idx]
order = np.argsort(d)[:15]
for k in order:
    print("d %.2f at" % d[k], np.round(P[k], 2), "normal", np.round(N[k], 2))
print("percentiles", np.round(np.percentile(d, [1, 2, 5, 10, 50]), 2))
