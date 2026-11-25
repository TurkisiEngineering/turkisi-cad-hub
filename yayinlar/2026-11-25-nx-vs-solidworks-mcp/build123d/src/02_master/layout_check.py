"""layout_check.py - WP-C numeric verification of the master layout + raw split solids for the concept renders.
Run:  python layout_check.py     (writes out/*.stl and out/layout_check.json)
"""
import json, math, sys, time
from pathlib import Path
from build123d import *
sys.path.insert(0, str(Path(__file__).resolve().parent))
import master as ML

t0 = time.time()
OUT = ML.OUT; OUT.mkdir(exist_ok=True)
R = {}
def rec(k, v, note=""):
    R[k] = v
    print(f"{k:42s} {v}  {note}")

_c = ML._skin_c(); S, I = _c['s'], _c['i']
bb = S.bounding_box()
rec("size_LxWxH_above_floor", [round(bb.max.Y - bb.min.Y, 2), round(bb.max.X - bb.min.X, 2), round(ML.top_z(S, ML.X_CL - 1.0, -74) - ML.Z_FLOOR, 2)])
rec("hump_Z_at_Y-74", round(ML.top_z(S, 37.6, -74), 2))

# ---- main buttons -----------------------------------------------------------------------------------
for side, sw, stop in (("L", ML.SW_MAIN_L, ML.STOP_PAD_L), ("R", ML.SW_MAIN_R, ML.STOP_PAD_R)):
    zu = ML.inner_z_at(*sw)
    rec(f"btn{side}_underside_Z_over_plunger", round(zu, 2), f"nub length {zu - ML.NUB_Z:.2f} to Z {ML.NUB_Z}")
    sx, sy = (stop[0] + stop[2]) / 2, (stop[1] + stop[3]) / 2
    zs = ML.inner_z_at(sx, sy)
    rec(f"btn{side}_stop_post", round(zs - ML.STOP_POST_Z, 2), f"long, from Z {zs:.2f} to {ML.STOP_POST_Z}")
    # side split line height on the skin
    pts = ML.BTN_SIDE_L if side == "L" else [(ML.mirror_x(x), y) for x, y in ML.BTN_SIDE_L]
    zz = []
    for x, y in pts:
        if y <= -15:
            zz.append((y, round(ML.top_z(S, x, y), 2)))
    rec(f"btn{side}_side_split_skin_Z", zz)
# finger arm / lever ratio
piv_y, piv_z = ML.HINGE_PIVOT
arm_nub = piv_y * -1 + ML.SW_MAIN_L[1]  # distance in Y
rec("hinge_arm_to_nub", round(ML.SW_MAIN_L[1] - piv_y, 2), f"finger at Y -12: arm {-12 - piv_y:.1f}, ratio {(ML.SW_MAIN_L[1]-piv_y)/(-12-piv_y):.2f}")
rec("btn_tip_travel_at_full_stop", round(ML.TRAVEL_STOP * (ML.Y_TIP - piv_y) / (ML.SW_MAIN_L[1] - piv_y), 2), f"< BTN_FRONT_GAP {ML.BTN_FRONT_GAP}")
# leaf clearance under the ceiling and over the PCB
for side, xr in (("L", ML.LEAF_X_L), ("R", ML.LEAF_X_R)):
    zmin = 1e9
    for x in [xr[0] + i * (xr[1] - xr[0]) / 8 for i in range(9)]:
        for y in [ML.LEAF_FREE_Y[1] - 0.5 - i * 1.75 for i in range(9)]:
            z = ML.inner_z_at(x, y)
            if y < ML.Y_BTN_REAR - 0.25:
                zmin = min(zmin, z)
    rec(f"leaf{side}_ceiling_min_Z", round(zmin, 2), f"leaf top {ML.LEAF_Z_TOP} -> clamp pad height >= {zmin - ML.LEAF_Z_TOP:.2f}")
# tallest part under the leaves
rec("leaf_over_tallest_part", round(ML.LEAF_Z_TOP - ML.LEAF_T - ML.USB_PIN_TOP_Z, 2), "leaf bottom above USB pin tops (clear)")

# ---- tongue, wheel, DPI ----------------------------------------------------------------------------
zt = ML.top_z(S, ML.X_CL, ML.ENC_AXIS_Y); zti = ML.inner_z_at(ML.X_CL, ML.ENC_AXIS_Y)
wr = ML.WHEEL_D / 2
rec("wheel_top_Z / skin_Z_at_wheel", [round(ML.ENC_AXIS_Z + wr, 3), round(zt, 2)], f"wheel proud {ML.ENC_AXIS_Z + wr - zt:.2f}")
half = math.sqrt(wr ** 2 - (zti - ML.ENC_AXIS_Z) ** 2)
rec("wheel_chord_half_at_inner_surface", round(half, 2), f"window half {(ML.WHEEL_WIN[3]-ML.WHEEL_WIN[1])/2:.2f}")
# wheel vs DPI switch body (front face Y -40.28 at Z <= 6.595)
dz = ML.SW_BODY_TOP_Z - ML.ENC_AXIS_Z
rec("wheel_to_DPI_body_gap", round(-40.28 - (ML.ENC_AXIS_Y - math.sqrt(wr ** 2 - dz ** 2)), 2) * -1)
rec("wheel_bottom_Z", round(ML.ENC_AXIS_Z - wr, 3), f"pocket floor {ML.Z_WHEEL_POCKET}; after 0.7 click ({0.7*(ML.X_CL-ML.ENC_PIVOT_X)/(ML.SW_MIDDLE[0]-ML.ENC_PIVOT_X):.2f} drop at wheel)")
zb = ML.BOARD_Z1
rec("wheel_Y_extent_at_board_top", round(ML.ENC_AXIS_Y - math.sqrt(wr ** 2 - (ML.ENC_AXIS_Z - zb) ** 2), 2), "slot back -39.37 (chamfer -38.1)")
rec("wheel_side_gaps_slot/hub/yoke", [round(ML.WHEEL_X[0] - ML.WHEEL_NOTCH[0], 2), round(ML.WHEEL_X[0] - ML.ENC_HUB_X[1], 2),
                                       round(ML.YOKE_X[0] - ML.WHEEL_X[1], 2), round(ML.WHEEL_NOTCH[2] - ML.YOKE_X[1], 2)])
rec("yoke_slot_Z", [round(ML.YOKE_SLOT_BOTTOM, 3), round(ML.YOKE_SLOT_TOP, 3)])
rec("middle_click_force_at_wheel_N", round(1.47 * (ML.SW_MIDDLE[0] - ML.ENC_PIVOT_X) / (ML.X_CL - ML.ENC_PIVOT_X), 2), "D2F std 1.47 N; D2F-01F 0.74 N halves it")
zd = ML.inner_z_at(*ML.SW_DPI)
rec("dpi_tongue_underside_Z", round(zd, 2), f"nub length {zd - ML.NUB_Z:.2f}")
rec("tongue_strip_wheelwin_to_dpiwin", round(ML.WHEEL_WIN[1] - ML.DPI_WIN[3], 2))
rec("tongue_rails_beside_wheel", [round(ML.WHEEL_WIN[0] - (ML.X_CL - ML.TONGUE_HW), 2), round(ML.X_CL + ML.TONGUE_HW - ML.WHEEL_WIN[2], 2)])

# ---- side buttons --------------------------------------------------------------------------------------
for n, sb in ML.SIDE_BTNS.items():
    yc = (sb["y0"] + sb["y1"]) / 2
    xs = []
    for z in (-2.9, -1.6, 0, 1.0, 2.5, 3.0, 6.5, 10.0):
        g = ML.cavity_section(z)
        from shapely.geometry import LineString
        ln = LineString([(-10, yc), (40, yc)]).intersection(g)
        xs.append((z, round(ML.skin_x_at(yc, z, "L"), 2), round(ln.bounds[0], 2)))
    rec(f"side_{n}_skin_X/inner_X_by_Z", xs)
    zsp = ML.top_z(S, ML.BTN_SIDE_L[0][0], yc) if yc > ML.Y_BTN_REAR else None
    rec(f"side_{n}_strip_notch_top_to_btn_split", round(zsp - ML.SIDE_NOTCH_TOP, 2) if zsp else "n/a (behind main button)")
px, pz = ML.SIDE_PIVOT
for n, sb in ML.SIDE_BTNS.items():
    cx = sb["plunger"][0]
    arm_p = cx - px; arm_f = ML.GROOVE_ZC - pz
    rec(f"side_{n}_lever", dict(theta_deg=round(math.degrees(0.8 / arm_p), 2), thumb_travel=round(0.8 * arm_f / arm_p, 2),
                                 force_N=round(1.47 * arm_p / arm_f, 2), nub_slide_x=round(0.8 * (ML.NUB_Z - pz) / arm_p, 2)))
rec("side_cradle_vs_board_corner", round(math.hypot(ML.BOARD_BBOX[0] - px, 0 - pz) - (ML.SIDE_CRADLE_ID / 2 + 1.0), 2), "cradle OD edge to the PCB bottom-left edge")
rec("side_cradle_room_to_wall", round(ML.room_at(px - 2.15, -50.8, pz), 2), "cradle outer edge inside cavity (>=0 ok, may merge)")

# ---- screws / bosses / cable ----------------------------------------------------------------------------
for (x, y) in ML.TS_SCREWS:
    zc = ML.inner_z_at(x, y)
    rec(f"ts_boss_{x:.1f}_{y:.1f}", dict(ceiling_Z=round(zc, 2), boss_height=round(zc - ML.Z_PART, 2),
        room_at_Z2=round(ML.room_at(x, y, 2.0), 2), need=ML.TS_BOSS_OD / 2 + ML.LIP_GAP + ML.LIP_T + ML.LIP_GAP))
for i, (x, y) in enumerate(ML.CABLE_PATH[:-1]):
    rec(f"cable_pt{i}_{x}_{y}_room", [round(ML.room_at(x, y, z), 2) for z in (-3.5, -2.0, -0.4)], f"need >= {ML.CABLE_W/2:.1f}")
from shapely.geometry import LineString, Point
path = LineString(ML.CABLE_PATH[:-1])
for z in (-3.5, -2.0, -0.4):
    g = ML.cavity_section(z)
    rec(f"cable_path_min_room_Z{z}", round(min(g.exterior.distance(path.interpolate(t, normalized=True)) for t in [i / 200 for i in range(201)]), 2))
rec("cable_exit_front_face_Y", round(ML.skin_y_at(ML.CABLE_EXIT[0], ML.CABLE_EXIT[2]), 3))
rec("cable_channel_to_pcb_boss", round(ML.CABLE_PATH[3][0] - ML.CABLE_W / 2 - (ML.PCB_HOLES[1][0] + ML.PCB_BOSS_OD / 2), 2))
rec("cable_front_run_to_ts_boss", round(ML.CABLE_PATH[6][0] - ML.CABLE_W / 2 - (ML.TS_SCREWS[0][0] + ML.TS_BOSS_OD / 2), 2))
import math as _m
rec("cable_to_front_right_pcb_boss", round(LineString(ML.CABLE_PATH).distance(Point(*ML.PCB_HOLES[1])) - ML.PCB_BOSS_OD / 2 - ML.CABLE_W / 2, 2))
# skates inside the underside with >= 2 mm
gU = ML.cavity_section(ML.Z_UNDER + ML.WALL + 0.05)   # ~ footprint (inner) - conservative
from shapely.geometry import box as sbox, Point
for k, sk in ML.SKATES.items():
    if sk["kind"] == "rrect":
        cx, cy = sk["c"]; sx, sy = sk["size"]
        geom = sbox(cx - sx / 2 - 0.1, cy - sy / 2 - 0.1, cx + sx / 2 + 0.1, cy + sy / 2 + 0.1)
    else:
        geom = Point(*sk["c"]).buffer(sk["od"] / 2 + 0.1)
    rec(f"skate_{k}_margin_to_inner_footprint", round(gU.exterior.distance(geom) if gU.contains(geom) else -1, 2), "(outer edge is a further 1.8 out)")

# ---- PCB clearances ---------------------------------------------------------------------------------------
rows = ML.pcb_clearances()
rec("pcb_min_clearance_to_cavity", [(round(d, 2), n) for d, n, _ in rows[:4]])
rec("lead_tip_to_floor", round(ML.THT_TIP_Z - ML.Z_INNER_FLOOR, 3))
rec("lens_plane_above_floor", round(ML.Z_LENS_PLANE - ML.Z_FLOOR, 3), "datasheet 2.4 (2.2-2.6)")
rec("pcb_top_to_floor", round(ML.BOARD_Z1 - ML.Z_FLOOR, 3), "datasheet 7.40 (real 1.6 board: %.2f)" % (ML.BOARD_Z1_REAL - ML.Z_FLOOR))

# ---- raw split solids for the renders -----------------------------------------------------------------
t1 = time.time()
parts = {}
parts["top_shell_raw"] = ML.top_shell_raw()
parts["bottom_shell_raw"] = ML.bottom_shell_raw()
parts["button_L_raw"] = ML.button_panel_raw("L")
parts["button_R_raw"] = ML.button_panel_raw("R")
for k, v in parts.items():
    c = ML.check_part(v, k)
    rec(f"raw_{k}", c)
    export_stl(v, str(OUT / f"{k}.stl"), tolerance=0.03, angular_tolerance=0.15)
export_stl(S, str(OUT / "skin.stl"), tolerance=0.03, angular_tolerance=0.15)
rec("raw_build_s", round(time.time() - t1, 1))
(OUT / "layout_check.json").write_text(json.dumps(R, indent=1, default=str))
print(f"done {time.time() - t0:.1f}s")
