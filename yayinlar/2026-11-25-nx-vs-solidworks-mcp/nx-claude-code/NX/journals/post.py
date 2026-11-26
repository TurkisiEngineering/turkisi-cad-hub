"""Print orientation + printability measurements on the NX STLs (assembly coordinates in render/).
Writes print-oriented STLs into TESLIM_NX/STL and printability.json."""
import json, os, sys, numpy as np, trimesh

R = r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx\render"
D = r"C:\Users\USER\Desktop\Mouse for PCB\TESLIM_NX\STL"
os.makedirs(D, exist_ok=True)


def rot(axis, deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), axis)


# print orientation per part (rotation applied about the origin, then dropped onto z=0, centred in xy)
ORIENT = {
    "bottom_shell": np.eye(4),                 # feet on the bed
    "top_shell": np.eye(4),                    # parting rim on the bed, tree supports under the roof
    "btn_left": np.eye(4),                     # as assembled: flexure tongue printed flat (layers along it)
    "btn_right": np.eye(4),
    "key_fwd": np.eye(4),                      # as assembled: hinge lug bottom on the bed, pin hole along Y
    "key_back": np.eye(4),
    "wheel": rot([0, 1, 0], 90),               # axis vertical, flat right face (x=+3.5) on the bed, stub up
}
out = {}
for k, M in ORIENT.items():
    m = trimesh.load(os.path.join(R, k + ".stl"))
    m.apply_transform(M)
    b = m.bounds
    m.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
    m.export(os.path.join(D, k + ".stl"))
    # overhangs: down-facing area steeper than 45 deg from vertical, not on the bed
    n = m.face_normals
    c = m.triangles_center
    a = m.area_faces
    down = n[:, 2] < -np.cos(np.radians(45))
    onbed = c[:, 2] < 0.05
    ov = down & ~onbed
    bed = (n[:, 2] < -0.999) & onbed
    # wall thickness by inward ray casting from sampled surface points
    pts, fi = trimesh.sample.sample_surface_even(m, 4000, seed=1)
    nn = m.face_normals[fi]
    origins = pts - nn * 1e-3
    loc, ri, ti = m.ray.intersects_location(origins, -nn, multiple_hits=False)
    th = np.full(len(pts), np.nan)
    th[ri] = np.linalg.norm(loc - origins[ri], axis=1)
    th = th[~np.isnan(th)]
    out[k] = {"watertight": bool(m.is_watertight), "volume_mm3": round(float(m.volume), 1),
              "bbox_print_mm": [round(float(x), 2) for x in (m.bounds[1] - m.bounds[0])],
              "bed_contact_mm2": round(float(a[bed].sum()), 1),
              "overhang_gt45_mm2": round(float(a[ov].sum()), 1),
              "overhang_share_pct": round(100 * float(a[ov].sum() / a.sum()), 1),
              "wall_p5_mm": round(float(np.percentile(th, 5)), 2), "wall_median_mm": round(float(np.median(th)), 2),
              "wall_min_mm": round(float(th.min()), 2)}
    print(k, out[k])
json.dump(out, open(os.path.join(R, "printability.json"), "w"), indent=1)
