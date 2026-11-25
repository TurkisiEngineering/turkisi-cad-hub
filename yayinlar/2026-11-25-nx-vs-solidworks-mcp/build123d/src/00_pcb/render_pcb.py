# Renders for WP-A: R00_pcb_top.png (annotated 2D, matplotlib) + R00_pcb_keepout.png. Run with system python.
# The iso view is render_pcb_iso.py (pyvista venv).
import json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "renders")); os.makedirs(OUT, exist_ok=True)
d = json.load(open(os.path.join(HERE, "PCB_DATA.json")))
B = d["board"]
COL = dict(switch="#e8590c", encoder="#1c7ed6", sensor="#2f9e44", usb_header="#ae3ec9", smd="#868e96")

def base(ax):
    ax.add_patch(Polygon(B["outline_ccw"], closed=True, fc="#1b5e3a", ec="k", lw=1.2, alpha=0.9))
    for c in B["cutouts"]:
        ax.add_patch(Polygon(c["poly"], closed=True, fc="white", ec="k", lw=1))
    for h in d["holes"]["mounting"]:
        ax.add_patch(Circle((h["x"], h["y"]), h["drill_d"] / 2, fc="white", ec="k"))
    ax.set_aspect("equal"); ax.set_xlim(B["bbox_xy"][0] - 6, B["bbox_xy"][2] + 6); ax.set_ylim(B["bbox_xy"][1] - 6, B["bbox_xy"][3] + 8)
    ax.grid(True, lw=0.3, alpha=0.5); ax.set_xlabel("X [mm]  (+X right)"); ax.set_ylabel("Y [mm]  (+Y = FRONT)")

fig, ax = plt.subplots(figsize=(9, 10.5), dpi=130)
base(ax)
for c in d["components"]:
    b = c["bbox"]; g = c["group"]
    if g == "smd":
        ax.add_patch(Rectangle((b[0], b[1]), b[3] - b[0], b[4] - b[1], fc=COL[g], ec="k", lw=0.3, alpha=0.8))
for s in d["switches"]:
    b = s["body_box"]; p = s["plunger_box"]
    ax.add_patch(Rectangle((b[0], b[1]), b[3] - b[0], b[4] - b[1], fc=COL["switch"], ec="k", lw=0.8, alpha=0.85))
    ax.add_patch(Rectangle((p[0], p[1]), p[3] - p[0], p[4] - p[1], fc="yellow", ec="k", lw=0.8))
    a = s["actuator_top"]; ax.plot(a[0], a[1], "k+", ms=8)
    lab = s["role"].split(" (")[0]
    ax.annotate(f"{lab}\nact ({a[0]:.2f},{a[1]:.2f},{a[2]:.2f})", (a[0], a[1]), xytext=(8, -8) if a[0] < 40 else (-8, -8),
                textcoords="offset points", fontsize=6.5, ha="left" if a[0] < 40 else "right", va="top",
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.5))
e = d["encoder"]; b = e["overall_bbox"]
ax.add_patch(Rectangle((b[0], b[1]), b[3] - b[0], b[4] - b[1], fc=COL["encoder"], ec="k", lw=0.8, alpha=0.85))
ax.plot([e["hub"]["x_range"][0] - 3, 52.5], [e["shaft_axis"]["point"][1]] * 2, "b--", lw=1)
ws = e["wheel_space"]; wc = ws["wheel_centre_suggest"]
ax.add_patch(Rectangle((wc[0] - 4, wc[1] - 10), 8, 20, fc="none", ec="b", ls=":", lw=1.2))
ax.annotate(f"EC10E axis Y{e['shaft_axis']['point'][1]} Z{e['shaft_axis']['point'][2]}\nwheel Ø20x8 example in slot", (wc[0], wc[1] + 10),
            xytext=(0, 18), textcoords="offset points", fontsize=6.5, ha="center", color="b", arrowprops=dict(arrowstyle="-", color="b"))
s = d["sensor"]; b = s["body_box"]
ax.add_patch(Rectangle((b[0], b[1]), b[3] - b[0], b[4] - b[1], fc=COL["sensor"], ec="k", lw=0.8, alpha=0.6))
oc = s["optical_centre_xy"]; ax.plot(oc[0], oc[1], "rx", ms=10, mew=2)
ax.annotate(f"PMW3360 optical centre\n({oc[0]:.2f},{oc[1]:.2f})", (oc[0], oc[1]), xytext=(0, -22), textcoords="offset points",
            ha="center", fontsize=6.5, color="darkred", bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.5))
u = d["usb_header"]; b = u["housing_box"]
ax.add_patch(Rectangle((b[0], b[1]), b[3] - b[0], b[4] - b[1], fc=COL["usb_header"], ec="k", lw=0.8, alpha=0.85))
for p in u["pins_xy"]: ax.add_patch(Rectangle((p[0] - 0.32, p[1] - 0.32), 0.64, 0.64, fc="gold", ec="k", lw=0.3))
ax.annotate("USB 1x4 header (pins to Z 10.1)", (u["centre_xy"][0], b[1]), xytext=(0, -14), textcoords="offset points", ha="center", fontsize=6.5)
for h in d["holes"]["mounting"]:
    ax.annotate(f"M2 Ø{h['drill_d']}\n({h['x']},{h['y']})", (h["x"], h["y"]), xytext=(0, 10 if h["y"] > -40 else -12),
                textcoords="offset points", ha="center", va="bottom" if h["y"] > -40 else "top", fontsize=6)
ax.annotate("FRONT (+Y)", (39.37, B["bbox_xy"][3] + 5), ha="center", fontsize=9, weight="bold")
ax.set_title("R00 · PCB top view, native STEP coords · switches orange (yellow = plunger), encoder blue, sensor green", fontsize=8.5)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "R00_pcb_top.png")); plt.close(fig)

# keep-out heat map
k = d["keepout"]; T = np.array(k["top_max_z"]); Bm = np.array(k["bottom_min_z"])
fig, axs = plt.subplots(1, 2, figsize=(12, 7.5), dpi=120)
ext = [k["x0"], k["x0"] + k["nx"] * k["cell_mm"], k["y0"], k["y0"] + k["ny"] * k["cell_mm"]]
im = axs[0].imshow(T, origin="lower", extent=ext, cmap="viridis", vmin=1.5, vmax=13)
fig.colorbar(im, ax=axs[0], shrink=0.7, label="max top Z [mm]")
axs[0].plot(*np.array(B["outline_ccw"] + [B["outline_ccw"][0]]).T, "w-", lw=1)
axs[0].set_title("Top side: max component Z per 1 mm cell (board top 1.51)", fontsize=9)
im2 = axs[1].imshow(Bm, origin="lower", extent=ext, cmap="magma", vmin=-2, vmax=0)
fig.colorbar(im2, ax=axs[1], shrink=0.7, label="min Z [mm]")
axs[1].plot(*np.array(B["outline_ccw"] + [B["outline_ccw"][0]]).T, "c-", lw=1)
axs[1].set_title("Bottom side: THT leads, min Z (board bottom 0)", fontsize=9)
for a in axs: a.set_aspect("equal"); a.set_xlabel("X"); a.set_ylabel("Y (+ = front)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "R00_pcb_keepout.png")); plt.close(fig)
print("ok")
