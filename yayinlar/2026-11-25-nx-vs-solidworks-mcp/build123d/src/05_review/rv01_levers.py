"""RV01: side-lever travel in fixed coords (rotated mesh, deepest point over the plunger box), stop angle vs board edge,
button nose thickness / nose split. -> 05_review/rv01_levers.json"""
import sys, json
import numpy as np, trimesh
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\05_review")
import master as ML
import rvlib as R

out = {}
G = R.pcb_groups()
board = G["board"]
for n, key in (("side_btn_fwd", "fwd"), ("side_btn_back", "back")):
    m = R.load(n)
    pl = ML.SIDE_BTNS[key]["plunger"]
    px, pz = ML.SIDE_PIVOT
    res = {}
    for deg in [0.0, 4.8, 5.0, 5.2, 5.3, 5.4, 5.48, 5.6]:
        a = np.radians(deg)
        mr = R.mesh_xf(m, lambda v: R.rot_y(v, px, pz, a))
        c = R.Caster(mr)
        zs = []
        for x in np.arange(pl[0] - 0.6, pl[0] + 0.6001, 0.05):
            for y in np.arange(pl[1] - 1.45, pl[1] + 1.4501, 0.1):
                z = c.vhits(x + 1.3e-5, y + 0.7e-5)
                z = z[(z > 5) & (z < 9)]
                if len(z):
                    zs.append(z.min())
        # board penetration: board edge region points inside the rotated lever
        bp, _ = R.samples(board, 0.1)
        bp = bp[(bp[:, 0] < 15.5) & (np.abs(bp[:, 1] - pl[1]) < 8)]
        ins = c.inside(bp)
        # min x of lever material at Z 0..1.51 that lies over the board (x > 14.478) -> overlap
        sp, _ = R.samples(mr, 0.08)
        band = sp[(sp[:, 2] > 0.02) & (sp[:, 2] < 1.49) & (np.abs(sp[:, 1] - pl[1]) < 8)]
        res[deg] = dict(plunger_depression=round(7.595 - min(zs), 3) if zs else None, nub_drop_total=round(7.695 - min(zs), 3) if zs else None,
                        board_pts_inside=int(ins.sum()), stopface_max_x=round(float(band[:, 0].max()), 3) if len(band) else None)
        print(n, deg, res[deg], flush=True)
    out[n] = res

# buttons: nose thickness and nose split
for sd in "LR":
    b = R.load(f"button_{sd}"); t = trimesh.load(str(R.MESH / "top_shell.stl"))
    bc = R.Caster(b); tc = R.Caster(t)
    x0 = 24.0 if sd == "L" else ML.mirror_x(24.0)
    rows = []
    for y in (-4.5, -5.0, -6.0, -7.0, -8.0, -9.0, -10.0, -12.0):
        zb = bc.vhits(x0, y); zt = tc.vhits(x0, y)
        below = zt[zt < (zb.min() if len(zb) else 99)]
        rows.append(dict(y=y, button_z=zb.round(3).tolist(), top_shell_below_max=round(float(below.max()), 3) if len(below) else None,
                         vertical_split=round(float(zb.min() - below.max()), 3) if len(zb) and len(below) else None))
    out[f"nose_{sd}"] = rows
    print(sd, rows, flush=True)
json.dump(out, open(r"C:\Users\marya\Desktop\Mouse for PCB\work\05_review\rv01_levers.json", "w"), indent=1, default=str)
