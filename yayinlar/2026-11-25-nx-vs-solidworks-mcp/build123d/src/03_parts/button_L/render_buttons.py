"""render_buttons.py - WP-F renders.
  iso:      <cadgenbench venv python> render_buttons.py iso      -> renders/R02_buttons_iso.png
  section:  python render_buttons.py section                       -> renders/R02_buttons_section_X20.32.png
"""
import sys
from pathlib import Path

WORK = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work")
PARTS = WORK / "03_parts"
REN = WORK / "renders"
PCB_STL = WORK / "00_pcb" / "pcb.stl"
PARAMS = dict(
    sec_x=20.32,            # = SW_MAIN_L X (section through the L nub, post, leaf)
    sec_x_R=58.42,          # = SW_MAIN_R X
    xlim=(-128, 0), ylim=(-7, 38),
    win=(1800, 1200),
)
P = PARAMS


def iso():
    import pyvista as pv
    pv.OFF_SCREEN = True
    pl = pv.Plotter(off_screen=True, window_size=P["win"])
    pl.set_background("white")
    pl.add_mesh(pv.read(str(PCB_STL)), color="#2e8b57", opacity=1.0)
    ts = PARTS / "top_shell" / "top_shell.stl"
    if ts.exists():
        pl.add_mesh(pv.read(str(ts)), color="#bbbbbb", opacity=0.18)
    for s, c in (("L", "#ff7f0e"), ("R", "#1f77b4")):
        pl.add_mesh(pv.read(str(PARTS / f"button_{s}" / f"button_{s}.stl")), color=c, smooth_shading=True)
    for nm, c in (("wheel", "#444444"),):
        f = PARTS / nm / f"{nm}.stl"
        if f.exists():
            pl.add_mesh(pv.read(str(f)), color=c, opacity=0.6)
    pl.camera_position = [(-60, 40, 120), (39.4, -45, 8), (0, 0, 1)]
    pl.add_text("WP-F main buttons L (orange) / R (blue), PETG - PCB native coords", font_size=11, color="black")
    out = REN / "R02_buttons_iso.png"
    pl.screenshot(str(out))
    # underside view (nub, post, web, leaf)
    pl2 = pv.Plotter(off_screen=True, window_size=P["win"])
    pl2.set_background("white")
    pl2.add_mesh(pv.read(str(PCB_STL)), color="#2e8b57", opacity=0.35)
    for s, c in (("L", "#ff7f0e"), ("R", "#1f77b4")):
        pl2.add_mesh(pv.read(str(PARTS / f"button_{s}" / f"button_{s}.stl")), color=c, smooth_shading=True)
    pl2.camera_position = [(-40, 60, -60), (39.4, -40, 12), (0, 0, 1)]
    pl2.add_text("underside: nub, stop post, web + flexure leaf (clamp holes)", font_size=11, color="black")
    pl2.screenshot(str(REN / "R02_buttons_iso_under.png"))
    print(out)


def section():
    import numpy as np
    import trimesh
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 1, figsize=(16, 11))
    for ax, side, x in ((axs[0], "L", P["sec_x"]), (axs[1], "R", P["sec_x_R"])):
        items = [(PCB_STL, "#2e8b57", "PCB (STEP mesh)", 1.0),
                 (PARTS / "top_shell" / "top_shell.stl", "#888888", "top_shell", 1.0),
                 (PARTS / "bottom_shell" / "bottom_shell.stl", "#555555", "bottom_shell", 1.0),
                 (PARTS / f"button_{side}" / f"button_{side}.stl", "#ff7f0e", f"button_{side} rest", 1.6),
                 (PARTS / f"button_{side}" / f"_button_{side}_pressed.stl", "#d62728", f"button_{side} pressed 0.8", 0.8)]
        for f, c, lab, lw in items:
            if not Path(f).exists():
                continue
            m = trimesh.load(str(f))
            sec = m.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
            if sec is None:
                continue
            first = True
            for ent in sec.discrete:
                e = np.asarray(ent)
                ax.plot(e[:, 1], e[:, 2], color=c, lw=lw, ls="--" if "pressed" in lab else "-",
                        label=lab if first else None)
                first = False
        ax.axhline(-5.85, color="k", lw=0.6, ls=":")
        ax.text(-127, -5.6, "floor Z -5.85", fontsize=8)
        ax.set_xlim(*P["xlim"]); ax.set_ylim(*P["ylim"]); ax.set_aspect("equal")
        ax.grid(alpha=0.3); ax.set_xlabel("Y (mm, +front)"); ax.set_ylabel("Z (mm)")
        ax.set_title(f"Section X = {x} (through the button_{side} nub on the main switch, stop post, web, leaf)")
        ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    out = REN / "R02_buttons_section_X20.32_X58.42.png"
    fig.savefig(str(out), dpi=130)
    # zoom on the nub / post / leaf of L
    fig, axs = plt.subplots(1, 2, figsize=(16, 6))
    for ax, (xl, yl, ttl) in zip(axs, (((-32, -14), (0, 16), "nub on D2F plunger + stop post (X 20.32)"),
                                       ((-76, -54), (14, 30), "web + flexure leaf + clamp zone (X 20.32)"))):
        for f, c, lab, lw in ((PCB_STL, "#2e8b57", "PCB", 1.0), (PARTS / "top_shell" / "top_shell.stl", "#888888", "top_shell", 1.0),
                              (PARTS / "button_L" / "button_L.stl", "#ff7f0e", "button_L rest", 1.6),
                              (PARTS / "button_L" / "_button_L_pressed.stl", "#d62728", "pressed 0.8", 0.8)):
            m = trimesh.load(str(f))
            for xs in ((P["sec_x"],) if "nub" in ttl else (P["sec_x"] + 1.2,)):
                sec = m.section(plane_origin=[xs, 0, 0], plane_normal=[1, 0, 0])
                if sec is None:
                    continue
                first = True
                for ent in sec.discrete:
                    e = np.asarray(ent)
                    ax.plot(e[:, 1], e[:, 2], color=c, lw=lw, ls="--" if "pressed" in lab else "-", label=lab if first else None)
                    first = False
        # stop post is at X 15.2..16.9: add its section too on the left plot
        if "nub" in ttl:
            for f, c, lab in ((PARTS / "button_L" / "button_L.stl", "#9467bd", "button_L at X 16.05 (stop post)"),
                              (PCB_STL, "#2e8b57", None)):
                m = trimesh.load(str(f))
                sec = m.section(plane_origin=[16.05, 0, 0], plane_normal=[1, 0, 0])
                first = True
                for ent in sec.discrete:
                    e = np.asarray(ent)
                    ax.plot(e[:, 1], e[:, 2], color=c, lw=1.0, ls="-.", label=lab if first else None)
                    first = False
        ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal"); ax.grid(alpha=0.3)
        ax.set_title(ttl); ax.legend(fontsize=8, loc="upper right"); ax.set_xlabel("Y"); ax.set_ylabel("Z")
    fig.tight_layout()
    fig.savefig(str(REN / "R02_buttons_section_zoom_L.png"), dpi=130)
    print(out)


if __name__ == "__main__":
    {"iso": iso, "section": section}[sys.argv[1]]()
