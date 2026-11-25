"""
build_bottom_shell.py - WP-D bottom_shell (re-runnable).

Starts from master.bottom_shell_raw() and adds every WP-D feature from master constants only.
Writes 03_parts/bottom_shell/bottom_shell.step/.stl (assembly position, native PCB coords),
bottom_shell_print.stl (underside on the bed, Z 0), bottom_shell_mesh.npz cache for checks.
Run: python build_bottom_shell.py   (then python check_bottom_shell.py)
"""
import sys, time, math
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *
import master as ML
import numpy as np

# ---------------------------------------------------------------------------------------------
# PARAMS (local build choices only; every interface number comes from master)
# ---------------------------------------------------------------------------------------------
PARAMS = dict(
    boss_base_z=-4.0,          # PCB bosses / ribs / TS columns start inside the floor plate (merge)
    pilot_bottom_z=-4.6,       # brief: PCB pilot blind to Z -4.6 (depth 4.6 >= 4.5)
    trench_top_z=-2.0,         # cable trench cutter top (cavity is empty above Z_INNER_FLOOR anyway)
    trench_wall_inset=0.3,     # trench clipped 0.3 inside the cavity outline (no cut into the wall)
    relief_post_d=2.0, relief_post_dx=1.2, relief_post_top=-0.5,
    exit_d=3.8, exit_chamfer=0.8,
    cradle_wall=1.0, cradle_open_half_deg=45.0, cradle_web_bot_z=-3.0, cradle_web_wall_embed=0.5,
    foot_chamfer=0.3,          # elephant-foot chamfer on the underside outer edge
    cut_low_z=-8.0,            # cutters start below the underside
    outline_n=480,             # resampled underside outline points
    wheel_pocket_relief=0.6,
    opt_land=0.8,
    lip_embed_d=1.0,           # lip ledge starts at skin offset 1.0 (inside the 1.8 wall -> solid merge)
    ledge_step=0.2,            # 45 deg staircase (0.2 x 0.2 steps = one layer each) under the lip, wall face 1.8 -> lip inner 2.95              # straight 4.0 x 6.0 land under Z -3.50 before the 45 deg flare (no knife edge at the rim)   # 45 deg relief on the Y-end top edges of the wheel pocket (wheel dropped 0.30 -> gap >= 0.5)
)
P = PARAMS
OUT = ML.part_dir("bottom_shell")
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def one(shape, what):
    """single valid solid after every boolean, else raise."""
    if shape is None:
        raise RuntimeError(f"{what}: boolean returned None")
    sols = shape.solids()
    if len(sols) != 1:
        vols = sorted([round(s.volume, 2) for s in sols], reverse=True)
        raise RuntimeError(f"{what}: {len(sols)} solids {vols[:6]}")
    s = sols[0]
    if not s.is_valid or s.volume <= 0:
        raise RuntimeError(f"{what}: invalid / empty")
    return s


def cyl_z(x, y, d, z0, z1):
    return Solid.make_cylinder(d / 2, z1 - z0, Plane(origin=(x, y, z0), z_dir=(0, 0, 1)))


def poly_face(pts, z):
    return Face(Wire.make_polygon([Vector(float(x), float(y), z) for x, y in pts], close=True))


def shapely_to_solid(poly, z0, z1):
    ext = list(poly.exterior.coords)[:-1]
    s = Solid.extrude(poly_face(ext, z0), Vector(0, 0, z1 - z0))
    for hole in poly.interiors:
        s = s - Solid.extrude(poly_face(list(hole.coords)[:-1], z0 - 0.1), Vector(0, 0, z1 - z0 + 0.2))
    return s


def frustum_rect(cx, cy, sx0, sy0, z0, sx1, sy1, z1):
    w0 = Wire.make_polygon([Vector(cx + a * sx0 / 2, cy + b * sy0 / 2, z0) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))], close=True)
    w1 = Wire.make_polygon([Vector(cx + a * sx1 / 2, cy + b * sy1 / 2, z1) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))], close=True)
    return Solid.make_loft([w0, w1], ruled=True)


def underside_outline(z):
    """shapely polygon of the skin cut at z (mesh section)."""
    import shapely.affinity as aff
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    m = ML.mesh_of(ML.skin(), 0.02)
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    p2, T = sec.to_2D()
    g = unary_union([Polygon(q) for q in p2.polygons_full])
    g = aff.affine_transform(g, [T[0, 0], T[0, 1], T[1, 0], T[1, 1], T[0, 3], T[1, 3]])
    if g.geom_type != "Polygon":
        g = max(g.geoms, key=lambda q: q.area)
    return g


def resample(poly, n):
    from shapely.geometry import LinearRing
    ring = poly.exterior
    if not LinearRing(ring.coords).is_ccw:
        ring = LinearRing(list(ring.coords)[::-1])
    L = ring.length
    pts = np.array([ring.interpolate(L * i / n).coords[0] for i in range(n)])
    return pts


def offset_pts(pts, d):
    """CCW polygon points moved d OUTWARD along the vertex normal."""
    nxt = np.roll(pts, -1, axis=0); prv = np.roll(pts, 1, axis=0)
    t = nxt - prv; t /= np.linalg.norm(t, axis=1)[:, None]
    nrm = np.c_[t[:, 1], -t[:, 0]]
    return pts + d * nrm


def offset_body(d):
    """skin offset inward by d; cached as BREP in this part folder (master's own cache is not written)."""
    from OCP.BRepTools import BRepTools
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shape, TopoDS
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    cdir = OUT / "cache"; cdir.mkdir(exist_ok=True)
    f = cdir / f"off_{d:.3f}_{ML._param_hash()}.brep"
    if f.exists():
        sh = TopoDS_Shape(); BRepTools.Read_s(sh, str(f), BRep_Builder())
        return Solid(TopoDS.Solid_s(TopExp_Explorer(sh, TopAbs_SOLID).Current()))
    s = ML._build_offset_body(d)
    BRepTools.Write_s(s.wrapped, str(f))
    return s


def lip_and_ledge():
    """Joint lip (skin offsets WALL+LIP_GAP .. +LIP_T, Z_PART .. Z_PART+LIP_H) + a 45 deg stepped ledge that ties it
    to the 1.8 wall below Z_PART. (master.bottom_shell_raw() returns NO lip ring - its keep_up boolean comes back empty.)"""
    d_out = ML.WALL + ML.LIP_GAP
    d_in = d_out + ML.LIP_T
    zp = ML.Z_PART
    big = lambda z0, z1: ML.box(-20, -140, z0, 100, 20, z1)
    emb = offset_body(P["lip_embed_d"])
    lip = one((offset_body(d_out) & big(zp, zp + ML.LIP_H)) - offset_body(d_in), "lip ring")
    pieces = [lip]
    n = int(round((d_in - ML.WALL) / P["ledge_step"]))
    for k in range(1, n + 1):
        d_k = min(ML.WALL + k * P["ledge_step"], d_in)
        z_lo = zp - (d_k - ML.WALL)
        pieces.append(one((emb & big(z_lo, zp)) - offset_body(d_k), f"ledge step {k}"))
    L = pieces[0]
    for q in pieces[1:]:
        L = one(L + q, "lip+ledge")
    for nm, sb in ML.SIDE_BTNS.items():          # interrupted at the side notches (the master tabs fill them)
        L = L - ML.box(-20, sb["y0"] - ML.SIDE_GAP - ML.LIP_NOTCH_EXTRA, -10, 30, sb["y1"] + ML.SIDE_GAP + ML.LIP_NOTCH_EXTRA, 20)
    return L


def build():
    t0 = time.time()
    B = one(ML.bottom_shell_raw(), "raw")
    log(f"raw: vol {B.volume:.1f}  ({time.time() - t0:.0f}s)")
    L = lip_and_ledge()
    for q in L.solids():
        B = one(B + q, "add lip")
    log(f"lip + ledge added: {len(L.solids())} pieces, vol {B.volume:.1f}  ({time.time() - t0:.0f}s)")

    # ---- 8a cable trench (cut BEFORE the bosses so the channel side is trimmed by the boss, never the boss)
    from shapely.geometry import LineString
    cav = ML.cavity_section(ML.Z_INNER_FLOOR + 0.05)
    path = ML.CABLE_PATH
    tr = LineString(path).buffer(ML.CABLE_W / 2, quad_segs=12, cap_style="round", join_style="round")
    tr = tr.intersection(cav.buffer(-P["trench_wall_inset"]))
    if tr.geom_type != "Polygon":
        tr = max(tr.geoms, key=lambda q: q.area)
    tr = tr.simplify(0.01)
    trench = shapely_to_solid(tr, ML.Z_CABLE_FLOOR, P["trench_top_z"])
    B = one(B - trench, "trench")

    # ---- 1 PCB bosses, 2 ribs, 3 TS columns, 8c relief posts (unions)
    adds = []
    for (x, y) in ML.PCB_HOLES:
        adds.append(("boss", cyl_z(x, y, ML.PCB_BOSS_OD, P["boss_base_z"], ML.Z_BOSS_TOP)))
    for (x0, y0, x1, y1) in ML.PCB_RIBS:
        adds.append(("rib", ML.box(x0, y0, P["boss_base_z"], x1, y1, ML.Z_BOSS_TOP)))
    for (x, y) in ML.TS_SCREWS:
        adds.append(("ts_col", cyl_z(x, y, ML.TS_BOTTOM_BOSS_OD, P["boss_base_z"], ML.Z_PART)))
    xc_r = ML.CABLE_PATH[2][0]
    for i, y in enumerate(ML.CABLE_RELIEF_Y):
        s = 1 if i % 2 == 0 else -1
        adds.append(("relief_post", cyl_z(xc_r + s * P["relief_post_dx"], y, P["relief_post_d"],
                                          ML.Z_CABLE_FLOOR - 0.3, P["relief_post_top"])))

    # ---- 7 side-lever C-cradles
    px, pz = ML.SIDE_PIVOT
    r_in = ML.SIDE_CRADLE_ID / 2
    r_out = r_in + P["cradle_wall"]
    a = math.radians(P["cradle_open_half_deg"])
    for name, sb in ML.SIDE_BTNS.items():
        for yc in (sb["y0"] + 1.8, sb["y1"] - 1.8):
            ya, yb = yc - ML.SIDE_CRADLE_LEN / 2, yc + ML.SIDE_CRADLE_LEN / 2
            xs = min(ML.skin_x_at(yy, zz, "L") for yy in (ya, yb) for zz in (P["cradle_web_bot_z"], pz))
            ax = Plane(origin=(px, ya, pz), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
            body = Solid.make_cylinder(r_out, ML.SIDE_CRADLE_LEN, ax)
            web = ML.box(xs + ML.WALL - P["cradle_web_wall_embed"], ya, P["cradle_web_bot_z"], px, yb, pz)
            body = one(body + web, "cradle body")
            bore = Solid.make_cylinder(r_in, ML.SIDE_CRADLE_LEN + 2, Plane(origin=(px, ya - 1, pz), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
            h = 6.0
            wedge_pts = [(px, pz), (px - h * math.tan(a), pz + h), (px + h * math.tan(a), pz + h)]
            wedge = Solid.extrude(Face(Wire.make_polygon([Vector(x, ya - 1, z) for x, z in wedge_pts], close=True)),
                                  Vector(0, ML.SIDE_CRADLE_LEN + 2, 0))
            body = one(body - bore - wedge, f"cradle {name} {yc}")
            adds.append((f"cradle_{name}_{yc:.1f}", body))

    for nm, s in adds:
        B = one(B + s, f"add {nm}")
    log(f"adds done: vol {B.volume:.1f}  ({time.time() - t0:.0f}s)")

    # ---- cuts
    cuts = []
    zl = P["cut_low_z"]
    for (x, y) in ML.PCB_HOLES:
        cuts.append(("pcb_pilot", cyl_z(x, y, ML.PCB_BOSS_PILOT, P["pilot_bottom_z"], ML.Z_BOSS_TOP + 1)))
    cb_d, cb_top = ML.TS_CBORE
    for (x, y) in ML.TS_SCREWS:
        cuts.append(("ts_hole", cyl_z(x, y, ML.TS_CLEAR_D, zl, ML.Z_PART + 1)))
        cuts.append(("ts_cbore", cyl_z(x, y, cb_d, zl, cb_top)))
    # 4 lens pocket + optical hole
    lp = ML.LENS_POCKET
    cuts.append(("lens_pocket", Solid.extrude(ML.rrect_face_xy(lp["c"][0], lp["c"][1], lp["size_x"], lp["size_y"], lp["r"], lp["z"]).faces()[0],
                                              Vector(0, 0, ML.Z_PART + 1 - lp["z"]))))
    oh = ML.OPT_HOLE
    zt, zu = oh["z_top"], ML.Z_UNDER
    zf0 = zt - P["opt_land"]
    grow = (zf0 - zu) * math.tan(math.radians(oh["flare_deg"]))
    ext = 0.5  # continue the 45 deg flare below the underside (clean exit)
    cuts.append(("opt_flare", frustum_rect(oh["c"][0], oh["c"][1], oh["size_x"] + 2 * (grow + ext), oh["size_y"] + 2 * (grow + ext),
                                           zu - ext, oh["size_x"], oh["size_y"], zf0)))
    cuts.append(("opt_slot", ML.box(oh["c"][0] - oh["size_x"] / 2, oh["c"][1] - oh["size_y"] / 2, zf0 - 0.01,
                                    oh["c"][0] + oh["size_x"] / 2, oh["c"][1] + oh["size_y"] / 2, zt + 0.5)))
    # 5 wheel pocket, 6 yoke socket
    x0, y0, x1, y1 = ML.WHEEL_POCKET
    cuts.append(("wheel_pocket", ML.box(x0, y0, ML.Z_WHEEL_POCKET, x1, y1, ML.Z_BOSS_TOP)))
    rl = P["wheel_pocket_relief"]; zf = ML.Z_INNER_FLOOR; ext = 0.5
    trap = [(y0, zf - rl), (y1, zf - rl), (y1 + rl + ext, zf + ext), (y0 - rl - ext, zf + ext)]
    cuts.append(("wheel_pocket_relief", Solid.extrude(Face(Wire.make_polygon([Vector(x0, y, z) for y, z in trap], close=True)),
                                                      Vector(x1 - x0, 0, 0))))
    x0, y0, x1, y1 = ML.YOKE_SOCKET
    cuts.append(("yoke_socket", ML.box(x0, y0, ML.Z_INNER_FLOOR - ML.YOKE_SOCKET_DEPTH, x1, y1, ML.Z_BOSS_TOP)))
    # 8b exit hole along +Y with 0.8 x 45 chamfer outside
    ex, ey, ez = ML.CABLE_EXIT
    r = P["exit_d"] / 2
    yf = ML.skin_y_at(ex, ez, "front")
    yin = ML.CABLE_PATH[-2][1]
    cuts.append(("exit_hole", Solid.make_cylinder(r, (yf + 2) - yin, Plane(origin=(ex, yin, ez), z_dir=(0, 1, 0)))))
    c = P["exit_chamfer"]
    cuts.append(("exit_chamfer", Solid.make_cone(r, r + c + 1.0, c + 1.0, Plane(origin=(ex, yf - c, ez), z_dir=(0, 1, 0)))))
    # 9 skate recesses
    for nm, sk in ML.SKATES.items():
        zr0, zr1 = zl, ML.Z_UNDER + ML.SKATE_RECESS
        if sk["kind"] == "rrect":
            f = ML.rrect_face_xy(sk["c"][0], sk["c"][1], sk["size"][0], sk["size"][1], sk["r"], zr0).faces()[0]
            cuts.append((f"skate_{nm}", Solid.extrude(f, Vector(0, 0, zr1 - zr0))))
        else:
            ring = cyl_z(sk["c"][0], sk["c"][1], sk["od"], zr0, zr1) - cyl_z(sk["c"][0], sk["c"][1], sk["id"], zr0 - 1, zr1 + 1)
            cuts.append((f"skate_{nm}", one(ring, "ring")))
    # 10 elephant-foot chamfer on the underside outer edge: cutter = slab - 45 deg frustum of the outline
    ol = underside_outline(ML.Z_UNDER + 0.01)
    pts = resample(ol, P["outline_n"])
    fc = P["foot_chamfer"]
    zb, ztop = ML.Z_UNDER - 0.2, ML.Z_UNDER + fc + 0.1          # frustum runs 45 deg: inset fc+0.2 at zb, outset 0.1 at ztop
    wb = Wire.make_polygon([Vector(float(x), float(y), zb) for x, y in offset_pts(pts, -(fc + 0.2))], close=True)
    wt = Wire.make_polygon([Vector(float(x), float(y), ztop) for x, y in offset_pts(pts, 0.1)], close=True)
    fr = Solid.make_loft([wb, wt], ruled=True)
    slab = ML.box(-20, -140, zl, 100, 20, ztop)
    cuts.append(("foot_chamfer", one(slab - fr, "chamfer cutter")))

    for nm, s in cuts:
        B = one(B - s, f"cut {nm}")
    log(f"cuts done: vol {B.volume:.1f}  ({time.time() - t0:.0f}s)")
    log(f"exit: front face Y at (X {ex}, Z {ez}) = {yf:.3f}")
    return B


if __name__ == "__main__":
    t0 = time.time()
    B = build()
    chk = ML.check_part(B, "bottom_shell")
    log("check_part:", chk)
    ML.export_part(B, "bottom_shell")
    # print-oriented STL: underside on the bed (no rotation, translate min Z -> 0)
    import trimesh
    m = trimesh.load(str(OUT / "bottom_shell.stl"))
    log(f"mesh: watertight {m.is_watertight}, bounds {np.round(m.bounds, 3).tolist()}")
    mp = m.copy(); mp.apply_translation([0, 0, -m.bounds[0, 2]])
    mp.export(str(OUT / "bottom_shell_print.stl"))
    log(f"print STL: underside on Z 0, bounds {np.round(mp.bounds, 3).tolist()}")
    log(f"build total {time.time() - t0:.0f}s")
    (OUT / "build_bottom_shell.log").write_text("\n".join(LOG))
