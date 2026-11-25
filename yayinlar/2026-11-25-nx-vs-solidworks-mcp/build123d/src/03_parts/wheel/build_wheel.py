"""
WP-G  scroll wheel + axle + yoke  (build + self-check + section PNGs + README)
Re-run:  python build_wheel.py        (~1-2 min; reads master.py, the PCB STEP and the master out/*.stl meshes)

Parts written (native PCB coords, assembly position):
  03_parts/wheel/wheel.step/.stl          wheel + axle as ONE solid (interface envelope; = one-piece printed variant)
  03_parts/wheel/wheel_body.step/.stl     the PRINTED wheel (hex stub + blind pin bore)   -> wheel_print.stl
  03_parts/wheel/axle_pin.step/.stl       steel pin ISO 2338 2 m6 x 16 (bought), pressed into wheel_body
  03_parts/wheel_yoke/wheel_yoke.step/.stl  PETG yoke                                    -> wheel_yoke_print.stl
"""
import sys, math, json, time
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *                      # noqa  (must come before master)
import master as ML
import numpy as np
import trimesh
from pathlib import Path

T0 = time.time()
def _t(msg):
    print(f"  [{time.time() - T0:6.1f} s] {msg}", flush=True)
# ==================================================================================================
# PARAMS  (interface numbers come from master; designer values are named here, nothing below is magic)
# ==================================================================================================
P = dict(
    # interface (master.py)
    AX_Y=ML.ENC_AXIS_Y, AX_Z=ML.ENC_AXIS_Z, X_CL=ML.X_CL,
    WHEEL_X0=ML.WHEEL_X[0], WHEEL_X1=ML.WHEEL_X[1], WHEEL_R=ML.WHEEL_D / 2,
    AXLE_R=ML.AXLE_D / 2, AXLE_X0=ML.AXLE_X[0], AXLE_X1=ML.AXLE_X[1],
    HEX_AF=ML.AXLE_HEX_AF, HEX_X0=ML.AXLE_HEX_X[0], HEX_X1=ML.AXLE_HEX_X[1],
    PIVOT_X=ML.ENC_PIVOT_X, MC_TRAVEL=ML.MC_TRAVEL,
    YOKE_X=ML.YOKE_X, YOKE_Y=ML.YOKE_Y, YOKE_TOP=ML.YOKE_TOP_Z, YOKE_SLOT_W=ML.YOKE_SLOT_W,
    YOKE_SLOT_TOP=ML.YOKE_SLOT_TOP, YOKE_SLOT_BOT=ML.YOKE_SLOT_BOTTOM,
    SOCKET=ML.YOKE_SOCKET, SOCKET_DEPTH=ML.YOKE_SOCKET_DEPTH, Z_FLOOR_IN=ML.Z_INNER_FLOOR,
    POCKET=ML.WHEEL_POCKET, Z_POCKET=ML.Z_WHEEL_POCKET, Z_UNDER=ML.Z_UNDER,
    WIN=ML.WHEEL_WIN, RAIL_Z=ML.RAIL_WEB_Z, TONGUE_HW=ML.TONGUE_HW,
    SW_MID=ML.SW_MIDDLE, PLUNGER_TOP=ML.PLUNGER_TOP_Z,
    # designer values (WP-G)
    SHOULDER_R=1.5,          # optional shoulder d3.0 (brief) = axial stop on the EC10E rotor
    SHOULDER_X0=32.20,       # 0.22 from the hub face 31.98
    RIM_CH_AX=1.2,           # rim chamfers 1.2 axial x 1.1 radial (42.5 deg from vertical on the bed side: below the
    RIM_CH_RAD=1.1,          # 45 deg limit even after tessellation); finger feel + tilted wheel stays clear of the pocket
    GAP_TOL=0.001,           # numeric tolerance on clearance comparisons (0.2999 reads 0.300)
    N_GROOVE=24,             # grip grooves (= 24 EC10E detents), no tyre
    GROOVE_W=0.8, GROOVE_D=0.4,
    PIN_L=16.0,              # steel pin ISO 2338 2 m6 x 16, flush with AXLE_X1
    PIN_BORE_FLOOR=0.48,     # material left between the blind bore end and the left wheel face
    PIN_BORE_AIR=0.20,       # bore deeper than the pin end
    YOKE_PLUG_FIT=0.05,      # push fit per side in the socket (Y only, see README)
    YOKE_PLUG_CHAMFER=0.3,   # lead-in on the plug bottom edges
    # materials (g/cm3)
    RHO_PLA=1.24, RHO_PETG=1.27, RHO_STEEL=7.85,
    # loads for the axle strength note (N, N.mm)
    F_PLUNGER=1.5, T_DETENT=8.0,
    TOL=1e-6,
)
WORK = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work")
D_W = ML.part_dir("wheel"); D_Y = ML.part_dir("wheel_yoke"); RND = WORK / "renders"
AXIS_PT = (0.0, P["AX_Y"], P["AX_Z"])
PIVOT = (P["PIVOT_X"], P["AX_Y"], P["AX_Z"])
THETA_NOM = P["MC_TRAVEL"] / (P["SW_MID"][0] - P["PIVOT_X"])        # rad, full click at the plunger
LOG = []


def log(s=""):
    print(s); LOG.append(s)


def one(shape, what):
    """single valid solid or raise"""
    sols = shape.solids() if hasattr(shape, "solids") else [shape]
    if len(sols) != 1 or not sols[0].is_valid or sols[0].volume <= 0:
        raise RuntimeError(f"{what}: n_solids={len(sols)} valid={[s.is_valid for s in sols]}")
    return sols[0]


def rot_loc(pt, d, ang):
    from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(*pt), gp_Dir(*d)), ang)
    return Location(t)


def xcyl(r, x0, x1):
    return Solid.make_cylinder(r, x1 - x0, Plane(origin=(x0, P["AX_Y"], P["AX_Z"]), z_dir=(1, 0, 0)))


# ==================================================================================================
# 1. geometry
# ==================================================================================================
def build_wheel_body(with_bore=True):
    y, z, ca, cr = P["AX_Y"], P["AX_Z"], P["RIM_CH_AX"], P["RIM_CH_RAD"]
    x0, x1, R = P["WHEEL_X0"], P["WHEEL_X1"], P["WHEEL_R"]
    prof = [(P["HEX_X1"], 0), (P["HEX_X1"], P["AXLE_R"]), (P["SHOULDER_X0"], P["AXLE_R"]),
            (P["SHOULDER_X0"], P["SHOULDER_R"]), (x0, P["SHOULDER_R"]), (x0, R - cr), (x0 + ca, R),
            (x1 - ca, R), (x1, R - cr), (x1, 0)]
    f = Face(Wire.make_polygon([Vector(px, y, z + pr) for px, pr in prof], close=True))
    body = one(Solid.revolve(f, 360, Axis(AXIS_PT, (1, 0, 0))), "revolve")
    # hex 1.70 A/F, flats top/bottom (vertices on +-Y)
    rc = P["HEX_AF"] / 2 / math.cos(math.radians(30))
    hp = [Vector(P["HEX_X0"], y + rc * math.cos(math.radians(a)), z + rc * math.sin(math.radians(a)))
          for a in range(0, 360, 60)]
    hexs = Solid.extrude(Face(Wire.make_polygon(hp, close=True)), Vector(P["HEX_X1"] - P["HEX_X0"] + 0.05, 0, 0))
    body = one(body + hexs, "hex fuse")
    # 24 grip grooves, a rib (not a groove) on top
    g0 = Solid.make_box(x1 - x0 + 2, P["GROOVE_W"], P["GROOVE_D"] + 1.0).moved(
        Location((x0 - 1, y - P["GROOVE_W"] / 2, z + R - P["GROOVE_D"])))
    step = 360.0 / P["N_GROOVE"]
    grooves = [g0.moved(rot_loc(AXIS_PT, (1, 0, 0), math.radians(step / 2 + k * step)))
               for k in range(P["N_GROOVE"])]
    body = one(body - Compound(grooves), "grooves")
    if with_bore:
        bx0 = x0 + P["PIN_BORE_FLOOR"]
        body = one(body - xcyl(P["AXLE_R"], bx0, x1 + 0.5), "pin bore")
    return body


def build_pin():
    return one(xcyl(P["AXLE_R"], P["AXLE_X1"] - P["PIN_L"], P["AXLE_X1"]), "pin")


def build_wheel_envelope():
    """wheel + axle as one solid (what the lead checks; also the one-piece printed variant)"""
    b = build_wheel_body(with_bore=False)
    return one(b + xcyl(P["AXLE_R"], P["WHEEL_X1"] - 0.5, P["AXLE_X1"]), "wheel+axle")


def build_yoke():
    (yx0, yx1), (yy0, yy1) = P["YOKE_X"], P["YOKE_Y"]
    zb = P["Z_FLOOR_IN"] - P["SOCKET_DEPTH"]
    sx0, sy0, sx1, sy1 = P["SOCKET"]
    f = P["YOKE_PLUG_FIT"]
    plate = ML.box(yx0, yy0, P["Z_FLOOR_IN"] - 0.01, yx1, yy1, P["YOKE_TOP"])
    plug = ML.box(yx0, sy0 + f, zb, yx1, sy1 - f, P["Z_FLOOR_IN"])
    plug = one(plug.chamfer(P["YOKE_PLUG_CHAMFER"], None, plug.edges().group_by(Axis.Z)[0]), "plug chamfer")
    y = one(plate + plug, "yoke fuse")
    w = P["YOKE_SLOT_W"]
    slot = ML.box(yx0 - 1, P["AX_Y"] - w / 2, P["YOKE_SLOT_BOT"], yx1 + 1, P["AX_Y"] + w / 2, P["YOKE_SLOT_TOP"])
    return one(y - slot, "yoke slot")


# ==================================================================================================
# 2. kinematics helpers
# ==================================================================================================
def tilt_loc(theta):
    return rot_loc(PIVOT, (0, 1, 0), theta)


def tilt_mat(theta):
    return trimesh.transformations.rotation_matrix(theta, [0, 1, 0], PIVOT)


def inter_vol(a, b):
    try:
        r = a & b
        return sum(s.volume for s in r.solids()) if r is not None else 0.0
    except Exception as e:                      # noqa
        return float("nan")


def zray(shape, x, y, up=True, z0=None):
    """first surface hit from below (up=True: lowest Z) or from above (up=False: highest Z); with z0: nearest hit above/below z0"""
    h = ML.ray_hits(shape, (x, y, 0.0), (0, 0, 1))
    zs = [q[2] for q in h]
    if z0 is not None:
        zs = [q for q in zs if (q > z0 if up else q < z0)]
        return (min(zs) if up else max(zs)) if zs else None
    return (min(zs) if up else max(zs)) if zs else None


def mesh(shape, tol=0.01):
    return ML.mesh_of(shape, tol)


# ==================================================================================================
# 3. build + validate + export
# ==================================================================================================
body = build_wheel_body(True); pin = build_pin(); wheel = build_wheel_envelope(); yoke = build_yoke()
log(f"# WP-G wheel / axle / yoke - self-check   (built {time.time() - T0:.1f} s)")
log("")
parts = {"wheel": wheel, "wheel_body": body, "axle_pin": pin, "wheel_yoke": yoke}
rho = {"wheel": P["RHO_PLA"], "wheel_body": P["RHO_PLA"], "axle_pin": P["RHO_STEEL"], "wheel_yoke": P["RHO_PETG"]}
checks = []


def chk(cid, what, value, ok):
    checks.append(dict(id=cid, what=what, value=value, pass_=bool(ok)))
    log(f"| {cid} | {what} | {value} | {'PASS' if ok else 'FAIL'} |")


for n, s in parts.items():
    d = D_Y if n == "wheel_yoke" else D_W
    export_step(s, str(d / f"{n}.step"))
    export_stl(s, str(d / f"{n}.stl"), tolerance=0.01, angular_tolerance=0.1)

meshes = {n: trimesh.load(str((D_Y if n == "wheel_yoke" else D_W) / f"{n}.stl")) for n in parts}
log("## Parts (measured)")
log("| part | solids | valid | volume mm3 | mass g | mesh bbox (X,Y,Z) | watertight |")
log("|---|---|---|---|---|---|---|")
for n, s in parts.items():
    m = meshes[n]; b = m.bounds
    log(f"| {n} | {len(s.solids())} | {s.is_valid} | {s.volume:.1f} | {s.volume * rho[n] / 1000:.2f} | "
        f"{b[0][0]:.3f}..{b[1][0]:.3f}, {b[0][1]:.3f}..{b[1][1]:.3f}, {b[0][2]:.3f}..{b[1][2]:.3f} | {m.is_watertight} |")
    chk(f"A1-{n}", f"{n}: one valid solid, vol>0, STL watertight", f"n={len(s.solids())} valid={s.is_valid} "
        f"vol={s.volume:.1f} wt={m.is_watertight}", len(s.solids()) == 1 and s.is_valid and s.volume > 0 and m.is_watertight)
log("")
log("## Gates")
log("| id | what | measured | self-check |")
log("|---|---|---|---|")

# ---- wheel geometry --------------------------------------------------------------------------------
mw = meshes["wheel"]
sec = mw.section(plane_origin=[P["X_CL"], 0, 0], plane_normal=[1, 0, 0])
pts = np.asarray(sec.vertices)
rr = np.hypot(pts[:, 1] - P["AX_Y"], pts[:, 2] - P["AX_Z"])
chk("WG-D", "wheel OD (section X 39.37, rib tips)", f"{2 * rr.max():.3f} (req {2 * P['WHEEL_R']:.2f})",
    abs(2 * rr.max() - 2 * P["WHEEL_R"]) < 0.05)
xs = mw.bounds[:, 0]
wface = [f for f in wheel.faces() if f.geom_type == GeomType.PLANE and abs(f.normal_at().X) > 0.99 and f.area > 50]
wx = sorted(round(f.center().X, 3) for f in wface)
chk("WG-W", "wheel side faces X (planar faces > 50 mm2)", f"{wx} (req {P['WHEEL_X0']:.2f}/{P['WHEEL_X1']:.2f})",
    len(wx) == 2 and abs(wx[0] - P["WHEEL_X0"]) < 0.01 and abs(wx[1] - P["WHEEL_X1"]) < 0.01)
chk("WG-AX", "axle X extent (mesh)", f"{xs[0]:.3f}..{xs[1]:.3f} (req {P['AXLE_X0']}..{P['AXLE_X1']})",
    abs(xs[0] - P["AXLE_X0"]) < 0.01 and abs(xs[1] - P["AXLE_X1"]) < 0.01)
# hex A/F from a section at the middle of the hex
hx = (P["HEX_X0"] + P["HEX_X1"]) / 2
hs = mw.section(plane_origin=[hx, 0, 0], plane_normal=[1, 0, 0])
hp = np.asarray(hs.vertices)[:, 1:]
widths = []
for a in np.radians(np.arange(0, 180, 0.5)):
    pr = hp @ np.array([math.cos(a), math.sin(a)]); widths.append(pr.max() - pr.min())
af, cc = min(widths), max(widths)
hex_area = (3 * math.sqrt(3) / 2) * (af / 2 / math.cos(math.radians(30))) ** 2
chk("WG-HEX", "hex A/F / corner dia at X %.2f" % hx, f"A/F {af:.3f}, corners {cc:.3f} (req A/F {P['HEX_AF']}, rotor hole 1.73..1.78)",
    abs(af - P["HEX_AF"]) < 0.01 and cc < 2.2)
# A10 axle on the middle plunger
ab = zray(wheel, P["SW_MID"][0], P["SW_MID"][1], up=True)
chk("A10a", "axle bottom Z over (50.8,-27.975) - 7.595", f"{ab - P['PLUNGER_TOP']:.4f} (axle bottom {ab:.4f})",
    0.0 <= ab - P["PLUNGER_TOP"] <= 0.10)
ymx = sum(P["YOKE_X"]) / 2
at = zray(wheel, ymx, P["AX_Y"], up=False)
slot_top = zray(yoke, ymx, P["AX_Y"], up=True, z0=P["AX_Z"])
slot_bot = zray(yoke, ymx, P["AX_Y"], up=False, z0=P["AX_Z"])
chk("A10b", "yoke slot top - axle top", f"{slot_top - at:.4f} (slot top {slot_top:.3f}, bottom {slot_bot:.3f}, axle top {at:.3f})",
    0.05 <= slot_top - at <= 0.15)
# slot width measured
sy_ = [q[1] for q in ML.ray_hits(yoke, (ymx, -40.0, P["AX_Z"] - 0.5), (0, 1, 0))]
sy_ = sorted(sy_)
slot_w = sy_[2] - sy_[1]
chk("WG-SLOT", "yoke slot width (ray Y)", f"{slot_w:.3f} (req {P['YOKE_SLOT_W']:.2f}; axle play {(slot_w - 2 * P['AXLE_R']) / 2:.3f}/side)",
    abs(slot_w - P["YOKE_SLOT_W"]) < 0.01)
# middle-click travel: tilt about the hex pivot until the axle touches the slot bottom (bisection, exact BRep)
lo, hi = 0.0, 0.06
for _ in range(30):
    mid = (lo + hi) / 2
    v = inter_vol(pin.moved(tilt_loc(mid)), yoke)
    lo, hi = (lo, mid) if v > 1e-7 else (mid, hi)
th_stop = lo
ab_t = zray(pin.moved(tilt_loc(th_stop)), P["SW_MID"][0], P["SW_MID"][1], up=True)
travel = ab - ab_t
chk("A10c", "plunger travel when the axle lands on the slot bottom (tilt about X %.1f)" % P["PIVOT_X"],
    f"{travel:.3f} (tilt {math.degrees(th_stop):.3f} deg; req 0.6..0.8, nominal 0.70)", 0.6 <= travel <= 0.8)
log(f"|  | tilt check sign: axle bottom at plunger rest {ab:.3f} -> stop {ab_t:.3f} | | |")
# A14 wheel proud
sk = trimesh.load(str(WORK / "02_master" / "out" / "skin.stl"))
loc, _, _ = sk.ray.intersects_location([[P["X_CL"], P["AX_Y"], 80]], [[0, 0, -1]])
skin_z = float(loc[:, 2].max())
wtop = mw.bounds[1][2]
chk("A14", "wheel top Z - skin Z at (39.37,-27.9)", f"{wtop - skin_z:.3f} (top {wtop:.3f}, skin {skin_z:.3f}; req 2.5..4.0)",
    2.5 <= wtop - skin_z <= 4.0)

# ---- clearances --------------------------------------------------------------------------------------
_t("pcb = ML.load_pcb()")
pcb = ML.load_pcb()
comps = ML.pcb_data()["components"]


def pcb_name(s):
    c = s.bounding_box().center()
    for cc_ in comps:
        b = cc_["bbox"]
        if b[0] - 0.2 <= c.X <= b[3] + 0.2 and b[1] - 0.2 <= c.Y <= b[4] + 0.2 and b[2] - 0.2 <= c.Z <= b[5] + 0.2:
            return cc_["name"] + f"@({(b[0] + b[3]) / 2:.1f},{(b[1] + b[4]) / 2:.1f})"
    return f"board/other@({c.X:.1f},{c.Y:.1f},{c.Z:.1f})"


def near(a, b, m=3.0):
    A, B = a.bounding_box(), b.bounding_box()
    return not (A.max.X + m < B.min.X or B.max.X + m < A.min.X or A.max.Y + m < B.min.Y or B.max.Y + m < A.min.Y
                or A.max.Z + m < B.min.Z or B.max.Z + m < A.min.Z)


pcb_solids = pcb.solids()


def pcb_report(shape, tag):
    rows = []
    for s in pcb_solids:
        if not near(shape, s):
            continue
        rows.append((ML.min_dist(shape, s), inter_vol(shape, s), pcb_name(s)))
    rows.sort()
    return rows


def designed(nm):
    return nm.startswith("Alps_EC10E") or "(50.8,-29.8)" in nm      # encoder (hex in rotor) + middle D2F (plunger)


states = {"rest": 0.0, "slot-stop tilt": th_stop, "0.30 drop (translation)": None}
wheel_states = {"rest": wheel, "slot-stop tilt": wheel.moved(tilt_loc(th_stop)),
                "0.30 drop (translation)": wheel.moved(Location((0, 0, -0.30)))}
log("")
log("## PCB (original STEP solids within 3 mm), min distance / intersection volume")
pcb_min = {}; pcb_rows = {}
for st, w in wheel_states.items():
    rows = pcb_rows[st] = pcb_report(w, st)
    log(f"- wheel {st}: " + "; ".join(f"{nm} d={d:.3f} v={v:.4f}" for d, v, nm in rows[:6]))
    nd = [(d, v, nm) for d, v, nm in rows if not designed(nm)]
    dd = [(d, v, nm) for d, v, nm in rows if designed(nm)]
    pcb_min[st] = (nd[0] if nd else None, dd)
rows_y = pcb_report(yoke, "yoke")
log("- yoke: " + "; ".join(f"{nm} d={d:.3f} v={v:.4f}" for d, v, nm in rows_y[:6]))
log("")
d0, v0, n0 = pcb_min["rest"][0]
chk("A5-wheel", "wheel(rest) intersection with every PCB solid", f"max vol {max(v for _, v, _ in pcb_rows['rest']):.5f}",
    all(v < 1e-6 for _, v, _ in pcb_rows["rest"]))
chk("A6-wheel", "wheel min dist to non-contact PCB parts (rest)", f"{d0:.3f} to {n0} (req >= 0.25)", d0 >= 0.25)
d1, v1, n1 = pcb_min["slot-stop tilt"][0]
chk("A13-pcb-tilt", "wheel tilted to slot stop: min dist to non-contact PCB parts", f"{d1:.3f} to {n1} (req >= 0.25 moving)", d1 >= 0.25 and v1 < 1e-6)
enc = [r for r in pcb_min["rest"][1] if r[2].startswith("Alps")]
mid = [r for r in pcb_min["slot-stop tilt"][1] if "(50.8,-29.8)" in r[2]]
log(f"|  | designed contacts: encoder rest d={enc[0][0]:.3f} v={enc[0][1]:.4f}; middle D2F at stop d={mid[0][0] if mid else 'n/a'} "
    f"v={(f"{mid[0][1]:.3f}" if mid else 'n/a')} mm3 (= plunger travel, placeholder plunger is a fixed block) | | |")
dy, vy, ny = rows_y[0]
chk("A5/A6-yoke", "yoke to PCB: min dist / intersection", f"{dy:.3f} to {ny}, vol {vy:.4f}", vy < 1e-6 and dy >= 0.25)

# board slot edges (exact BRep board outline from master)
_t("board = ML.board_sol")
board = ML.board_solid()
for st, w in wheel_states.items():
    db = ML.min_dist(w, board)
    chk(f"A13-slot-{st}", f"wheel to board slot edges ({st})", f"{db:.3f} (req >= 0.3)", db >= 0.3 - P["GAP_TOL"])

# top shell: raw mesh (window cut) + rail-web envelopes (WP-E) as BRep boxes
x0w, y0w, x1w, y1w = P["WIN"]
rails = [ML.box(P["X_CL"] - P["TONGUE_HW"], y0w, P["RAIL_Z"], x0w, y1w, 24.0),
         ML.box(x1w, y0w, P["RAIL_Z"], P["X_CL"] + P["TONGUE_HW"], y1w, 24.0)]
_t("top_m = trimesh.load")
top_m = trimesh.load(str(WORK / "02_master" / "out" / "top_shell_raw.stl"))
bot_m = trimesh.load(str(WORK / "02_master" / "out" / "bottom_shell_raw.stl"))
bot_up = trimesh.intersections.slice_mesh_plane(bot_m, [0, 0, 1], [0, 0, P["Z_FLOOR_IN"] + 0.4], cap=True)
bot_local = one(ML.box(P["POCKET"][0] - 3, P["POCKET"][1] - 6, P["Z_UNDER"], P["POCKET"][2] + 3, P["POCKET"][3] + 6, P["Z_FLOOR_IN"])
                - ML.box(*P["POCKET"][:2], P["Z_POCKET"], *P["POCKET"][2:], P["Z_FLOOR_IN"] + 1), "pocket env")


def mesh_gap(wm, other, zmin=None):
    """min distance wheel-mesh <-> other mesh, both directions, + count of wheel samples inside other"""
    pts = np.vstack([wm.vertices, trimesh.sample.sample_surface_even(wm, 20000, seed=1)[0]])
    if zmin is not None:
        pts = pts[pts[:, 2] > zmin]
    bb = wm.bounds
    ov = other.vertices
    sel = np.all((ov > bb[0] - 2) & (ov < bb[1] + 2), axis=1)
    tc = other.triangles_center
    fsel = np.all((tc > bb[0] - 4) & (tc < bb[1] + 4), axis=1)
    if not fsel.any():
        return 99.0, 0
    sub = other.submesh([np.where(fsel)[0]], append=True)
    pq = trimesh.proximity.ProximityQuery(sub)
    d1 = pq.on_surface(pts)[1].min() if len(pts) else 99
    inside = int(other.contains(pts).sum()) if len(pts) else 0
    d2 = 99.0
    if sel.any():
        d2 = trimesh.proximity.ProximityQuery(wm).on_surface(ov[sel])[1].min()
    return min(d1, d2), inside


for st, w in wheel_states.items():
    wm = mw.copy()
    if st == "slot-stop tilt":
        wm.apply_transform(tilt_mat(th_stop))
    elif st.startswith("0.30"):
        wm.apply_translation([0, 0, -0.30])
    g, ins = mesh_gap(wm, top_m)
    chk(f"A13-top-{st}", f"wheel to top_shell_raw (window) [mesh, +-0.02] ({st})", f"gap {g:.3f}, samples inside {ins}",
        g >= 0.3 - P["GAP_TOL"] and ins == 0)
    dr = min(ML.min_dist(w, r) for r in rails); vr = sum(inter_vol(w, r) for r in rails)
    chk(f"A13-rail-{st}", f"wheel to tongue rail webs X {P['X_CL'] - P['TONGUE_HW']:.2f}..{x0w:.2f}/{x1w:.2f}..{P['X_CL'] + P['TONGUE_HW']:.2f}, Z>={P['RAIL_Z']} ({st})",
        f"{dr:.3f}, vol {vr:.4f} (req >= 0.3)", dr >= 0.3 - P["GAP_TOL"] and vr < 1e-6)
    dp = ML.min_dist(w, bot_local); vp = inter_vol(w, bot_local)
    chk(f"A13-pocket-{st}", f"wheel to bottom floor incl. WHEEL_POCKET rim edges ({st})",
        f"{dp:.3f}, vol {vp:.4f} (req >= 0.3)", dp >= 0.3 - P["GAP_TOL"] and vp < 1e-6)
    zlow = wm.vertices[:, 2].min()
    chk(f"WG-pocketfloor-{st}", f"wheel lowest Z to pocket floor Z {P['Z_POCKET']} ({st})", f"{zlow - P['Z_POCKET']:.3f} (req >= 0.5)",
        zlow - P["Z_POCKET"] >= 0.5 - P["GAP_TOL"])
    g2, ins2 = mesh_gap(wm, bot_up)
    chk(f"A13-bot-{st}", f"wheel to bottom_shell_raw above Z {P['Z_FLOOR_IN'] + 0.4:.1f} (walls/lip) [mesh] ({st})", (f"gap {g2:.3f}" if g2 < 90 else "gap > 4.0 (no shell faces within 4 mm)") + f", inside {ins2}",
        g2 >= 0.3 and ins2 == 0)
    dyk = ML.min_dist(w, yoke); vyk = inter_vol(w, yoke)
    if st == "rest":
        chk("A13-yoke-rest", "wheel (incl. axle) to yoke at rest", f"{dyk:.3f} (axle in slot), vol {vyk:.5f}", vyk < 1e-6)
    else:
        log(f"|  | wheel-yoke {st}: d={dyk:.3f} vol={vyk:.5f} (axle lands on the slot bottom = designed stop) | | |")
dwy = ML.min_dist(body, yoke)
chk("A13-rim-yoke", "wheel body (rim/face) to yoke at rest", f"{dwy:.3f} (req >= 0.3)", dwy >= 0.3 - P["GAP_TOL"])
# yoke vs socket fit + top shell
sx0, sy0, sx1, sy1 = P["SOCKET"]
yb = yoke.bounding_box()
log(f"|  | yoke plug in socket: X gap {yb.min.X - sx0:.3f}/{sx1 - yb.max.X:.3f}, Y gap {yb.min.Y - sy0:.3f}/{sy1 - yb.max.Y:.3f}, "
    f"bottom Z {yb.min.Z:.3f} (socket bottom {P['Z_FLOOR_IN'] - P['SOCKET_DEPTH']:.2f}) | | |")
gy, iy = mesh_gap(meshes["wheel_yoke"], top_m)
chk("A23-yoke-top", "yoke to top_shell_raw (drop path is vertical; yoke top vs rails)", f"mesh gap {gy:.3f}, inside {iy}; "
    f"rail gap {min(ML.min_dist(yoke, r) for r in rails):.3f}", gy >= 0.3 and iy == 0)
# axle end vs middle switch body at the stop
mbody = ML.box(*ML.SW_BODIES["middle"])
dmb = ML.min_dist(pin.moved(tilt_loc(th_stop)), mbody)
chk("WG-MB", "axle (tilted to stop) to middle D2F body box", f"{dmb:.3f} (req >= 0.25)", dmb >= 0.25)

_t("# ---- printability")
# ---- printability ------------------------------------------------------------------------------------
def print_mesh(m, rot_deg):
    pm = m.copy()
    pm.apply_transform(trimesh.transformations.rotation_matrix(math.radians(rot_deg), [0, 1, 0]))
    c = pm.bounds.mean(axis=0)
    pm.apply_translation([-c[0], -c[1], -pm.bounds[0][2]])
    return pm


def overhang(pm, lim_deg=45.0):
    n = pm.face_normals; zc = pm.triangles_center[:, 2]
    bad = (n[:, 2] < -math.cos(math.radians(lim_deg)) - 0.01) & (zc > 0.01)
    if not bad.any():
        return 0.0, 0.0
    span = 0.0
    for zl in np.unique(np.round(zc[bad], 1)):
        tri = pm.triangles[bad & (np.abs(zc - zl) < 0.06)]
        span = max(span, float(np.ptp(tri[:, :, :2].reshape(-1, 2), axis=0).max()))
    return float(pm.area_faces[bad].sum()), span


pw = print_mesh(meshes["wheel_body"], 90.0)     # +90 about Y: +X -> -Z: right face (X 43.12) on the bed, hex up
pw.export(str(D_W / "wheel_print.stl"))
py_ = print_mesh(meshes["wheel_yoke"], -90.0)   # -90 about Y: +X -> +Z: YZ face X 44.10 on the bed
py_.export(str(D_Y / "wheel_yoke_print.stl"))
pe = print_mesh(meshes["wheel"], 90.0)
a_w, s_w = overhang(pw); a_y, s_y = overhang(py_); a_e, s_e = overhang(pe)
chk("A17-wheel", "wheel_body print (axis vertical, right face on bed): overhang >45 deg", f"{a_w:.2f} mm2, span {s_w:.2f} (= pin-bore ceiling bridge; req bridge <= 10)",
    s_w <= 10.0)
chk("A17-yoke", "wheel_yoke print (YZ face on bed): overhang >45 deg", f"{a_y:.2f} mm2", a_y < 0.5)
log(f"|  | one-piece wheel.step printed axis-vertical would need support: overhang {a_e:.1f} mm2 (wheel face over the d2 axle) | | |")
log(f"|  | print footprints: wheel_body {np.ptp(pw.bounds[:, 0]):.2f} x {np.ptp(pw.bounds[:, 1]):.2f} x h {pw.bounds[1][2]:.2f}; "
    f"yoke {np.ptp(py_.bounds[:, 0]):.2f} x {np.ptp(py_.bounds[:, 1]):.2f} x h {py_.bounds[1][2]:.2f} | | |")

# ---- axle strength (why the steel pin) ---------------------------------------------------------------
Zd2 = math.pi * (2 * P["AXLE_R"]) ** 3 / 32
arm = P["SW_MID"][0] - P["WHEEL_X1"]
sig_far = P["F_PLUNGER"] * arm / Zd2
F_hex = P["F_PLUNGER"] * (P["SW_MID"][0] - P["PIVOT_X"]) / (P["X_CL"] - P["PIVOT_X"]) - P["F_PLUNGER"]
sig_neck = F_hex * (P["SHOULDER_X0"] - P["PIVOT_X"]) / Zd2
Zp_hex = 0.2 * af ** 3
tau_hex = P["T_DETENT"] / Zp_hex
log("")
log("## Axle decision (measured hex + beam estimate)")
log(f"- far end d2.0, plunger {P['F_PLUNGER']} N at {arm:.2f} from the wheel face: bending {sig_far:.1f} MPa. Printed axis-vertical "
    f"that is inter-layer tension (PLA ~15-25 MPa static, far less in fatigue) -> too weak; and the wheel face over a d2 axle cannot print without support.")
log(f"- hex stub: reaction at the hex {F_hex:.2f} N, neck d2.0 at {P['SHOULDER_X0'] - P['PIVOT_X']:.2f} from the pivot -> {sig_neck:.1f} MPa; "
    f"detent torque {P['T_DETENT']} N.mm on hex A/F {af:.3f} -> {tau_hex:.1f} MPa shear. Low -> hex stays printed on the wheel (top of the print).")
log(f"- a printed hex SLEEVE on a d2.0 pin is impossible: A/F {af:.2f} < pin d{2 * P['AXLE_R']:.1f}.")
log(f"- DEFAULT: printed wheel_body (hex stub up) + steel pin ISO 2338 2 m6 x {P['PIN_L']:.0f} pressed into a blind d2.0 bore "
    f"(depth {P['WHEEL_X1'] - P['WHEEL_X0'] - P['PIN_BORE_FLOOR']:.2f}, pin engagement {P['WHEEL_X1'] - (P['AXLE_X1'] - P['PIN_L']):.2f}).")

# swept keep-out for WP-E / WP-D (wheel rest + tilt to the slot stop, +0.30), envelope only, not a part
ko = one(xcyl(P["WHEEL_R"] + 0.30, P["WHEEL_X0"] - 0.30, P["WHEEL_X1"] + 0.30)
         + xcyl(P["WHEEL_R"] + 0.30, P["WHEEL_X0"] - 0.30, P["WHEEL_X1"] + 0.30).moved(tilt_loc(th_stop)), "keepout")
export_step(ko, str(D_W / "wheel_keepout_envelope.step"))
kb = ML.mesh_of(ko).bounds
log(f"|  | wheel_keepout_envelope.step (rest + stop tilt, +0.30): X {kb[0][0]:.2f}..{kb[1][0]:.2f}, Y {kb[0][1]:.2f}..{kb[1][1]:.2f}, "
    f"Z {kb[0][2]:.2f}..{kb[1][2]:.2f} | | |")
_t("passed = sum(")
passed = sum(c["pass_"] for c in checks)
log("")
log(f"RESULT: {passed}/{len(checks)} checks PASS   (total {time.time() - T0:.0f} s)")
(D_W / "selfcheck.json").write_text(json.dumps(dict(checks=checks, theta_stop_deg=math.degrees(th_stop), travel=travel,
                                                    hex_af=af, hex_cc=cc, skin_z=skin_z, wheel_top=wtop), indent=1))
(D_W / "selfcheck.log").write_text("\n".join(LOG), encoding="utf-8")

# ==================================================================================================
# 4. section PNGs (matplotlib, nothing clipped)
# ==================================================================================================
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
pcb_m = trimesh.load(str(WORK / "00_pcb" / "pcb.stl"))
layers = [("PCB", pcb_m, "#2e7d32", 0.55), ("top_shell_raw", top_m, "#90a4ae", 0.45), ("bottom_shell_raw", bot_m, "#455a64", 0.45),
          ("wheel_body (PLA)", meshes["wheel_body"], "#ff6f00", 0.9), ("axle_pin (steel)", meshes["axle_pin"], "#d50000", 0.95),
          ("wheel_yoke (PETG)", meshes["wheel_yoke"], "#1565c0", 0.9)]


def section_png(normal, origin, ax_idx, lim, fname, title):
    fig, ax = plt.subplots(figsize=(12, 7.5), dpi=130)
    for nm, m, col, al in layers:
        s = m.section(plane_origin=origin, plane_normal=normal)
        if s is None:
            continue
        for ent in s.discrete:
            p = np.asarray(ent)
            ax.fill(p[:, ax_idx[0]], p[:, ax_idx[1]], color=col, alpha=al, lw=0.6, ec="k")
        ax.plot([], [], color=col, lw=6, label=nm)
    # rail webs + pocket outline (envelopes of WP-E / WP-D)
    if ax_idx[0] == 0:
        for r in rails:
            b = r.bounding_box(); ax.add_patch(plt.Rectangle((b.min.X, b.min.Z), b.size.X, 21.0 - b.min.Z, fill=False, ls="--", ec="#6a1b9a"))
        ax.add_patch(plt.Rectangle((P["POCKET"][0], P["Z_POCKET"]), P["POCKET"][2] - P["POCKET"][0], P["Z_FLOOR_IN"] - P["Z_POCKET"],
                                   fill=False, ls="--", ec="#6a1b9a"))
        ax.plot([], [], color="#6a1b9a", ls="--", label="WP-E rail webs / WP-D wheel pocket (envelopes)")
        ax.plot(P["PIVOT_X"], P["AX_Z"], "k+", ms=14); ax.annotate("tilt pivot", (P["PIVOT_X"], P["AX_Z"] + 0.6))
    ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_title(title); ax.legend(loc="upper right", fontsize=8)
    ax.set_xlabel("XYZ"[ax_idx[0]] + " mm"); ax.set_ylabel("Z mm")
    fig.tight_layout(); fig.savefig(str(RND / fname)); plt.close(fig)


section_png([0, 1, 0], [0, P["AX_Y"], 0], (0, 2), ((18, 62), (-7, 26)), "R02_wheel_section_Y-27.9.png",
            "WP-G section Y -27.9 (axle plane): hex in EC10E, wheel, steel pin on middle D2F, yoke")
section_png([1, 0, 0], [P["X_CL"], 0, 0], (1, 2), ((-50, -5), (-7, 26)), "R02_wheel_section_X39.37.png",
            "WP-G section X 39.37 (wheel mid-plane): window, board slot, pocket")
print(f"sections written ({time.time() - T0:.0f} s)")
