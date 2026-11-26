"""Milestone renders from the NX STLs (assembly coordinates). usage: render_all.py which [which...]"""
import sys, os, numpy as np, pyvista as pv
R = r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx\render"
COL = {"pcb": "seagreen", "bottom_shell": "dimgray", "top_shell": "lightsteelblue", "btn_left": "tomato",
       "btn_right": "tomato", "key_fwd": "gold", "key_back": "gold", "wheel": "royalblue", "axle_pin": "silver",
       "lens": "orchid", "hinge_f": "silver"}
M = {}


def mesh(k):
    if k not in M:
        M[k] = pv.read(os.path.join(R, k + ".stl"))
    return M[k]


def shot(out, title, items, views, size=(1600, 1200), shape=(2, 2)):
    pl = pv.Plotter(off_screen=True, shape=shape, window_size=size)
    allm = pv.MultiBlock([m for m, _, _ in items])
    b = np.array(allm.bounds)
    ctr = [(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2]
    dist = 2.3 * max(b[1] - b[0], b[3] - b[2], b[5] - b[4])
    for i, (nm, d) in enumerate(views):
        pl.subplot(i // shape[1], i % shape[1])
        pl.set_background("white")
        for m, c, o in items:
            pl.add_mesh(m, color=c, opacity=o, smooth_shading=True, specular=0.3)
        pl.add_text(nm, font_size=9, color="black")
        dv = np.array(d, float) / np.linalg.norm(d)
        up = (0, 1, 0) if abs(dv[2]) > 0.99 else (0, 0, 1)
        pl.camera_position = [tuple(np.array(ctr) + dv * dist), tuple(ctr), up]
        pl.camera.zoom(1.3)
    pl.subplot(0, 0)
    pl.add_text(title, position="upper_right", font_size=10, color="black")
    pl.screenshot(os.path.join(R, out))
    print("wrote", out)


ISO = [("iso", (1.0, -1.3, 0.9)), ("iso arka", (-1.2, 1.1, 0.8)), ("yan", (-1, 0, 0.0001)), ("ust", (0, 0, 1))]
which = sys.argv[1:]
if "bottom" in which:
    shot("r02_bottom_shell.png", "Alt kabuk + PCB", [(mesh("bottom_shell"), COL["bottom_shell"], 1), (mesh("pcb"), COL["pcb"], 0.5), (mesh("lens"), COL["lens"], 1)],
         [("iso", (1.0, -1.3, 0.9)), ("alttan", (0.3, -0.4, -1)), ("yan", (-1, 0, 0.0001)), ("ust", (0, 0, 1))])
if "top" in which:
    shot("r03_top_shell.png", "Ust kabuk (tus pencereleri, tekerlek yarigi, DPI dili)", [(mesh("top_shell"), COL["top_shell"], 1)],
         [("iso", (1.0, -1.3, 0.9)), ("icten (alttan)", (0.3, -0.5, -1)), ("yan", (-1, 0, 0.0001)), ("ust", (0, 0, 1))])
if "keys" in which:
    shot("r04_keys_wheel.png", "Tuslar + yan tuslar + tekerlek, PCB uzerinde",
         [(mesh(k), COL[k], 1) for k in ("btn_left", "btn_right", "key_fwd", "key_back", "wheel", "axle_pin", "pcb")],
         [("iso", (1.0, -1.3, 0.9)), ("iso sol", (-1.3, -0.6, 0.7)), ("yan", (-1, 0, 0.0001)), ("on", (0, 1, 0.15))])
if "asm" in which:
    items = [(mesh(k), COL[k], 1) for k in ("bottom_shell", "top_shell", "btn_left", "btn_right", "key_fwd", "key_back", "wheel")]
    shot("r06_assembly.png", "Montaj (NX)", items, ISO)
    ex = {"bottom_shell": -25, "pcb": -8, "lens": -8, "top_shell": 30, "btn_left": 55, "btn_right": 55, "key_fwd": 30, "key_back": 30,
          "wheel": 12, "axle_pin": 12}
    exi = []
    for k, dz in ex.items():
        m = mesh(k).translate((-25 if k.startswith("key") else 0, 0, dz), inplace=False)
        exi.append((m, COL[k], 1))
    shot("r07_exploded.png", "Patlatilmis gorunus", exi, [("iso", (1.0, -1.3, 0.7)), ("iso arka", (-1.2, 1.1, 0.6)), ("yan", (-1, 0, 0.0001)), ("on", (0.1, 1, 0.2))])
if "section" in which:
    pl = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1800, 800))
    for i, (orig, nrm, title, cam) in enumerate([((0, 0, 0), (1, 0, 0), "Kesit x=0 (tekerlek, sensor/lens)", (-1, 0, 0)),
                                                  ((0, 22.063, 0), (0, 1, 0), "Kesit y=22.06 (sol/sag tus nub - D2F)", (0, -1, 0))]):
        pl.subplot(0, i)
        pl.set_background("white")
        for k in ("bottom_shell", "top_shell", "btn_left", "btn_right", "wheel", "axle_pin", "pcb", "lens", "key_fwd", "key_back"):
            s = mesh(k).slice(normal=nrm, origin=orig)
            if s.n_points:
                pl.add_mesh(s, color=COL[k], line_width=3)
        pl.add_text(title, font_size=10, color="black")
        pl.view_vector(cam, viewup=(0, 0, 1))
        pl.camera.zoom(1.4)
    pl.screenshot(os.path.join(R, "r08_sections.png"))
    print("wrote r08_sections.png")
