"""
render_small_buttons.py - WP-H renders.
  sections (system python: trimesh + matplotlib):  python render_small_buttons.py sec
  iso (pyvista venv):  C:\\Users\\marya\\.venvs\\cadgenbench\\Scripts\\python.exe render_small_buttons.py iso
Outputs work/renders/R04_fix_WP-H_*.png
"""
import sys, math
from pathlib import Path
import numpy as np

WORK = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work")
PARTS = WORK / "03_parts"
REN = WORK / "renders"
PCB = WORK / "00_pcb" / "pcb.stl"
OUT = WORK / "02_master" / "out"
PARTS_LIST = ["dpi_button", "side_btn_fwd", "side_btn_back"]
COL = {"dpi_button": "#ffb000", "side_btn_fwd": "#00d0ff", "side_btn_back": "#ff4fa0"}
PIVOT = (12.2, -1.6)
TH_STOP = 5.476   # deg, from checks_side_btn_*.json (theta_stop_deg)


def sec():
    import trimesh, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MP

    def draw(ax, mesh, origin, normal, axes_idx, color, fill=True, lw=1.0, ls="-", alpha=0.85, label=None):
        s = mesh.section(plane_origin=origin, plane_normal=normal)
        if s is None:
            return
        first = True
        for ent in s.discrete:
            p = ent[:, axes_idx]
            if fill:
                ax.add_patch(MP(p, closed=True, fc=color, ec="k", lw=0.4, alpha=alpha, label=label if first else None))
            else:
                ax.plot(p[:, 0], p[:, 1], ls, color=color, lw=lw, label=label if first else None)
            first = False

    pcb = trimesh.load(str(PCB))
    ts = trimesh.load(str(OUT / "top_shell_raw.stl")); bs = trimesh.load(str(OUT / "bottom_shell_raw.stl"))
    # 1. side levers: XZ section at each plunger Y, rest + at the stop
    for nm, y in (("side_btn_fwd", -50.8), ("side_btn_back", -68.58)):
        fig, ax = plt.subplots(figsize=(11, 8))
        o, n, ix = [0, y, 0], [0, 1, 0], [0, 2]
        draw(ax, ts, o, n, ix, "#c8c8c8", label="top_shell_raw (master)")
        draw(ax, bs, o, n, ix, "#8a8a8a", label="bottom_shell_raw (master)")
        draw(ax, pcb, o, n, ix, "#2e8b57", label="PCB (STEP mesh)")
        lv = trimesh.load(str(PARTS / nm / f"{nm}.stl"))
        draw(ax, lv, o, n, ix, COL[nm], label=f"{nm} rest")
        R = trimesh.transformations.rotation_matrix(math.radians(TH_STOP), [0, 1, 0], [PIVOT[0], 0, PIVOT[1]])
        lv2 = lv.copy(); lv2.apply_transform(R)
        draw(ax, lv2, o, n, ix, "#d00000", fill=False, lw=1.2, ls="--", label=f"at stop ({TH_STOP:.2f} deg, nub 0.80)")
        ax.plot(*PIVOT, "k+", ms=12); ax.annotate("pivot (12.2, -1.6)", PIVOT, (5, -7), fontsize=9)
        ax.axhline(7.595, color="g", lw=0.6, ls=":"); ax.annotate("plunger top 7.595", (23.5, 7.7), fontsize=8, color="g")
        ax.axvline(14.478, color="g", lw=0.6, ls=":"); ax.annotate("board edge X 14.478", (14.6, -3.6), fontsize=8, color="g")
        ax.set_xlim(2, 32); ax.set_ylim(-7, 16); ax.set_aspect("equal"); ax.grid(alpha=0.3)
        ax.set_xlabel("X (mm)"); ax.set_ylabel("Z (mm)")
        ax.set_title(f"{nm}: section Y = {y} (through the side plunger), rest + at the hard stop")
        ax.legend(loc="upper right", fontsize=8)
        f = REN / f"R04_fix_WP-H_sec_{nm}_Y{y}.png"
        fig.savefig(f, dpi=130, bbox_inches="tight"); plt.close(fig); print(f)
    # 2. DPI: YZ section at X 40.04 (with the wheel envelope)
    fig, ax = plt.subplots(figsize=(10, 8))
    o, n, ix = [40.04, 0, 0], [1, 0, 0], [1, 2]
    draw(ax, ts, o, n, ix, "#c8c8c8", label="top_shell_raw (master, no sleeve yet)")
    draw(ax, pcb, o, n, ix, "#2e8b57", label="PCB (STEP mesh)")
    d = trimesh.load(str(PARTS / "dpi_button" / "dpi_button.stl"))
    draw(ax, d, o, n, ix, COL["dpi_button"], label="dpi_button rest")
    d2 = d.copy(); d2.apply_translation([0, 0, -0.75])
    draw(ax, d2, o, n, ix, "#d00000", fill=False, lw=1.2, ls="--", label="pressed 0.75")
    th = np.linspace(0, 2 * np.pi, 200)
    ax.plot(-27.9 + 11.8 * np.cos(th), 8.595 + 11.8 * np.sin(th), color="#4060ff", lw=1, label="wheel envelope d23.6")
    # sleeve outline per spec (WP-E)
    y0, y1 = -43.18 - 2.5 - 0.15, -43.18 + 2.5 + 0.15
    for yy in ((y0 - 1.0, y0), (y1, y1 + 1.0)):
        ax.add_patch(MP([[yy[0], 13.5], [yy[1], 13.5], [yy[1], 21.06], [yy[0], 21.06]], fc="none", ec="#555", ls="--", lw=0.8))
    ax.annotate("sleeve (WP-E, spec)", (y1 + 1.1, 17), fontsize=8)
    ax.set_xlim(-56, -24); ax.set_ylim(-2, 28); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_xlabel("Y (mm)"); ax.set_ylabel("Z (mm)"); ax.set_title("dpi_button: section X = 40.04 (through the DPI plunger)")
    ax.legend(loc="upper left", fontsize=8)
    f = REN / "R04_fix_WP-H_sec_dpi_X40.04.png"
    fig.savefig(f, dpi=130, bbox_inches="tight"); plt.close(fig); print(f)


def iso():
    import pyvista as pv
    pv.OFF_SCREEN = True
    pl = pv.Plotter(off_screen=True, window_size=(1600, 1150))
    pl.set_background("#1d2a6b")
    pl.add_mesh(pv.read(str(PCB)), color="#3aa364", smooth_shading=False)
    pl.add_mesh(pv.read(str(OUT / "bottom_shell_raw.stl")), color="#bfbfbf", opacity=0.18)
    for nm in PARTS_LIST:
        pl.add_mesh(pv.read(str(PARTS / nm / f"{nm}.stl")), color=COL[nm], smooth_shading=True, specular=0.3)
    pl.camera_position = [(-55, -150, 75), (32, -50, 4), (0, 0, 1)]
    pl.add_text("WP-H: dpi_button (amber), side_btn_fwd (cyan), side_btn_back (pink) on the PCB", font_size=11, color="white")
    f = REN / "R04_fix_WP-H_iso.png"
    pl.screenshot(str(f)); print(f)


if __name__ == "__main__":
    (sec if (sys.argv[1:] or ["sec"])[0] == "sec" else iso)()
