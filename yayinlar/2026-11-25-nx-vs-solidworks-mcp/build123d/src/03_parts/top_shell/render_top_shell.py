"""render_top_shell.py - progress renders for WP-E (run with the cadgenbench venv python, pyvista offscreen).
-> work/renders/R02_top_shell_iso.png, R02_top_shell_iso_under.png, R02_top_shell_sec_X39.37.png, R02_top_shell_sec_Y-70.4.png
"""
from pathlib import Path

import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
WORK = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work")
OUT = WORK / "renders"
TS = pv.read(str(WORK / "03_parts" / "top_shell" / "top_shell.stl"))
PCB = pv.read(str(WORK / "00_pcb" / "pcb.stl"))
BSR = pv.read(str(WORK / "02_master" / "out" / "bottom_shell_raw.stl"))
C_TS, C_PCB, C_BS = "#f2b134", "#2e9e4f", "#5a5a66"
BG = "#1f3a93"
PARAMS = dict(win=(1600, 1100), sec_x=39.37, sec_y=-70.4)


def base():
    p = pv.Plotter(off_screen=True, window_size=PARAMS["win"])
    p.set_background(BG)
    return p


def iso(name, view_up_under=False):
    p = base()
    p.add_mesh(TS, color=C_TS, smooth_shading=False, specular=0.3, opacity=1.0 if not view_up_under else 0.85)
    p.add_mesh(PCB, color=C_PCB)
    if view_up_under:
        p.camera_position = [(39.4 + 120, -64 + 90, 15 - 110), (39.4, -64, 15), (0, 0, 1)]
        p.reset_camera()
    else:
        p.camera_position = [(39.4 - 120, -64 + 110, 12 + 120), (39.4, -64, 12), (0, 0, 1)]
        p.reset_camera()
    p.add_text(f"top_shell (PLA) + PCB  {name}", font_size=14, color="white")
    p.screenshot(str(OUT / f"R02_top_shell_{name}.png"))
    p.close()


def section(axis):
    """Filled 2D section (matplotlib, mesh slices), limits expanded so nothing is clipped."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from matplotlib.patches import Polygon as MPoly, Circle
    if axis == "x":
        o, n, idx, tag, xl = (PARAMS["sec_x"], 0, 0), (1, 0, 0), (1, 2), f"sec_X{PARAMS['sec_x']}", "Y [mm]"
    else:
        o, n, idx, tag, xl = (0, PARAMS["sec_y"], 0), (0, 1, 0), (0, 2), f"sec_Y{PARAMS['sec_y']}", "X [mm]"
    fig, ax = plt.subplots(figsize=(14, 7))
    allpts = []
    for f, col, lab in ((WORK / "03_parts" / "top_shell" / "top_shell.stl", C_TS, "top_shell"),
                        (WORK / "02_master" / "out" / "bottom_shell_raw.stl", C_BS, "bottom_shell_raw"),
                        (WORK / "00_pcb" / "pcb.stl", C_PCB, "PCB")):
        m = trimesh.load(str(f))
        s = m.section(plane_origin=o, plane_normal=n)
        if s is None:
            continue
        from shapely.geometry import Polygon as SPoly
        from matplotlib.path import Path as MPath
        from matplotlib.patches import PathPatch
        g = None
        for d in s.discrete:
            xy = d[:, idx]
            allpts.append(xy)
            pg = SPoly(xy).buffer(0)
            g = pg if g is None else g.symmetric_difference(pg)      # even-odd fill: holes stay open
        geoms = getattr(g, "geoms", [g])
        first = True
        for pg in geoms:
            if pg.is_empty or pg.geom_type != "Polygon":
                continue
            verts, codes = [], []
            for ring in [pg.exterior] + list(pg.interiors):
                c = np.asarray(ring.coords)
                verts += c.tolist(); codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
            ax.add_patch(PathPatch(MPath(verts, codes), fc=col, ec="k", lw=0.6, alpha=0.9,
                                   label=lab if first else None))
            first = False
    if axis == "x":
        ax.add_patch(Circle((-27.9, 8.595), 11.8, fill=False, ec="red", ls="--", lw=1.2, label="wheel envelope"))
    P = np.vstack(allpts)
    pad = 4
    ax.set_xlim(P[:, 0].min() - pad, P[:, 0].max() + pad)
    ax.set_ylim(P[:, 1].min() - pad, P[:, 1].max() + pad)
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.set_xlabel(xl); ax.set_ylabel("Z [mm]")
    ax.set_title(f"R02 top_shell section {tag} (native coords; orange top_shell, grey bottom_shell_raw, green PCB)")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(str(OUT / f"R02_top_shell_{tag}.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    iso("iso")
    iso("iso_under", True)
    section("x")
    section("y")
    print("renders written")
