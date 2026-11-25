"""WP-B: side section (YZ, at X = 39.37 mouse centreline) of the Z stack-up rules.
Re-run: python stackup_fig.py  -> ../renders/B01_stackup.png"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import os
OUT = os.path.join(os.path.dirname(__file__), "..", "renders", "B01_stackup.png")
Z_FLOOR, Z_SHELL_U, Z_SHELL_IN = -5.85, -5.40, -2.90
Z_LENS, PCB_T, SEAT = -3.45, 1.51, 1.595
fig, ax = plt.subplots(figsize=(13, 6.2), dpi=130)
ax.axhline(Z_FLOOR, color="k", lw=2); ax.text(-95, Z_FLOOR-2.4, "floor / mousepad  Z = -5.85", fontsize=9)
# bottom shell plate
ax.add_patch(Rectangle((-124, Z_SHELL_U), 120, Z_SHELL_IN-Z_SHELL_U, fc="#9ecae1", ec="k"))
ax.text(-122, -4.4, "bottom shell plate 2.5 (Z -5.40..-2.90)", fontsize=8)
# skates
for y0, y1 in [(-120, -100), (-14, -6), (-64, -51)]:
    ax.add_patch(Rectangle((y0, Z_FLOOR), y1-y0, 0.8, fc="#fdae6b", ec="k"))
ax.text(-120, -8.3, "PTFE skate 0.8 in 0.35 recess", fontsize=8)
# pcb
ax.add_patch(Rectangle((-76.454, 0), 61.722, PCB_T, fc="#31a354", ec="k"))
ax.text(-75, 0.25, "PCB Z 0..1.51 (brief 1.6)", fontsize=7, color="w")
# lens + sensor
ax.add_patch(Rectangle((-57.44-10.6, Z_LENS), 21.15, 0.6, fc="#bcbddc", ec="k"))
ax.add_patch(Rectangle((-64.62, SEAT), 16.2, 3.3, fc="#555", ec="k"))
ax.text(-66, 5.4, "PMW3360 (top = floor+9.81)", fontsize=8)
ax.plot([-57.44, -57.44], [Z_FLOOR, 6], "r--", lw=1); ax.text(-57.2, -1.2, "optical ctr\nY -57.44", color="r", fontsize=8)
ax.annotate("", xy=(-45, Z_FLOOR), xytext=(-45, Z_LENS), arrowprops=dict(arrowstyle="<->"))
ax.text(-44.5, -4.9, "Z=2.40 (2.2..2.6)\nlens flange plane Z -3.45", fontsize=8)
ax.annotate("", xy=(-30, Z_FLOOR), xytext=(-30, PCB_T), arrowprops=dict(arrowstyle="<->", color="b"))
ax.text(-29.5, -2.6, "PCB top to floor 7.40", fontsize=8, color="b")
# wheel + encoder axis
ax.add_patch(Circle((-27.9, 8.595), 12, fc="none", ec="m", lw=1.5)); ax.plot(-27.9, 8.595, "m+")
ax.text(-24, 23.0, "wheel D24, axle Z 8.595 (STEP H=7)\nslot in PCB; shell pocket to Z -3.9", color="m", fontsize=8)
# D2F plunger
ax.add_patch(Rectangle((-24.13, SEAT), 1.2, 6.0, fc="#fd8d3c", ec="k"))
ax.text(-23, 7.9, "D2F plunger top 7.595\nnub rest Z 7.70", fontsize=7)
# top shell profile (schematic)
import numpy as np
ky = [-124, -122, -116, -105, -90, -74, -60, -45, -28, -14, -4]
kz = [-5.4, 3.0, 13.0, 23.0, 30.5, 34.15, 33.0, 27.5, 17.2, 12.0, 8.0]   # top-surface key heights
try:
    from scipy.interpolate import PchipInterpolator
    y = np.linspace(-124, -4, 300); h = PchipInterpolator(ky, kz)(y)
except Exception:
    y, h = np.array(ky), np.array(kz)
ax.plot(ky, kz, "ko", ms=3)
ax.plot(y, h, "k-", lw=1.5); ax.text(-112, 35.6, "top: H 40 above floor (Z 34.15) at Y -74; button surface at wheel Z 17.2 (23 above floor)", fontsize=9)
ax.set_xlim(-130, 2); ax.set_ylim(-9, 38); ax.set_aspect("equal")
ax.set_xlabel("Y (native STEP, +Y = front)  [mm]"); ax.set_ylabel("Z [mm]")
ax.set_title("WP-B stack-up rules (section at X = 39.37, mouse centreline) - schematic")
ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(OUT); print(os.path.abspath(OUT))
