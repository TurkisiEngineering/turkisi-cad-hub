"""RV01 lead review - independent mesh measurements of every DESIGN_SPEC section-5 row on the delivered parts.
Meshes: finest tessellation of each delivered STEP (05_review/mesh from rv01_step.py, or the builder's finer STL).
usage: python rv01_checks.py [group ...]   groups: base bottom top buttons wheel small drop print   -> 05_review/rv01_<group>.json
"""
import sys, json, time
import numpy as np, trimesh
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\05_review")
import master as ML
import rvlib as R
from scipy.spatial import cKDTree

W = R.W; P3 = W / "03_parts"; OUT = W / "05_review"
groups = sys.argv[1:] or ["bottom", "top", "buttons", "wheel", "small", "drop", "print"]
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:6.1f}]", *a, flush=True)


def finest(name):
    cands = [R.MESH / f"{name}.stl", P3 / name / f"{name}.stl"]
    if name in ("wheel", "wheel_body"):
        cands = [R.MESH / f"{name}.stl", P3 / "wheel" / f"{name}.stl"]
    ms = [trimesh.load(str(c), force="mesh") for c in cands if c.exists()]
    return max(ms, key=lambda m: len(m.faces))


NAMES = ["bottom_shell", "top_shell", "button_L", "button_R", "wheel", "wheel_yoke", "dpi_button", "side_btn_fwd", "side_btn_back"]
M = {n: finest(n) for n in NAMES}
for n, m in M.items():
    log(n, len(m.faces), "watertight", m.is_watertight, "bounds", m.bounds.round(3).tolist())
_C = {}


def C(n):
    if n not in _C:
        _C[n] = R.Caster(M[n])
    return _C[n]


G = R.pcb_groups()
PCB = trimesh.util.concatenate(list(G.values()))
SK = trimesh.load(str(R.MESH / "skin.stl"), force="mesh")
SKC = R.Caster(SK)
_S = {}


def S(n, sp=0.2):
    k = (n, sp)
    if k not in _S:
        _S[k] = R.samples(M[n], sp)
    return _S[k]


res = {}


def row(gid, what, value, limit, ok, note=""):
    res[gid] = dict(what=what, measured=value, limit=limit, pass_=ok, note=note)
    log(gid, "|", value, "|", limit, "|", "PASS" if ok is True else ("FAIL" if ok is False else ok), note)


def col_material(c, x, y, z0, z1):
    z = c.vhits(x + 1.3e-5, y + 0.7e-5)
    tot = 0.0
    for i in range(0, len(z) - 1, 2):
        a, b = z[i], z[i + 1]
        tot += max(0.0, min(b, z1) - max(a, z0))
    return tot


def lowest(c, x, y):
    z = c.vhits(x + 1.3e-5, y + 0.7e-5)
    return z[0] if len(z) else None


def grid_rect(x0, y0, x1, y1, st):
    xs = np.arange(x0, x1 + 1e-9, st); ys = np.arange(y0, y1 + 1e-9, st)
    return [(x, y) for x in xs for y in ys]


def in_rrect(x, y, cx, cy, sx, sy, r):
    dx = max(abs(x - cx) - (sx / 2 - r), 0); dy = max(abs(y - cy) - (sy / 2 - r), 0)
    return dx * dx + dy * dy <= r * r


def pcb_gap(pts, exclude=None, groups_=None):
    out = {}
    if exclude is not None:
        pts = pts[~exclude(pts)]
    for g, m in G.items():
        if groups_ and g not in groups_:
            continue
        d, p = R.gap(pts, m, thresh=3.0)
        out[g] = (round(d, 3), None if p is None else p.round(2).tolist())
    return out


def thick_rays(n, sp=0.2, skin_only=True, maxlen=6.0):
    pts, nr = S(n, sp)
    if skin_only:
        cp, d, tid = trimesh.proximity.closest_point(SK, pts) if len(pts) < 60000 else (None, None, None)
        if d is None:
            kd = cKDTree(R.samples(SK, 0.1)[0]); d, _ = kd.query(pts)
        sel = d < 0.04
        pts, nr = pts[sel], nr[sel]
    loc, ri, ti = M[n].ray.intersects_location(pts - nr * 1e-3, -nr, multiple_hits=False)
    t = np.full(len(pts), np.inf)
    dd = np.linalg.norm(loc - (pts[ri] - nr[ri] * 1e-3), axis=1)
    t[ri] = np.where(dd <= maxlen, dd, np.inf)
    return pts, t


def clusters(pts, r=1.5):
    if len(pts) == 0:
        return []
    kd = cKDTree(pts); lab = -np.ones(len(pts), int); k = 0
    for i in range(len(pts)):
        if lab[i] >= 0:
            continue
        st = [i]; lab[i] = k
        while st:
            j = st.pop()
            for q in kd.query_ball_point(pts[j], r):
                if lab[q] < 0:
                    lab[q] = k; st.append(q)
        k += 1
    out = []
    for c in range(k):
        q = pts[lab == c]
        out.append(dict(n=len(q), lo=q.min(0).round(1).tolist(), hi=q.max(0).round(1).tolist()))
    return sorted(out, key=lambda z: -z["n"])[:8]


# ------------------------------------------------------------------ A1
stepj = {}
for n in NAMES + ["wheel_body"]:
    f = R.MESH / f"{n}_step.json"
    if f.exists():
        stepj[n] = json.load(open(f))
if "base" in groups or "bottom" in groups:
    a1 = {n: (j["n_solids"], j["valid"], j["volume"]) for n, j in stepj.items()}
    row("A1", "one valid solid per part (STEP re-import)", a1, "n=1, valid", all(v[0] == 1 and v[1] for v in a1.values()) and len(a1) >= 10)
    wt = {n: bool(m.is_watertight) for n, m in M.items()}
    row("A1m", "meshes watertight", wt, "all", all(wt.values()))
    a5 = {n: (j.get("A5_tested"), j.get("A5_maxvol"), j.get("A5_hits")) for n, j in stepj.items()}
    row("A5", "part x PCB STEP solids, exact boolean (bbox-overlapping solids)", a5, "0 mm3",
        all(v[1] is not None and v[1] < 1e-4 and not v[2] for v in a5.values()))

# ------------------------------------------------------------------ bottom shell
if "bottom" in groups:
    B = M["bottom_shell"]; BC = C("bottom_shell")
    zmin = B.bounds[0, 2]
    row("A2", "underside Z (mesh min) -> floor = under - 0.45", f"under {zmin:.3f} -> floor {zmin-0.45:.3f}", "-5.85 +-0.05", abs(zmin - 0.45 + 5.85) <= 0.05)
    cx, cy = ML.OPT_C
    vol = 0.0
    for (x, y) in grid_rect(cx - 1.95, cy - 2.95, cx + 1.95, cy + 2.95, 0.1):
        vol += col_material(BC, x, y, -5.5, 0.0) * 0.01
    row("A3", "bottom shell material in prism 4.0x6.0 at OPT_C, Z -5.5..0 (0.1 grid columns)", f"{vol:.4f} mm3", "0", vol < 1e-3)
    vol = 0.0
    for (x, y) in grid_rect(cx - 9.75, cy - 11.05, cx + 9.75, cy + 11.05, 0.2):
        if in_rrect(x, y, cx, cy, 19.5, 22.1, 6.95):
            vol += col_material(BC, x, y, -3.49, 0.0) * 0.04
    lp = [lowest(BC, cx + 6, cy)]
    zz = BC.vhits(cx + 6, cy)
    row("A4", "material in lens rrect 19.6x22.2 R7, Z -3.50..0 (0.2 grid, 0.05 inset)", f"{vol:.4f} mm3; pocket floor at (OPT_C+6,0): {zz.round(3).tolist()}", "0, floor -3.50", vol < 1e-3)
    # A6
    bp, bn = S("bottom_shell", 0.2)

    def excl_b(p):
        e = np.zeros(len(p), bool)
        for hx, hy in ML.PCB_HOLES:
            e |= (np.hypot(p[:, 0] - hx, p[:, 1] - hy) < 2.3) & (p[:, 2] > -0.6)
        for x0, y0, x1, y1 in ML.PCB_RIBS:
            e |= (p[:, 0] > x0 - 0.05) & (p[:, 0] < x1 + 0.05) & (p[:, 1] > y0 - 0.05) & (p[:, 1] < y1 + 0.05) & (p[:, 2] > -0.6)
        return e
    g6 = pcb_gap(bp, excl_b)
    lead_floor = []
    row("A6-B", "bottom shell to PCB groups (boss/rib tops excluded); switch/encoder/sensor/header include lead tips", g6,
        ">=1.0 (lead tips >=0.99)", min(v[0] for k, v in g6.items() if k != "board") >= 0.99 and g6["board"][0] >= 0.0,
        "board gap is to the nearest non-contact board point")
    # board gap ignoring contact columns: points of B within the board footprint above Z -0.6
    # A15 walls
    pts, t = thick_rays("bottom_shell", 0.25)
    side = np.abs(R.samples(M["bottom_shell"], 0.25)[1][:0].sum()) if False else None
    zsel = pts[:, 2] > -5.3
    tt = t[zsel]; pp = pts[zsel]
    fin = np.isfinite(tt)
    thin = pp[fin & (tt < 1.6)]
    row("A15-B", "bottom shell skin wall thickness (normal rays from outer skin samples above Z -5.3)",
        dict(n=int(fin.sum()), min=round(float(tt[fin].min()), 3), p1=round(float(np.percentile(tt[fin], 1)), 3), median=round(float(np.median(tt[fin])), 3), n_below_1p6=int(len(thin)), where=clusters(thin)),
        ">=1.6", len(thin) == 0)
    # floor plate thickness from below
    fl = []
    for (x, y) in grid_rect(10, -122, 70, -6, 0.5):
        z = BC.vhits(x + 1.3e-5, y + 0.7e-5)
        if len(z) >= 2 and z[0] < -5.0:
            fl.append((x, y, z[1] - z[0], z[0], z[1]))
    fl = np.array(fl)
    thin_f = fl[fl[:, 2] < 1.6]
    res["floor_plate"] = dict(min=round(float(fl[:, 2].min()), 3), n_below_1p6=len(thin_f),
                              where=clusters(np.c_[thin_f[:, 0], thin_f[:, 1], thin_f[:, 2]], 1.0) if len(thin_f) else [])
    log("floor plate", res["floor_plate"])
    # A18 TS screws from below
    a18 = {}
    for (sx, sy) in ML.TS_SCREWS:
        for dia in (4.4, 4.5):
            v = 0.0
            for (x, y) in grid_rect(sx - dia / 2, sy - dia / 2, sx + dia / 2, sy + dia / 2, 0.05):
                if np.hypot(x - sx, y - sy) <= dia / 2 - 0.01:
                    v += col_material(BC, x, y, -5.6, -3.26) * 0.0025
            a18[f"{sx},{sy} d{dia}"] = round(v, 3)
    row("A18-TS", "material in vertical tool path from below to each TS head seat (Z -5.6..-3.26)", a18, "0 in d4.5", all(v < 1e-3 for k, v in a18.items() if "d4.5" in k),
        "d4.4 counterbore column also listed")
    # A19 PCB pilots + boss tops, TS cbore/through
    a19 = {}
    for (hx, hy) in ML.PCB_HOLES:
        z = BC.vhits(hx + 1e-4, hy + 1e-4)
        zt = BC.vhits(hx + 2.0, hy + 1e-4)
        pil_r = BC.first(np.array([[hx, hy, -2.0]] * 8), np.array([[np.cos(a), np.sin(a), 0] for a in np.linspace(0, 2 * np.pi, 9)[:-1]]), maxlen=3)
        a19[f"PCB {hx},{hy}"] = dict(hits_centre=z.round(3).tolist(), boss_top=float(zt.max().round(3)), pilot_d=round(2 * float(np.min(pil_r)), 3),
                                     depth=round(0 - float(z[z < 0].max()) if len(z[z < 0]) else -1, 3))
    for (sx, sy) in ML.TS_SCREWS:
        z = BC.vhits(sx + 1e-4, sy + 1e-4)
        zr = BC.vhits(sx + 1.8, sy + 1e-4)
        thr = BC.first(np.array([[sx, sy, -1.0]] * 8), np.array([[np.cos(a), np.sin(a), 0] for a in np.linspace(0, 2 * np.pi, 9)[:-1]]), maxlen=4)
        cb = BC.first(np.array([[sx, sy, -4.5]] * 8), np.array([[np.cos(a), np.sin(a), 0] for a in np.linspace(0, 2 * np.pi, 9)[:-1]]), maxlen=4)
        a19[f"TS {sx},{sy}"] = dict(hits_centre=z.round(3).tolist(), hits_r1p8=zr.round(3).tolist(), through_d=round(2 * float(np.min(thr)), 3), cbore_d=round(2 * float(np.min(cb)), 3))
    okp = all(v["depth"] >= 4.5 and abs(v["boss_top"]) < 0.02 for k, v in a19.items() if k.startswith("PCB"))
    row("A19-B", "PCB pilot depth / boss top / TS through + counterbore", a19, "pilot >=4.5, boss top 0", okp)
    # A20 cable
    path = ML.CABLE_PATH
    st = []
    for (x0, y0), (x1, y1) in zip(path[:-1], path[1:]):
        L = np.hypot(x1 - x0, y1 - y0); n = max(int(L / 1.5), 1)
        for k in range(n):
            u = (k + 0.5) / n; st.append((x0 + u * (x1 - x0), y0 + u * (y1 - y0), (x1 - x0) / L, (y1 - y0) / L))
    wid, flo = [], []
    for (x, y, dx, dy) in st:
        z = BC.vhits(x + 1.3e-5, y + 0.7e-5)
        zf = z[(z < -2.95) & (z > -5.0)]
        flo.append(round(float(zf.max()), 3) if len(zf) else None)
        o = np.array([[x, y, -3.6], [x, y, -3.6]]); d = np.array([[-dy, dx, 0], [dy, -dx, 0]])
        r = BC.first(o, d, maxlen=6)
        wid.append(round(float(r.sum()), 3))
    wid = np.array(wid); flo_arr = np.array([f if f is not None else np.nan for f in flo])
    # exit hole
    ang = np.linspace(0, np.pi, 24, endpoint=False)
    ex = ML.CABLE_EXIT
    o = np.array([[ex[0], -5.0, ex[2]]] * 48)
    d = np.vstack([np.c_[np.cos(ang), np.zeros_like(ang), np.sin(ang)], np.c_[-np.cos(ang), np.zeros_like(ang), -np.sin(ang)]])
    r = BC.first(o, d, maxlen=5)
    dia = r[:24] + r[24:]
    clear = BC.first(np.array([[ex[0], -9.8, ex[2]], [ex[0] - 1.6, -9.8, ex[2]], [ex[0] + 1.6, -9.8, ex[2]], [ex[0], -9.8, ex[2] + 1.6], [ex[0], -9.8, ex[2] - 1.6]]),
                     np.array([[0, 1, 0]] * 5), maxlen=7)
    yfront = B.bounds[1, 1]
    row("A20", "cable channel width (Z -3.6, perpendicular rays) / floor / exit hole", dict(
        stations=len(st), width_min=float(np.min(wid)), width_p5=float(np.percentile(wid, 5)), n_width_lt_4=int((wid < 3.99).sum()),
        narrow_at=[(round(st[i][0], 1), round(st[i][1], 1), wid[i]) for i in np.where(wid < 3.99)[0]][:12],
        floor_min=float(np.nanmin(flo_arr)), floor_max=float(np.nanmax(flo_arr)), n_floor_ne=int(np.sum(np.abs(flo_arr + 3.9) > 0.02)),
        floor_off=[(round(st[i][0], 1), round(st[i][1], 1), flo[i]) for i in np.where(~(np.abs(flo_arr + 3.9) <= 0.02))[0]][:12],
        exit_min_dia=round(float(dia.min()), 3), exit_ray_clear_posY=[round(float(v), 2) for v in clear], front_face_Y=round(float(yfront), 3)),
        "w>=4.0, floor -3.90, exit d>=3.8 at X46.5", None)
    # A21 skates
    mask = []
    for (x, y) in grid_rect(8, -124, 71.5, -4, 0.25):
        z0 = lowest(BC, x, y)
        mask.append((x, y, z0 if z0 is not None else np.nan))
    mk = np.array(mask)
    rec = mk[np.abs(mk[:, 2] + 5.05) < 0.02]
    under = mk[np.abs(mk[:, 2] + 5.40) < 0.02]
    recl = clusters(np.c_[rec[:, :2], np.zeros(len(rec))], 0.3)
    # edge distance: underside outline = section at Z -5.3
    sec = B.section(plane_origin=[0, 0, -5.3], plane_normal=[0, 0, 1])
    pl, _ = sec.to_planar() if sec is not None else (None, None)
    outline = None
    try:
        polys = pl.polygons_full
        outline = max(polys, key=lambda q: q.area)
    except Exception as e:
        log("outline err", e)
    edged = {}
    if outline is not None:
        from shapely.geometry import Point
        ext = outline.exterior
        for c in recl:
            lo, hi = c["lo"], c["hi"]
            q = rec[(rec[:, 0] >= lo[0] - 0.11) & (rec[:, 0] <= hi[0] + 0.11) & (rec[:, 1] >= lo[1] - 0.11) & (rec[:, 1] <= hi[1] + 0.11)]
            edged[f"{lo}..{hi}"] = round(min(ext.distance(Point(a, b)) for a, b, _ in q[::3]), 2)
    heads = {}
    for (sx, sy) in ML.TS_SCREWS:
        zs = [lowest(BC, sx + 2.3 * np.cos(a), sy + 2.3 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 16, endpoint=False)]
        heads[f"{sx},{sy}"] = round(float(np.min(zs)), 3)
    row("A21", "skate recesses: ceiling Z -5.05 regions (0.25 grid), edge distance, TS heads under recess",
        dict(recess_regions=recl, edge_dist=edged, head_ring_lowest_Z=heads, depth=round(-5.05 - zmin, 3)),
        "0.35 deep, >=1.5 from edge, heads covered", None)
    row("ZMAX", "bottom shell max Z", round(float(B.bounds[1, 2]), 3), "<=2.7", B.bounds[1, 2] <= 2.701)
    # A25 underside chamfer
    def inset(m, z_lo, z_hi):
        a = []
        for z in (z_lo, z_hi):
            s_ = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]); p_, _ = s_.to_planar()
            a.append(max(p_.polygons_full, key=lambda q: q.area))
        return round((a[1].area - a[0].area) / a[1].exterior.length, 3)
    row("A25-B", "underside bed-edge chamfer: outline inset at Z -5.39 vs -4.9", inset(B, -5.39, -4.9), "~0.3 present", None)
    # lip vs top shell
    T = M["top_shell"]
    lp = bp[bp[:, 2] > 1.02]
    dlip, plip = R.gap(lp, T, thresh=1.0)
    nin, _ = R.penetration(lp, T, C("top_shell"))
    row("LIP", "bottom-shell material above Z 1.02 (lip/tabs) to top_shell", f"min gap {dlip:.3f} at {None if plip is None else plip.round(2).tolist()}, {nin} points inside", ">=0.10 (design 0.15)", dlip >= 0.1 and nin == 0)
    # yoke socket
    s_ = B.section(plane_origin=[0, 0, -3.6], plane_normal=[0, 0, 1]); p_, to3 = s_.to_planar()
    sock = None
    for poly in p_.polygons_full:
        for hole in poly.interiors:
            hb = np.array(hole.coords)
            h3 = trimesh.transform_points(np.c_[hb, np.zeros(len(hb))], to3)
            if (h3[:, 0].min() > 43 and h3[:, 0].max() < 46.5 and h3[:, 1].min() > -33 and h3[:, 1].max() < -22):
                sock = [round(float(v), 3) for v in (h3[:, 0].min(), h3[:, 1].min(), h3[:, 0].max(), h3[:, 1].max())]
    Y_ = M["wheel_yoke"].bounds
    row("YOKE", "yoke socket (B section Z -3.6) vs yoke bbox", dict(socket=sock, yoke=Y_.round(3).tolist(),
        socket_floor=[float(v) for v in BC.vhits(44.7, -27.9).round(3)]), "push fit 0.05-0.10 per side", None)
    # cradles vs lever pins
    for n in ("side_btn_fwd", "side_btn_back"):
        lpp, _ = S(n, 0.1)
        pin = lpp[(np.hypot(lpp[:, 0] - 12.2, lpp[:, 2] + 1.6) < 1.05)]
        d, p = R.gap(pin, B, thresh=1.0)
        nin, _ = R.penetration(lpp, B, BC)
        row(f"CRADLE-{n}", "lever pin to bottom shell (cradle bore) / lever points inside B", f"{d:.3f} at {None if p is None else p.round(2).tolist()}; inside {nin}", "0.15 radial, 0 inside", nin == 0)
    json.dump(res, open(OUT / "rv01_bottom.json", "w"), indent=1, default=str)

# ------------------------------------------------------------------ top shell
if "top" in groups:
    res.clear()
    T = M["top_shell"]; TC = C("top_shell")
    j = stepj.get("top_shell", {})
    dp = j.get("down_planes", [])
    row("A16", "top shell min Z / downward planar faces (STEP)", dict(min_z=round(float(T.bounds[0, 2]), 4), lowest_down_planes=dp[:8]), "min Z 1.00, bottom planar at 1.00",
        abs(T.bounds[0, 2] - 1.0) < 0.002 and (len(dp) > 0 and abs(dp[0][0] - 1.0) < 1e-3))
    tp, tn = S("top_shell", 0.2)
    g6 = pcb_gap(tp)
    row("A6-T", "top shell to PCB groups", g6, ">=1.0", min(v[0] for v in g6.values()) >= 1.0)
    pts, t = thick_rays("top_shell", 0.25)
    fin = np.isfinite(t)
    thin = pts[fin & (t < 1.6)]
    row("A15-T", "top shell skin wall thickness (normal rays)", dict(n=int(fin.sum()), min=round(float(t[fin].min()), 3), p1=round(float(np.percentile(t[fin], 1)), 3),
        median=round(float(np.median(t[fin])), 3), n_below_1p6=len(thin), frac_below=round(len(thin) / fin.sum(), 4), where=clusters(thin)), ">=1.6", len(thin) == 0)
    # A18 insert holes, A19 depth, leaf pilots, pins
    a19 = {}
    rays8 = np.array([[np.cos(a), np.sin(a), 0] for a in np.linspace(0, 2 * np.pi, 9)[:-1]])
    for (sx, sy) in ML.TS_SCREWS:
        z = TC.vhits(sx + 1e-4, sy + 1e-4)
        r = TC.first(np.array([[sx, sy, 3.0]] * 8), rays8, maxlen=4)
        ro = TC.first(np.array([[sx, sy, 3.0]] * 8), rays8, maxlen=8)
        a19[f"insert {sx},{sy}"] = dict(hits=z.round(3).tolist()[:4], hole_d=round(2 * float(r.min()), 3), depth=round(float(z[z > 1.0].min()) - 1.0, 3) if len(z[z > 1.0]) else None)
    for (lx, ly) in (ML.LEAF_SCREW_L, ML.LEAF_SCREW_R):
        z = TC.vhits(lx + 1e-4, ly + 1e-4)
        r = TC.first(np.array([[lx, ly, 22.0]] * 8), rays8, maxlen=3)
        a19[f"leaf pilot {lx},{ly}"] = dict(hits=z.round(3).tolist()[:4], pilot_d=round(2 * float(r.min()), 3))
        for dx in (-ML.LEAF_PIN_DX, ML.LEAF_PIN_DX):
            zp = TC.vhits(lx + dx + 1e-4, ly + 1e-4)
            rp = TC.first(np.array([[lx + dx, ly, 19.5]] * 8), -rays8, maxlen=1.5)
            a19[f"pin {lx+dx},{ly}"] = dict(hits=zp.round(3).tolist()[:3])
    row("A19-T", "insert holes (d, depth from Z 1.00), leaf pilots, pins", a19, "insert d3.2 x >=4.0, leaf pilot >=5", None)
    # A25 rim chamfer
    a = []
    for z in (1.01, 1.6):
        s_ = T.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]); p_, _ = s_.to_planar()
        q = max(p_.polygons_full, key=lambda q: q.area); a.append(q)
    from shapely.geometry import Polygon
    o0, o1 = Polygon(a[0].exterior), Polygon(a[1].exterior)
    row("A25-T", "rim chamfer: outer outline inset at Z 1.01 vs 1.6", round((o1.area - o0.area) / o1.exterior.length, 3), "~0.3 present", None)
    # envelope A24
    B = M["bottom_shell"]
    lo = np.minimum(T.bounds[0], B.bounds[0]); hi = np.maximum(T.bounds[1], B.bounds[1])
    L, Wd, H = hi[1] - lo[1], hi[0] - lo[0], hi[2] - ML.Z_FLOOR
    row("A24", "L x W x H above floor (T u B mesh bounds)", f"{L:.2f} x {Wd:.2f} x {H:.2f}", "118-126 x 62-68 x 38-42", 118 <= L <= 126 and 62 <= Wd <= 68 and 38 <= H <= 42)
    json.dump(res, open(OUT / "rv01_top.json", "w"), indent=1, default=str)

# ------------------------------------------------------------------ buttons
if "buttons" in groups:
    res.clear()
    T = M["top_shell"]; TC = C("top_shell")
    tps = S("top_shell", 0.2)[0]
    ang = -np.arctan(0.8 / 39.87)
    yc, zc = ML.HINGE_PIVOT
    for sd in "LR":
        n = f"button_{sd}"; Bm = M[n]; BCn = C(n)
        sw = ML.SW_MAIN_L if sd == "L" else ML.SW_MAIN_R
        zs = [lowest(BCn, x, y) for (x, y) in grid_rect(sw[0] - 1.45, sw[1] - 0.6, sw[0] + 1.45, sw[1] + 0.6, 0.1)]
        zs = np.array([z for z in zs if z is not None])
        row(f"A7-{sd}", "nub face Z - 7.595 over the plunger box 2.9x1.2", f"{zs.min()-7.595:.3f}..{zs.max()-7.595:.3f}", "0.05..0.30", 0.05 <= zs.min() - 7.595 and zs.max() - 7.595 <= 0.30)
        sp = ML.STOP_PAD_L if sd == "L" else ML.STOP_PAD_R
        zs = [lowest(BCn, x, y) for (x, y) in grid_rect(sp[0] + 0.05, sp[1] + 0.05, sp[2] - 0.05, sp[3] - 0.05, 0.1)]
        zs = np.array([z for z in zs if z is not None])
        row(f"A9-{sd}", "stop post bottom Z - 1.51", f"{zs.min()-1.51:.3f}..{zs.max()-1.51:.3f}", "0.75..0.90", 0.75 <= zs.min() - 1.51 <= 0.90)
        bp, bn = S(n, 0.15)
        keep = bp[:, 1] > -66.9
        d, p = R.gap(bp[keep], T, tps, thresh=1.5)
        nin, _ = R.penetration(bp[keep], T, TC)
        nose = bp[(bp[:, 2] < 8.0) & (bp[:, 1] > -12)]
        dn, pn = R.gap(nose, T, tps, thresh=2.5)
        row(f"A11-{sd}", "button to top_shell at rest (clamp zone Y<-67.3 excluded) / nose split / points inside T",
            f"min {d:.3f} at {None if p is None else p.round(2).tolist()}; nose {dn:.3f}; inside {nin}", "0.40..0.60, nose >=1.30", 0.40 <= d <= 0.60 and dn >= 1.30 and nin == 0)
        # clamp zone contact: leaf top vs pad face
        cz = bp[bp[:, 1] <= -66.9] - [0, 0, 0.02]
        dcz, pcz = R.gap(cz, T, tps, thresh=1.0)
        res[f"clamp-{sd}"] = dict(leaf_to_pad=round(dcz, 3), at=None if pcz is None else pcz.round(2).tolist(), inside=R.penetration(cz, T, TC)[0])
        log("clamp", sd, res[f"clamp-{sd}"])
        # leaf thickness, free zone
        lx = ML.LEAF_X_L if sd == "L" else ML.LEAF_X_R
        lz = [BCn.vhits(x, y).round(3).tolist() for (x, y) in [(lx[0] + 2, -63.4), ((lx[0] + lx[1]) / 2, -63.4), (lx[1] - 2, -61)]]
        res[f"leaf-{sd}"] = dict(z_hits_free_zone=lz, x_extent=[round(float(bp[(bp[:, 1] < -60) & (bp[:, 1] > -67)][:, 0].min()), 3), round(float(bp[(bp[:, 1] < -60) & (bp[:, 1] > -67)][:, 0].max()), 3)])
        log("leaf", sd, res[f"leaf-{sd}"])
        # A6 rest (exclude nub pad zone and stop post)
        def ex(p, sw=sw, sp=sp):
            e = (np.abs(p[:, 0] - sw[0]) < 1.9) & (np.abs(p[:, 1] - sw[1]) < 1.4) & (p[:, 2] < 8.3)
            e |= (p[:, 0] > sp[0] - 0.1) & (p[:, 0] < sp[2] + 0.1) & (p[:, 1] > sp[1] - 0.1) & (p[:, 1] < sp[3] + 0.1) & (p[:, 2] < 2.4)
            return e
        g6 = pcb_gap(bp, ex)
        row(f"A6-{sd}", "button to PCB at rest (nub pad + stop post bottom excluded)", g6, ">=0.25", min(v[0] for v in g6.values()) >= 0.25)
        # A12 pressed
        mv = bp[bp[:, 1] > yc]
        pr = R.rot_x(mv, yc, zc, ang)
        Mp = R.mesh_xf(Bm, lambda v: R.rot_x(v, yc, zc, ang))
        d, p = R.gap(pr, T, tps, thresh=1.5)
        nin, _ = R.penetration(pr, T, TC)
        g6p = pcb_gap(pr, ex)
        nose_tip = R.rot_x(np.array([[0, -4.03, 6.7]]), yc, zc, ang)[0]
        others = {}
        for o in ("wheel", "dpi_button", "side_btn_fwd", "side_btn_back", "bottom_shell", "wheel_yoke", "button_L" if sd == "R" else "button_R"):
            others[o] = round(R.gap(pr, M[o], thresh=3.0)[0], 3)
        row(f"A12-{sd}", "button rotated -atan(0.8/39.87) about HINGE_PIVOT (rigid, leaf behind pivot excluded): vs top_shell / PCB / others",
            dict(top_shell_gap=round(d, 3), top_shell_inside=nin, pcb=g6p, others=others, tip_drop=round(6.7 - nose_tip[2], 3)), "0 interference (designed nub/post contacts excluded)",
            nin == 0 and d > 0 and min(v[0] for v in g6p.values()) > 0 and min(others.values()) > 0)
        # A15 panel
        pts, t = thick_rays(n, 0.2)
        fin = np.isfinite(t); thin = pts[fin & (t < 1.6)]
        row(f"A15-{sd}", "button panel thickness (normal rays from skin samples)", dict(n=int(fin.sum()), min=round(float(t[fin].min()), 3), p1=round(float(np.percentile(t[fin], 1)), 3),
            median=round(float(np.median(t[fin])), 3), n_below_1p6=len(thin), where=clusters(thin)), ">=1.6", len(thin) == 0)
    d, p = R.gap(S("button_L", 0.15)[0], M["button_R"], thresh=5)
    row("A11-LR", "button_L to button_R", round(d, 3), ">=0.40", d >= 0.4)
    json.dump(res, open(OUT / "rv01_buttons.json", "w"), indent=1, default=str)

# ------------------------------------------------------------------ wheel
if "wheel" in groups:
    res.clear()
    Wm = M["wheel"]; WC = C("wheel"); Ym = M["wheel_yoke"]; YC = C("wheel_yoke")
    zs = [lowest(WC, x, y) for (x, y) in grid_rect(50.8 - 0.5, -27.975 - 0.3, 50.8 + 0.5, -27.975 + 0.3, 0.1)]
    zb = float(np.min([z for z in zs if z is not None]))
    yk = YC.vhits(44.7, -27.9); ax = WC.vhits(44.7, -27.9)
    slot_bot = float(yk[1]); slot_top = float(yk[2]); ax_top = float(ax.max()); ax_bot = float(ax.min())
    xfar = float(Ym.bounds[1, 0])
    tan = (ax_bot - (zb - 7.595) * 0 - slot_bot) / (xfar - ML.ENC_PIVOT_X)
    # axle bottom at the yoke far edge drops (xfar-31)*tan
    trav = tan * (50.8 - ML.ENC_PIVOT_X) - (zb - 7.595)
    row("A10", "axle bottom over middle plunger / slot top - axle top / plunger travel at slot-bottom stop",
        dict(axle_bottom_gap=round(zb - 7.595, 4), yoke_hits=yk.round(3).tolist(), slot_top_minus_axle_top=round(slot_top - ax_top, 3), stop_angle_deg=round(np.degrees(np.arctan(tan)), 3), plunger_travel=round(trav, 3)),
        "0..0.10 / 0.05..0.15 / 0.6..0.8", 0 <= zb - 7.595 <= 0.10 and 0.05 <= slot_top - ax_top <= 0.15 and 0.6 <= trav <= 0.8)
    sk = SKC.vhits(39.37, -27.9)
    row("A14", "wheel top Z - skin Z at (39.37,-27.9)", f"top {Wm.bounds[1,2]:.3f}, skin {sk.max():.3f} -> {Wm.bounds[1,2]-sk.max():.3f}", "2.5..4.0", 2.5 <= Wm.bounds[1, 2] - sk.max() <= 4.0)
    wp, wn = S("wheel", 0.12)
    tilt = np.arctan(tan)
    poses = {"rest": wp, "drop0.30": wp - [0, 0, 0.30], "up0.10": wp + [0, 0, 0.10], "tilt_stop": R.rot_y(wp, ML.ENC_PIVOT_X, ML.ENC_AXIS_Z, tilt)}
    out = {}
    for pn, pp in poses.items():
        o = {}
        for tgt in ("top_shell", "bottom_shell", "wheel_yoke"):
            sel = pp if tgt != "wheel_yoke" else pp[(wp[:, 0] < 43.3)]   # axle-in-slot excluded for the yoke
            d, p = R.gap(sel, M[tgt], thresh=2.0)
            nin, pin_ = R.penetration(pp, M[tgt], C(tgt))
            o[tgt] = (round(d, 3), None if p is None else p.round(2).tolist(), nin)
        def exw(p, wp=wp):
            e = wp[:, 0] < 32.3                                    # hex/stub in the encoder (designed)
            e |= (wp[:, 0] > 49.0) & (wp[:, 2] < 8.0)              # axle on the middle plunger (designed)
            return e[: len(p)]
        g = {}
        sel = pp[~exw(pp)]
        for gname in ("board", "switch", "encoder"):
            d, p = R.gap(sel, G[gname], thresh=3.0); g[gname] = (round(d, 3), None if p is None else p.round(2).tolist())
        o["pcb"] = g
        out[pn] = o
        log(pn, o)
    minshell = min(min(out[k]["top_shell"][0], out[k]["bottom_shell"][0]) for k in ("rest", "drop0.30"))
    pen = sum(out[k][t][2] for k in out for t in ("top_shell", "bottom_shell", "wheel_yoke"))
    row("A13", "wheel vs top_shell / bottom_shell / yoke / PCB at rest, dropped 0.30, up 0.10, tilted to the slot stop", out,
        ">=0.3 to shells + board slot, 0 interference", minshell >= 0.3 and out["tilt_stop"]["top_shell"][0] > 0 and pen == 0 and min(out[k]["pcb"]["board"][0] for k in out) >= 0.3)
    # hex
    s_ = Wm.section(plane_origin=[31.05, 0, 0], plane_normal=[1, 0, 0]); p_, _ = s_.to_planar()
    poly = max(p_.polygons_full, key=lambda q: q.area); c = np.array(poly.exterior.coords)
    ws = []
    for a in np.linspace(0, np.pi, 360, endpoint=False):
        pr_ = c @ np.array([np.cos(a), np.sin(a)]); ws.append(pr_.max() - pr_.min())
    row("HEX", "hex section at X 31.05: across flats / corners", f"{min(ws):.3f} / {max(ws):.3f}", "1.70 A/F", abs(min(ws) - 1.70) <= 0.03)
    json.dump(res, open(OUT / "rv01_wheel.json", "w"), indent=1, default=str)

# ------------------------------------------------------------------ small buttons
if "small" in groups:
    res.clear()
    T = M["top_shell"]; TC = C("top_shell"); Bsh = M["bottom_shell"]; BC = C("bottom_shell")
    D = M["dpi_button"]; DC = C("dpi_button")
    zs = [lowest(DC, x, y) for (x, y) in grid_rect(ML.SW_DPI[0] - 0.6, ML.SW_DPI[1] - 1.45, ML.SW_DPI[0] + 0.6, ML.SW_DPI[1] + 1.45, 0.1)]
    zs = np.array([z for z in zs if z is not None])
    row("A8-dpi", "DPI nub face - 7.595 over plunger box", f"{zs.min()-7.595:.3f}..{zs.max()-7.595:.3f}", "0.0..0.30", -0.001 <= zs.min() - 7.595 and zs.max() - 7.595 <= 0.30)
    dp_, _ = S("dpi_button", 0.08)
    o = {}
    for pn, off in (("rest", 0.0), ("pressed0.75", -0.75), ("lifted0.14", 0.14)):
        pp = dp_ + [0, 0, off]
        d, p = R.gap(pp, T, thresh=1.0); nin, _ = R.penetration(pp, T, TC)
        dw, _ = R.gap(pp, M["wheel"], thresh=3.0)
        o[pn] = dict(top_shell=(round(d, 3), None if p is None else p.round(2).tolist(), nin), wheel=round(dw, 3))
    corners = [(ML.DPI_CAP[0] + 0.2, ML.DPI_CAP[1] + 0.2), (ML.DPI_CAP[2] - 0.2, ML.DPI_CAP[3] - 0.2), (ML.SW_DPI[0], ML.SW_DPI[1])]
    fl = [round(float(DC.vhits(x, y).max() - SKC.vhits(x, y).max()), 3) for x, y in corners]
    g6 = pcb_gap(dp_, lambda p: (p[:, 2] < 7.7) & (np.abs(p[:, 0] - ML.SW_DPI[0]) < 1.4) & (np.abs(p[:, 1] - ML.SW_DPI[1]) < 1.9))
    row("DPI", "DPI cap vs top_shell (sleeve/window) rest / pressed 0.75 / lifted to flange stop; flush; PCB", dict(poses=o, cap_minus_skin=fl, pcb=g6),
        "sleeve 0.15, window 0.30, no interference; flush; PCB >=0.25", all(v["top_shell"][2] == 0 for v in o.values()) and min(v[0] for v in g6.values()) >= 0.25)
    for n, key in (("side_btn_fwd", "fwd"), ("side_btn_back", "back")):
        Lm = M[n]; LC = C(n)
        pl = ML.SIDE_BTNS[key]["plunger"]
        zs = [lowest(LC, x, y) for (x, y) in grid_rect(pl[0] - 0.6, pl[1] - 1.45, pl[0] + 0.6, pl[1] + 1.45, 0.1)]
        zs = np.array([z for z in zs if z is not None])
        cols = [(round(x, 2), round(y, 2), lowest(LC, x, y)) for (x, y) in grid_rect(pl[0] - 0.6, pl[1] - 1.45, pl[0] + 0.6, pl[1] + 1.45, 0.1)]
        res[f"A8cols-{key}"] = [c for c in cols if c[2] is None or c[2] > 7.9][:40]
        log("A8 cols >7.9", key, len(res[f"A8cols-{key}"]), res[f"A8cols-{key}"][:12])
        row(f"A8-{key}", "side nub face - 7.595 over plunger box", f"{zs.min()-7.595:.3f}..{zs.max()-7.595:.3f}", "0.0..0.30", -0.001 <= zs.min() - 7.595 and zs.max() - 7.595 <= 0.30)
        lp_, _ = S(n, 0.1)
        px, pz = ML.SIDE_PIVOT
        # stop angle: stop face points (Z 0..1.51, X > 13) reach board edge X 14.478
        sf = lp_[(lp_[:, 2] > 0.0) & (lp_[:, 2] < 1.51)]
        angs = np.radians(np.arange(0, 8.0, 0.01)); a_stop = None
        for a in angs:
            if R.rot_y(sf, px, pz, a)[:, 0].max() >= ML.BOARD_BBOX[0]:
                a_stop = a; break
        nubp = lp_[(np.abs(lp_[:, 0] - pl[0]) < 0.6) & (np.abs(lp_[:, 1] - pl[1]) < 1.45) & (lp_[:, 2] < 7.75)]
        def travel(a):
            q = R.rot_y(nubp, px, pz, a)
            return float(7.695 - q[:, 2].min()) if len(q) else None
        def ex(p, pl=pl):
            e = (np.abs(p[:, 0] - pl[0]) < 2.2) & (np.abs(p[:, 1] - pl[1]) < 1.6) & (p[:, 2] < 7.8)
            return e
        o = {}
        for pn, a in (("rest", 0.0), ("5.2deg", np.radians(5.2)), ("stop", a_stop if a_stop else 0.0)):
            pp = R.rot_y(lp_, px, pz, a)
            oo = {}
            for tgt in ("top_shell", "bottom_shell", "button_L", "wheel"):
                d, p = R.gap(pp, M[tgt], thresh=2.0); nin, _ = R.penetration(pp, M[tgt], C(tgt))
                oo[tgt] = (round(d, 3), None if p is None else p.round(2).tolist(), nin)
            sel = pp[~ex(lp_)]
            if pn == "stop":
                sel = sel[~((lp_[~ex(lp_)][:, 2] > -0.2) & (lp_[~ex(lp_)][:, 2] < 1.7) & (lp_[~ex(lp_)][:, 0] > 13.5))]
            g = {}
            for gname in ("board", "switch", "usb_header"):
                d, p = R.gap(sel, G[gname], thresh=3.0); g[gname] = (round(d, 3), None if p is None else p.round(2).tolist())
            oo["pcb"] = g
            o[pn] = oo
        ok = all(o[k][t][2] == 0 for k in o for t in ("top_shell", "bottom_shell", "button_L", "wheel")) and o["5.2deg"]["top_shell"][0] >= 0.15 \
            and min(o[k]["pcb"][g][0] for k in ("rest", "5.2deg") for g in o[k]["pcb"]) >= 0.25
        row(f"A22-{key}", "lever rest / 5.2 deg / hard stop about SIDE_PIVOT vs top_shell, bottom_shell, button_L, wheel, PCB (nub excluded; stop face excluded at the stop)",
            dict(poses=o, stop_angle_deg=None if a_stop is None else round(np.degrees(a_stop), 2), nub_travel_5p2=round(travel(np.radians(5.2)), 3), nub_travel_stop=None if a_stop is None else round(travel(a_stop), 3)),
            "0 interference, face-notch >=0.15, PCB >=0.25, travel 0.8+-0.05 at stop", ok)
    json.dump(res, open(OUT / "rv01_small.json", "w"), indent=1, default=str)

# ------------------------------------------------------------------ assembly drop
if "drop" in groups:
    res.clear()
    moving = ["top_shell", "button_L", "button_R", "dpi_button"]
    fixed = ["bottom_shell", "wheel", "wheel_yoke", "side_btn_fwd", "side_btn_back"]
    hits = {}
    pcbs, _ = R.samples(PCB, 0.3)
    fixed_pts = {f: S(f, 0.25)[0] for f in fixed}; fixed_pts["pcb"] = pcbs
    for mvn in moving:
        mc = C(mvn)
        for fn, q in fixed_pts.items():
            bad = []
            lo, hi = M[mvn].bounds
            sel = q[(q[:, 0] > lo[0]) & (q[:, 0] < hi[0]) & (q[:, 1] > lo[1]) & (q[:, 1] < hi[1]) & (q[:, 2] > lo[2] - 0.01)]
            for p in sel:
                p = p - [0, 0, 0.02]
                z = mc.vhits(p[0] + 1.3e-5, p[1] + 0.7e-5)
                zz = z[(z < p[2] - 0.01) & (z > p[2] - 15)]
                # material below q within 15: either a crossing in (q-15, q) or q itself inside
                inside = (np.sum(z > p[2]) % 2) == 1
                if len(zz) or inside:
                    bad.append(p)
            hits[f"{mvn} over {fn}"] = (len(bad), clusters(np.array(bad)) if bad else [])
            log("drop", mvn, fn, len(bad))
    # converse: moving samples, fixed material above within 15
    for mvn in moving:
        q = S(mvn, 0.25)[0]
        for fn in fixed:
            fc = C(fn); bad = []
            lo, hi = M[fn].bounds
            sel = q[(q[:, 0] > lo[0]) & (q[:, 0] < hi[0]) & (q[:, 1] > lo[1]) & (q[:, 1] < hi[1]) & (q[:, 2] < hi[2] + 0.01)]
            for p in sel:
                z = fc.vhits(p[0] + 1.3e-5, p[1] + 0.7e-5)
                zz = z[(z > p[2] + 0.01) & (z < p[2] + 15)]
                if len(zz):
                    bad.append(p)
            hits[f"{fn} above {mvn}"] = (len(bad), clusters(np.array(bad)) if bad else [])
            log("drop2", fn, mvn, len(bad))
    row("A23", "vertical drop +15 -> 0 of top_shell (+ pre-mounted buttons, DPI cap) over PCB, bottom_shell, wheel, yoke, levers (sample + vertical-ray sweep, contacts <0.01 ignored)",
        hits, "no collision", all(v[0] == 0 for v in hits.values()))
    # A18 PCB screws from above (top shell + its buttons removed)
    a18 = {}
    for (hx, hy) in ML.PCB_HOLES:
        for f in ["bottom_shell", "wheel", "wheel_yoke", "side_btn_fwd", "side_btn_back"]:
            v = 0.0
            for (x, y) in grid_rect(hx - 2.25, hy - 2.25, hx + 2.25, hy + 2.25, 0.1):
                if np.hypot(x - hx, y - hy) <= 2.24:
                    v += col_material(C(f), x, y, 1.6, 40.0) * 0.01
            if v > 0:
                a18[f"{hx},{hy} {f}"] = round(v, 3)
        pcbv = []
        for gname in ("switch", "encoder", "usb_header", "smd"):
            d = trimesh.proximity.closest_point(G[gname], np.array([[hx, hy, z] for z in np.arange(1.6, 12, 0.5)]))[1]
            pcbv.append((gname, round(float(d.min()) - 0.0, 3)))
        a18[f"{hx},{hy} axis-to-PCB-part"] = pcbv
    row("A18-PCB", "d4.5 path from above to each PCB screw (Z 1.6..40, top shell removed): material from other parts", a18, "0", all(not isinstance(v, float) for v in a18.values()))
    json.dump(res, open(OUT / "rv01_drop.json", "w"), indent=1, default=str)

# ------------------------------------------------------------------ printability
if "print" in groups:
    res.clear()
    PR = {"bottom_shell": P3 / "bottom_shell" / "bottom_shell_print.stl", "top_shell": P3 / "top_shell" / "top_shell_print.stl",
          "button_L": P3 / "button_L" / "button_L_print.stl", "button_R": P3 / "button_R" / "button_R_print.stl",
          "wheel_body": P3 / "wheel" / "wheel_print.stl", "wheel_yoke": P3 / "wheel_yoke" / "wheel_yoke_print.stl",
          "dpi_button": P3 / "dpi_button" / "dpi_button_print.stl", "side_btn_fwd": P3 / "side_btn_fwd" / "side_btn_fwd_print.stl",
          "side_btn_back": P3 / "side_btn_back" / "side_btn_back_print.stl"}
    for n, f in PR.items():
        m = trimesh.load(str(f), force="mesh")
        z0 = m.bounds[0, 2]
        nz = m.face_normals[:, 2]; cz = m.triangles_center[:, 2]; ar = m.area_faces
        bed = (nz < -0.999) & (cz < z0 + 0.01)
        ov = (nz < -np.cos(np.radians(45.5))) & ~bed
        # connected regions of overhang facets
        idx = np.where(ov)[0]
        regs = []
        if len(idx):
            adj = m.face_adjacency
            s = set(idx.tolist())
            e = adj[np.isin(adj[:, 0], idx) & np.isin(adj[:, 1], idx)]
            import networkx as nx
            g = nx.Graph(); g.add_nodes_from(idx.tolist()); g.add_edges_from(e.tolist())
            for comp in nx.connected_components(g):
                cc = np.array(list(comp)); a = float(ar[cc].sum())
                if a < 0.2:
                    continue
                v = m.triangles[cc].reshape(-1, 3)
                lo, hi = v.min(0), v.max(0); ext = hi - lo
                regs.append(dict(area=round(a, 2), z=[round(float(lo[2] - z0), 2), round(float(hi[2] - z0), 2)], span_xy=[round(float(ext[0]), 2), round(float(ext[1]), 2)],
                                 lo=lo.round(1).tolist(), hi=hi.round(1).tolist(), flat=bool(np.all(nz[cc] < -0.99))))
            regs.sort(key=lambda r: -r["area"])
        res[f"PRINT-{n}"] = dict(file=str(f), bed_contact_mm2=round(float(ar[bed].sum()), 2), overhang_total_mm2=round(float(ar[ov].sum()), 2), n_regions=len(regs), regions=regs[:25],
                                 height=round(float(m.bounds[1, 2] - z0), 2), watertight=bool(m.is_watertight))
        log(n, "bed", res[f"PRINT-{n}"]["bed_contact_mm2"], "overhang", res[f"PRINT-{n}"]["overhang_total_mm2"], "regions", len(regs))
        for r in regs[:12]:
            log("   ", r)
    # thin features < 0.8 on small parts (normal rays, all samples)
    for n in ["button_L", "button_R", "wheel", "wheel_yoke", "dpi_button", "side_btn_fwd", "side_btn_back"]:
        pts, nr = S(n, 0.12)
        loc, ri, ti = M[n].ray.intersects_location(pts - nr * 1e-3, -nr, multiple_hits=False)
        t = np.full(len(pts), np.inf); t[ri] = np.linalg.norm(loc - (pts[ri] - nr[ri] * 1e-3), axis=1)
        fin = np.isfinite(t); th = pts[fin & (t < 0.8)]
        res[f"THIN-{n}"] = dict(min=round(float(t[fin].min()), 3), n_below_0p8=len(th), frac=round(len(th) / max(fin.sum(), 1), 4), where=clusters(th, 1.0))
        log("thin", n, res[f"THIN-{n}"])
    json.dump(res, open(OUT / "rv01_print.json", "w"), indent=1, default=str)

log("done")
