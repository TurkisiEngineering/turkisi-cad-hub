# Concept renders of the master layout (raw split parts + PCB). Run AFTER layout_check.py, with the cadgenbench venv:
#   "C:\Users\marya\.venvs\cadgenbench\Scripts\python.exe" render_concept.py
import os
import numpy as np
import pyvista as pv
pv.global_theme.allow_empty_mesh = True

HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.join(HERE, "out")
REN = os.path.normpath(os.path.join(HERE, "..", "renders"))
PCB = os.path.normpath(os.path.join(HERE, "..", "00_pcb", "mesh"))
PCBCOL = dict(board="#1b6b40", smd="#555a60", switch="#ff7a1a", encoder="#2f8cff", sensor="#3cc35a", usb_header="#c04de0")
X_CL, AX_Y, AX_Z, WD, WW = 39.37, -27.9, 8.595, 23.6, 7.5
Z_FLOOR = -5.85


def m(name):
    return pv.read(os.path.join(OUTD, name + ".stl"))


def add_pcb(pl, clip=None):
    for g, c in PCBCOL.items():
        p = os.path.join(PCB, g + ".stl")
        if os.path.exists(p):
            mm = pv.read(p)
            if clip is not None:
                mm = mm.clip(**clip)
            pl.add_mesh(mm, color=c, specular=0.2)
    wheel = pv.Cylinder(center=(X_CL, AX_Y, AX_Z), direction=(1, 0, 0), radius=WD / 2, height=WW, resolution=72)
    if clip is not None:
        wheel = wheel.clip(**clip)
    pl.add_mesh(wheel, color="#30343a")
    pl.add_mesh(pv.Line((30.1, AX_Y, AX_Z), (52.3, AX_Y, AX_Z)), color="black", line_width=4)


def floor(pl):
    pl.add_mesh(pv.Plane(center=(X_CL, -64, Z_FLOOR), direction=(0, 0, 1), i_size=110, j_size=160), color="#d9dde2", opacity=0.6)


def shot(pl, cam, name, zoom=1.0):
    pl.camera_position = cam
    pl.reset_camera()
    pl.camera.zoom(zoom)
    pl.screenshot(os.path.join(REN, name))
    pl.close()


C = (X_CL, -64.0, 12.0)
parts = dict(top_shell_raw="#e8ecf2", bottom_shell_raw="#2b2f36", button_L_raw="#ff5a36", button_R_raw="#ff5a36")

# 1. iso, top shell transparent, buttons semi
pl = pv.Plotter(off_screen=True, window_size=(1800, 1300)); pl.set_background("white")
floor(pl); add_pcb(pl)
pl.add_mesh(m("bottom_shell_raw"), color=parts["bottom_shell_raw"], opacity=0.85, specular=0.3)
pl.add_mesh(m("top_shell_raw"), color=parts["top_shell_raw"], opacity=0.35, specular=0.4)
pl.add_mesh(m("button_L_raw"), color="#ff5a36", opacity=0.45)
pl.add_mesh(m("button_R_raw"), color="#ff5a36", opacity=0.45)
pl.add_text("R01 concept - master layout (raw split: top shell / bottom shell / L+R buttons), PCB at native coords",
            font_size=11, color="black")
shot(pl, [(C[0] - 95, C[1] + 115, 105), C, (0, 0, 1)], "R01_concept_iso.png", 1.05)

# 2. iso solid (opaque) - what the user will see
pl = pv.Plotter(off_screen=True, window_size=(1800, 1300)); pl.set_background("white")
floor(pl); add_pcb(pl)
pl.add_mesh(m("bottom_shell_raw"), color="#2b2f36", specular=0.3)
pl.add_mesh(m("top_shell_raw"), color="#e8ecf2", specular=0.4)
pl.add_mesh(m("button_L_raw"), color="#ff5a36", specular=0.4)
pl.add_mesh(m("button_R_raw"), color="#ff5a36", specular=0.4)
shot(pl, [(C[0] - 95, C[1] + 115, 105), C, (0, 0, 1)], "R01_concept_iso_solid.png", 1.05)

# 3. side view (from the left = thumb side), shell transparent
pl = pv.Plotter(off_screen=True, window_size=(1800, 1000)); pl.set_background("white")
add_pcb(pl)
pl.add_mesh(m("skin"), color="#8fa3b8", opacity=0.25)
pl.add_mesh(pv.Line((-5, -130, Z_FLOOR), (-5, 2, Z_FLOOR)), color="gray", line_width=3)
pl.add_text("R01 side (left / thumb side), floor Z -5.85, front = LEFT", font_size=11, color="black")
pl.enable_parallel_projection()
shot(pl, [(-200, -64, 12), (X_CL, -64, 12), (0, 0, 1)], "R01_concept_side.png", 1.5)

# 4. top view
pl = pv.Plotter(off_screen=True, window_size=(1300, 1800)); pl.set_background("white")
add_pcb(pl)
pl.add_mesh(m("top_shell_raw"), color="#e8ecf2", opacity=0.35)
pl.add_mesh(m("button_L_raw"), color="#ff5a36", opacity=0.35)
pl.add_mesh(m("button_R_raw"), color="#ff5a36", opacity=0.35)
pl.add_text("R01 top (front up)", font_size=11, color="black")
pl.enable_parallel_projection()
shot(pl, [(X_CL, -64, 250), (X_CL, -64, 0), (0, 1, 0)], "R01_concept_top.png", 1.3)

# 5. sections: X = wheel/sensor centreline (YZ section) and Y = wheel axis (XZ section)
for nm, normal, origin, cam, txt in (
        ("R01_concept_section_X39.png", (1, 0, 0), (X_CL + 0.01, 0, 0), [(250, -64, 12), (X_CL, -64, 12), (0, 0, 1)],
         "R01 section X 39.37 (wheel + sensor centreline), viewed from +X; front = RIGHT"),
        ("R01_concept_section_Y-27.9.png", (0, 1, 0), (0, AX_Y, 0), [(X_CL, 150, 10), (X_CL, AX_Y, 10), (0, 0, 1)],
         "R01 section Y -27.9 (wheel axle / encoder / middle switch), viewed from the front")):
    clip = dict(normal=normal, origin=origin, invert=True)
    pl = pv.Plotter(off_screen=True, window_size=(1800, 1000)); pl.set_background("white")
    add_pcb(pl, clip)
    for k, c in parts.items():
        pl.add_mesh(m(k).clip(**clip), color=c, specular=0.3)
    pl.add_mesh(pv.Line((-5, -130, Z_FLOOR), (85, 2, Z_FLOOR)), color="gray", line_width=3)
    pl.add_text(txt, font_size=11, color="black")
    pl.enable_parallel_projection()
    shot(pl, cam, nm, 1.6 if "Y-27" in nm else 1.45)
print("renders ok")
