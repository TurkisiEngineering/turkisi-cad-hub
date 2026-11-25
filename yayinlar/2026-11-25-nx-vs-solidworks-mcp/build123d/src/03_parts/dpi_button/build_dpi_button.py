"""
build_dpi_button.py - WP-H DPI button: sliding cap in the top-shell tongue window, guided by the sleeve (WP-E),
flange = up-stop under the sleeve, long nub resting on the DPI D2F plunger.

Run:  python build_dpi_button.py
Writes 03_parts/dpi_button/dpi_button.step/.stl, dpi_button_print.stl, checks_dpi_button.json
Native PCB coords (+X right, +Y front, +Z up). Interfaces from master.py (ML.*).
"""
import sys, json, math, time
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *
import master as ML
import numpy as np

# ---------------------------------------------------------------------------------------------------
# PARAMS (designer-defined; interfaces come from ML)
# ---------------------------------------------------------------------------------------------------
PARAMS = dict(
    top_lower=0.0,          # cap top = skin surface lowered by this (brief: 0.0)
    flange_t=1.0,           # flange thickness (brief)
    stem=(2.5, 2.5),        # nub stem X x Y (brief: >= 2.5 x 2.5)
    pad_t=1.0,              # nub pad thickness
    overlap=0.1,            # union overlap between stacked blocks
    press_travel=0.75,      # checked press depth at the plunger (PT 0.5 + OT 0.25)
    sleeve_wall=1.0,        # WP-E sleeve wall (for the clearance check model only)
    mesh_tol=0.02,
    stem_frustum=True,      # RV02 F-6: stem = frustum pad footprint -> flange footprint (<= 45 deg), print stem-down
)
P = PARAMS
CX, CY = ML.SW_DPI


def one(s, what):
    sols = s.solids() if s is not None else []
    if len(sols) != 1:
        raise RuntimeError(f"{what}: expected 1 solid, got {len(sols)}")
    if not sols[0].is_valid or sols[0].volume <= 0:
        raise RuntimeError(f"{what}: invalid")
    return sols[0]


def build():
    t0 = time.time()
    x0, y0, x1, y1 = ML.DPI_CAP
    z_fl_top = ML.DPI_GUIDE_Z - ML.DPI_GUIDE_CLR                # 13.35
    z_fl_bot = z_fl_top - P["flange_t"]
    cap = one(ML.skin() & ML.box(x0, y0, z_fl_top - P["overlap"], x1, y1, 60.0), "cap body")
    if P["top_lower"] > 0:
        cap = one(cap - cap.moved(Location((0, 0, 60))).moved(Location((0, 0, -60 - P["top_lower"]))), "lower")
    f = ML.DPI_FLANGE
    flange = ML.box(x0 - f, y0 - f, z_fl_bot, x1 + f, y1 + f, z_fl_top)
    z_pad = ML.PLUNGER_TOP_Z                                    # rests on the plunger (gap 0.0)
    sx, sy = P["stem"]
    stem = ML.box(CX - sx / 2, CY - sy / 2, z_pad + P["pad_t"] - P["overlap"], CX + sx / 2, CY + sy / 2, z_fl_bot + P["overlap"])
    px, py = ML.DPI_NUB_PAD
    if P["stem_frustum"]:
        za, zb = z_pad + P["pad_t"], z_fl_bot
        ra = Rectangle(px, py); rb = Rectangle(x1 - x0 + 2 * f, y1 - y0 + 2 * f)
        fa = Plane(origin=(CX, CY, za)) * ra; fb = Plane(origin=((x0 + x1) / 2, (y0 + y1) / 2, zb)) * rb
        stem = one(Solid.make_loft([Wire(fa.edges()), Wire(fb.edges())]), "frustum")
    pad = ML.box(CX - px / 2, CY - py / 2, z_pad, CX + px / 2, CY + py / 2, z_pad + P["pad_t"])
    b = cap
    for nm, q in (("flange", flange), ("stem", stem), ("pad", pad)):
        b = one(b + q, f"+{nm}")
    return b, dict(z_flange=(z_fl_bot, z_fl_top), build_s=time.time() - t0)


def sleeve_model():
    """WP-E guide sleeve per spec (inner = DPI_CAP + 0.15, wall 1.0, tongue underside .. DPI_GUIDE_Z) - check only."""
    x0, y0, x1, y1 = ML.DPI_CAP
    c = ML.DPI_GUIDE_CLR; w = P["sleeve_wall"]
    zt = ML.inner_z_at(CX, CY)
    outer = ML.box(x0 - c - w, y0 - c - w, ML.DPI_GUIDE_Z, x1 + c + w, y1 + c + w, zt + 0.5)
    return (outer - ML.box(x0 - c, y0 - c, ML.DPI_GUIDE_Z - 1, x1 + c, y1 + c, zt + 1)).solids()[0], zt


def wheel_model(drop=0.0):
    x0, x1 = ML.WHEEL_X
    pl = Plane(origin=(x0, ML.ENC_AXIS_Y, ML.ENC_AXIS_Z - drop), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    return Solid.make_cylinder(ML.WHEEL_D / 2, ML.WHEEL_W, pl)


def vol(s):
    return sum(q.volume for q in s.solids()) if s is not None else 0.0


def check(b, info):
    import trimesh
    R = {}
    cp = ML.check_part(b, "dpi_button")
    R["A1_single_valid_solid"] = dict(value=f"n={cp['n_solids']} valid={cp['valid']}", ok=cp["n_solids"] == 1 and cp["valid"])
    R["volume_mm3"] = dict(value=round(b.volume, 1), ok=b.volume > 0)
    m = ML.mesh_of(b, P["mesh_tol"])
    R["mesh_watertight"] = dict(value=bool(m.is_watertight), ok=bool(m.is_watertight))
    R["bbox"] = dict(value=[round(float(v), 2) for v in list(m.bounds[0]) + list(m.bounds[1])], ok=True)
    # A8 nub rest gap over the plunger box (1.2 X x 2.9 Y)
    zs = []
    for x in np.linspace(CX - 0.6, CX + 0.6, 5):
        for y in np.linspace(CY - 1.45, CY + 1.45, 7):
            loc, _, _ = m.ray.intersects_location([[x, y, -10]], [[0, 0, 1]])
            zs.append(loc[:, 2].min())
    gap = min(zs) - ML.PLUNGER_TOP_Z
    R["A8_nub_rest_gap(0..0.30)"] = dict(value=round(gap, 3), ok=-1e-3 <= gap <= 0.30)
    # cap top vs skin (flush)
    dz = [ML.top_z(b, x, y) - ML.skin_z_at(x, y) for x in np.linspace(ML.DPI_CAP[0] + 0.3, ML.DPI_CAP[2] - 0.3, 4)
          for y in np.linspace(ML.DPI_CAP[1] + 0.3, ML.DPI_CAP[3] - 0.3, 4)]
    R["cap_top_minus_skin(flush 0.0)"] = dict(value=[round(min(dz), 3), round(max(dz), 3)], ok=max(abs(v) for v in dz) <= 0.05)
    # PCB: exact interference (STEP) + clearances (meshes), rest and pressed
    pcb = ML.load_pcb()
    plbox = (CX - 0.65, CY - 1.5, 6.5, CX + 0.65, CY + 1.5, 7.7)
    pcbm = {g: trimesh.load(str(ML.WORK / "00_pcb" / "mesh" / f"{g}.stl")) for g in
            ("board", "switch", "encoder", "sensor", "usb_header", "smd")}

    def interf(shape):
        bb = shape.bounding_box(); tot = 0.0; cont = 0.0
        for s in pcb.solids():
            sb = s.bounding_box()
            if sb.max.X < bb.min.X - .5 or sb.min.X > bb.max.X + .5 or sb.max.Y < bb.min.Y - .5 or sb.min.Y > bb.max.Y + .5 \
                    or sb.max.Z < bb.min.Z - .5 or sb.min.Z > bb.max.Z + .5:
                continue
            v = vol(shape & s)
            if v > 1e-6:
                vin = vol((shape & s) & ML.box(*plbox)); cont += vin; tot += v - vin
        return tot, cont

    def clear(mm):
        out = {}
        for g, pm in pcbm.items():
            v = mm.vertices
            d = np.abs(trimesh.proximity.ProximityQuery(pm).signed_distance(v))
            if g == "switch":   # designed contact: pad on the plunger
                d = d[~((np.abs(v[:, 0] - CX) < ML.DPI_NUB_PAD[0] / 2 + 0.05) & (np.abs(v[:, 1] - CY) < ML.DPI_NUB_PAD[1] / 2 + 0.05)
                        & (v[:, 2] < ML.PLUNGER_TOP_Z + P["pad_t"] - 0.05) & (v[:, 2] > ML.PLUNGER_TOP_Z - 1.0)
                        & (np.abs(v[:, 0] - CX) < 0.6 + 0.3) & (v[:, 2] > ML.SW_BODY_TOP_Z + 0.2))]
            pv = pm.vertices
            near = (pv[:, 0] > mm.bounds[0][0] - 3) & (pv[:, 0] < mm.bounds[1][0] + 3) & (pv[:, 1] > mm.bounds[0][1] - 3) & \
                   (pv[:, 1] < mm.bounds[1][1] + 3)
            pv = pv[near]
            if g == "switch" and len(pv):
                pv = pv[~((np.abs(pv[:, 0] - CX) < 0.7) & (np.abs(pv[:, 1] - CY) < 1.55) & (pv[:, 2] > ML.SW_BODY_TOP_Z + 0.05))]
            d2 = np.abs(trimesh.proximity.ProximityQuery(mm).signed_distance(pv)) if len(pv) else np.array([99.0])
            out[g] = round(float(min(d.min(), d2.min())), 3)
        return out

    vi, vc = interf(b)
    R["A5_pcb_interference_rest_mm3"] = dict(value=dict(outside_contact=round(vi, 4), plunger_contact=round(vc, 4)), ok=vi < 1e-4)
    cl = clear(m)
    R["A6_pcb_clearance_rest(>=0.25, excl. pad/plunger)"] = dict(value=cl, ok=min(cl.values()) >= ML.CLR_SLIDE)
    bp = b.moved(Location((0, 0, -P["press_travel"])))
    mp = ML.mesh_of(bp, P["mesh_tol"])
    vip, _ = interf(bp)
    clp = clear(mp)
    # pad underside to the switch body top when pressed (pad overhangs the plunger)
    R["pressed_0.75_pcb"] = dict(value=dict(interf_outside_plunger=round(vip, 4), clear=clp,
                                            pad_to_body_top=round(ML.PLUNGER_TOP_Z - P["press_travel"] - ML.SW_BODY_TOP_Z, 3)),
                                 ok=vip < 1e-4 and min(clp.values()) >= ML.CLR_SLIDE - 0.005)
    # window (top_shell_raw), sleeve model, wheel envelope, buttons
    import trimesh as tm
    ts = tm.load(str(ML.OUT / "top_shell_raw.stl"))

    def mdist(a, bm):
        da = tm.proximity.ProximityQuery(bm).signed_distance(a.vertices)
        db = tm.proximity.ProximityQuery(a).signed_distance(bm.vertices)
        return round(float(min(np.abs(da).min(), np.abs(db).min())), 3), round(float(max(da.max(), db.max())), 3)
    w_rest = mdist(m, ts); w_pr = mdist(mp, ts)
    R["window_gap_top_shell_raw(design 0.30)"] = dict(value=dict(rest=w_rest, pressed=w_pr),
                                                      ok=w_rest[1] <= 0 and w_pr[1] <= 0 and min(w_rest[0], w_pr[0]) >= 0.28)
    sl, zt = sleeve_model()
    d_sl = ML.min_dist(b, sl); i_sl = vol(b & sl)
    # flange top to sleeve bottom (up-stop)
    fl_gap = ML.DPI_GUIDE_Z - info["z_flange"][1]
    R["sleeve_clearance(0.15)+flange_upstop_gap"] = dict(value=dict(min_dist=round(d_sl, 3), interf=round(i_sl, 4),
                                                                    flange_to_sleeve=round(fl_gap, 3), tongue_underside=round(zt, 2)),
                                                         ok=i_sl < 1e-6 and d_sl >= 0.149)
    wr = {}
    for drop in (0.0, 0.30):
        wm = wheel_model(drop)
        for pr in (0.0, P["press_travel"]):
            bb_ = b.moved(Location((0, 0, -pr)))
            wr[f"wheel_drop{drop}_dpi_press{pr}"] = (round(ML.min_dist(bb_, wm), 3), round(vol(bb_ & wm), 4))
    R["wheel_envelope_clearance(>=0.25)"] = dict(value=wr, ok=all(v[1] < 1e-6 and v[0] >= ML.CLR_SLIDE for v in wr.values()))
    bl = tm.load(str(ML.OUT / "button_L_raw.stl")); br = tm.load(str(ML.OUT / "button_R_raw.stl"))
    R["main_button_raw_clearance"] = dict(value=dict(L=mdist(m, bl), R=mdist(m, br)),
                                          ok=mdist(m, bl)[1] <= 0 and mdist(m, br)[1] <= 0)
    R["placement"] = dict(value=f"placed by nub pad on DPI plunger {ML.SW_DPI} (face Z {ML.PLUNGER_TOP_Z}), slide axis (0,0,-1)", ok=True)
    return R


def export(b):
    d = ML.export_part(b, "dpi_button")
    # print orientation (RV02 F-6): as installed, nub pad face on the bed, stem frustum + flange above (no overhang)
    m = ML.mesh_of(b, 0.02)
    m.apply_translation(-np.array([0, 0, m.bounds[0][2]]))
    m.export(str(d / "dpi_button_print.stl"))
    nz = m.face_normals[:, 2]; zc = m.triangles_center[:, 2]
    bed = (nz < -0.9998) & (zc < 0.02)
    ovh = (nz < -0.7071) & ~bed
    from build123d import import_step
    vstep = sum(q.volume for q in import_step(str(d / "dpi_button.step")).solids())
    return d, m.bounds, dict(bed_mm2=round(float(m.area_faces[bed].sum()), 2),
                             overhang_gt45_mm2=round(float(m.area_faces[ovh].sum()), 2), step_volume=round(vstep, 1)), 0.0


if __name__ == "__main__":
    b, info = build()
    d, pb, ang, sag = export(b)
    R = check(b, info)
    R["print_orientation"] = dict(value=dict(orientation="as installed, pad face down", bounds=[[round(float(v), 2) for v in r] for r in pb]),
                                  ok=abs(pb[0][2]) < 1e-6)
    R["A17_print_overhang_and_bed(F-6)"] = dict(value=ang, ok=ang["overhang_gt45_mm2"] <= 0.5)
    R["volume_mm3"] = dict(value=ang["step_volume"], ok=ang["step_volume"] > 0)
    (d / "checks_dpi_button.json").write_text(json.dumps(R, indent=1, default=str))
    print(f"==== dpi_button ({info['build_s']:.0f}s build) ====")
    for k, v in R.items():
        print(f"  {'PASS' if v['ok'] else 'FAIL'}  {k}: {v['value']}")
