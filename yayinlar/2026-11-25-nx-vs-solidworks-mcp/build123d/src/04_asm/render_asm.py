r"""WP-I renders (cadgenbench venv): R03_asm_iso, R03_asm_exploded, R03_asm_sec_wheel, R03_asm_sec_sensor."""
import json
from pathlib import Path
import numpy as np, trimesh, pyvista as pv
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly

ASM = Path(__file__).resolve().parent; MESH = ASM / "mesh"; REN = ASM.parent / "renders"
PSOL = json.load(open(ASM / "pcb_solids.json"))
COL = {"bottom_shell": (0.16, 0.17, 0.19), "top_shell": (0.92, 0.92, 0.95), "button_L": (0.93, 0.33, 0.20),
       "button_R": (0.98, 0.55, 0.15), "wheel_body": (0.20, 0.75, 0.95), "axle_pin": (0.70, 0.72, 0.75),
       "wheel_yoke": (0.98, 0.85, 0.10), "dpi_button": (0.60, 0.30, 0.90), "side_btn_fwd": (0.15, 0.80, 0.40),
       "side_btn_back": (0.10, 0.55, 0.30)}
M = {n: trimesh.load(MESH / f"{n}.stl") for n in COL}
PCB = trimesh.util.concatenate([trimesh.load(MESH / f"pcb_{d['idx']:02d}.stl") for d in PSOL])
EXPL = {"bottom_shell": 0, "pcb": 14, "side_btn_fwd": 22, "side_btn_back": 22, "wheel_yoke": 30, "wheel_body": 30,
        "axle_pin": 30, "dpi_button": 48, "button_L": 62, "button_R": 62, "top_shell": 80}
EXPL_X = {"side_btn_fwd": -14, "side_btn_back": -14, "axle_pin": 16, "wheel_yoke": 8}


def pvm(m):
    f = np.hstack([np.full((len(m.faces), 1), 3), m.faces]).ravel()
    return pv.PolyData(np.asarray(m.vertices), f)


def iso(name, explode=False, hide_top=False):
    p = pv.Plotter(off_screen=True, window_size=(1600, 1200)); p.set_background("white")
    for n, m in M.items():
        if hide_top and n == "top_shell": continue
        mm = m.copy()
        if explode: mm.apply_translation((EXPL_X.get(n, 0), 0, EXPL[n]))
        p.add_mesh(pvm(mm), color=COL[n], smooth_shading=True, specular=0.3,
                   opacity=1.0)
    pm = PCB.copy()
    if explode: pm.apply_translation((0, 0, EXPL["pcb"]))
    p.add_mesh(pvm(pm), color=(0.10, 0.45, 0.20), smooth_shading=False)
    import numpy as _np
    c = _np.array([39.4, -64.0, 14.0 if not explode else 45.0])
    d = _np.array([-1.0, 1.1, 0.9]) if not explode else _np.array([-1.0, 0.75, 0.45])
    p.camera_position = [tuple(c + 300 * d / _np.linalg.norm(d)), tuple(c), (0, 0, 1)]
    p.reset_camera(); p.camera.zoom(1.25 if not explode else 1.15)
    p.enable_anti_aliasing()
    p.screenshot(str(REN / name)); p.close()


def section(name, origin, normal, axes, xlim, ylim, title):
    fig, ax = plt.subplots(figsize=(14, 7.5), dpi=130)
    items = list(M.items()) + [("pcb", PCB)]
    for n, m in items:
        sec = m.section(plane_origin=origin, plane_normal=normal)
        if sec is None: continue
        for ent in sec.discrete:
            P = ent[:, axes]
            c = COL.get(n, (0.10, 0.45, 0.20))
            ax.add_patch(MPoly(P, closed=True, facecolor=c, edgecolor="k", lw=0.4, alpha=0.85))
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    lab = "XYZ"
    ax.set_xlabel(lab[axes[0]] + " mm"); ax.set_ylabel(lab[axes[1]] + " mm"); ax.set_title(title)
    hs = [plt.Rectangle((0, 0), 1, 1, fc=c) for c in list(COL.values()) + [(0.10, 0.45, 0.20)]]
    ax.legend(hs, list(COL) + ["pcb"], loc="upper right", fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(REN / name); plt.close(fig)


iso("R03_asm_iso.png")
iso("R03_asm_iso_open.png", hide_top=True)
iso("R03_asm_exploded.png", explode=True)
section("R03_asm_sec_wheel_Y-27.9.png", (0, -27.9, 0), (0, 1, 0), [0, 2], (4, 75), (-8, 38),
        "Assembly section Y -27.9 (wheel axis): wheel + pin + yoke on the middle D2F, buttons, shells")
section("R03_asm_sec_sensor_Y-57.44.png", (0, -57.44, 0), (0, 1, 0), [0, 2], (4, 75), (-8, 38),
        "Assembly section Y -57.44 (sensor optical centre): lens pocket + optical hole, side lever, hump")
section("R03_asm_sec_X39.37.png", (39.37, 0, 0), (1, 0, 0), [1, 2], (-128, 0), (-8, 38),
        "Assembly section X 39.37 (centreline): wheel, DPI cap, sensor, hump")
print("renders done")
