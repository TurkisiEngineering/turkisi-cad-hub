"""
check_rv01_a13.py - RV01 fast checks for WP-E top_shell (F-1): A1 + A13 at rest / dropped / tilted to the
middle-click stop, right rail web X span + thickness, measured on the exported top_shell.step / .stl.
Run after build_top_shell.py:  python check_rv01_a13.py   (-> check_rv01_a13.json)
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
from build123d import *          # noqa: E402,F401
import master as ML              # noqa: E402
import numpy as np               # noqa: E402
import trimesh                   # noqa: E402

PARAMS = dict(
    n_surface=400000,            # dense samples on the shell
    wheel_drop=0.30,             # spec 4.2 dropped state
    tilt_deg_review=1.943,       # tilt measured by the reviewer at the yoke-slot stop
    a13_min=0.30,                # A13 clearance (rest / dropped)
    tilt_min=0.25,               # sliding clearance at the stop (review rule 43.12 + 0.32 + 0.25)
    rail_min_t=0.8,              # min rib / web thickness
    rail_probe_z=(12.6, 14.0),   # Z band to read the right rail web X span
)
P = PARAMS
D = Path(__file__).resolve().parent
RES = []


def rec(cid, what, value, ok):
    RES.append(dict(id=cid, what=what, value=value, pass_=bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {cid:<10} {what}: {value}")


def dist_wheel(pts):
    yc, zc = ML.WHEEL_C[1], ML.WHEEL_C[2]
    x0, x1 = ML.WHEEL_X
    dr = np.maximum(np.hypot(pts[:, 1] - yc, pts[:, 2] - zc) - ML.WHEEL_D / 2, 0)
    dx = np.maximum.reduce([x0 - pts[:, 0], pts[:, 0] - x1, np.zeros(len(pts))])
    return np.hypot(dr, dx)


def to_wheel_frame(pts, phi):
    """World points -> frame of a wheel rotated by -phi about the axis X=ENC_PIVOT_X, Z=axle, along Y
    (phi > 0: the +X / yoke end of the wheel goes down, as the middle click does)."""
    px, pz = ML.ENC_PIVOT_X, ML.WHEEL_C[2]
    c, s = math.cos(phi), math.sin(phi)
    q = pts.copy()
    dx, dz = pts[:, 0] - px, pts[:, 2] - pz
    q[:, 0] = px + dx * c - dz * s
    q[:, 2] = pz + dx * s + dz * c
    return q


def main():
    T = import_step(str(D / "top_shell.step"))
    sols = T.solids()
    rec("A1", "n_solids / is_valid / volume mm3", f"{len(sols)} / {sols[0].is_valid} / {sols[0].volume:.1f}",
        len(sols) == 1 and sols[0].is_valid and sols[0].volume > 0)
    m = trimesh.load(str(D / "top_shell.stl"))
    spts, _ = trimesh.sample.sample_surface_even(m, P["n_surface"])
    spts = np.vstack([spts, m.vertices])
    near = spts[(np.abs(spts[:, 1] - ML.WHEEL_C[1]) < 16) & (spts[:, 0] > 25) & (spts[:, 0] < 55)]

    d0 = dist_wheel(near).min()
    dd = near.copy()
    dd[:, 2] += P["wheel_drop"]
    d1 = dist_wheel(dd).min()
    rec("A13", "wheel d23.6x7.5 -> top_shell min gap rest / dropped 0.30", f"{d0:.3f} / {d1:.3f}",
        d0 >= P["a13_min"] - 1e-3 and d1 >= P["a13_min"] - 1e-3)

    th_master = math.degrees(math.atan(ML.MC_TRAVEL / (ML.SW_MIDDLE[0] - ML.ENC_PIVOT_X)))
    for nm, th in (("review", P["tilt_deg_review"]), ("plunger", th_master)):
        q = to_wheel_frame(near, math.radians(th))
        dt = dist_wheel(q)
        i = int(np.argmin(dt))
        n_in = int((dt < 1e-9).sum())
        rec(f"A13_tilt_{nm}", f"wheel tilted {th:.3f} deg about X {ML.ENC_PIVOT_X} -> top_shell min gap / "
            f"samples inside / at", f"{dt.min():.3f} / {n_in} / ({near[i, 0]:.2f}, {near[i, 1]:.2f}, {near[i, 2]:.2f})",
            dt.min() >= P["tilt_min"] - 1e-3 and n_in == 0)
        # opposite direction is only reachable up to the yoke-slot up-stop (YOKE_SLOT_TOP, 0.10 above the axle)
        th_up = math.atan((ML.YOKE_SLOT_TOP - ML.WHEEL_C[2] - ML.AXLE_D / 2) / ((ML.YOKE_X[0] + ML.YOKE_X[1]) / 2 - ML.ENC_PIVOT_X))
        if nm == "plunger":
            qo = to_wheel_frame(near, -th_up)
            do = dist_wheel(qo).min()
            rec("A13_tilt_up", f"wheel tilted {math.degrees(th_up):.3f} deg the other way (yoke up-stop) min gap",
                f"{do:.3f}", do >= P["tilt_min"] - 1e-3)

    # right rail web X span (mesh vertices + samples in the window Y range, inside the tongue)
    wx0, wy0, _, wy1 = ML.WHEEL_WIN
    z0, z1 = P["rail_probe_z"]
    r = spts[(spts[:, 1] > wy0 + 1) & (spts[:, 1] < wy1 - 1) & (spts[:, 2] > z0) & (spts[:, 2] < z1)
             & (spts[:, 0] > ML.X_CL) & (spts[:, 0] < ML.X_CL + ML.TONGUE_HW + 0.5)]
    xa, xb = r[:, 0].min(), r[:, 0].max()
    rec("RAIL_R", "right rail web X span / thickness (Z 12.6..14)", f"{xa:.3f}..{xb:.3f} / {xb - xa:.3f}",
        xa >= 43.75 - 1e-3 and xb - xa >= P["rail_min_t"])
    rl = spts[(spts[:, 1] > wy0 + 1) & (spts[:, 1] < wy1 - 1) & (spts[:, 2] > z0) & (spts[:, 2] < z1)
              & (spts[:, 0] < ML.X_CL) & (spts[:, 0] > ML.X_CL - ML.TONGUE_HW - 0.5)]
    rec("RAIL_L", "left rail web X span / thickness",
        f"{rl[:, 0].min():.3f}..{rl[:, 0].max():.3f} / {rl[:, 0].max() - rl[:, 0].min():.3f}",
        rl[:, 0].max() - rl[:, 0].min() >= P["rail_min_t"] and rl[:, 0].max() <= 35.25 + 1e-3)
    zb = spts[(np.abs(spts[:, 0] - (xa + xb) / 2) < 0.3) & (spts[:, 1] > wy0 + 1)
                                          & (spts[:, 1] < wy1 - 1)][:, 2].min()
    rec("RAIL_Z", "right rail web bottom Z (=RAIL_WEB_Z, yoke top 11.5)", f"{zb:.3f}", abs(zb - ML.RAIL_WEB_Z) < 0.05)
    (D / "check_rv01_a13.json").write_text(json.dumps(RES, indent=1))
    print(f"{sum(r_['pass_'] for r_ in RES)}/{len(RES)} pass")


if __name__ == "__main__":
    main()
