"""render_rv01_f1.py - RV01 F-1 proof render: section of top_shell at the wheel axle plane Y=ENC_AXIS_Y with the
wheel outline at rest and tilted to the middle-click stop.  -> work/renders/R04_fix_WP-E_secY_wheel.png
Run: python render_rv01_f1.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
import master as ML              # noqa: E402
import matplotlib                # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402
import trimesh                   # noqa: E402

PARAMS = dict(sec_y=ML.ENC_AXIS_Y - 5.9, xlim=(28, 50), ylim=(4, 24), tilt_deg=2.025)
P = PARAMS
D = Path(__file__).resolve().parent
OUT = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work\renders")

m = trimesh.load(str(D / "top_shell.stl"))
sec = m.section(plane_origin=[0, P["sec_y"], 0], plane_normal=[0, 1, 0])
fig, ax = plt.subplots(figsize=(9, 8))
for e in sec.discrete:
    ax.plot(e[:, 0], e[:, 2], color="#d98c00", lw=1.6)
# wheel outline in this Y plane: half chord of the d23.6 tyre
yc, zc = ML.WHEEL_C[1], ML.WHEEL_C[2]
h = math.sqrt(max((ML.WHEEL_D / 2) ** 2 - (P["sec_y"] - yc) ** 2, 0))
x0, x1 = ML.WHEEL_X
rect = np.array([[x0, zc - h], [x1, zc - h], [x1, zc + h], [x0, zc + h], [x0, zc - h]])
ax.plot(rect[:, 0], rect[:, 1], "g-", lw=1.2, label="wheel at rest")
th = math.radians(P["tilt_deg"])
px = ML.ENC_PIVOT_X
c, s = math.cos(-th), math.sin(-th)
rt = np.c_[px + (rect[:, 0] - px) * c - (rect[:, 1] - zc) * s, zc + (rect[:, 0] - px) * s + (rect[:, 1] - zc) * c]
ax.plot(rt[:, 0], rt[:, 1], "r--", lw=1.2, label=f"wheel tilted {P['tilt_deg']:.2f} deg (middle-click stop)")
ax.axvline(43.75, color="k", lw=0.6, ls=":")
ax.text(43.8, P["ylim"][0] + 0.5, "window / rail X 43.75", fontsize=8)
ax.set_xlim(*P["xlim"])
ax.set_ylim(*P["ylim"])
ax.set_aspect("equal")
ax.grid(alpha=0.3)
ax.legend(loc="lower left", fontsize=8)
ax.set_xlabel("X mm")
ax.set_ylabel("Z mm")
ax.set_title(f"WP-E RV01 F-1: top_shell section Y {P['sec_y']:.2f} - wheel window right edge moved to X 43.75")
fig.savefig(str(OUT / "R04_fix_WP-E_secY_wheel.png"), dpi=130, bbox_inches="tight")
print("saved", OUT / "R04_fix_WP-E_secY_wheel.png")
