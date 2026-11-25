"""
build_top_shell.py - WP-E top_shell (PLA, prints rim-down on the Z_PART plane, dome up).

Start: ML.top_shell_raw()  (wall above Z_PART, button regions + wheel/DPI windows + side notches cut)
Adds : 0.3 chamfers (rim bed edge, notch / window outer edges), 3 heat-set insert bosses (front one webbed
       to the front band), 2 leaf clamp pads with 45 deg gussets + pilot + 2 locating pins each,
       2 rail webs beside the wheel window, DPI guide sleeve.
Native PCB coordinates (+X right, +Y front, +Z up), mm. Every interface number comes from master.py;
PARAMS holds only the local (non-interface) feature sizes.

Run:  python build_top_shell.py      (-> top_shell.step / .stl / top_shell_print.stl, then run check_top_shell.py)
"""
import math
import sys
import time

sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *          # noqa: E402,F401  (build123d first, then master)
import master as ML              # noqa: E402

PARAMS = dict(
    rim_chamfer=0.30,            # elephant-foot chamfer on the rim bed edge (outer skin edge at Z_PART)
    edge_chamfer=0.30,           # chamfer on the notch / window outer edges
    front_web_t=1.2,             # web front boss -> front band (X thickness)
    front_web_z_gap=0.30,        # web bottom stays this far above the bottom-shell lip top (Z_PART + LIP_H)
    front_web_y_end=1.0,         # web runs to Y_TIP + this (clipped by the cavity anyway)
    pad_side_extra=1.0,          # clamp pad footprint = leaf X +/- this
    gusset_h=15.0,               # 45 deg gusset rib height above the pad face (clipped by the cavity)
    gusset_inboard_max=1.0,      # inboard side ribs stop this far from the centreline X_CL
    gusset_t=1.2,                # gusset rib thickness (ribs 0.8-1.2)
    pilot_extra=1.0,             # pilot depth = LEAF_SCREW_PILOT depth + this
    pin_len=1.0,                 # locating pin length below the pad face (= leaf thickness)
    sleeve_wall=1.0,             # DPI guide sleeve wall
    cut_top=40.0,                # top Z of helper prisms (above the hump, clipped by the cavity)
    insert_hole_extra=0.0,       # extra insert hole depth (0 = exactly TS_INSERT_HOLE depth)
    window_z0=10.0,              # bottom Z of the window cutter (same as ML.wheel_window_prism)
    wheel_clr=0.50,              # wheel window front edge: wheel envelope (rest) to tongue underside corner >= this
    wheel_probe_step=0.05,       # Y step of the window-front search
    wheel_probe_nx=9,            # X samples across the window for the tongue underside
    stl_tol=0.005,               # STL linear deflection (ML.export_part's 0.02 leaves 0.4 mm facet error at the rim)
    stl_ang=0.05,                # STL angular deflection
)
P = PARAMS


def one(shape, what):
    """Single valid solid after every boolean, else stop."""
    sols = shape.solids() if shape is not None else []
    if len(sols) != 1:
        raise RuntimeError(f"{what}: {len(sols)} solids")
    s = sols[0]
    if not s.is_valid or s.volume <= 0:
        raise RuntimeError(f"{what}: invalid / empty")
    return s


def cyl_z(x, y, d, z0, z1):
    return Solid.make_cylinder(d / 2, z1 - z0, Plane(origin=(x, y, z0)))


def chamfer_outer_edges(T, skin_mesh):
    """0.3 chamfers on edges lying on the OUTER skin: rim bed edge (Z_PART) + notch / window outer edges."""
    import numpy as np
    import trimesh
    pq = trimesh.proximity.ProximityQuery(skin_mesh)
    rim = []
    for e in T.edges():
        pts = [e.position_at(t) for t in (0.2, 0.5, 0.8)]
        d = np.abs(pq.signed_distance(np.array([[p.X, p.Y, p.Z] for p in pts])))
        if d.max() > 0.03:
            continue                                     # not on the outer skin
        if e.bounding_box().max.Z < ML.Z_PART + 1e-4:
            rim.append(e)
    log = {}
    out = T
    try:
        out = one(out.chamfer(P["rim_chamfer"], None, rim), "rim chamfer")
        log["rim_chamfer"] = f"{len(rim)} edges OK"
    except Exception as ex:                              # noqa: BLE001
        log["rim_chamfer"] = f"FAILED ({ex}) on {len(rim)} edges"
    return out, log


def chamfer_cut_edges(T, skin_mesh):
    """Window + notch outer edges: edges on the outer skin that are shared with a PLANAR face (the cut faces).
    Button split edges are included (also visible split edges). Tried as one set, then per edge."""
    import numpy as np
    import trimesh
    pq = trimesh.proximity.ProximityQuery(skin_mesh)
    planar = [f for f in T.faces() if f.geom_type == GeomType.PLANE and abs(f.normal_at().Z) < 0.99]
    cand = []
    for f in planar:
        for e in f.edges():
            bb = e.bounding_box()
            if bb.max.Z < ML.Z_PART + 1e-3:
                continue
            pts = [e.position_at(t) for t in (0.2, 0.5, 0.8)]
            d = np.abs(pq.signed_distance(np.array([[p.X, p.Y, p.Z] for p in pts])))
            if d.max() < 0.03:
                cand.append(e)
    # de-duplicate
    uniq = []
    for e in cand:
        if not any(e.is_same(u) for u in uniq):
            uniq.append(e)
    try:
        return one(T.chamfer(P["edge_chamfer"], None, uniq), "cut-edge chamfer"), f"{len(uniq)} edges OK (one set)"
    except Exception:                                    # noqa: BLE001
        pass
    ok = 0
    out = T
    for e in uniq:
        try:
            ee = [x for x in out.edges() if (x.center() - e.center()).length < 1e-3]
            if not ee:
                continue
            out = one(out.chamfer(P["edge_chamfer"], None, ee), "edge chamfer")
            ok += 1
        except Exception:                                # noqa: BLE001
            continue
    return out, f"{ok}/{len(uniq)} edges chamfered individually"


def build():
    t0 = time.time()
    I = ML.inner()
    T = ML.top_shell_raw()
    print(f"[t {time.time() - t0:5.1f}] raw: vol {T.volume:.1f} valid {T.is_valid}")
    log = {}

    # ---- 0. wheel window front edge (master WHEEL_WIN front Y is too short: the tongue underside at the window
    # front sits inside the d23.6 wheel). Move the front edge forward until the underside corner clears the
    # wheel envelope by wheel_clr, measured on the cavity mesh (ML.inner_z_at).
    import numpy as np
    wx0, wy0, wx1, wy1 = ML.WHEEL_WIN
    yc, zc_w, rw = ML.WHEEL_C[1], ML.WHEEL_C[2], ML.WHEEL_D / 2
    ye = wy1
    xs = np.linspace(wx0, wx1, P["wheel_probe_nx"])
    while True:
        zu = min(ML.inner_z_at(x, ye) for x in xs)
        if math.hypot(ye - yc, zu - zc_w) >= rw + P["wheel_clr"]:
            break
        ye += P["wheel_probe_step"]
    log["wheel_win_front_Y"] = f"{wy1:.2f} -> {ye:.2f} (underside Z {zu:.2f})"
    if ye > wy1 + 1e-6:
        T = one(T - ML.box(wx0, wy1 - 0.01, P["window_z0"], wx1, ye, P["cut_top"]), "wheel window extension")

    # ---- 6. chamfers on the raw shell (before features: fewer, cleaner edges)
    skin_mesh = ML.mesh_of(ML.skin(), 0.01)
    T, lg = chamfer_outer_edges(T, skin_mesh)
    log.update(lg)
    T, log["cut_edge_chamfer"] = chamfer_cut_edges(T, skin_mesh)
    print(f"[t {time.time() - t0:5.1f}] chamfers: {log}")

    zc = P["cut_top"]
    # ---- 1. insert bosses (bottom face exactly Z_PART), front one webbed to the front band
    hole_d, hole_depth = ML.TS_INSERT_HOLE
    for i, (x, y) in enumerate(ML.TS_SCREWS):
        boss = one(cyl_z(x, y, ML.TS_BOSS_OD, ML.Z_PART, zc) & I, f"boss{i} & inner")
        T = one(T + boss, f"T + boss{i}")
    fx, fy = ML.TS_SCREWS[0]
    web = ML.box(fx - P["front_web_t"] / 2, fy, ML.Z_PART + ML.LIP_H + P["front_web_z_gap"],
                 fx + P["front_web_t"] / 2, ML.Y_TIP + P["front_web_y_end"], zc)
    T = one(T + one(web & I, "front web & inner"), "T + front web")
    for i, (x, y) in enumerate(ML.TS_SCREWS):
        T = one(T - cyl_z(x, y, hole_d, ML.Z_PART - 1.0, ML.Z_PART + hole_depth + P["insert_hole_extra"]),
                f"T - insert hole{i}")
    print(f"[t {time.time() - t0:5.1f}] bosses done, vol {T.volume:.1f}")

    # ---- 2. leaf clamp pads + 45 deg gussets, pilot, locating pins
    cy0, cy1 = ML.LEAF_CLAMP_Y
    zp = ML.LEAF_Z_TOP
    g, t = P["gusset_h"], P["gusset_t"]

    def tri_rib(p0, p1, p2, ext):
        """Triangular rib: plane triangle p0-p1-p2 extruded by vector ext."""
        w = Wire.make_polygon([Vector(*p0), Vector(*p1), Vector(*p2)], close=True)
        return Solid.extrude(Face(w), Vector(*ext))

    for side, (lx0, lx1), (sx, sy) in (("L", ML.LEAF_X_L, ML.LEAF_SCREW_L), ("R", ML.LEAF_X_R, ML.LEAF_SCREW_R)):
        x0, x1 = lx0 - P["pad_side_extra"], lx1 + P["pad_side_extra"]
        pad = ML.box(x0, cy0, zp, x1, cy1, zc)                # clamp block: face Z 20 up to the ceiling
        # 45 deg gusset ribs: 3 on the rear face (-Y), 1 on each X side; the +Y face (over the free leaf) stays plain
        for xr in (x0, (x0 + x1 - t) / 2, x1 - t):
            pad = one(pad + tri_rib((xr, cy0, zp), (xr, cy0, zp + g), (xr, cy0 - g, zp + g), (t, 0, 0)), "rear rib")
        ym = (cy0 + cy1 - t) / 2
        for xe, s in ((x0, -1), (x1, 1)):
            rib = tri_rib((xe, ym, zp), (xe, ym, zp + g), (xe + s * g, ym, zp + g), (0, t, 0))
            # side ribs never cross the centreline (2 x gusset_inboard_max apart) - no lump between the pads
            lim = ML.box(-20, -140, zp, ML.X_CL - P["gusset_inboard_max"], 20, zc) if side == "L" else                 ML.box(ML.X_CL + P["gusset_inboard_max"], -140, zp, 100, 20, zc)
            pad = one(pad + one(rib & lim, "side rib trim"), "side rib")
        pad = one(pad & I, f"pad {side} & inner")
        T = one(T + pad, f"T + pad {side}")
        pd, pdepth = ML.LEAF_SCREW_PILOT
        T = one(T - cyl_z(sx, sy, pd, zp - 0.5, zp + pdepth + P["pilot_extra"]), f"T - pilot {side}")
        for dx in (-ML.LEAF_PIN_DX, ML.LEAF_PIN_DX):
            T = one(T + cyl_z(sx + dx, sy, ML.LEAF_PIN_D, zp - P["pin_len"], zp + 0.5), f"T + pin {side}{dx:+}")
    print(f"[t {time.time() - t0:5.1f}] pads done, vol {T.volume:.1f}")

    # ---- 3. rail webs beside the wheel window (tongue strips X 33.87..35.32 / 43.42..44.87)
    wx0, wy0, wx1, wy1 = ML.WHEEL_WIN
    tx0, tx1 = ML.X_CL - ML.TONGUE_HW, ML.X_CL + ML.TONGUE_HW
    for i, (a, b) in enumerate(((tx0, wx0), (wx1, tx1))):
        rail = one(ML.box(a, wy0, ML.RAIL_WEB_Z, b, wy1, zc) & I, f"rail{i} & inner")
        T = one(T + rail, f"T + rail{i}")
    print(f"[t {time.time() - t0:5.1f}] rails done")

    # ---- 4. DPI guide sleeve (cap + 0.15 per side, wall 1.0, down to DPI_GUIDE_Z)
    c = ML.DPI_CAP
    cl, w = ML.DPI_GUIDE_CLR, P["sleeve_wall"]
    ring = ML.box(c[0] - cl - w, c[1] - cl - w, ML.DPI_GUIDE_Z, c[2] + cl + w, c[3] + cl + w, zc) - \
        ML.box(c[0] - cl, c[1] - cl, ML.DPI_GUIDE_Z - 1, c[2] + cl, c[3] + cl, zc + 1)
    sleeve = one(one(ring, "sleeve ring") & I, "sleeve & inner")
    T = one(T + sleeve, "T + sleeve")
    # keep the cap path open through the whole tongue (window already wider than the sleeve bore)
    T = one(T - ML.box(c[0] - cl, c[1] - cl, ML.DPI_GUIDE_Z - 1, c[2] + cl, c[3] + cl, zc + 10), "T - sleeve bore")
    print(f"[t {time.time() - t0:5.1f}] sleeve done")

    # ---- final: nothing below Z_PART (guard cut; must remove nothing)
    v0 = T.volume
    T = one(T - ML.below(ML.Z_PART), "guard cut below Z_PART")
    log["guard_cut_removed_mm3"] = round(v0 - T.volume, 4)
    return T, log


def export_meshes(T, d):
    """Fine STLs: assembly position + print orientation (rim plane Z_PART on the bed Z 0, dome up)."""
    export_stl(T, str(d / "top_shell.stl"), tolerance=P["stl_tol"], angular_tolerance=P["stl_ang"])
    export_stl(T.moved(Location((0, 0, -ML.Z_PART))), str(d / "top_shell_print.stl"), tolerance=P["stl_tol"],
               angular_tolerance=P["stl_ang"])


if __name__ == "__main__":
    t0 = time.time()
    if "--mesh-only" in sys.argv:              # re-export the STLs from the existing STEP
        d = ML.part_dir("top_shell")
        export_meshes(import_step(str(d / "top_shell.step")).solids()[0], d)
        print(f"meshes re-exported in {time.time() - t0:.1f}s")
        sys.exit(0)
    T, log = build()
    chk = ML.check_part(T, "top_shell")
    print("check_part:", chk, "| log:", log)
    assert chk["n_solids"] == 1 and chk["valid"] and chk["volume"] > 0, "top_shell failed the single-valid-solid check"
    d = ML.export_part(T, "top_shell")
    export_meshes(T, d)
    (d / "build_log.txt").write_text(f"{chk}\n{log}\n")
    print(f"exported to {d} in {time.time() - t0:.1f}s")
