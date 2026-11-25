"""
check_top_shell.py - self-checks for WP-E top_shell, measured on the EXPORTED geometry
(top_shell.step / .stl) against master.py interfaces, the PCB STEP / meshes and ML.button_panel_raw.
Writes check_top_shell.json next to this file and prints one line per check.

Run after build_top_shell.py:  python check_top_shell.py
"""
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *          # noqa: E402,F401
import master as ML              # noqa: E402
import numpy as np               # noqa: E402
import trimesh                   # noqa: E402

PARAMS = dict(
    density_pla=1.24,            # g/cm3 (PLA)
    n_surface=150000,            # surface samples on the top shell for distance checks
    n_fixed=30000,               # samples per fixed-part mesh for the drop sweep
    drop=15.0,                   # A23 drop height
    wheel_drop=0.30,             # wheel dropped by the middle click (spec 4.2)
    a11_band=(0.40, 0.60),
    nose_min=1.30,
    wall_min=ML.MIN_WALL,
    n_wall=6000,
    overhang_deg=45.0,
    on_skin_tol=0.05,
)
P = PARAMS
D = Path(__file__).resolve().parent
RES = []


def rec(cid, what, value, ok, note=""):
    RES.append(dict(id=cid, what=what, value=value, pass_=bool(ok), note=note))
    print(f"{'PASS' if ok else 'FAIL'}  {cid:<10} {what}: {value} {note}")


def mesh_dist(mesh, pts):
    return trimesh.proximity.ProximityQuery(mesh).on_surface(pts)[1]


def dist_box(pts, b):
    x0, y0, z0, x1, y1, z1 = b
    dx = np.maximum.reduce([x0 - pts[:, 0], pts[:, 0] - x1, np.zeros(len(pts))])
    dy = np.maximum.reduce([y0 - pts[:, 1], pts[:, 1] - y1, np.zeros(len(pts))])
    dz = np.maximum.reduce([z0 - pts[:, 2], pts[:, 2] - z1, np.zeros(len(pts))])
    return np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)


def dist_wheel(pts, dz=0.0):
    yc, zc = ML.WHEEL_C[1], ML.WHEEL_C[2] - dz
    x0, x1 = ML.WHEEL_X
    r = np.hypot(pts[:, 1] - yc, pts[:, 2] - zc)
    dr = np.maximum(r - ML.WHEEL_D / 2, 0)
    dx = np.maximum.reduce([x0 - pts[:, 0], pts[:, 0] - x1, np.zeros(len(pts))])
    return np.hypot(dr, dx)


def main():
    t0 = time.time()
    T = import_step(str(D / "top_shell.step"))
    sols = T.solids()
    S = sols[0]
    m = trimesh.load(str(D / "top_shell.stl"))
    rec("A1", "n_solids / is_valid", f"{len(sols)} / {S.is_valid}", len(sols) == 1 and S.is_valid)
    vol = S.volume
    rec("VOL", "volume mm3 / mass g (PLA 1.24)", f"{vol:.1f} / {vol * P['density_pla'] / 1000:.1f}", vol > 0)
    rec("WT", "STL watertight / winding consistent", f"{m.is_watertight} / {m.is_winding_consistent}",
        m.is_watertight and m.is_winding_consistent)
    pm = trimesh.load(str(D / "top_shell_print.stl"))
    rec("PRINT", "print STL min Z / watertight", f"{pm.bounds[0][2]:.4f} / {pm.is_watertight}",
        abs(pm.bounds[0][2]) < 1e-3 and pm.is_watertight)
    lo, hi = m.bounds
    env = f"X {lo[0]:.2f}..{hi[0]:.2f}  Y {lo[1]:.2f}..{hi[1]:.2f}  Z {lo[2]:.3f}..{hi[2]:.2f} " \
          f"(L {hi[1] - lo[1]:.2f} x W {hi[0] - lo[0]:.2f}, top {hi[2] - ML.Z_FLOOR:.2f} above floor)"
    rec("ENV", "envelope (mesh bounds)", env, True)

    # ---- A16: min Z = Z_PART, bottom = planar faces at Z_PART
    bot = [f for f in S.faces() if f.geom_type == GeomType.PLANE and f.normal_at().Z < -0.999]
    bz = sorted({round(f.center().Z, 4) for f in bot})
    low = [f for f in bot if f.center().Z < ML.Z_PART + 1e-3]
    rec("A16", "mesh min Z / downward planar faces at min Z (count, area)",
        f"{lo[2]:.4f} / {len(low)} faces, {sum(f.area for f in low):.1f} mm2, Z set {bz[:3]}",
        abs(lo[2] - ML.Z_PART) < 1e-3 and all(abs(f.center().Z - ML.Z_PART) < 1e-4 for f in low))

    # ---- A25: rim chamfer: outer outline at Z_PART+0.01 vs skin outline
    sk = ML.mesh_of(ML.skin(), 0.01)
    pts_rim = m.vertices[np.abs(m.vertices[:, 2] - ML.Z_PART) < 1e-4]
    d_rim = mesh_dist(sk, pts_rim)
    outer_rim = d_rim[d_rim < 0.6]
    rec("A25", "rim bed edge inset from skin (chamfer 0.3), median / max of outer rim vertices",
        f"{np.median(outer_rim):.3f} / {outer_rim.max():.3f}", 0.2 < np.median(outer_rim) < 0.4)

    # ---- samples on the part
    spts, sfi = trimesh.sample.sample_surface_even(m, P["n_surface"])
    spts = np.vstack([spts, m.vertices])

    # ---- A5: PCB interference (exact boolean vs the original STEP solids)
    pcb = ML.load_pcb()
    bb = S.bounding_box()
    inter = 0.0
    n_test = 0
    for s in pcb.solids():
        b = s.bounding_box()
        if b.max.Z < ML.Z_PART or b.min.X > bb.max.X or b.max.X < bb.min.X or b.min.Y > bb.max.Y or b.max.Y < bb.min.Y:
            continue
        n_test += 1
        r = S & s
        inter += sum(x.volume for x in r.solids()) if r is not None else 0.0
    rec("A5", "top_shell AND PCB STEP solids volume", f"{inter:.4f} mm3 ({n_test} solids tested)", inter < 1e-6)

    # ---- A6: clearance to PCB components (mesh, both directions)
    mdir = ML.WORK / "00_pcb" / "mesh"
    worst = {}
    for f in sorted(mdir.glob("*.stl")):
        g = trimesh.load(str(f))
        gp, _ = trimesh.sample.sample_surface_even(g, 40000)
        gp = np.vstack([gp, g.vertices])
        d1 = mesh_dist(m, gp)
        near = spts[np.all((spts >= g.bounds[0] - 6) & (spts <= g.bounds[1] + 6), axis=1)]
        d2 = mesh_dist(g, near).min() if len(near) else 99.0
        worst[f.stem] = round(float(min(d1.min(), d2)), 3)
    wmin = min(worst.values())
    rec("A6", "min distance top_shell -> PCB meshes (per group)", f"{wmin:.3f} {worst}", wmin >= ML.CLR_PCB)

    # ---- clearance to master envelopes
    bsr = trimesh.load(str(ML.OUT / "bottom_shell_raw.stl"))
    fbs = ML.PARTS_DIR / "bottom_shell" / "bottom_shell.stl"          # WP-D part if built (the out/ raw STL is stale)
    bsl = trimesh.load(str(fbs)) if fbs.exists() else bsr
    # lip + notch tabs = bottom_shell_raw material above the parting plane (the rim contact at Z_PART is designed)
    bp_, _ = trimesh.sample.sample_surface_even(bsl, 80000)
    bp_ = np.vstack([bp_, bsl.vertices])
    bp_ = bp_[bp_[:, 2] > ML.Z_PART + 0.05]
    dlip = mesh_dist(m, bp_).min()
    rec("CLR_LIP", f"{'bottom_shell (WP-D)' if fbs.exists() else 'bottom_shell_raw'} lip/tabs (Z>1.05) -> top_shell min gap", f"{dlip:.3f}", dlip >= 0.10,
        f"(design lip gap {ML.LIP_GAP}, tab gap 0.15)")
    dw0 = dist_wheel(spts).min()
    dw1 = dist_wheel(spts, P["wheel_drop"]).min()
    rec("A13", "wheel envelope (d23.6 x 7.5) -> top_shell min gap rest / dropped 0.30", f"{dw0:.3f} / {dw1:.3f}",
        dw0 >= 0.3 - 1e-3 and dw1 >= 0.3 - 1e-3)
    yb = (ML.YOKE_X[0], ML.YOKE_Y[0], ML.Z_INNER_FLOOR - ML.YOKE_SOCKET_DEPTH, ML.YOKE_X[1], ML.YOKE_Y[1], ML.YOKE_TOP_Z)
    dy = dist_box(spts, yb).min()
    rec("CLR_YOKE", "yoke envelope -> top_shell min gap", f"{dy:.3f}", dy >= 0.5)
    c = ML.DPI_CAP
    cap = (c[0], c[1], ML.DPI_GUIDE_Z - 0.15 - 1.0, c[2], c[3], 30.0)
    dcap = dist_box(spts, cap).min()
    fl = (c[0] - ML.DPI_FLANGE, c[1] - ML.DPI_FLANGE, ML.DPI_GUIDE_Z - 0.15 - 1.0,
          c[2] + ML.DPI_FLANGE, c[3] + ML.DPI_FLANGE, ML.DPI_GUIDE_Z - 0.15)
    dfl = dist_box(spts, fl).min()
    rec("CLR_DPI", "DPI cap body -> sleeve bore gap / flange -> sleeve bottom gap", f"{dcap:.3f} / {dfl:.3f}",
        abs(dcap - ML.DPI_GUIDE_CLR) < 0.02 and dfl >= 0.10)
    # wheel to sleeve (brief: >= 0.5)
    sl = spts[(spts[:, 1] < c[1] + 2) & (spts[:, 1] > c[1] - 3) & (spts[:, 2] < 22)]
    rec("CLR_SLV_WHL", "DPI sleeve -> wheel (rest / dropped)", f"{dist_wheel(sl).min():.3f} / {dist_wheel(sl, P['wheel_drop']).min():.3f}",
        dist_wheel(sl).min() >= 0.5)

    # ---- A11 / A12: buttons (WP-F parts if present, else raw panels)
    for side in "LR":
        f = ML.PARTS_DIR / f"button_{side}" / f"button_{side}.stl"
        src = "WP-F part" if f.exists() else "ML.button_panel_raw"
        bm = trimesh.load(str(f)) if f.exists() else ML.mesh_of(ML.button_panel_raw(side), 0.01)
        bp, _ = trimesh.sample.sample_surface_even(bm, 60000)
        bp = np.vstack([bp, bm.vertices])
        keep = bp[:, 1] > ML.LEAF_WEB_Y[0]          # leaf (clamped under the pad = designed contact) excluded
        d = mesh_dist(m, bp[keep])
        a11 = d.min()
        # nose split: vertical gap under the button nose, away from the side splits (> 1.5 inside the region)
        from shapely.geometry import Polygon, Point
        poly = Polygon(ML.btn_region_pts(side)).buffer(-1.5)
        nose = bp[(bp[:, 2] < ML.Z_BTN_LOW + ML.BTN_FRONT_GAP / 2 + 0.05)]
        nose = nose[[poly.contains(Point(p[0], p[1])) for p in nose]]
        dn = mesh_dist(m, nose).min() if len(nose) else float("nan")
        rec(f"A11_{side}", f"button_{side} ({src}, leaf Y<-59.4 excluded) -> top_shell min gap / nose split gap",
            f"{a11:.3f} / {dn:.3f}", P["a11_band"][0] <= a11 <= P["a11_band"][1] and dn >= P["nose_min"])
        # A12: rotate about HINGE_PIVOT (axis X) by the full stop, front goes down
        ang = -math.atan(ML.TRAVEL_STOP / 39.87)
        R = trimesh.transformations.rotation_matrix(ang, [1, 0, 0], [0, ML.HINGE_PIVOT[0], ML.HINGE_PIVOT[1]])
        bpr = trimesh.transformations.transform_points(bp[bp[:, 1] > ML.HINGE_PIVOT[0]], R)   # leaf behind the pivot bends, stays clamped
        sd = trimesh.proximity.signed_distance(m, bpr[::6])      # >0 = inside the top shell
        dmin = mesh_dist(m, bpr).min()
        rec(f"A12_{side}", f"button_{side} rotated {math.degrees(ang):.3f} deg: max penetration / min gap",
            f"{max(sd.max(), 0):.3f} / {dmin:.3f}", sd.max() <= 1e-3)

    # ---- A15: wall thickness (outer-skin samples, ray along -normal, valid when the exit face is the inner skin)
    skin_pq = trimesh.proximity.ProximityQuery(sk)
    fid = np.arange(len(m.faces))
    cen = m.triangles_center[fid]
    on_skin = np.abs(skin_pq.signed_distance(cen)) < P["on_skin_tol"]
    cen, nrm = cen[on_skin], m.face_normals[fid][on_skin]
    
    loc, ir, it = m.ray.intersects_location(cen - nrm * 0.01, -nrm, multiple_hits=False)
    th = np.linalg.norm(loc - cen[ir], axis=1) + 0.01
    inn = ML.mesh_of(ML.inner(), 0.01)
    on_inner = np.abs(trimesh.proximity.ProximityQuery(inn).signed_distance(loc)) < P["on_skin_tol"]
    tv = th[on_inner]
    rec("A15", "wall thickness skin->inner skin along the normal (min / p1 / median, n)",
        f"{tv.min():.3f} / {np.percentile(tv, 1):.3f} / {np.median(tv):.3f}, n={len(tv)}", tv.min() >= P["wall_min"])
    te = th[~on_inner]
    pe = loc[~on_inner]
    thin = pe[te < P["wall_min"]]
    rec("A15_edge", "normal rays leaving through a cut face (free edges): n<1.6 / min / where",
        f"{len(thin)} / {te.min():.3f} / X {thin[:, 0].min():.1f}..{thin[:, 0].max():.1f} Y {thin[:, 1].min():.1f}..{thin[:, 1].max():.1f}"
        if len(thin) else "0", len(thin) == 0,
        "(knife edge where the vertical button side-split cuts the inclined side wall - master button_prism)")

    # ---- A18 / A19: insert holes open from below + depth; leaf pilots; measured placement from BRep cylinders
    def cyl_faces(r):
        out = []
        for f in S.faces():
            if f.geom_type == GeomType.CYLINDER and abs(f.radius - r) < 1e-3:
                c0 = f.bounding_box().center()
                out.append((round(c0.X, 3), round(c0.Y, 3)))
        return sorted(set(out))
    ins = cyl_faces(ML.TS_INSERT_HOLE[0] / 2)
    deps = []
    for (x, y) in ML.TS_SCREWS:
        loc, _, _ = m.ray.intersects_location([[x, y, ML.Z_PART - 5]], [[0, 0, 1]])
        zz = np.sort(loc[:, 2]) if len(loc) else np.array([99.0])
        deps.append(round(float(zz[0] - ML.Z_PART), 3))
        hole_open = S & Solid.make_cylinder(ML.TS_INSERT_HOLE[0] / 2 - 0.05, ML.TS_INSERT_HOLE[1] + 0.99,
                                            Plane(origin=(x, y, ML.Z_PART - 1)))
        v = sum(q.volume for q in hole_open.solids()) if hole_open is not None else 0.0
        if v > 1e-6:
            deps[-1] = -1
    rec("A18", "TS insert holes: first material above Z_PART along the axis (=hole depth), d3.2 hole centres",
        f"depths {deps}; centres {ins}", all(d >= ML.TS_INSERT_HOLE[1] - 1e-3 for d in deps) and len(ins) == 3)
    rec("A19_ins", "insert hole d x depth", f"{ML.TS_INSERT_HOLE[0] if len(ins) == 3 else 'n/a'} x min {min(deps)}",
        min(deps) >= ML.TS_INSERT_HOLE[1] - 1e-3)
    pil = cyl_faces(ML.LEAF_SCREW_PILOT[0] / 2)
    pdep = []
    pad_face = []
    for (x, y) in (ML.LEAF_SCREW_L, ML.LEAF_SCREW_R):
        loc, _, _ = m.ray.intersects_location([[x, y, 0.0]], [[0, 0, 1]])
        zz = np.sort(loc[:, 2])
        pdep.append(round(float(zz[0] - ML.LEAF_Z_TOP), 3))
        loc2, _, _ = m.ray.intersects_location([[x, y - 1.5, 0.0]], [[0, 0, 1]])
        pad_face.append(round(float(np.sort(loc2[:, 2])[0]), 3))
    rec("A19_leaf", "leaf pilot d1.6 depth above pad face (>=5) / pad face Z (=20.0) / pilot centres",
        f"{pdep} / {pad_face} / {pil}", min(pdep) >= ML.LEAF_SCREW_PILOT[1] and
        all(abs(z - ML.LEAF_Z_TOP) < 0.01 for z in pad_face) and len(pil) == 2)
    pins = cyl_faces(ML.LEAF_PIN_D / 2)
    tips = []
    for (x, y) in pins:
        loc, _, _ = m.ray.intersects_location([[x, y, 0.0]], [[0, 0, 1]])
        tips.append(round(float(np.sort(loc[:, 2])[0]), 3))
    rec("PINS", "locating pins d1.5: centres / tip Z (=19.0)", f"{pins} / {tips}",
        len(pins) == 4 and all(abs(t - (ML.LEAF_Z_TOP - 1.0)) < 0.01 for t in tips))
    # rails + sleeve bottoms
    wx0, wy0, wx1, wy1 = ML.WHEEL_WIN
    rz = []
    for x in ((ML.X_CL - ML.TONGUE_HW + wx0) / 2, (wx1 + ML.X_CL + ML.TONGUE_HW) / 2):
        loc, _, _ = m.ray.intersects_location([[x, (wy0 + wy1) / 2, 0.0]], [[0, 0, 1]])
        rz.append(round(float(np.sort(loc[:, 2])[0]), 3))
    loc, _, _ = m.ray.intersects_location([[c[0] - 0.5, (c[1] + c[3]) / 2, 0.0]], [[0, 0, 1]])
    sz = round(float(np.sort(loc[:, 2])[0]), 3)
    rec("FEAT", "rail web bottoms Z (=12.5) / DPI sleeve bottom Z (=13.5)", f"{rz} / {sz}",
        all(abs(z - ML.RAIL_WEB_Z) < 0.01 for z in rz) and abs(sz - ML.DPI_GUIDE_Z) < 0.01)

    # ---- A17: overhangs in print orientation (= assembly orientation, rim on the bed)
    nz = m.face_normals[:, 2]
    down = nz < -math.cos(math.radians(P["overhang_deg"]))
    bed = np.abs(m.triangles_center[:, 2] - ML.Z_PART) < 1e-3
    oh = down & ~bed
    outer = np.abs(skin_pq.signed_distance(m.triangles_center[oh])) < P["on_skin_tol"]
    a_out = m.area_faces[oh][outer].sum()
    a_in = m.area_faces[oh][~outer].sum()
    rec("A17", "overhang >45 deg area: on the outer skin / inside (declared tree-support zone)",
        f"{a_out:.2f} / {a_in:.1f} mm2", a_out < 1.0)

    # ---- A23: vertical drop +15 -> 0 over the fixed parts (PCB, bottom_shell_raw, wheel, yoke, built levers)
    fixed = {"pcb": trimesh.load(str(ML.PCB_STL)), "bottom_shell_raw": bsr}
    wheel = trimesh.creation.cylinder(radius=ML.WHEEL_D / 2, height=ML.WHEEL_W, sections=96)
    wheel.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    wheel.apply_translation([ML.X_CL, ML.WHEEL_C[1], ML.WHEEL_C[2]])
    fixed["wheel_env"] = wheel
    fixed["yoke_env"] = trimesh.creation.box(bounds=[yb[:3], yb[3:]])
    for nm in ("side_btn_fwd", "side_btn_back", "wheel", "wheel_yoke", "bottom_shell"):
        f = ML.PARTS_DIR / nm / f"{nm}.stl"
        if f.exists():
            fixed[nm] = trimesh.load(str(f))
    hits = {}
    for nm, g in fixed.items():
        gp, _ = trimesh.sample.sample_surface_even(g, P["n_fixed"])
        gp = np.vstack([gp, g.vertices])
        gp = gp[gp[:, 2] > ML.Z_PART + 0.01]          # rim contact plane Z_PART is the designed joint
        n = 0
        if len(gp):
            loc, ir, _ = m.ray.intersects_location(gp + [0, 0, 1e-4], np.tile([0, 0, -1.0], (len(gp), 1)))
            if len(loc):
                dz = gp[ir, 2] - loc[:, 2]
                n += int((dz <= P["drop"]).sum())
        # reverse: top-shell points with fixed material above within the drop
        up = spts[(spts[:, 2] <= g.bounds[1][2]) & (spts[:, 2] > ML.Z_PART + 0.01)]
        up = up[np.all((up[:, :2] >= g.bounds[0][:2]) & (up[:, :2] <= g.bounds[1][:2]), axis=1)]
        if len(up):
            loc, ir, _ = g.ray.intersects_location(up - [0, 0, 1e-4], np.tile([0, 0, 1.0], (len(up), 1)))
            if len(loc):
                n += int(((loc[:, 2] - up[ir, 2]) <= P["drop"]).sum())
        hits[nm] = n
    rec("A23", "drop sweep collisions per fixed part (ray samples)", f"{hits}", sum(hits.values()) == 0,
        "(levers not yet built -> not in the set)" if "side_btn_fwd" not in fixed else "")

    out = dict(results=[dict(r, **{"pass": r.pop("pass_")}) for r in RES], runtime_s=round(time.time() - t0, 1))
    (D / "check_top_shell.json").write_text(json.dumps(out, indent=1))
    print(f"checks done in {time.time() - t0:.1f}s; {sum(r['pass'] for r in out['results'])}/{len(out['results'])} pass")


if __name__ == "__main__":
    main()
