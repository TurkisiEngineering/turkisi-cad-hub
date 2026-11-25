# Iso render of the board with highlighted parts. Run with the cadgenbench venv python (pyvista, offscreen).
import os, json
import pyvista as pv
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "renders"))
d = json.load(open(os.path.join(HERE, "PCB_DATA.json")))
COL = dict(board="#1b6b40", smd="#555a60", switch="#ff7a1a", encoder="#2f8cff", sensor="#3cc35a", usb_header="#c04de0")

def scene(views):
    for name, cam in views:
        pl = pv.Plotter(off_screen=True, window_size=(1600, 1200))
        pl.set_background("white")
        for g, c in COL.items():
            p = os.path.join(HERE, "mesh", g + ".stl")
            if os.path.exists(p):
                pl.add_mesh(pv.read(p), color=c, smooth_shading=False, specular=0.2)
        e = d["encoder"]["shaft_axis"]; P = e["point"]
        pl.add_mesh(pv.Line((P[0] - 3, P[1], P[2]), (54, P[1], P[2])), color="blue", line_width=3)
        wc = d["encoder"]["wheel_space"]["wheel_centre_suggest"]
        pl.add_mesh(pv.Cylinder(center=wc, direction=(1, 0, 0), radius=10, height=8, resolution=60), color="#2f8cff", opacity=0.25)
        oc = d["sensor"]["optical_centre_xy"]
        pl.add_mesh(pv.Line((oc[0], oc[1], -6), (oc[0], oc[1], 8)), color="red", line_width=4)
        for s in d["switches"]:
            a = s["actuator_top"]
            pl.add_mesh(pv.Sphere(radius=0.6, center=a), color="yellow")
        for h in d["holes"]["mounting"]:
            pl.add_mesh(pv.Line((h["x"], h["y"], -4), (h["x"], h["y"], 14)), color="black", line_width=2)
        pl.add_point_labels([(39.37, -12, 2)], ["FRONT +Y"], font_size=20, text_color="black", shape_opacity=0)
        pl.camera_position = cam
        pl.camera.zoom(0.95)
        pl.screenshot(os.path.join(OUT, name)); pl.close()

c = (39.37, -45.6, 3)
scene([("R00_pcb_iso.png", [(c[0] - 70, c[1] - 85, 75), c, (0, 0, 1)]),
       ("R00_pcb_iso_front.png", [(c[0] + 55, c[1] + 80, 45), c, (0, 0, 1)])])
print("ok")
