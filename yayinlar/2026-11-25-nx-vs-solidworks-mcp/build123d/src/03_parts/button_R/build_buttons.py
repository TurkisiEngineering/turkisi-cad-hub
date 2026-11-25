"""build_buttons.py - WP-F main buttons L + R (PETG), native PCB coords (+X right, +Y front, +Z up), mm.

Builds button_L and button_R from master.button_panel_raw(side) + nub + stop post + web + flexure leaf,
validates, exports STEP/STL (assembly position) + <part>_print.stl (finger face up, resting on Z 0),
and runs the WP-F self-checks (A1, A5, A6, A7, A9, A11, A12, A15 panel, tip travel, leaf strain).
Checks are measured on the built geometry (BRep for validity/volume, 0.02 mesh for distances/rays).

Run:  python build_buttons.py               build + export + check
      python build_buttons.py --check-only  re-check the exported STEP files
Master copy in 03_parts/button_L/, copied to 03_parts/button_R/ on every run.
"""
import sys, json, math, time, shutil
from pathlib import Path

sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *          # noqa: E402,F401  (must come before master)
import master as ML              # noqa: E402
import numpy as np               # noqa: E402
import trimesh                   # noqa: E402

# ====================================================================================================
# PARAMS - every interface number comes from master (ML.*); only local feature sizes are defined here
# ====================================================================================================
PARAMS = dict(
    sides=("L", "R"),
    # nub (interface: ML.NUB_PAD, ML.NUB_Z, ML.SW_MAIN_L/R)
    nub_pad_t=1.0,            # pad thickness (Z) above the contact face
    nub_pad_r=0.3,            # edge radius on the pad (CONSTRAINTS: flat, edge R0.3)
    nub_stem=(2.5, 2.5),      # stem X x Y (brief: >= 2.5 x 2.5)
    nub_gusset_h=2.0,         # 45 deg gusset height under the panel (stem widens by 2*h)
    # merge depth: features are clipped by the skin offset inward by this (= half the wall) so they
    # overlap the panel by 0.9 instead of sharing its curved inner face (robust OCC fuse)
    merge_offset=0.9,
    # leaf holes (interface: ML.LEAF_SCREW_*, ML.LEAF_PIN_DX)
    leaf_screw_hole_d=2.4,    # brief: hole d2.4 at LEAF_SCREW
    leaf_pin_hole_d=1.7,      # brief: holes d1.7 at screw X +/- LEAF_PIN_DX
    z_feature_top=40.0,       # raw feature boxes run up to here, then get clipped by the skin offset
    # checks
    press_travel=ML.TRAVEL_STOP,  # 0.8 at the nub
    tip_travel_max=1.3,
    leaf_strain_max=0.01,     # PETG 1 %
    a7=(0.05, 0.30), a9=(0.75, 0.90), a11=(0.40, 0.60), a11_nose=1.30,
    clr_moving=ML.CLR_SLIDE,  # 0.25 moving part to PCB
    min_wall=ML.MIN_WALL,
    density_petg=1.27e-3,     # g/mm3
    mesh_tol=0.01,
    mesh_ang=0.05,            # ML.export_part's 0.15 rad leaves ~0.2 mm chord error on the panel B-spline -> re-export
    n_samples=60000,
)
P = PARAMS
OUTDIR = {s: ML.part_dir(f"button_{s}") for s in P["sides"]}


# ====================================================================================================
# helpers
# ====================================================================================================
def one_solid(shape, what):
    sols = shape.solids() if shape is not None else []
    if len(sols) != 1:
        raise RuntimeError(f"{what}: expected 1 solid, got {len(sols)}")
    s = sols[0]
    if not s.is_valid or s.volume <= 0:
        raise RuntimeError(f"{what}: invalid solid (valid={s.is_valid}, vol={s.volume})")
    return s


def sw_xy(side):
    return ML.SW_MAIN_L if side == "L" else ML.SW_MAIN_R


def leaf_x(side):
    return ML.LEAF_X_L if side == "L" else ML.LEAF_X_R


def leaf_screw(side):
    return ML.LEAF_SCREW_L if side == "L" else ML.LEAF_SCREW_R


def stop_pad(side):
    return ML.STOP_PAD_L if side == "L" else ML.STOP_PAD_R


def frustum(cx, cy, w0, d0, z0, w1, d1, z1):
    """Rectangular frustum (ruled loft) from w0 x d0 at z0 to w1 x d1 at z1."""
    def rw(w, d, z):
        return Wire.make_polygon([Vector(cx - w / 2, cy - d / 2, z), Vector(cx + w / 2, cy - d / 2, z),
                                  Vector(cx + w / 2, cy + d / 2, z), Vector(cx - w / 2, cy + d / 2, z)], close=True)
    return Solid.make_loft([rw(w0, d0, z0), rw(w1, d1, z1)], ruled=True)


# ====================================================================================================
# build
# ====================================================================================================
def build_button(side):
    t0 = time.time()
    clip = ML.inner_offset(P["merge_offset"])               # skin offset 0.9 inward (cached)
    panel = ML.button_panel_raw(side)
    sx, sy = sw_xy(side)
    zt = P["z_feature_top"]

    # --- nub: pad (R0.3 edges) + stem + 45 deg gusset into the panel ---------------------------------
    pw, pd = ML.NUB_PAD
    ptop = ML.NUB_Z + P["nub_pad_t"]
    pad = Solid.extrude(ML.rrect_face_xy(sx, sy, pw, pd, P["nub_pad_r"], ML.NUB_Z).faces()[0], Vector(0, 0, P["nub_pad_t"]))
    pad = one_solid(pad.fillet(P["nub_pad_r"] - 0.01, [e for e in pad.edges() if abs(e.center().Z - ML.NUB_Z) < 1e-4]),
                    "pad fillet")
    s_w, s_d = P["nub_stem"]
    h = P["nub_gusset_h"]
    z_under = ML.inner_z_at(sx, sy)                          # panel underside above the plunger (mesh probe)
    zg0 = z_under - h
    stem = ML.box(sx - s_w / 2, sy - s_d / 2, ML.NUB_Z + P["nub_pad_t"] / 2, sx + s_w / 2, sy + s_d / 2, zg0 + 0.01)
    gus = frustum(sx, sy, s_w, s_d, zg0, s_w + 2 * h, s_d + 2 * h, z_under)
    cap = ML.box(sx - s_w / 2 - h, sy - s_d / 2 - h, z_under - 0.01, sx + s_w / 2 + h, sy + s_d / 2 + h, zt)
    nub = one_solid(pad + stem, "pad+stem")
    nub = one_solid(nub + gus, "nub+gusset")
    nub = one_solid(nub + cap, "nub+cap")

    # --- stop post: footprint STOP_PAD, bottom STOP_POST_Z, up into the panel ----------------------------
    x0, y0, x1, y1 = stop_pad(side)
    post = ML.box(x0, y0, ML.STOP_POST_Z, x1, y1, zt)

    # --- web (panel -> leaf) + leaf -----------------------------------------------------------------------
    lx0, lx1 = leaf_x(side)
    zl1 = ML.LEAF_Z_TOP
    zl0 = ML.LEAF_Z_TOP - ML.LEAF_T
    web = ML.box(lx0, ML.LEAF_WEB_Y[0], zl0 + 0.01, lx1, ML.LEAF_WEB_Y[1], zt)
    leaf = ML.box(lx0, ML.LEAF_CLAMP_Y[0], zl0, lx1, ML.LEAF_WEB_Y[1], zl1)
    lsx, lsy = leaf_screw(side)
    for hx, d in ((lsx, P["leaf_screw_hole_d"]), (lsx - ML.LEAF_PIN_DX, P["leaf_pin_hole_d"]),
                  (lsx + ML.LEAF_PIN_DX, P["leaf_pin_hole_d"])):
        leaf = leaf - Solid.make_cylinder(d / 2, ML.LEAF_T + 2).moved(Location((hx, lsy, zl0 - 1)))
    leaf = one_solid(leaf, "leaf")

    # --- clip the 'up to zt' features by the skin offset (they end 0.9 inside the 1.8 panel) ------------
    body = panel
    for nm, f in (("nub", nub), ("post", post), ("web", web)):
        fc = one_solid(f & clip, f"{nm}&clip")
        body = one_solid(body + fc, f"panel+{nm}")
    body = one_solid(body + leaf, "panel+leaf")
    print(f"[build {side}] {time.time() - t0:.1f}s  vol {body.volume:.1f}", flush=True)
    return body, dict(z_under_nub=round(z_under, 3))


# ====================================================================================================
# checks (measured on the built geometry)
# ====================================================================================================
def to_mesh(shape, tol=None):
    import tempfile
    f = Path(tempfile.gettempdir()) / f"_wpf_{id(shape)}.stl"
    export_stl(shape, str(f), tolerance=tol or P["mesh_tol"], angular_tolerance=P["mesh_ang"])
    m = trimesh.load(str(f)); f.unlink(missing_ok=True)
    return m


def ray_minz(m, x, y):
    """Lowest surface Z of mesh m on the vertical line through (x, y)."""
    loc, _, _ = m.ray.intersects_location([[x, y, -50.0]], [[0, 0, 1]])
    return float(loc[:, 2].min()) if len(loc) else None


def press_matrix(theta):
    """Rigid rotation about the hinge pivot line (along X through Y,Z = HINGE_PIVOT), front going DOWN.
    Rotation about +X by -theta lowers points ahead (+Y) of the pivot."""
    py, pz = ML.HINGE_PIVOT
    return trimesh.transformations.rotation_matrix(-theta, [1, 0, 0], point=[0, py, pz])


def crop(mesh, lo, hi, margin=3.0):
    c = mesh.triangles_center
    k = np.all((c > np.asarray(lo) - margin) & (c < np.asarray(hi) + margin), axis=1)
    return mesh.submesh([np.nonzero(k)[0]], append=True) if k.any() else None


def pts_gap(pts, B, band=0.3, cap=3000, kn=12, n_kd=120000, margin=2.0):
    """Min distance from points to the surface of mesh B + number of points inside B.
    B is cropped to the points' bbox + margin; KD prefilter on a dense surface sample of the crop; exact
    point-triangle distance to the faces of the kn nearest samples; inside/outside from the closest face
    normal. A surface crossing shows up as gap ~0. Returns (99, 0) if nothing of B is within the margin."""
    from scipy.spatial import cKDTree
    Bc = crop(B, pts.min(0), pts.max(0), margin)
    if Bc is None or len(Bc.faces) == 0:
        return 99.0, 0
    q, fidx = trimesh.sample.sample_surface(Bc, n_kd)
    q = np.vstack([q, Bc.triangles_center]); fidx = np.r_[fidx, np.arange(len(Bc.faces))]
    tree = cKDTree(q)
    dk, _ = tree.query(pts)
    order = np.argsort(dk)[:cap]
    cand = pts[order[dk[order] < dk.min() + band]]
    _, ik = tree.query(cand, k=kn)
    fids = fidx[ik]
    tri = Bc.triangles[fids.ravel()]
    rep = np.repeat(cand, kn, axis=0)
    cp = trimesh.triangles.closest_point(tri, rep)
    d = np.linalg.norm(rep - cp, axis=1).reshape(-1, kn)
    j = np.argmin(d, axis=1)
    ar = np.arange(len(cand))
    dmin = d[ar, j]
    c = cp.reshape(-1, kn, 3)[ar, j]
    sgn = np.einsum("ij,ij->i", cand - c, Bc.face_normals[fids[ar, j]])
    flag = (sgn < -1e-6) & (dmin > 1e-4)
    n_in = int(B.contains(cand[flag][:200]).sum()) if (flag.any() and B.is_watertight) else int(flag.sum())
    return float(dmin.min()), n_in


def mesh_gap(A_pts, A_mesh, B, nB=60000, b_keep=None):
    """Two-way min distance between the surfaces of A and B + interference counts (A pts in B, B pts in A)."""
    dA, inA = pts_gap(A_pts, B)
    lo, hi = A_pts.min(0) - 3, A_pts.max(0) + 3
    bp = np.vstack([B.sample(nB), B.vertices])
    bp = bp[np.all((bp > lo) & (bp < hi), axis=1)]
    if b_keep is not None:
        bp = bp[b_keep(bp)]
    if not len(bp):
        return dA, inA, 0
    dB, inB = pts_gap(bp, A_mesh)
    return min(dA, dB), inA, inB


def box_gap(pts, b):
    """Analytic min distance from points to an axis-aligned box; second value = points inside the box."""
    lo, hi = np.asarray(b[:3]), np.asarray(b[3:])
    q = np.maximum(np.maximum(lo - pts, 0), pts - hi)
    d = np.linalg.norm(q, axis=1)
    return float(d.min()), int((d == 0).sum())


def pcb_box_list():
    out = []
    for i, c in enumerate(ML.pcb_data()["components"]):
        x0, y0, z0, x1, y1, z1 = c["bbox"]
        out.append((f"{c['name']}#{i}", (x0, y0, max(z0, ML.SEAT_Z), x1, y1, z1)))
    x0, y0, x1, y1 = ML.BOARD_BBOX
    out.append(("board", (x0, y0, ML.BOARD_Z0, x1, y1, ML.BOARD_Z1)))
    return out


def check_side(side, body, others, refs):
    R = {}
    t0 = time.time()
    R["A1_n_solids"] = len(body.solids())
    R["A1_valid"] = bool(body.is_valid)
    R["volume_mm3"] = round(body.volume, 1)
    R["mass_g_PETG"] = round(body.volume * P["density_petg"], 2)
    m = refs["mesh"][side]
    R["mesh_watertight"] = bool(m.is_watertight)
    lo, hi = m.bounds
    R["envelope_mesh_xyz"] = [round(float(v), 2) for v in (*lo, *hi)]
    sx, sy = sw_xy(side)
    py, pz = ML.HINGE_PIVOT

    # A7 nub rest gap: lowest Z over the plunger box (2.9 x 1.2) minus the plunger top
    zs = [ray_minz(m, sx + dx, sy + dy) for dx in np.linspace(-1.45, 1.45, 7) for dy in np.linspace(-0.6, 0.6, 5)]
    zs = [z for z in zs if z is not None]
    R["A7_nub_face_Z_min/max"] = [round(min(zs), 3), round(max(zs), 3)]
    R["A7_nub_rest_gap"] = round(min(zs) - ML.PLUNGER_TOP_Z, 3)
    for nm, zc in (("nub_pad_XxY_at_face+0.5", ML.NUB_Z + 0.5), ("nub_stem_XxY_at_pad+1", ML.NUB_Z + P["nub_pad_t"] + 1.0)):
        sec = m.section(plane_origin=[0, 0, zc], plane_normal=[0, 0, 1])
        vb = sec.vertices
        sel = vb[(abs(vb[:, 0] - sx) < 4) & (abs(vb[:, 1] - sy) < 4)]
        R[nm] = [round(float(np.ptp(sel[:, 0])), 2), round(float(np.ptp(sel[:, 1])), 2)]
        R[nm + "_centre"] = [round(float(sel[:, 0].min() + np.ptp(sel[:, 0]) / 2), 2),
                             round(float(sel[:, 1].min() + np.ptp(sel[:, 1]) / 2), 2)]
    # A9 hard stop: post bottom over its footprint
    x0, y0, x1, y1 = stop_pad(side)
    zp = [ray_minz(m, x, y) for x in np.linspace(x0 + 0.1, x1 - 0.1, 4) for y in np.linspace(y0 + 0.1, y1 - 0.1, 4)]
    zp = [z for z in zp if z is not None]
    R["A9_post_bottom_Z"] = round(min(zp), 3)
    R["A9_stop_gap_STEP_board"] = round(min(zp) - ML.BOARD_Z1, 3)
    R["A9_stop_gap_real_1.6_board"] = round(min(zp) - ML.BOARD_Z1_REAL, 3)
    post_cy = (y0 + y1) / 2
    travel_at_nub = (min(zp) - ML.BOARD_Z1) * (sy - py) / (post_cy - py)
    R["travel_at_nub_to_stop"] = round(travel_at_nub, 3)
    R["plunger_travel_after_contact"] = round(travel_at_nub - (min(zs) - ML.PLUNGER_TOP_Z), 3)

    # leaf: thickness, Z, web rear face, free length, strain, plain free zone, holes
    lx0, lx1 = leaf_x(side)
    lxm = (lx0 + lx1) / 2
    ym = (ML.LEAF_FREE_Y[0] + ML.LEAF_FREE_Y[1]) / 2
    loc, _, _ = m.ray.intersects_location([[lxm + 2.0, ym, -50.0]], [[0, 0, 1]])
    zz = sorted(loc[:, 2])
    leaf_t = zz[1] - zz[0]
    R["leaf_thickness"] = round(leaf_t, 3)
    R["leaf_Z"] = [round(zz[0], 3), round(zz[1], 3)]
    R["leaf_width_X"] = round(float(np.ptp(m.vertices[(m.vertices[:, 1] < ML.LEAF_WEB_Y[0] - 0.5), 0])), 3)
    loc, _, _ = m.ray.intersects_location([[lxm + 2.0, -90.0, ML.LEAF_Z_TOP + 0.5]], [[0, 1, 0]])
    web_rear = float(loc[:, 1].min())
    R["web_rear_face_Y"] = round(web_rear, 3)
    loc, _, _ = m.ray.intersects_location([[lxm + 2.0, -90.0, ML.LEAF_Z_TOP - 0.5]], [[0, 1, 0]])
    R["leaf_rear_end_Y"] = round(float(loc[:, 1].min()), 3)
    lf = web_rear - ML.LEAF_CLAMP_Y[1]
    R["leaf_free_length(web rear - clamp pad front)"] = round(lf, 3)
    hits = 0
    for x in np.linspace(lx0 + 0.3, lx1 - 0.3, 12):
        for y in np.linspace(ML.LEAF_FREE_Y[0] + 0.1, ML.Y_BTN_REAR - ML.BTN_GAP / 2 - 0.1, 8):   # panel ends at -59.75
            loc, _, _ = m.ray.intersects_location([[x, y, 60.0]], [[0, 0, -1]])
            if len(loc) and loc[:, 2].max() > ML.LEAF_Z_TOP + 0.01:
                hits += 1
    R["leaf_free_zone_plain"] = hits == 0
    theta = math.atan(P["press_travel"] / (sy - py))
    R["press_angle_rad"] = round(theta, 5)
    R["leaf_strain_pct"] = round(100 * leaf_t * theta / (2 * lf), 3)
    lsx, lsy = leaf_screw(side)
    sec = m.section(plane_origin=[0, 0, ML.LEAF_Z_TOP - ML.LEAF_T / 2], plane_normal=[0, 0, 1])
    holes = []
    for ent in sec.discrete:
        e = np.asarray(ent)
        span = np.ptp(e[:, :2], axis=0)
        if span.max() < 3.0 and abs(e[:, 1].mean() - lsy) < 1.0:
            holes.append((round(float(e[:, 0].mean()), 2), round(float(span.mean()), 2)))
    R["leaf_holes(x,d)"] = sorted(holes)

    # tip travel: frontmost vertex moved by the press rotation
    tip = m.vertices[int(np.argmax(m.vertices[:, 1]))]
    R["tip_point"] = [round(float(v), 2) for v in tip]
    R["tip_travel"] = round((tip[1] - py) * math.sin(theta), 3)

    # A15 panel wall: from finger-side surface samples (outward normal up) cast a ray along the inward normal,
    # thickness = distance to the next surface of the same part (measured on the built button)
    pts, fid = trimesh.sample.sample_surface(m, 6000)
    nrm = m.face_normals[fid]
    k = ((nrm[:, 2] > 0.3) & (pts[:, 2] > ML.NUB_Z + P["nub_pad_t"] + 0.1)          # above the nub pad top ring
         & ~((pts[:, 1] < ML.LEAF_WEB_Y[1] + 0.1) & (pts[:, 2] < ML.LEAF_Z_TOP + 0.05)))      # panel only, not the leaf
    o = pts[k] - nrm[k] * 1e-3
    loc, ri, ti = m.ray.intersects_location(o, -nrm[k], multiple_hits=False)
    opp = np.einsum("ij,ij->i", m.face_normals[ti], nrm[k][ri]) < -0.9     # hit face ~antiparallel = inner skin
    th = np.linalg.norm(loc - o[ri], axis=1)[opp]
    R["A15_n_rays_used"] = int(opp.sum())
    oo = o[ri][opp]
    R["A15_thinnest_5(x,y,z,t)"] = [[round(float(v), 2) for v in (*oo[i], np.linalg.norm(loc[opp][i] - oo[i]))]
                                    for i in np.argsort(np.linalg.norm(loc[opp] - oo, axis=1))[:5]]
    R["A15_panel_wall_min(p1)"] = round(float(np.percentile(th, 1)), 3)
    R["A15_panel_wall_abs_min(edge rays incl.)"] = round(float(th.min()), 3)
    R["A15_panel_wall_median"] = round(float(np.median(th)), 3)

    S = np.vstack([m.sample(P["n_samples"]), m.vertices])
    # A5 vs the PCB mesh of the original STEP (pcb.stl) + per-group meshes; A6 vs every component bbox
    R["A5_gap_to_PCB_mesh,pts_inside"] = [round(v, 3) for v in pts_gap(S, refs["pcb_mesh"])]
    rows = []
    for nm, b in refs["pcb_boxes"]:
        g_, n_ = box_gap(S, b)
        rows.append((round(g_, 3), nm, n_))
    rows.sort()
    R["A6_closest_pcb_boxes(d,name,n_in)"] = rows[:5]
    nondes = [r for r in rows if r[1] not in (refs["own_switch"][side], "board")]
    R["A6_min_clear_excl_designed"] = list(nondes[0][:2])
    R["A6_own_switch_gap(nub rest)"] = [r for r in rows if r[1] == refs["own_switch"][side]][0][0]
    R["A6_board_gap(post)"] = [r for r in rows if r[1] == "board"][0][0]
    R["A6_encoder_gap"] = [r for r in rows if r[1] == refs["encoder"]][0][0]

    # A11 rest gaps to the top shell (leaf clamp zone excluded = designed contact with the clamp pad)
    clamp_line = (S[:, 1] < ML.LEAF_CLAMP_Y[1] + 0.5) & (S[:, 2] <= ML.LEAF_Z_TOP + 0.01)
    Snc = S[(S[:, 1] > ML.LEAF_CLAMP_Y[1]) & ~clamp_line]
    # top-shell side: drop the clamp pad face + locating pins (Z <= pad face + 0.6 behind the clamp line)
    g, a_in, b_in = mesh_gap(Snc, m, refs["top_shell_mesh"],
                             b_keep=lambda q: ~((q[:, 1] < ML.LEAF_CLAMP_Y[1] + 0.5) & (q[:, 2] <= ML.LEAF_Z_TOP + 0.6)))
    R["A11_gap_to_top_shell"] = round(g, 3)
    R["A11_interf_pts(btn_in_ts,ts_in_btn)"] = [a_in, b_in]
    R["A11_top_shell_source"] = refs["top_shell_src"]
    tsm = refs["top_shell_mesh"]
    gaps = []
    for x in np.linspace(sx - 5, sx + 5, 11):
        for yf in (ML.Y_TIP - 1.0, ML.Y_TIP - 2.0, ML.Y_TIP - 3.0):
            zb = ray_minz(m, x, yf)
            loc, _, _ = tsm.ray.intersects_location([[x, yf, ML.Z_BTN_LOW + 4]], [[0, 0, -1]])
            if zb is not None and len(loc) and zb < ML.Z_BTN_LOW + 3:
                gaps.append(zb - loc[:, 2].max())
    R["A11_nose_split_gap"] = round(min(gaps), 3) if gaps else None
    for on, om in others.items():
        g, a_in, b_in = mesh_gap(S, m, om)
        R[f"A11_gap_to_{on}"] = round(g, 3)
    for on, om in refs["other_parts"].items():
        g, a_in = pts_gap(S, om)
        R[f"rest_gap_to_{on},pts_in"] = [round(g, 3), a_in]

    # A12 pressed: rigid rotation of the moving part (ahead of the web rear face / above the leaf) by theta
    M4 = press_matrix(theta)
    movS = S[(S[:, 1] > web_rear + 0.05) | (S[:, 2] > ML.LEAF_Z_TOP + 0.05)]
    rotS = trimesh.transform_points(movS, M4)
    rm = m.copy(); rm.apply_transform(M4)
    zs2 = [ray_minz(rm, sx + dx, sy + dy) for dx in np.linspace(-1.45, 1.45, 5) for dy in np.linspace(-0.6, 0.6, 3)]
    R["A12_pressed_nub_face_Z"] = round(min(z for z in zs2 if z is not None), 3)
    zp2 = [ray_minz(rm, x, y) for x in np.linspace(x0 + 0.1, x1 - 0.1, 4) for y in np.linspace(y0 + 0.1, y1 - 0.1, 4)]
    R["A12_pressed_post_bottom_Z"] = round(min(z for z in zp2 if z is not None), 3)
    R["A12_nub_into_plunger(designed)"] = round(ML.PLUNGER_TOP_Z - R["A12_pressed_nub_face_Z"], 3)
    R["A12_post_to_board(designed)"] = round(R["A12_pressed_post_bottom_Z"] - ML.BOARD_Z1, 3)
    g, a_in = pts_gap(rotS[(rotS[:, 1] > ML.LEAF_CLAMP_Y[1] + 0.5) | (rotS[:, 2] > ML.LEAF_Z_TOP + 0.05)],
                      refs["top_shell_mesh"])
    R["A12_pressed_gap_to_top_shell,pts_in"] = [round(g, 3), a_in]
    for on, om in others.items():
        g, a_in = pts_gap(rotS, om)
        R[f"A12_pressed_gap_to_{on}(rest),pts_in"] = [round(g, 3), a_in]
    pad_zone = (abs(movS[:, 0] - sx) < 3) & (abs(movS[:, 1] - sy) < 3) & (movS[:, 2] < ML.NUB_Z + 0.5)
    post_zone = ((movS[:, 0] > x0 - 0.5) & (movS[:, 0] < x1 + 0.5) & (movS[:, 1] > y0 - 0.5) & (movS[:, 1] < y1 + 0.5)
                 & (movS[:, 2] < ML.STOP_POST_Z + 0.5))
    rk = rotS[~(pad_zone | post_zone)]
    rows2 = sorted((round(box_gap(rk, b)[0], 3), nm) for nm, b in refs["pcb_boxes"])
    R["A12_pressed_min_clear_PCB_boxes(excl nub/post)"] = list(rows2[0])
    R["A12_pressed_gap_PCB_mesh(excl nub/post),pts_in"] = [round(v, 3) for v in pts_gap(rk, refs["pcb_mesh"])]
    for on, om in refs["other_parts"].items():
        g, a_in = pts_gap(rotS, om)
        R[f"A12_pressed_gap_to_{on},pts_in"] = [round(g, 3), a_in]
    refs.setdefault("rot", {})[side] = (rotS, rm)
    print(f"[check {side}] {time.time() - t0:.1f}s", flush=True)
    return R


def gate_table(side, R):
    g = []

    def add(i, what, val, ok):
        g.append(dict(id=f"{side}:{i}", what=what, value=str(val), passed=bool(ok)))
    add("A1", "one valid solid, vol > 0", f"n={R['A1_n_solids']} valid={R['A1_valid']} vol={R['volume_mm3']}",
        R["A1_n_solids"] == 1 and R["A1_valid"] and R["volume_mm3"] > 0)
    add("mesh", "STL watertight", R["mesh_watertight"], R["mesh_watertight"])
    a5 = R["A5_gap_to_PCB_mesh,pts_inside"]
    add("A5", "no interference with the PCB (STEP mesh): gap > 0, 0 pts inside", a5, a5[0] > 0 and a5[1] == 0)
    add("A6", "clearance to PCB comps (excl nub/plunger, post/board) >= 0.25", R["A6_min_clear_excl_designed"],
        R["A6_min_clear_excl_designed"][0] >= P["clr_moving"])
    add("A7", "nub rest gap 0.05..0.30", R["A7_nub_rest_gap"], P["a7"][0] <= R["A7_nub_rest_gap"] <= P["a7"][1])
    add("A9", "stop post bottom - 1.51 in 0.75..0.90", R["A9_stop_gap_STEP_board"],
        P["a9"][0] <= R["A9_stop_gap_STEP_board"] <= P["a9"][1])
    add("A11", "gap to top shell 0.40..0.60", R["A11_gap_to_top_shell"],
        P["a11"][0] <= R["A11_gap_to_top_shell"] <= P["a11"][1] and R["A11_interf_pts(btn_in_ts,ts_in_btn)"] == [0, 0])
    add("A11n", "nose split >= 1.30", R["A11_nose_split_gap"],
        R["A11_nose_split_gap"] is not None and R["A11_nose_split_gap"] >= P["a11_nose"])
    for k, v in R.items():
        if k.startswith("A11_gap_to_button"):
            add("A11b", "gap to the other button >= 0.40 (not adjacent: tongue between)", v, v >= P["a11"][0])
    ok12 = (R["A12_pressed_gap_to_top_shell,pts_in"][0] > 0 and R["A12_pressed_gap_to_top_shell,pts_in"][1] == 0
            and R["A12_pressed_gap_PCB_mesh(excl nub/post),pts_in"][0] > 0
            and R["A12_pressed_gap_PCB_mesh(excl nub/post),pts_in"][1] == 0
            and all(v[0] > 0 and v[1] == 0 for k, v in R.items() if k.startswith("A12_pressed_gap_to_button"))
            and all(v[0] > 0 and v[1] == 0 for k, v in R.items() if k.startswith("A12_pressed_gap_to_") and "top_shell" not in k)
            and abs(R["A12_post_to_board(designed)"]) < 0.05)
    add("A12", "pressed 0.8: no contact except nub/plunger + post/board",
        f"ts {R['A12_pressed_gap_to_top_shell,pts_in']}, pcb STEP {R['A12_pressed_gap_PCB_mesh(excl nub/post),pts_in']}, "
        f"post-board {R['A12_post_to_board(designed)']}", ok12)
    rest = {k: v for k, v in R.items() if k.startswith("rest_gap_to_")}
    add("A12r", "rest: no contact with wheel/yoke/dpi/side levers/bottom shell (gap > 0.25)", rest,
        all(v[0] >= P["clr_moving"] and v[1] == 0 for v in rest.values()))
    add("A6p", "pressed: clearance to PCB STEP (excl nub/post) >= 0.25", R["A12_pressed_gap_PCB_mesh(excl nub/post),pts_in"],
        R["A12_pressed_gap_PCB_mesh(excl nub/post),pts_in"][0] >= P["clr_moving"])
    add("A15", "panel wall >= 1.6", R["A15_panel_wall_min(p1)"], R["A15_panel_wall_min(p1)"] >= P["min_wall"])
    add("tip", "tip travel <= 1.3 and < BTN_FRONT_GAP 1.40", R["tip_travel"],
        R["tip_travel"] <= P["tip_travel_max"] and R["tip_travel"] < ML.BTN_FRONT_GAP)
    add("leaf", "leaf strain <= 1 % PETG, free zone plain", f"{R['leaf_strain_pct']} % plain={R['leaf_free_zone_plain']}",
        R["leaf_strain_pct"] <= 100 * P["leaf_strain_max"] and R["leaf_free_zone_plain"])
    return g


def main(check_only=False):
    T0 = time.time()
    bodies, info = {}, {}
    for s in P["sides"]:
        name = f"button_{s}"
        if check_only:
            bodies[s] = one_solid(import_step(str(OUTDIR[s] / f"{name}.step")), name)
            continue
        bodies[s], info[s] = build_button(s)
        d = ML.export_part(bodies[s], name)
        export_stl(bodies[s], str(d / f"{name}.stl"), tolerance=P["mesh_tol"], angular_tolerance=P["mesh_ang"])
        m = trimesh.load(str(d / f"{name}.stl"))
        print(f"  {name}.stl watertight {m.is_watertight}", flush=True)
        m.apply_translation([0, 0, -m.bounds[0][2]])     # finger face up = assembly orientation, lowest point on Z 0
        m.export(str(d / f"{name}_print.stl"))
        if Path(__file__).resolve().parent != d.resolve():
            shutil.copy2(__file__, d / Path(__file__).name)
    print(f"parts ready {time.time() - T0:.1f}s", flush=True)

    refs = {"mesh": {s: trimesh.load(str(OUTDIR[s] / f"button_{s}.stl")) for s in P["sides"]}}
    ts_path = ML.PARTS_DIR / "top_shell" / "top_shell.step"
    fine = OUTDIR["L"] / "_top_shell_fine.stl"
    if ts_path.exists():
        if not fine.exists() or fine.stat().st_mtime < ts_path.stat().st_mtime:
            export_stl(import_step(str(ts_path)), str(fine), tolerance=P["mesh_tol"], angular_tolerance=P["mesh_ang"])
        refs["top_shell_mesh"] = trimesh.load(str(fine))
        refs["top_shell_src"] = "03_parts/top_shell/top_shell.step (WP-E), re-tessellated 0.01/0.05"
    else:
        refs["top_shell_mesh"] = to_mesh(ML.top_shell_raw(), 0.03); refs["top_shell_src"] = "ML.top_shell_raw()"
    refs["pcb_mesh"] = trimesh.load(str(ML.PCB_STL))
    refs["pcb_boxes"] = pcb_box_list()
    refs["other_parts"] = {}
    for nm in ("wheel", "wheel_yoke", "dpi_button", "side_btn_fwd", "side_btn_back", "bottom_shell"):
        f = ML.PARTS_DIR / nm / f"{nm}.stl"
        if f.exists():
            refs["other_parts"][nm] = trimesh.load(str(f))
    own = {}
    for s in P["sides"]:
        sx, sy = sw_xy(s)
        for i, c in enumerate(ML.pcb_data()["components"]):
            x0, y0, z0, x1, y1, z1 = c["bbox"]
            if x0 <= sx <= x1 and y0 <= sy <= y1 and z1 > ML.PLUNGER_TOP_Z - 0.01:
                own[s] = f"{c['name']}#{i}"
    for i, c in enumerate(ML.pcb_data()["components"]):
        if abs(c["bbox"][5] - ML.ENC_BODY[5]) < 0.01:
            refs["encoder"] = f"{c['name']}#{i}"
    refs["own_switch"] = own
    print(f"refs ready {time.time() - T0:.1f}s  own switches {own}, encoder {refs['encoder']}, "
          f"pcb mesh watertight {refs['pcb_mesh'].is_watertight}, top shell mesh watertight "
          f"{refs['top_shell_mesh'].is_watertight}", flush=True)

    report, gates = {}, []
    for s in P["sides"]:
        other = {f"button_{o}": refs["mesh"][o] for o in P["sides"] if o != s}
        report[s] = check_side(s, bodies[s], other, refs)
        gates += gate_table(s, report[s])
    (rL, mL), (rR, mR) = refs["rot"]["L"], refs["rot"]["R"]
    g, n_in = pts_gap(rL, mR)
    report["both_pressed_gap_L_R"] = [round(g, 3), n_in]
    gates.append(dict(id="LR:A12", what="both pressed: L-R gap > 0", value=str(report["both_pressed_gap_L_R"]),
                      passed=g > 0 and n_in == 0))
    report["info"] = info
    report["runtime_s"] = round(time.time() - T0, 1)
    for s in P["sides"]:
        (OUTDIR[s] / f"check_button_{s}.json").write_text(json.dumps(
            dict(part=f"button_{s}", checks=report[s], build_info=info.get(s),
                 both_pressed_gap_L_R=report["both_pressed_gap_L_R"],
                 gates=[x for x in gates if x["id"].startswith(s) or x["id"].startswith("LR")]), indent=1, default=str))
    for s in P["sides"]:
        print(f"\n===== button_{s} =====")
        for k, v in report[s].items():
            print(f"  {k:50s} {v}")
    print(f"\n  both pressed L-R gap: {report['both_pressed_gap_L_R']}")
    print("\n===== GATES =====")
    for x in gates:
        print(f"  {'PASS' if x['passed'] else 'FAIL'}  {x['id']:9s} {x['what']:66s} {x['value']}")
    print(f"total {report['runtime_s']} s")
    # pressed meshes + top-shell reference mesh for the renders
    for s in P["sides"]:
        refs["rot"][s][1].export(str(OUTDIR[s] / f"_button_{s}_pressed.stl"))
    refs["top_shell_mesh"].export(str(OUTDIR["L"] / "_top_shell_ref.stl"))


if __name__ == "__main__":
    main(check_only="--check-only" in sys.argv)
