"""
check_bottom_shell.py - WP-D self-checks, measured on the DELIVERED bottom_shell.step / .stl (+ PCB STEP and meshes).
Writes check_bottom_shell.json/.log and the section PNGs R02_bottom_shell_sec_*.png.
"""
import sys, json, math, time
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *
import master as ML
import numpy as np
import trimesh
from pathlib import Path

PARAMS = dict(
    probe_step=1.0,         # floor-thickness grid
    comp_samples=400000,    # surface samples on the PCB component meshes
    comp_z_max=4.0,         # only PCB points below this Z can come near the bottom shell (max Z 2.7)
    overhang_nz=-math.cos(math.radians(45.0)) - 0.01,
    bed_tol=0.02,
    lip_band=(1.1, 2.4),
)
P = PARAMS
D = ML.part_dir("bottom_shell")
R = {}
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)


def row(gid, what, value, ok, note=""):
    R[gid] = dict(what=what, value=value, pass_=bool(ok), note=note)
    log(f"{gid:14s} {'PASS' if ok else 'FAIL'}  {what}: {value} {note}")


def lip_exact():
    """Exact BRep rays (master skin / inner = top-shell wall inner face / lip outer face) - the out/*.stl meshes are too coarse for a 0.15 gap."""
    sys.path.insert(0, str(D))
    import build_bottom_shell as BB
    S, I, L = ML.skin(), ML.inner(), BB.offset_body(ML.WALL + ML.LIP_GAP)
    gaps = []
    for y in (-118, -110, -104, -96, -86, -40, -30, -20, -12):
        for z in (1.2, 2.4):
            for dx in (1, -1):
                xs = []
                for b in (I, L):
                    h = [p[0] for p in ML.ray_hits(b, (ML.X_CL, y, z), (dx, 0, 0)) if (p[0] - ML.X_CL) * dx > 0]
                    xs.append(max(h) if dx > 0 else min(h))
                gaps.append((round(abs(xs[0] - xs[1]), 3), y, z, "R" if dx > 0 else "L"))
    for x in (30, 39.37, 50):
        for z in (1.2, 2.4):
            for dy, nm in ((1, "front"), (-1, "rear")):
                ys = []
                for b in (I, L):
                    h = [p[1] for p in ML.ray_hits(b, (x, -60, z), (0, dy, 0)) if (p[1] + 60) * dy > 0]
                    ys.append(max(h) if dy > 0 else min(h))
                gaps.append((round(abs(ys[0] - ys[1]), 3), x, z, nm))
    gaps.sort()
    return gaps


if "--lip" in sys.argv:
    g = lip_exact(); print("lip gap exact min/max", g[0], g[-1], "n", len(g)); sys.exit()

t0 = time.time()
B = import_step(str(D / "bottom_shell.step"))
sols = B.solids()
Bs = sols[0]
m = trimesh.load(str(D / "bottom_shell.stl"))
pq = trimesh.proximity.ProximityQuery(m)
row("A1", "n_solids / valid / volume mm3", f"{len(sols)} / {Bs.is_valid} / {Bs.volume:.1f}", len(sols) == 1 and Bs.is_valid and Bs.volume > 0)
row("mesh", "STL watertight / faces", f"{m.is_watertight} / {len(m.faces)}", m.is_watertight)
mass = Bs.volume * 1.24e-3
log(f"mass PLA 1.24 g/cc: {mass:.1f} g ; PETG 1.27: {Bs.volume * 1.27e-3:.1f} g")
lo, hi = m.bounds
row("envelope", "mesh bounds X/Y/Z", f"X {lo[0]:.2f}..{hi[0]:.2f}  Y {lo[1]:.2f}..{hi[1]:.2f}  Z {lo[2]:.3f}..{hi[2]:.3f}", True)
row("Zmax", "max Z (no material above 2.7)", f"{hi[2]:.3f}", hi[2] <= ML.SIDE_TAB_TOP + 1e-3)


def ray_z(x, y, z_from=-20.0, d=+1):
    loc, _, _ = m.ray.intersects_location([[x, y, z_from]], [[0, 0, d]])
    return sorted(loc[:, 2]) if len(loc) else []


# A2 underside Z outside the recesses (rays from below at points of the plain underside)
und = [ray_z(x, y)[0] for (x, y) in [(39.37, -30.0), (25, -60), (55, -110), (60, -40), (20, -40)]]
zu = float(np.mean(und))
row("A2", "underside Z -> floor Z (underside - 0.45 skate proud)", f"underside {zu:.3f} -> floor {zu - (ML.SKATE_T - ML.SKATE_RECESS):.3f}",
    abs(zu - (ML.SKATE_T - ML.SKATE_RECESS) - ML.Z_FLOOR) <= 0.05)

# A3 / A4 exact booleans
oc = ML.OPT_C
pr = ML.box(oc[0] - 2.0, oc[1] - 3.0, -5.5, oc[0] + 2.0, oc[1] + 3.0, 0.0)
v3 = (Bs & pr); v3 = sum(s.volume for s in v3.solids()) if v3 is not None else 0.0
row("A3", "bottom shell x 4.0x6.0 prism Z -5.5..0 (mm3)", f"{v3:.4f}", v3 < 1e-3)
lp = ML.LENS_POCKET
f = ML.rrect_face_xy(oc[0], oc[1], lp["size_x"], lp["size_y"], lp["r"], ML.Z_LENS_POCKET).faces()[0]
v4 = Bs & Solid.extrude(f, Vector(0, 0, 0 - ML.Z_LENS_POCKET))
v4 = sum(s.volume for s in v4.solids()) if v4 is not None else 0.0
row("A4", "bottom shell x lens rrect 19.6x22.2 R7 Z -3.5..0 (mm3)", f"{v4:.4f}", v4 < 1e-3)
lens_floor = ray_z(oc[0] + 6.0, oc[1], 5.0, -1)
log(f"   lens pocket floor Z at (OPT_C x+6) = {lens_floor[-1] if lens_floor else None}")

# A5 exact: bottom shell x every PCB STEP solid near it
pcb = ML.load_pcb()
bbB = Bs.bounding_box()
vtot, n_test, worst = 0.0, 0, []
for s in pcb.solids():
    bb = s.bounding_box()
    if bb.min.Z > hi[2] or bb.max.X < lo[0] or bb.min.X > hi[0] or bb.max.Y < lo[1] or bb.min.Y > hi[1]:
        continue
    n_test += 1
    r = Bs & s
    v = sum(q.volume for q in r.solids()) if r is not None else 0.0
    if v > 1e-6:
        worst.append((round(v, 4), [round(bb.min.X, 2), round(bb.min.Y, 2), round(bb.min.Z, 2)]))
    vtot += v
row("A5", f"bottom shell x PCB STEP solids ({n_test} tested) mm3", f"{vtot:.5f}", vtot < 1e-3, str(worst[:5]))

# A6 mesh clearance to components (board excluded: designed contact on bosses/ribs) - surface samples
mdir = ML.WORK / "00_pcb" / "mesh"
pts_all = []
for g in ["switch", "encoder", "sensor", "usb_header", "smd"]:
    mm = trimesh.load(str(mdir / f"{g}.stl"))
    sp, _ = trimesh.sample.sample_surface_even(mm, P["comp_samples"] // 5) if len(mm.faces) else (np.zeros((0, 3)), None)
    pp = np.vstack([sp, mm.vertices])
    pp = pp[pp[:, 2] < P["comp_z_max"]]
    pts_all.append((g, pp))
worst6 = []
for g, pp in pts_all:
    if not len(pp):
        continue
    _, dist, _ = pq.on_surface(pp)
    lead = pp[:, 2] < ML.BOARD_Z0
    for sel, lab in ((lead, "lead tips (Z<0)"), (~lead, "bodies (Z>=0)")):
        if sel.any():
            i = np.argmin(np.where(sel, dist, 1e9))
            worst6.append((round(float(dist[i]), 3), g, lab, np.round(pp[i], 2).tolist()))
worst6.sort()
for w in worst6:
    log("   A6 min dist", w)
leads = [w for w in worst6 if "lead" in w[2]]
bodies = [w for w in worst6 if "bodies" in w[2]]
row("A6_bodies", "min dist shell -> PCB component bodies (Z>=0)", f"{bodies[0][0]} ({bodies[0][1]} @ {bodies[0][3]})", bodies[0][0] >= ML.CLR_PCB - 1e-3)
row("A6_leads", "min dist shell -> lead tips under the board", f"{leads[0][0]} ({leads[0][1]} @ {leads[0][3]})", leads[0][0] >= 0.99)
# board: designed contacts at Z 0 (bosses, ribs); report the closest NON-contact points (board edges)
bmesh = trimesh.load(str(mdir / "board.stl"))
bp, _ = trimesh.sample.sample_surface_even(bmesh, 200000)
_, bd, _ = pq.on_surface(bp)
non_contact = bp[:, 2] > 0.05
for hx, hy in ML.PCB_HOLES:
    non_contact &= np.hypot(bp[:, 0] - hx, bp[:, 1] - hy) > ML.PCB_BOSS_OD / 2 + 0.6
for (rx0, ry0, rx1, ry1) in ML.PCB_RIBS:
    non_contact &= ~((bp[:, 0] > rx0 - 0.6) & (bp[:, 0] < rx1 + 0.6) & (bp[:, 1] > ry0 - 0.6) & (bp[:, 1] < ry1 + 0.6))
i = np.argmin(np.where(non_contact, bd, 1e9))
log(f"   board (non-contact faces, Z>0.05) min dist {bd[i]:.3f} @ {np.round(bp[i], 2).tolist()}")
R["board_noncontact_min"] = float(bd[i])

# cradle to board edge (spec: >= 0.6)
cr = []
for nm, sb in ML.SIDE_BTNS.items():
    for yc in (sb["y0"] + 1.8, sb["y1"] - 1.8):
        bpts = np.array([[ML.BOARD_BBOX[0], yc + dy, z] for dy in np.linspace(-1.5, 1.5, 7) for z in np.linspace(0, 1.51, 7)
                         if min(math.hypot(ML.BOARD_BBOX[0] - hx, yc + dy - hy) for hx, hy in ML.PCB_HOLES) > ML.PCB_BOSS_OD / 2 + 0.6])
        _, dd, _ = pq.on_surface(bpts)
        cr.append(float(dd.min()))
row("cradle_board", "C-cradle -> board left edge (min over 4 cradles)", f"{min(cr):.3f}", min(cr) >= 0.6 - 1e-3)

# cradle bore: radial clearance to a d2.0 pin on SIDE_PIVOT (rays from the axis)
px, pz = ML.SIDE_PIVOT
rads = []
for nm, sb in ML.SIDE_BTNS.items():
    for yc in (sb["y0"] + 1.8, sb["y1"] - 1.8):
        for ang in np.linspace(60, 300, 13):        # downward arc (opening is +Z +-45)
            a = math.radians(ang)
            d = [math.sin(a), 0, math.cos(a)]
            loc, _, _ = m.ray.intersects_location([[px, yc, pz]], [d])
            if len(loc):
                rads.append(float(np.min(np.linalg.norm(loc - [px, yc, pz], axis=1))))
row("cradle_bore", "cradle bore dia (2x min radius) / wrap opening +-45", f"{2 * min(rads):.3f} .. {2 * max(rads):.3f}", abs(2 * min(rads) - ML.SIDE_CRADLE_ID) < 0.05)

# wheel envelope (rest and dropped 0.30) and yoke in socket
wc = ML.WHEEL_C
for drop in (0.0, 0.30):
    cyl = Solid.make_cylinder(ML.WHEEL_D / 2, ML.WHEEL_W, Plane(origin=(ML.WHEEL_X[0], wc[1], wc[2] - drop), z_dir=(1, 0, 0)))
    inter = Bs & cyl
    vi = sum(q.volume for q in inter.solids()) if inter is not None else 0.0
    dmin = ML.min_dist(Bs, cyl)
    row(f"A13_wheel_d{drop:.2f}", f"wheel envelope (dropped {drop}) x shell / min gap (A13 >= 0.3, WP-G asks 0.5)", f"{vi:.4f} mm3 / {dmin:.3f}", vi < 1e-3 and dmin >= 0.3)
x0, y0, x1, y1 = ML.YOKE_X[0], ML.YOKE_Y[0], ML.YOKE_X[1], ML.YOKE_Y[1]
yk = ML.box(x0, y0, ML.Z_INNER_FLOOR - ML.YOKE_SOCKET_DEPTH, x1, y1, ML.YOKE_TOP_Z)
vi = Bs & yk; vi = sum(q.volume for q in vi.solids()) if vi is not None else 0.0
sock_floor = ray_z((x0 + x1) / 2, (y0 + y1) / 2, 5.0, -1)
row("yoke_socket", "yoke plate x shell / socket floor Z / fit per side", f"{vi:.4f} / {sock_floor[-1]:.3f} / {ML.min_dist(Bs, yk):.3f}",
    vi < 1e-3 and abs(sock_floor[-1] - (ML.Z_INNER_FLOOR - ML.YOKE_SOCKET_DEPTH)) < 0.02)
yc_ = ((x0 + x1) / 2, (y0 + y1) / 2, -3.6)
sx = [float(np.min(np.linalg.norm(m.ray.intersects_location([yc_], [d])[0] - yc_, axis=1))) for d in ([1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0])]
log(f"   yoke socket measured {sx[0] + sx[1]:.3f} x {sx[2] + sx[3]:.3f} vs yoke {x1 - x0:.2f} x {y1 - y0:.2f} -> {(sx[0] + sx[1] - (x1 - x0)) / 2:.3f} / {(sx[2] + sx[3] - (y1 - y0)) / 2:.3f} per side")
wp_floor = ray_z(ML.X_CL, ML.ENC_AXIS_Y, 5.0, -1)
log(f"   wheel pocket floor Z {wp_floor[-1]:.3f}")

# A18 tool paths
tp = []
for (x, y) in ML.TS_SCREWS:
    for d in (4.5, ML.TS_CBORE[0]):
        c = Solid.make_cylinder(d / 2, ML.TS_CBORE[1] - 0.01 - (-20), Plane(origin=(x, y, -20)))
        v = Bs & c; v = sum(q.volume for q in v.solids()) if v is not None else 0.0
        tp.append((x, y, d, round(v, 3)))
for (x, y) in ML.PCB_HOLES:
    c = Solid.make_cylinder(4.5 / 2, 40 - 0.01, Plane(origin=(x, y, 0.01)))
    v = Bs & c; v = sum(q.volume for q in v.solids()) if v is not None else 0.0
    tp.append((x, y, 4.5, round(v, 3)))
for t in tp:
    log("   A18 path", t)
ts45 = max(t[3] for t in tp[:6:2]); ts44 = max(t[3] for t in tp[1:6:2]); pcbv = max(t[3] for t in tp[6:])
row("A18_pcb", "d4.5 path from above to the 4 PCB screws (Z 0..40), material mm3", f"{pcbv}", pcbv < 1e-3)
row("A18_ts", "TS screws from below: material in d4.4 (cbore) path / in d4.5 path, mm3", f"{ts44} / {ts45}", ts44 < 1e-3,
    "(d4.5 tool > d4.4 cbore: interface conflict, see issues)" if ts45 > 1e-3 else "")

# A19 pilot depth
pd = []
for (x, y) in ML.PCB_HOLES:
    h = ray_z(x, y, 5.0, -1)
    pd.append(round(ML.Z_BOSS_TOP - h[-1], 3))
    # boss top at the OD ring
    ht = ray_z(x + ML.PCB_BOSS_OD / 2 - 0.3, y, 5.0, -1)
    pd[-1] = (pd[-1], round(ht[-1], 3))
row("A19", "PCB pilot depth (from boss top) / boss top Z", str(pd), all(p[0] >= 4.5 and abs(p[1] - ML.Z_BOSS_TOP) < 0.01 for p in pd))
ts = []
for (x, y) in ML.TS_SCREWS:
    hz = ray_z(x + ML.TS_CLEAR_D / 2 + 0.3, y)          # inside the cbore ring -> cbore top
    top = ray_z(x + ML.TS_BOTTOM_BOSS_OD / 2 - 0.3, y, 5.0, -1)
    thr = ray_z(x, y)
    ts.append(dict(cbore_top=round(hz[0], 3), col_top=round(top[-1], 3), through=len(thr) == 0))
row("TS_cols", "TS columns: cbore top Z / column top Z / d2.4 through", str(ts),
    all(abs(t["cbore_top"] - ML.TS_CBORE[1]) < 0.02 and abs(t["col_top"] - ML.Z_PART) < 0.02 and t["through"] for t in ts))

# A20 cable channel
from shapely.geometry import LineString
path = LineString(ML.CABLE_PATH)
widths, floors = [], []
for s in np.linspace(1.0, path.length - 6.0, 80):
    p = np.array(path.interpolate(s).coords[0]); q = np.array(path.interpolate(s + 0.2).coords[0])
    t = (q - p) / np.linalg.norm(q - p); n = np.array([-t[1], t[0]])
    z = ML.Z_CABLE_FLOOR + 0.3
    hits = []
    for sg in (1, -1):
        loc, _, _ = m.ray.intersects_location([[p[0], p[1], z]], [[sg * n[0], sg * n[1], 0]])
        hits.append(float(np.min(np.linalg.norm(loc[:, :2] - p, axis=1))) if len(loc) else 99)
    widths.append((sum(hits), round(p[0], 2), round(p[1], 2)))
    fz = ray_z(p[0], p[1], 0.5, -1)
    if fz:
        floors.append((round(fz[-1], 3), round(p[0], 2), round(p[1], 2)))
widths.sort(); floors.sort()
# relief posts narrow the channel on purpose (zig-zag): exclude stations within 1.2 of a post
posts = [(ML.CABLE_PATH[2][0] + (1.2 if i % 2 == 0 else -1.2), y) for i, y in enumerate(ML.CABLE_RELIEF_Y)]
wclean = [w for w in widths if min(abs(w[2] - b) + (0 if abs(w[1] - ML.CABLE_PATH[2][0]) < 0.5 else 99) for a, b in posts) > 1.1]
log(f"   channel width min (all) {widths[:3]}; floor Z min/max {floors[0]} / {floors[-1]}")
row("A20_width", "channel width min (away from the 3 relief posts)", f"{wclean[0][0]:.3f} @ ({wclean[0][1]}, {wclean[0][2]})", wclean[0][0] >= ML.CABLE_W - 0.01)
fl_ok = [f for f in floors if abs(f[0] - ML.Z_CABLE_FLOOR) < 0.02]
row("A20_floor", "channel floor Z (rays on the centre line, posts excluded)", f"{len(fl_ok)}/{len(floors)} at {ML.Z_CABLE_FLOOR}; others {[f for f in floors if abs(f[0] - ML.Z_CABLE_FLOOR) >= 0.02][:4]}",
    len(fl_ok) >= len(floors) - 6)
ex, ey, ez = ML.CABLE_EXIT
rr = []
for ang in np.linspace(0, 360, 24, endpoint=False):
    a = math.radians(ang)
    loc, _, _ = m.ray.intersects_location([[ex, ey - 1.4, ez]], [[math.cos(a), 0, math.sin(a)]])
    if len(loc):
        rr.append(float(np.min(np.linalg.norm(loc - [ex, ey - 1.4, ez], axis=1))))
loc, _, _ = m.ray.intersects_location([[ex, -9.0, ez]], [[0, 1, 0]])
row("A20_exit", "exit hole dia in the front wall (2x min radius) / clear along +Y", f"{2 * min(rr):.3f} / {'clear' if len(loc) == 0 else 'BLOCKED'}",
    2 * min(rr) >= 3.8 - 0.01 and len(loc) == 0)
lc, _, _ = m.ray.intersects_location([[ex, ey + 1.0, ez + 2.6]], [[0, -1, 0]])
log(f"   exit chamfer: ray at r 2.6 from the axis hits the wall at Y {lc[:, 1].max() if len(lc) else None} (face Y {ey})")

# A21 skates
import shapely.affinity as aff
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
sec = trimesh.load(str(D / "bottom_shell.stl")).section(plane_origin=[0, 0, ML.Z_UNDER + 0.05], plane_normal=[0, 0, 1])
p2, T = sec.to_2D()
und_poly = unary_union([Polygon(q) for q in p2.polygons_full])
und_poly = aff.affine_transform(und_poly, [T[0, 0], T[0, 1], T[1, 0], T[1, 1], T[0, 3], T[1, 3]])
outer = Polygon(max(und_poly.geoms, key=lambda g: g.area).exterior) if und_poly.geom_type != "Polygon" else Polygon(und_poly.exterior)
sk_rows = []
for nm, sk in ML.SKATES.items():
    c = sk["c"]
    if sk["kind"] == "rrect":
        pt = (c[0] + sk["size"][0] / 2 - sk["r"], c[1])
        poly = Point(c).buffer(1).envelope  # placeholder replaced below
        hx, hy = sk["size"][0] / 2 - sk["r"], sk["size"][1] / 2 - sk["r"]
        poly = Polygon([(c[0] - hx, c[1] - hy), (c[0] + hx, c[1] - hy), (c[0] + hx, c[1] + hy), (c[0] - hx, c[1] + hy)]).buffer(sk["r"], quad_segs=16)
        probe = (c[0], c[1] + sk["size"][1] / 2 - 0.5)
    else:
        poly = Point(c).buffer(sk["od"] / 2, quad_segs=32)
        probe = (c[0] + (sk["od"] + sk["id"]) / 4, c[1])
    depth = ray_z(*probe)[0] - zu
    edge = outer.exterior.distance(poly)
    sk_rows.append((nm, round(depth, 3), round(edge, 2)))
cov = []
for (x, y) in ML.TS_SCREWS:
    head = Point(x, y).buffer(ML.TS_CBORE[0] / 2)
    cov.append(any(Polygon([(sk["c"][0] - sk["size"][0] / 2 + 0.0, sk["c"][1] - sk["size"][1] / 2), (sk["c"][0] + sk["size"][0] / 2, sk["c"][1] - sk["size"][1] / 2),
                            (sk["c"][0] + sk["size"][0] / 2, sk["c"][1] + sk["size"][1] / 2), (sk["c"][0] - sk["size"][0] / 2, sk["c"][1] + sk["size"][1] / 2)]).buffer(-0.01).contains(head)
                   for sk in ML.SKATES.values() if sk["kind"] == "rrect"))
row("A21", "skate (name, recess depth, distance to underside edge) / TS heads covered", f"{sk_rows} / {cov}",
    all(abs(r[1] - ML.SKATE_RECESS) < 0.02 and r[2] >= 1.5 for r in sk_rows) and all(cov))

# lip: outer face offset from the skin (= WALL + LIP_GAP 1.95 -> 0.15 inside the top-shell wall)
skin_m = trimesh.load(str(ML.OUT / "skin.stl")) if (ML.OUT / "skin.stl").exists() else ML.mesh_of(ML.skin(), 0.02)
v, _ = trimesh.sample.sample_surface(trimesh.load(str(D / "bottom_shell.stl")), 400000, seed=1)
lipv = v[(v[:, 2] > P["lip_band"][0]) & (v[:, 2] < P["lip_band"][1])]
log(f"   lip band samples {len(lipv)}")
_, dl, _ = trimesh.proximity.ProximityQuery(skin_m).on_surface(lipv)
notch_ok = np.ones(len(lipv), bool)
for sb in ML.SIDE_BTNS.values():
    notch_ok &= ~((lipv[:, 1] > sb["y0"] - 1.5) & (lipv[:, 1] < sb["y1"] + 1.5) & (lipv[:, 0] < 20))
notch_ok &= dl > 1.0      # outer skin tabs (distance 0) are not lip
dlip = float(dl[notch_ok].min()) if notch_ok.any() else float("nan")
log(f"   lip samples used {notch_ok.sum()}, lip outer offset p1/p50 {np.percentile(dl[notch_ok], [1, 50]).round(3).tolist() if notch_ok.any() else None}")
log(f"   (skin-mesh lip offset probe: {dlip})")
ts_m = trimesh.load(str(ML.OUT / "top_shell_raw.stl"))
_, dts, _ = trimesh.proximity.ProximityQuery(ts_m).on_surface(v[v[:, 2] > ML.Z_PART + 0.05])
inside = ts_m.contains(v[(v[:, 2] > ML.Z_PART + 0.05)][::7]).sum() if ts_m.is_watertight else -1
log(f"   lip/tabs -> top_shell_raw MESH (coarse chords): min {dts.min():.3f}, samples inside {inside}")
lg = lip_exact()
row("lip_gap", f"lip outer face -> top-shell wall inner face, exact BRep rays ({len(lg)} probes, sides/front/rear, Z 1.2/2.4)", f"min {lg[0][0]} @ {lg[0][1:]}, max {lg[-1][0]}",
    lg[0][0] >= ML.LIP_GAP - 0.03, "(axis-aligned rays: values > 0.15 are oblique hits on the curved caps, not a larger normal gap)")

# A15 wall thickness: side walls (horizontal rays from outside at Z -4.5..0.5) + floor plate (vertical rays)
wt = []
for y in np.arange(-120, -6, 2.0):
    for z in (-4.5, -3.0, -1.5, 0.0, 0.8):
        for sgn, x0 in ((1, -10.0), (-1, 90.0)):
            loc, _, _ = m.ray.intersects_location([[x0, y, z]], [[sgn, 0, 0]])
            if len(loc) >= 2:
                xs = np.sort(loc[:, 0])[:: sgn]
                wt.append((round(abs(xs[1] - xs[0]), 3), y, z, 'L' if sgn > 0 else 'R'))
for x in np.arange(14, 66, 2.0):
    for z in (-4.5, -2.0, 0.5):
        loc, _, _ = m.ray.intersects_location([[x, 20.0, z]], [[0, -1, 0]])
        if len(loc) >= 2:
            ys = np.sort(loc[:, 1])[::-1]
            wt.append((round(ys[0] - ys[1], 3), x, z, 'front'))
        loc, _, _ = m.ray.intersects_location([[x, -140.0, z]], [[0, 1, 0]])
        if len(loc) >= 2:
            ys = np.sort(loc[:, 1])
            wt.append((round(ys[1] - ys[0], 3), x, z, 'rear'))
wt.sort()
log(f"   side wall samples {len(wt)}, thinnest {wt[:4]}")
ft = []
from shapely.geometry import Point as Pt
for x in np.arange(10.27, 70, P["probe_step"]):
    for y in np.arange(-121.73, -6, P["probe_step"]):
        if not outer.buffer(-2.5).contains(Pt(x, y)):
            continue
        h = ray_z(x, y)
        if len(h) >= 2 and h[0] < ML.Z_UNDER + 0.5 and h[1] <= ML.Z_INNER_FLOOR + 0.01:   # floor plate only
            ft.append((round(h[1] - h[0], 3), round(x, 1), round(y, 1)))
ft.sort()
log(f"   floor plate samples {len(ft)}, thinnest {ft[:6]}")
hist = {}
for t in ft:
    k = round(t[0], 2)
    hist[k] = hist.get(k, 0) + 1
log(f"   floor thickness histogram (<2.4): {sorted([(k, n) for k, n in hist.items() if k < 2.4])}")
row("A15_wall", "min side/front/rear wall thickness (horizontal rays, Z -4.5..0.8)", f"{wt[0][0]} @ {wt[0][1:]}", wt[0][0] >= 1.6)
thin = sorted(set(round(t[0], 2) for t in ft if t[0] < 1.6))
row("A15_floor", "min floor-plate thickness (vertical rays, 1 mm grid); values < 1.6", f"{ft[0][0]} @ {ft[0][1:]}; thin values {thin[:10]}",
    ft[0][0] >= 0.8 - 1e-3, "<1.6 only at brief-defined local floors: pilot bottoms 0.8, opt-hole land 0.8+, yoke socket 1.0, cable over front skate 1.15, wheel pocket 1.3, channel 1.5, lens pocket over ring skate 1.55")

# A17 overhangs (print: underside on the bed, +Z up) - mesh faces facing down steeper than 45 deg, off the bed
fn = m.face_normals; fc = m.triangles_center
down = (fn[:, 2] < P["overhang_nz"]) & (fc[:, 2] > lo[2] + P["bed_tol"])
sub = m.submesh([np.where(down)[0]], append=True) if down.any() else None
ov = []
if sub is not None:
    for comp in sub.split(only_watertight=False):
        import shapely
        tri = [Polygon(t[:, :2]) for t in comp.triangles if Polygon(t[:, :2]).area > 1e-9]
        pg = unary_union(tri).buffer(0.01).buffer(-0.01) if tri else None
        span = 2 * shapely.maximum_inscribed_circle(pg, 0.02).length if pg is not None and not pg.is_empty else 0.0
        ov.append(dict(area=round(comp.area, 2), z=round(float(comp.vertices[:, 2].mean()), 2), min_span=round(span, 2),
                       c=np.round(comp.bounds.mean(axis=0)[:2], 1).tolist()))
ov.sort(key=lambda d: -d["area"])
for o in ov[:20]:
    log("   A17 down-face", o)
bad = [o for o in ov if o["min_span"] > 10.0]
row("A17", "down-facing (>45 deg) patches: total area / count / patches with bridge span (inscribed dia) > 10", f"{sum(o['area'] for o in ov):.1f} mm2 / {len(ov)} / {[(o['c'], o['min_span']) for o in bad]}",
    len(bad) == 0, "others: skate/cbore/exit-hole bridges <= 10, lip ledge 0.2x0.2 staircase (45 deg, Z -0.15..1.0), 0.3 foot chamfer, single sliver mesh triangles")

# section PNGs with the PCB
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
pcbm = trimesh.load(str(ML.PCB_STL))


def draw_sec(ax, mesh, origin, normal, axes, color, alpha=1.0, lw=0.4):
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    if s is None:
        return
    for ent in s.discrete:
        q = ent[:, axes]
        ax.add_patch(MPoly(q, closed=True, fc=color, ec="k", lw=lw, alpha=alpha))


renders = ML.RENDERS
for tag, origin, normal, axes, xl, yl, title in [
    ("X39.37", [ML.X_CL, 0, 0], [1, 0, 0], [1, 2], (-128, 0), (-8, 6), "section X 39.37 (lens pocket, optical hole, wheel pocket, front TS column)"),
    ("Y-73.8", [0, -73.8, 0], [0, 1, 0], [0, 2], (4, 75), (-8, 12), "section Y -73.8 (rear C-cradle, rear PCB bosses, cable at header)"),
    ("Y-16.76", [0, -16.764, 0], [0, 1, 0], [0, 2], (4, 75), (-8, 12), "section Y -16.76 (front PCB bosses, cable under the board corner)"),
]:
    fig, ax = plt.subplots(figsize=(14, 4.2) if tag.startswith("X") else (12, 4.0))
    draw_sec(ax, m, origin, normal, axes, "#2b2b2b")
    draw_sec(ax, pcbm, origin, normal, axes, "#2e8b57", 0.85)
    ax.axhline(ML.Z_FLOOR, color="tab:blue", lw=0.8, ls="--"); ax.text(xl[0] + 1, ML.Z_FLOOR - 0.9, "floor Z -5.85", color="tab:blue", fontsize=8)
    ax.axhline(ML.Z_PART, color="tab:red", lw=0.6, ls=":"); ax.text(xl[0] + 1, ML.Z_PART + 0.2, "parting Z 1.00", color="tab:red", fontsize=8)
    ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal"); ax.grid(alpha=0.25)
    ax.set_title(f"bottom_shell (dark) + PCB (green): {title}", fontsize=10)
    ax.set_xlabel("Y" if tag.startswith("X") else "X"); ax.set_ylabel("Z")
    fig.tight_layout(); fig.savefig(renders / f"R02_bottom_shell_sec_{tag}.png", dpi=150); plt.close(fig)
log(f"sections written; total {time.time() - t0:.0f}s")

(D / "check_bottom_shell.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
(D / "check_bottom_shell.log").write_text("\n".join(LOG))
