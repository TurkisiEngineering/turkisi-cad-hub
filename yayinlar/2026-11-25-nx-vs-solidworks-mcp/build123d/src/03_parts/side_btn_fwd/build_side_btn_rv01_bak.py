"""
build_side_btn.py - WP-H side bell-crank levers (side_btn_fwd / side_btn_back), PETG.

Run:  python build_side_btn.py fwd      (or: back, or: all)
Writes 03_parts/side_btn_<name>/side_btn_<name>.step/.stl, side_btn_<name>_print.stl, checks_side_btn_<name>.json
Native PCB coords (+X right, +Y front, +Z up). Every interface number comes from master.py (ML.*).
Lever rotates about SIDE_PIVOT (axis +Y). Positive angle (right-hand about +Y) = thumb press:
points above the pivot move +X, the arm over the board moves -Z onto the side D2F plunger.
"""
import sys, json, math, time
from pathlib import Path
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *
import master as ML
import numpy as np

# ---------------------------------------------------------------------------------------------------
# PARAMS (designer-defined values; interfaces come from ML)
# ---------------------------------------------------------------------------------------------------
PARAMS = dict(
    backing_x0=11.0,          # backing slab behind the face plate starts here (inside the notch, overlaps face plate)
    flange_clr=0.15,          # flange X >= max cavity-wall X around the notch + this (spec 0.2; 0.15 keeps the outward-stop nub lift <= 0.30)
    flange_w=0.80,            # flange reach beyond the notch rim (per side / top) and its thickness
    flange_z_from=3.60,       # flange only above this Z (keeps >= 0.6 from the bottom-shell lip, top Z 2.5)
    notch_min_gap=0.17,       # face must keep this to the notch edges at the stop angle (A22)
    body_x1=13.80,            # body plate X range = SIDE_BODY_X0 .. body_x1
    body_z_top=3.50,          # body plate (below the backing) top
    body_axial_clr=0.25,      # body plate to the cradle end faces (sliding)
    arm_w=4.0,                # arm width (Y), centred on the plunger Y
    arm_t=2.0,                # arm thickness (Z) above SIDE_ARM_Z_MIN
    arm_x0=12.80,             # arm start X (stays clear of the wall above the notch on the outward stop)
    pad_t=0.70,               # nub pad: from NUB_Z up to the arm underside (8.4 - 7.695)
    pad_flat_dx=0.06,         # flat part of the pad ends at plunger X + this (rest); +X beyond it is bevelled
    pad_bevel_deg=30.0,       # bevel rise angle (keeps the pad edge >= 0.25 off the switch body at the stop)
    stop_w=0.88,              # stop pad thickness in X (stop frame), face at the board edge at the stop angle
    stop_z=(0.20, 1.30),      # stop face Z range (stop frame)
    stop_y_inset=1.0,         # stop pad Y range = body Y range inset by this (clear of the rear-left boss/screw)
    mesh_tol=0.02,
)
P = PARAMS
OUTROOT = ML.PARTS_DIR
PX, PZ = ML.SIDE_PIVOT
PIVOT_AX = Axis((PX, 0, PZ), (0, 1, 0))


def one(s, what):
    sols = s.solids() if s is not None else []
    if len(sols) != 1:
        raise RuntimeError(f"{what}: expected 1 solid, got {len(sols)}")
    sol = sols[0]
    if not sol.is_valid or sol.volume <= 0:
        raise RuntimeError(f"{what}: invalid solid")
    return sol


def theta_for_travel(plunger_x, travel):
    """Rotation (rad) at which the nub face drops `travel` at the plunger centre X (exact, not small-angle)."""
    u0 = plunger_x - PX; v0 = ML.NUB_Z - PZ
    f = lambda t: v0 - (v0 - u0 * math.sin(t)) / math.cos(t) - travel
    a, b = 0.0, 0.3
    for _ in range(80):
        m = (a + b) / 2
        a, b = (m, b) if f(m) < 0 else (a, m)
    return (a + b) / 2


def build(name):
    sb = ML.SIDE_BTNS[name]
    y0, y1 = sb["y0"], sb["y1"]
    plx, ply = sb["plunger"]
    th_stop = theta_for_travel(plx, ML.TRAVEL_STOP)
    deg_stop = math.degrees(th_stop)
    t0 = time.time()
    S, I = ML.skin(), ML.inner()
    # 1. face plate = skin patch inside the face profile, outer surface moved -X by SIDE_PROUD, inner = cavity
    prof = ML.side_face_profile(name)
    fp = one((S.moved(Location((-ML.SIDE_PROUD, 0, 0))) & prof) - I, "face plate")
    # backing slab behind the face (fills face plate -> body), inside the face profile only
    # cavity wall X around the notch (mesh probe of the inner skin)
    im = ML._mesh_for(I)
    wall_x = []
    for y in np.arange(y0 - ML.SIDE_GAP - P["flange_w"], y1 + ML.SIDE_GAP + P["flange_w"] + 0.01, 0.5):
        for z in np.arange(P["flange_z_from"], ML.SIDE_FACE_Z[1] + ML.SIDE_GAP + P["flange_w"] + 0.01, 0.25):
            loc, _, _ = im.ray.intersects_location([[-50, y, z]], [[1, 0, 0]])
            if len(loc):
                wall_x.append(float(loc[:, 0].min()))
    wall_xmax = max(wall_x)
    fx0 = wall_xmax + P["flange_clr"]
    fx1 = fx0 + P["flange_w"]
    backing = ML.box(P["backing_x0"], y0, ML.SIDE_FACE_Z[0], fx1, y1, ML.SIDE_FACE_Z[1]) & prof
    face = one(fp + backing, "face+backing")
    # trim: at the stop angle the face must stay >= notch_min_gap inside the notch (profile grown SIDE_GAP - gap)
    keep = ML.side_face_profile(name, grow=ML.SIDE_GAP - P["notch_min_gap"]).rotate(PIVOT_AX, -deg_stop)
    face = one(face & keep, "face trimmed")
    # 2. flange behind the notch rim (sides + top), outward stop against the cavity wall
    fl_prof = ML.side_face_profile(name, grow=ML.SIDE_GAP + P["flange_w"], z_from=P["flange_z_from"])
    flange = fl_prof & ML.box(fx0, -200, -20, fx1, 50, 40)
    # 3. pin + body plate between the cradles
    cr = [y0 + 1.8, y1 - 1.8]                       # cradle centres (rear, front)
    half = ML.SIDE_CRADLE_LEN / 2
    stub = (ML.SIDE_CRADLE_LEN + 0.3) / 2
    pin = Solid.make_cylinder(ML.SIDE_PIN_D / 2, (cr[1] + stub) - (cr[0] - stub),
                              Plane(origin=(PX, cr[0] - stub, PZ), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
    by0, by1 = cr[0] + half + P["body_axial_clr"], cr[1] - half - P["body_axial_clr"]
    body = ML.box(ML.SIDE_BODY_X0, by0, PZ, P["body_x1"], by1, P["body_z_top"])
    body_up = ML.box(ML.SIDE_BODY_X0, by0, P["body_z_top"] - 0.5, fx1, by1, ML.SIDE_FACE_Z[1] - 0.5)  # ties body -> backing
    # 4. stop pad: face at the board edge X at the stop angle (built in the stop frame, rotated back to rest)
    sy0, sy1 = by0 + P["stop_y_inset"], by1 - P["stop_y_inset"]
    stop = ML.box(ML.BOARD_BBOX[0] - P["stop_w"], sy0, P["stop_z"][0], ML.BOARD_BBOX[0], sy1, P["stop_z"][1])
    stop = stop.rotate(PIVOT_AX, -deg_stop)
    # 5. arm over the board + nub pad (flat face at NUB_Z, bevel on the +X side)
    az0 = ML.SIDE_ARM_Z_MIN
    padx0 = plx + ML.SIDE_NUB_DX - ML.SIDE_NUB_PAD[0] / 2
    padx1 = plx + ML.SIDE_NUB_DX + ML.SIDE_NUB_PAD[0] / 2
    arm = ML.box(P["arm_x0"], ply - P["arm_w"] / 2, az0, padx1, ply + P["arm_w"] / 2, az0 + P["arm_t"])
    xb = plx + P["pad_flat_dx"]
    rise = (padx1 - xb) * math.tan(math.radians(P["pad_bevel_deg"]))
    zt = ML.NUB_Z + P["pad_t"] + 0.2          # overlap into the arm
    prof_pts = [(padx0, ML.NUB_Z), (xb, ML.NUB_Z), (padx1, ML.NUB_Z + rise), (padx1, zt), (padx0, zt)]
    w = Wire.make_polygon([Vector(x, ply - ML.SIDE_NUB_PAD[1] / 2, z) for x, z in prof_pts], close=True)
    pad = Solid.extrude(Face(w), Vector(0, ML.SIDE_NUB_PAD[1], 0))
    lever = face
    for nm, part in (("flange", flange), ("body_up", body_up), ("body", body), ("pin", pin), ("stop", stop),
                     ("arm", arm), ("pad", pad)):
        lever = one(lever + part, f"+{nm}")
    info = dict(theta_stop_deg=deg_stop, wall_xmax=wall_xmax, flange_x=(fx0, fx1), cradles=cr, body_y=(by0, by1),
                stop_y=(sy0, sy1), pad=(padx0, padx1, xb, rise), build_s=time.time() - t0)
    return lever, info


# ---------------------------------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------------------------------
def cradle_solids(name):
    """Bottom-shell C-cradles as specified for WP-D (bore SIDE_CRADLE_ID, wall 1.0, 270 deg, open +-45 deg about +Z)."""
    sb = ML.SIDE_BTNS[name]
    out = []
    for yc in (sb["y0"] + 1.8, sb["y1"] - 1.8):
        pl = Plane(origin=(PX, yc - ML.SIDE_CRADLE_LEN / 2, PZ), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
        ring = Solid.make_cylinder(ML.SIDE_CRADLE_ID / 2 + 1.0, ML.SIDE_CRADLE_LEN, pl) - \
            Solid.make_cylinder(ML.SIDE_CRADLE_ID / 2, ML.SIDE_CRADLE_LEN, pl)
        # opening: wedge +-45 deg about +Z
        r = 5.0
        wpts = [(PX, PZ), (PX - r, PZ + r), (PX + r, PZ + r)]
        wedge = Solid.extrude(Face(Wire.make_polygon([Vector(x, yc - 3, z) for x, z in wpts], close=True)),
                              Vector(0, 6, 0))
        out.append((ring - wedge).solids()[0])
    return out


def mesh_dist(a_mesh, b_mesh):
    """Min distance between two meshes (vertex->surface both ways) and penetration flag (signed)."""
    import trimesh
    pa = trimesh.proximity.ProximityQuery(b_mesh)
    pb = trimesh.proximity.ProximityQuery(a_mesh)
    da = pa.signed_distance(a_mesh.vertices)        # >0 inside b
    db = pb.signed_distance(b_mesh.vertices)        # >0 inside a
    pen = max(float(da.max()), float(db.max()))
    dmin = min(float(np.abs(da).min()), float(np.abs(db).min()))
    return dmin, pen


def check(name, lever, info):
    import trimesh
    R = {}
    sb = ML.SIDE_BTNS[name]
    plx, ply = sb["plunger"]
    cp = ML.check_part(lever, name)
    R["A1_single_valid_solid"] = dict(value=f"n={cp['n_solids']} valid={cp['valid']}", ok=cp["n_solids"] == 1 and cp["valid"])
    R["volume_mm3"] = dict(value=round(lever.volume, 1), ok=lever.volume > 0)
    m = ML.mesh_of(lever, P["mesh_tol"])
    R["mesh_watertight"] = dict(value=bool(m.is_watertight), ok=bool(m.is_watertight))
    R["bbox"] = dict(value=[round(v, 2) for v in list(m.bounds[0]) + list(m.bounds[1])], ok=True)
    # A8 nub rest gap: lowest lever Z over the plunger box (1.2 X x 2.9 Y)
    zs = []
    for x in np.linspace(plx - 0.6, plx + 0.6, 7):
        for y in np.linspace(ply - 1.45, ply + 1.45, 7):
            loc, _, _ = m.ray.intersects_location([[x, y, -10]], [[0, 0, 1]])
            if len(loc):
                zs.append(loc[:, 2].min())
    gap = min(zs) - ML.PLUNGER_TOP_Z
    R["A8_nub_rest_gap"] = dict(value=round(gap, 3), ok=0.0 <= gap <= 0.30)
    # PCB meshes
    pcbm = {g: trimesh.load(str(ML.WORK / "00_pcb" / "mesh" / f"{g}.stl")) for g in
            ("board", "switch", "encoder", "sensor", "usb_header", "smd")}
    plbox = (plx - 0.6 - 0.05, ply - 1.45 - 0.05, 6.5, plx + 0.6 + 0.05, ply + 1.45 + 0.05, 7.7)
    # exact interference with the PCB STEP (bbox-filtered), plunger contact separated
    pcb = ML.load_pcb()
    bbl = lever.bounding_box()

    def pcb_interf(shape):
        tot, contact = 0.0, 0.0
        b = shape.bounding_box()
        for s in pcb.solids():
            sbx = s.bounding_box()
            if sbx.max.X < b.min.X - 0.5 or sbx.min.X > b.max.X + 0.5 or sbx.max.Y < b.min.Y - 0.5 or \
                    sbx.min.Y > b.max.Y + 0.5 or sbx.max.Z < b.min.Z - 0.5 or sbx.min.Z > b.max.Z + 0.5:
                continue
            c = shape & s
            v = sum(q.volume for q in c.solids()) if c is not None else 0.0
            if v > 1e-6:
                cin = c & ML.box(*plbox)
                vin = sum(q.volume for q in cin.solids()) if cin is not None else 0.0
                contact += vin; tot += v - vin
        return tot, contact
    def stopz(v):
        sy0, sy1 = info["stop_y"]
        return (v[:, 0] > 13.4) & (v[:, 1] > sy0 - 0.05) & (v[:, 1] < sy1 + 0.05) & (v[:, 2] > 0.05) & (v[:, 2] < 1.5)

    # clearance to PCB components (mesh, excluding the plunger zone)
    def pcb_clear(mm):
        rows = {}
        for g, pm in pcbm.items():
            pq = trimesh.proximity.ProximityQuery(pm)
            v = mm.vertices
            d = np.abs(pq.signed_distance(v))
            inz = (v[:, 0] > plbox[0] - 0.3) & (v[:, 0] < plbox[3] + 0.3) & (v[:, 1] > plbox[1] - 0.3) & \
                  (v[:, 1] < plbox[4] + 0.3) & (v[:, 2] < 8.0)
            if g == "switch":
                d = d[~inz]
            if g == "board":   # designed contact: stop pad face on the board left edge
                d = d[~stopz(v)]
            # also PCB vertices -> lever
            pq2 = trimesh.proximity.ProximityQuery(mm)
            pv = pm.vertices
            near = (pv[:, 0] > mm.bounds[0][0] - 3) & (pv[:, 0] < mm.bounds[1][0] + 3) & \
                   (pv[:, 1] > mm.bounds[0][1] - 3) & (pv[:, 1] < mm.bounds[1][1] + 3)
            pv = pv[near]
            if g == "board" and len(pv):
                sy0, sy1 = info["stop_y"]
                pv = pv[~((pv[:, 0] < ML.BOARD_BBOX[0] + 0.12) & (pv[:, 1] > sy0 - 0.3) & (pv[:, 1] < sy1 + 0.3))]
            if g == "switch" and len(pv):
                pv = pv[~((pv[:, 0] > plbox[0] - 0.3) & (pv[:, 0] < plbox[3] + 0.3) & (pv[:, 1] > plbox[1] - 0.3) &
                          (pv[:, 1] < plbox[4] + 0.3) & (pv[:, 2] > 6.9))]
            d2 = np.abs(pq2.signed_distance(pv)) if len(pv) else np.array([99.0])
            rows[g] = round(float(min(d.min(), d2.min())), 3)
        return rows
    vs = m.vertices[stopz(m.vertices)]
    R["stop_face_gap_to_board_edge_rest(design 0.22 @Z0.75)"] = dict(
        value=dict(min=round(float(ML.BOARD_BBOX[0] - vs[:, 0].max()), 3),
                   at_Z0_75=round(float(ML.BOARD_BBOX[0] - m.ray.intersects_location(
                       [[ML.BOARD_BBOX[0] + 1.0, sum(info["stop_y"]) / 2, 0.75]], [[-1, 0, 0]])[0][:, 0].max()), 3)), ok=True)
    vi, vc = pcb_interf(lever)
    R["A5_pcb_interference_rest_mm3"] = dict(value=round(vi, 4), ok=vi < 1e-4)
    cl = pcb_clear(m)
    R["A6_pcb_clearance_rest"] = dict(value=cl, ok=min(cl.values()) >= ML.CLR_SLIDE)
    # fixed envelopes (master raw shells, meshes from layout_check) + cradles per spec
    env = {k: trimesh.load(str(ML.OUT / f"{k}.stl")) for k in ("top_shell_raw", "bottom_shell_raw", "button_L_raw")}
    cr = cradle_solids(name)
    crm = trimesh.util.concatenate([ML.mesh_of(c, 0.02) for c in cr])
    env["cradles(spec)"] = crm

    def env_clear(mm, sh):
        out = {}
        for k, em in env.items():
            if k == "cradles(spec)":
                d = min(ML.min_dist(sh, c) for c in cr)
                inter = sum((sum(q.volume for q in (sh & c).solids()) if (sh & c) is not None else 0) for c in cr)
                out[k] = (round(d, 3), round(inter, 4))
            else:
                d, pen = mesh_dist(mm, em)
                out[k] = (round(d, 3), round(pen, 3))
        return out
    ec = env_clear(m, lever)
    # no penetration; min distance reported (top shell min = flange outward-stop gap, designed 0.15 to the wall)
    R["clearance_rest_to_envelopes(min_d, penetration)"] = dict(
        value=ec, ok=all(v[1] <= 1e-3 for v in ec.values()))
    # lip clearance (lip is part of bottom_shell_raw: report the bottom-shell distance at Z 1..2.5 region)
    # rotated states
    th_stop = info["theta_stop_deg"]
    res_rot = {}
    for deg in (5.2, th_stop):
        L2 = lever.rotate(PIVOT_AX, deg)
        m2 = ML.mesh_of(L2, P["mesh_tol"])
        vi2, vc2 = pcb_interf(L2)
        cl2 = pcb_clear(m2)
        ec2 = env_clear(m2, L2)
        # nub drop at the plunger centre
        loc, _, _ = m2.ray.intersects_location([[plx, ply, -10]], [[0, 0, 1]])
        zn = float(loc[:, 2].min())
        # stop face to board edge: min X distance of the rotated lever (Z 0..1.51) to X 14.478
        v = m2.vertices
        sel = (v[:, 2] > 0.0) & (v[:, 2] < ML.BOARD_Z1) & (v[:, 0] < ML.BOARD_BBOX[0] + 0.5)
        stop_gap = float(ML.BOARD_BBOX[0] - v[sel, 0].max()) if sel.any() else None
        res_rot[round(deg, 2)] = dict(nub_travel=round(ML.NUB_Z - zn, 3), pcb_interf_outside_plunger=round(vi2, 4),
                                     plunger_contact_mm3=round(vc2, 3), pcb_clear=cl2, env=ec2,
                                     stop_gap_to_board_edge=None if stop_gap is None else round(stop_gap, 3))
    r52, rs = res_rot[5.2], res_rot[round(th_stop, 2)]
    R["A22_rot5.2_interference_outside_designed_contacts"] = dict(
        value=dict(pcb=r52["pcb_interf_outside_plunger"], env={k: v[1] for k, v in r52["env"].items()}),
        ok=r52["pcb_interf_outside_plunger"] < 1e-4 and all(v[1] <= 1e-3 for v in r52["env"].values()))
    R["A22_at_stop_interference"] = dict(
        value=dict(deg=round(th_stop, 2), pcb=rs["pcb_interf_outside_plunger"], env={k: v[1] for k, v in rs["env"].items()},
                   stop_gap=rs["stop_gap_to_board_edge"]),
        ok=rs["pcb_interf_outside_plunger"] < 1e-4 and all(v[1] <= 1e-3 for v in rs["env"].values()))
    R["nub_travel_at_stop(0.8+-0.05)"] = dict(value=dict(at_stop=rs["nub_travel"], stop_gap=rs["stop_gap_to_board_edge"],
                                                          at_5_2deg=r52["nub_travel"]),
                                               ok=abs(rs["nub_travel"] - ML.TRAVEL_STOP) <= 0.05 and
                                               rs["stop_gap_to_board_edge"] is not None and rs["stop_gap_to_board_edge"] <= 0.03)
    R["A22_face_in_notch_min_gap_at_stop(>=0.15)"] = dict(value=rs["env"]["top_shell_raw"][0],
                                                          ok=rs["env"]["top_shell_raw"][0] >= 0.15 - 0.01)
    worst_pcb = min(min(r["pcb_clear"].values()) for r in res_rot.values())
    R["moving_pcb_clearance_full_rotation(>=0.25, excl. nub/plunger)"] = dict(
        value={k: r["pcb_clear"] for k, r in res_rot.items()}, ok=worst_pcb >= ML.CLR_SLIDE - 0.005)
    # outward stop (flange on the cavity wall): first contact when rotating negative
    th_out = None
    for k in range(1, 13):
        deg = -0.25 * k
        L3 = lever.rotate(PIVOT_AX, deg)
        m3 = ML.mesh_of(L3, 0.03)
        pen = max(mesh_dist(m3, env["top_shell_raw"])[1], mesh_dist(m3, env["bottom_shell_raw"])[1])
        if pen > 0:
            th_out = deg; break
    if th_out is not None:
        t = math.radians(th_out)
        u0 = plx - PX; v0 = ML.NUB_Z - PZ
        z_out = PZ + (v0 - u0 * math.sin(t)) / math.cos(t)
        R["A8_nub_gap_on_outward_stop(0..0.30)"] = dict(value=dict(outward_stop_deg=th_out, nub_gap=round(z_out - ML.PLUNGER_TOP_Z, 3)),
                                                     ok=0.0 <= z_out - ML.PLUNGER_TOP_Z <= 0.30)
    else:
        R["A8_nub_gap_on_outward_stop(0..0.30)"] = dict(value="no outward stop within 3 deg", ok=False)
    # A23-style drop: no top-shell material below any lever point (top shell lowered vertically from +15)
    ts = env["top_shell_raw"]
    pts = np.vstack([m.vertices, m.sample(20000)])
    loc, idx, _ = ts.ray.intersects_location(pts, np.tile([0, 0, -1.0], (len(pts), 1)))
    hit = 0
    if len(loc):
        dz = pts[idx, 2] - loc[:, 2]
        hit = int(((dz >= -1e-6) & (dz <= 15.0)).sum())
    R["A23_drop_top_shell_sweep_hits"] = dict(value=hit, ok=hit == 0)
    R["placement"] = dict(value=f"placed by pin axis on SIDE_PIVOT {ML.SIDE_PIVOT} (cradle centres Y {info['cradles']}), "
                                f"axis (0,1,0); nub on plunger {sb['plunger']}", ok=True)
    R["_rotations"] = res_rot
    R["_info"] = info
    return R


def export(name, lever):
    part = f"side_btn_{name}"
    d = ML.export_part(lever, part)
    # print orientation: lying on the face plate (outer face -X down), pin axis (Y) parallel to the bed
    pr = lever.rotate(Axis((0, 0, 0), (0, 1, 0)), -90)
    zmin = pr.bounding_box().min.Z
    m = ML.mesh_of(pr, 0.02)
    m.apply_translation([0, 0, -m.bounds[0][2]])
    m.export(str(d / f"{part}_print.stl"))
    return d, m.bounds


def main(names):
    for n in names:
        lever, info = build(n)
        d, pb = export(n, lever)
        R = check(n, lever, info)
        R["print_stl_bounds"] = dict(value=[[round(v, 2) for v in r] for r in pb], ok=abs(pb[0][2]) < 1e-6)
        (d / f"checks_side_btn_{n}.json").write_text(json.dumps(R, indent=1, default=str))
        print(f"==== side_btn_{n}  ({info['build_s']:.0f}s build) ====")
        for k, v in R.items():
            if k.startswith("_"):
                continue
            print(f"  {'PASS' if v['ok'] else 'FAIL'}  {k}: {v['value']}")
        print("  info:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in info.items()})


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "all"
    main(["fwd", "back"] if a == "all" else [a])
