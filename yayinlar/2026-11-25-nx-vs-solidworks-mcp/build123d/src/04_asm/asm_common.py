"""WP-I shared helpers: part list, colours, loaders, PCB solid labelling, exact common volume."""
import sys, json, math
from pathlib import Path
sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *          # noqa
import master as ML              # noqa  (never edited)

ASM = Path(__file__).resolve().parent
PARTS = ML.PARTS_DIR
MESH = ASM / "mesh"; MESH.mkdir(exist_ok=True)

# (name, step file, rgb, material) - wheel = printed wheel_body + bought axle_pin (wheel.step is only an envelope)
PARTS_LIST = [
    ("bottom_shell", PARTS / "bottom_shell/bottom_shell.step", (0.16, 0.17, 0.19), "PLA/PETG dark"),
    ("top_shell", PARTS / "top_shell/top_shell.step", (0.92, 0.92, 0.95), "PLA"),
    ("button_L", PARTS / "button_L/button_L.step", (0.93, 0.33, 0.20), "PETG"),
    ("button_R", PARTS / "button_R/button_R.step", (0.98, 0.55, 0.15), "PETG"),
    ("wheel_body", PARTS / "wheel/wheel_body.step", (0.20, 0.75, 0.95), "PLA"),
    ("axle_pin", PARTS / "wheel/axle_pin.step", (0.70, 0.72, 0.75), "steel ISO 2338 d2x16"),
    ("wheel_yoke", PARTS / "wheel_yoke/wheel_yoke.step", (0.98, 0.85, 0.10), "PETG"),
    ("dpi_button", PARTS / "dpi_button/dpi_button.step", (0.60, 0.30, 0.90), "PLA"),
    ("side_btn_fwd", PARTS / "side_btn_fwd/side_btn_fwd.step", (0.15, 0.80, 0.40), "PETG"),
    ("side_btn_back", PARTS / "side_btn_back/side_btn_back.step", (0.10, 0.55, 0.30), "PETG"),
]
COLORS = {n: c for n, _, c, _ in PARTS_LIST}

ROLE = {42: "SW_mainL", 9: "SW_mainR", 12: "SW_middle", 32: "SW_dpi", 21: "SW_side_fwd", 22: "SW_side_back",
        43: "EC10E", 16: "PMW3360", 30: "USB_header"}


def load_part(name):
    p = dict((n, f) for n, f, _, _ in PARTS_LIST)[name]
    s = import_step(str(p))
    sol = s.solids()
    return sol[0] if len(sol) == 1 else s


def pcb_solids():
    """Original STEP solids, each labelled from PCB_DATA components (bbox containment)."""
    pcb = ML.load_pcb()
    comps = ML.pcb_data()["components"]
    out = []
    for i, s in enumerate(pcb.solids()):
        bb = s.bounding_box()
        c = ((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2)
        sx, sy, sz = bb.max.X - bb.min.X, bb.max.Y - bb.min.Y, bb.max.Z - bb.min.Z
        if sx > 40 and sy > 40:
            lab, ci = "board", -1
        else:
            ci = -1
            best = None
            for k, cc in enumerate(comps):
                x0, y0, z0, x1, y1, z1 = cc["bbox"]
                if x0 - .05 <= c[0] <= x1 + .05 and y0 - .05 <= c[1] <= y1 + .05 and z0 - .05 <= c[2] <= z1 + .05:
                    vol = (x1 - x0) * (y1 - y0) * (z1 - z0)
                    if best is None or vol < best[0]:
                        best = (vol, k)
            ci = best[1] if best else -1
            base = ROLE.get(ci, comps[ci]["group"] + f"{ci}" if ci >= 0 else "unknown")
            sub = ""
            if ci in ROLE and ROLE[ci].startswith("SW"):
                if abs(bb.max.Z - 7.595) < 0.02 and abs(sz - 1.0) < 0.05 and min(sx, sy) < 1.3:
                    sub = "_plunger"
                elif bb.max.Z < 0.1:
                    sub = "_lead"
                else:
                    sub = "_body"
            lab = base + sub
        out.append(dict(idx=i, label=lab, comp=ci, solid=s,
                        bbox=(bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)))
    return pcb, out


def bbox_of(s, tol=0.0):
    bb = s.bounding_box()
    return (bb.min.X - tol, bb.min.Y - tol, bb.min.Z - tol, bb.max.X + tol, bb.max.Y + tol, bb.max.Z + tol)


def bb_overlap(a, b, tol=0.05):
    return all(a[i] - tol <= b[i + 3] and b[i] - tol <= a[i + 3] for i in range(3))


def common_vol(a, b, fuzzy=1e-4):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    op = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
    if not op.IsDone():
        return None
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(op.Shape(), g)
    return abs(g.Mass())


# ---------------------------------------------------------------- motion poses
BTN_AXIS = Axis((0, ML.HINGE_PIVOT[0], ML.HINGE_PIVOT[1]), (1, 0, 0))
WHEEL_AXIS = Axis((ML.ENC_PIVOT_X, ML.ENC_AXIS_Y, ML.ENC_AXIS_Z), (0, 1, 0))
SIDE_AXIS = Axis((ML.SIDE_PIVOT[0], 0, ML.SIDE_PIVOT[1]), (0, 1, 0))


def btn_stop_deg():
    """Rotation (negative about +X = nose down) at which the stop-post front-bottom corner lands on Z 1.51."""
    yc, zc = ML.HINGE_PIVOT
    y_front = ML.STOP_PAD_L[3]; dy, dz = y_front - yc, ML.STOP_POST_Z - zc
    f = lambda t: zc + dy * math.sin(-t) + dz * math.cos(t) - ML.BOARD_Z1
    lo, hi = 0.0, 0.1
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if f(m) > 0 else (lo, m)
    return -math.degrees(lo)


def wheel_stop_deg():
    """Tilt about +Y at ENC_PIVOT_X until the pin bottom at the yoke +X face meets YOKE_SLOT_BOTTOM."""
    xc, zc = ML.ENC_PIVOT_X, ML.ENC_AXIS_Z
    dx, dz = ML.YOKE_X[1] - xc, -ML.AXLE_D / 2
    f = lambda t: zc - dx * math.sin(t) + dz * math.cos(t) - ML.YOKE_SLOT_BOTTOM
    lo, hi = 0.0, 0.2
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if f(m) > 0 else (lo, m)
    return math.degrees(lo)


def rot_point(p, axis_pt, axis_dir, deg):
    import numpy as np
    p = np.asarray(p, float); o = np.asarray(axis_pt, float); k = np.asarray(axis_dir, float)
    t = math.radians(deg); v = p - o
    return o + v * math.cos(t) + np.cross(k, v) * math.sin(t) + k * np.dot(k, v) * (1 - math.cos(t))
