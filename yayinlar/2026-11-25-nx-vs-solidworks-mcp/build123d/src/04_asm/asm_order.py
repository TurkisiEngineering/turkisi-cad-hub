r"""WP-I step 4 (cadgenbench venv): assembly-order paths + mesh overlap volumes for the zero-gap pairs.
<venv>\python asm_order.py -> asm_order.json"""
import json, math
import numpy as np, trimesh, open3d as o3d
import mesh_checks_lib as L

OUT = {}
M, MP, PCB = L.M, L.MP, L.PCB
PCBall = dict(PCB)

# ---------------------------------------------------------------- overlap volumes (voxel occupancy, 0.02 mm)
def overlap(a, b, h=0.02):
    lo = np.maximum(a.bounds[0], b.bounds[0]); hi = np.minimum(a.bounds[1], b.bounds[1])
    if np.any(hi <= lo): return 0.0, None
    # candidate points: near both surfaces (overlaps of these parts are thin)
    pa = L.samples(a, 200000); pa = pa[np.all((pa >= lo - .3) & (pa <= hi + .3), 1)]
    if len(pa) == 0: return 0.0, None
    db = L.scene([b]).compute_distance(o3d.core.Tensor(pa.astype(np.float32))).numpy()
    pa = pa[db < 0.6]
    if len(pa) == 0: return 0.0, None
    C = 0.4; k = 10; h = C / k                     # coarse cells around the candidates, filled at h 0.04
    cells = np.unique(np.floor(pa / C).astype(np.int64), axis=0)
    off = np.array([(i, j, l) for i in (-1, 0, 1) for j in (-1, 0, 1) for l in (-1, 0, 1)])
    cells = np.unique((cells[:, None, :] + off[None]).reshape(-1, 3), axis=0)
    f = (np.stack(np.meshgrid(*[np.arange(k)] * 3, indexing="ij"), -1).reshape(-1, 3) + 0.5) * h
    G = (cells[:, None, :] * C + f[None]).reshape(-1, 3).astype(np.float32)
    tot = 0.0; pts = []
    for c in range(0, len(G), 4_000_000):
        P = G[c:c + 4_000_000]
        oa = L.scene([a]).compute_occupancy(o3d.core.Tensor(P)).numpy() > 0.5
        if not oa.any(): continue
        P = P[oa]
        ob = L.scene([b]).compute_occupancy(o3d.core.Tensor(P)).numpy() > 0.5
        tot += ob.sum() * h ** 3; pts.append(P[ob])
    P = np.vstack(pts) if pts else np.zeros((0, 3))
    return float(tot), ([P.min(0).round(2).tolist(), P.max(0).round(2).tolist()] if len(P) else None)


ov = {}
for a, b, A, B in [("bottom_shell", "top_shell", M["bottom_shell"], M["top_shell"]),
                   ("bottom_shell", "wheel_yoke", M["bottom_shell"], M["wheel_yoke"]),
                   ("top_shell", "button_L", M["top_shell"], M["button_L"]),
                   ("top_shell", "button_R", M["top_shell"], M["button_R"]),
                   ("wheel_body", "axle_pin", M["wheel_body"], M["axle_pin"]),
                   ("top_shell", "button_L@stop", M["top_shell"], MP["button_L"]),
                   ("top_shell", "button_R@stop", M["top_shell"], MP["button_R"]),
                   ("top_shell", "wheel_body@stop", M["top_shell"], MP["wheel_body"]),
                   ("wheel_yoke", "axle_pin@stop", M["wheel_yoke"], MP["axle_pin"]),
                   ("bottom_shell", "side_btn_fwd", M["bottom_shell"], M["side_btn_fwd"]),
                   ("bottom_shell", "side_btn_back", M["bottom_shell"], M["side_btn_back"]),
                   ("top_shell", "side_btn_fwd@stop", M["top_shell"], MP["side_btn_fwd"]),
                   ("top_shell", "side_btn_back@stop", M["top_shell"], MP["side_btn_back"]),
                   ("top_shell", "dpi_button", M["top_shell"], M["dpi_button"])]:
    v, bb = overlap(A, B); ov[f"{a}|{b}"] = (round(v, 4), bb); print("OV", a, b, round(v, 4), bb, flush=True)
OUT["overlap_mm3"] = ov

# ---------------------------------------------------------------- button into the top shell: L-shaped path
def moved(m, t):
    c = m.copy(); c.apply_translation(t); return c


d, dz = 7.0, 1.05
path = {}
for side in ("button_L", "button_R"):
    B = M[side]; TS = {"top_shell": M["top_shell"]}
    s1 = L.sweep({side: moved(B, (0, -d, -dz))}, TS, (0, 0, 1), 40.0)      # up from below, 7 behind, 1.05 low
    s2 = L.sweep({side: moved(B, (0, 0, -dz))}, TS, (0, 1, 0), d)           # forward 7
    s3 = L.sweep({side: B}, TS, (0, 0, 1), dz)                              # up 1.05 onto the pins
    path[side] = dict(up_from_below_7_rear=L.summarize(s1), slide_forward_7=L.summarize(s2), up_onto_pins=L.summarize(s3))
    print("PATH", side, {k: v["n"] for k, v in path[side].items()}, flush=True)
OUT["button_insert_L_path"] = path

# ---------------------------------------------------------------- side levers: tilted entry into the cradles
cradle = lambda P: ((P[:, 0] - 12.2) ** 2 + (P[:, 2] + 1.6) ** 2) < 1.75 ** 2
lev = {}
for nm in ("side_btn_fwd", "side_btn_back"):
    r = {}
    for k in (0.0, 0.3, 0.6, 1.0):
        h = L.sweep({nm: M[nm]}, {"bottom_shell": M["bottom_shell"], **PCBall}, (-k, 0, -1), 15.0, ignore=cradle)
        r[f"dir(-{k},0,-1)"] = L.summarize(h)
    lev[nm] = r; print("LEV", nm, {k: v["n"] for k, v in r.items()}, flush=True)
OUT["lever_entry"] = lev

# ---------------------------------------------------------------- wheel: on the hex with the PCB in hand, then PCB+wheel lowered
pcb_wheel = {**{k: v for k, v in PCB.items()}, "wheel_body": M["wheel_body"]}
OUT["pcb_plus_wheel_lowered_into_bottom_shell"] = L.summarize(L.sweep(pcb_wheel, {"bottom_shell": M["bottom_shell"]}, (0, 0, -1), 20.0))
OUT["wheel_hex_slide_-X_2.1_vs_pcb_only"] = L.summarize(L.sweep({"wheel_body": M["wheel_body"]},
                                                        {k: v for k, v in PCB.items() if "EC10E" not in k}, (-1, 0, 0), 2.1))
print("WHEEL", OUT["pcb_plus_wheel_lowered_into_bottom_shell"]["n"], OUT["wheel_hex_slide_-X_2.1_vs_pcb_only"]["n"], flush=True)

# ---------------------------------------------------------------- PCB screw heads (M2 pan head d3.5 x 1.3 on the board top) vs parts
heads = {}
for i, (x, y) in enumerate([(16.51, -16.764), (62.23, -16.764), (16.51, -74.422), (62.23, -74.422)]):
    cyl = trimesh.creation.cylinder(radius=1.75, height=1.3, sections=48); cyl.apply_translation((x, y, 1.51 + 0.65))
    tool = trimesh.creation.cylinder(radius=2.25, height=38.0, sections=48); tool.apply_translation((x, y, 2.0 + 19.0))
    row = {}
    for n in ("side_btn_fwd", "side_btn_back", "button_L", "button_R", "wheel_body", "wheel_yoke"):
        if L.bbgap(cyl, M[n]) < 3: row[n + "_rest"] = round(L.mindist(cyl, M[n])[0], 3)
        if n in MP and L.bbgap(cyl, MP[n]) < 3: row[n + "_stop"] = round(L.mindist(cyl, MP[n])[0], 3)
        if L.bbgap(tool, M[n]) < 0.01:
            row[n + "_blocks_driver_d4.5"] = round(overlap(tool, M[n])[0], 3)
    heads[f"PCB_screw_{i}@({x},{y})"] = row; print("HEAD", i, row, flush=True)
OUT["pcb_screw_heads"] = heads
json.dump(OUT, open(L.ASM / "asm_order.json", "w"), indent=1, default=str)
print("done")
