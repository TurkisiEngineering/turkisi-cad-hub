import sys, numpy as np, trimesh, math
from build123d import import_step
asm = import_step(sys.argv[1])
ch = [c for c in asm.children if c.label == "DPIButton"][0]
v, f = ch.tessellate(0.005, 0.05)
m = trimesh.Trimesh(np.array([[p.X, p.Y, p.Z] for p in v]), np.array(f), process=True)
sel = (m.face_normals[:, 2] > 0.5) & (m.triangles_center[:, 2] > 26.0)
c = m.triangles_center[sel]; a = m.area_faces[sel]; n = (m.face_normals[sel] * a[:, None]).sum(0)
n /= np.linalg.norm(n)
print("cap area %.1f mm2, mean normal" % a.sum(), np.round(n, 4), "tilt about X deg %.2f" % math.degrees(math.atan2(n[1], n[2])),
      "about Y deg %.2f" % math.degrees(math.atan2(n[0], n[2])), "z range", round(c[:, 2].min(), 2), round(c[:, 2].max(), 2))
