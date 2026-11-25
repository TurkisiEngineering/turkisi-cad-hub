"""
master.py - WP-C master layout for the DIY gaming mouse shell around mouse_pcb.step.

ONE importable build123d module. Every part builder (WP-D..WP-H) does

    import sys; sys.path.insert(0, r"C:\\Users\\marya\\Desktop\\Mouse for PCB\\work\\02_master")
    import master as M

and uses ONLY the constants / helpers below for anything that touches another part.
Builders must NOT edit this file. If an interface is wrong, report it to the lead.

Frame: native STEP coordinates of the PCB, mm. +X right, +Y FRONT, +Z up (component side).
The PCB is never moved: board bottom Z 0, top Z 1.51 (STEP) / 1.6 (real), parts seated at Z 1.595.
Tracking surface (mouse pad) = plane Z = Z_FLOOR.

Run `python master.py` for the self-test (builds skin + inner, checks validity and PCB clearances,
writes STLs for the concept renders into 02_master/out/).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator

from build123d import (Axis, Box, Compound, Edge, Face, Kind, Location, Plane, Pos, Rot, Solid, Vector, Wire,
                       export_step, export_stl, import_step)

# ----------------------------------------------------------------------------------------------------
# paths
# ----------------------------------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
WORK = HERE.parent
ROOT = WORK.parent
PCB_STEP = ROOT / "mouse_pcb.step"
PCB_JSON = WORK / "00_pcb" / "PCB_DATA.json"
PCB_STL = WORK / "00_pcb" / "pcb.stl"
PARTS_DIR = WORK / "03_parts"          # builders write <PARTS_DIR>/<part>/<part>.step + .stl
RENDERS = WORK / "renders"
CACHE = HERE / "cache"
OUT = HERE / "out"

# ====================================================================================================
# 1. PCB (read-only facts, native coords)
# ====================================================================================================
BOARD_Z0 = 0.0
BOARD_Z1 = 1.51              # STEP board top
BOARD_Z1_REAL = 1.60         # real board top (brief) - parts that bear on the board top use this tolerance
SEAT_Z = 1.595               # component seating plane in the STEP
BOARD_BBOX = (14.478, -76.454, 64.262, -14.732)          # xmin, ymin, xmax, ymax
BOARD_OUTLINE = [(33.02, -38.1), (33.02, -15.24), (32.512, -14.732), (14.986, -14.732), (14.478, -15.24),
                 (14.478, -75.946), (14.986, -76.454), (63.754, -76.454), (64.262, -75.946), (64.262, -15.24),
                 (63.754, -14.732), (46.228, -14.732), (45.72, -15.24), (45.72, -38.1), (44.45, -39.37),
                 (34.29, -39.37)]
WHEEL_NOTCH = (33.02, -39.37, 45.72, -14.732)             # board notch for the wheel (open to the front)
SENSOR_CUTOUT = (35.07, -65.88, 43.67, -48.62)            # closed board cut-out for the lens
PCB_HOLES = [(16.51, -16.764), (62.23, -16.764), (16.51, -74.422), (62.23, -74.422)]   # 4x d2.2 (M2)
PCB_HOLE_D = 2.2
THT_TIP_Z = -1.905           # lowest lead tip under the board (D2F, EC10E); PDIP / header -1.405

# D2F switches: plunger top Z 7.595 (= free position), plunger box 2.9 x 1.2 (main/mid) or 1.2 x 2.9 (DPI/side)
PLUNGER_TOP_Z = 7.595
SW_MAIN_L = (20.32, -23.53)  # actuator XY, plunger 2.9(X) x 1.2(Y)
SW_MAIN_R = (58.42, -23.53)
SW_MIDDLE = (50.80, -27.975)  # under the wheel axle line
SW_DPI = (40.04, -43.18)      # plunger 1.2(X) x 2.9(Y)
SW_SIDE_FWD = (20.99, -50.80)  # plunger 1.2(X) x 2.9(Y), pushes -Z
SW_SIDE_BACK = (20.99, -68.58)
SW_BODY_TOP_Z = 6.595
SW_BODIES = {   # body boxes (x0,y0,z0,x1,y1,z1) from PCB_DATA.json
    "main_L": (17.42, -31.80, 1.595, 23.22, -19.00, 6.595),
    "main_R": (55.52, -31.80, 1.595, 61.32, -19.00, 6.595),
    "middle": (47.90, -36.245, 1.595, 53.70, -23.445, 6.595),
    "dpi": (35.51, -46.08, 1.595, 48.31, -40.28, 6.595),
    "side_fwd": (16.46, -53.70, 1.595, 29.26, -47.90, 6.595),
    "side_back": (16.46, -71.48, 1.595, 29.26, -65.68, 6.595),
}

# EC10E encoder (placeholder in STEP; real part = hollow shaft with hex 1.73 A/F)
ENC_BODY = (25.78, -32.70, 1.595, 30.18, -23.10, 12.595)
ENC_AXIS_Y = -27.9
ENC_AXIS_Z = 8.595           # H = 7 variant as in the STEP. RISK: EC10E1220501 lists H = 9 (Z 10.595)
ENC_HUB_X = (23.98, 31.98)   # hub faces; wheel side hub face = 31.98
ENC_HUB_D = 5.2
ENC_HEX_AF = 1.73            # hex hole across flats in the rotor (+0.05/0)
ENC_HEX_DEPTH = 1.7
ENC_PIVOT_X = 31.0           # middle-click tilt pivot (axle tilts about the hex, 3 deg flare)

# PMW3360 + LM19-LSI lens (datasheet stack-up, CONSTRAINTS.md section 1)
OPT_C = (39.37, -57.44)      # optical centre (datasheet Fig.3 from pin 1) - use this, not the pad centroid
SENSOR_BODY = (33.77, -64.62, 1.595, 44.97, -48.42, 4.895)

# USB 1x4 header (cable soldered to the pins, no Dupont housing)
USB_PINS = [(20.33, -74.676), (22.87, -74.676), (25.41, -74.676), (27.95, -74.676)]
USB_PIN_TOP_Z = 10.135

# ====================================================================================================
# 2. Z stack (sensor sets it)  - CONSTRAINTS.md section 1
# ====================================================================================================
Z_FLOOR = -5.85              # tracking surface = PCB top - 7.40 (PMW3360 Fig.4); lens Z = 2.40
Z_LENS_PLANE = -3.45         # LM19-LSI reference plane (flange bottom)
SKATE_T = 0.80               # PTFE skate incl. adhesive
SKATE_RECESS = 0.35          # skate recess depth in the underside -> skate 0.45 proud
Z_UNDER = Z_FLOOR + SKATE_T - SKATE_RECESS      # -5.40 shell underside (outside the recesses)
Z_INNER_FLOOR = -2.90        # bottom shell floor top under the PCB (datasheet base-plate gap 2.90)
Z_LENS_POCKET = -3.50        # lens pocket floor (0.05 below the lens plane, no preload)
Z_PART = 1.00                # parting plane: bottom shell below, top shell above (flat, top shell prints rim-down)
Z_BOSS_TOP = 0.00            # PCB rests on 4 boss tops at Z 0

# ====================================================================================================
# 3. Overall shape (right-handed, palm/claw)  - CONSTRAINTS.md section 4
# ====================================================================================================
X_CL = 39.37                 # mouse centreline = PCB centre = sensor X
Y_TIP = -4.0                 # front face plane
Y_TAIL = -124.0              # rear face plane  -> length 120.0
Z_HUMP = 34.15               # 40.0 above the floor
WALL = 1.80                  # shell / button panel wall (normal thickness of the skin offset)
NOSE_R = 6.0                 # fillet on the front cap edge
TAIL_R = 6.0                 # fillet on the rear cap edge

# key tables (Y ascending). Smooth PCHIP interpolation.
_Y_TOP = [-124, -121, -116, -108, -98, -86, -74, -62, -52, -40, -34, -28, -24, -18, -10, -6, -4]
_Z_TOP = [9.0, 13.0, 17.5, 23.2, 29.0, 33.2, 34.15, 31.8, 27.6, 21.4, 19.0, 17.2, 16.7, 15.6, 12.8, 10.8, 9.4]
_Y_W = [-124, -122, -119, -115, -109, -102, -94, -86, -75, -62, -50, -40, -30, -20, -14, -10, -7, -5.2, -4]
_A_L = [13.0, 18.0, 22.0, 25.5, 28.2, 29.8, 30.8, 31.3, 31.5, 31.5, 31.4, 31.2, 31.0, 30.7, 30.3, 29.4, 27.3, 24.8, 22.5]
_A_R = [13.5, 18.5, 22.5, 26.0, 28.8, 30.4, 31.4, 31.8, 32.0, 32.0, 32.0, 31.9, 31.8, 31.6, 31.3, 30.5, 28.5, 26.0, 23.5]
_Y_C = [-124, -62, -30, -4]
_X_C = [37.6, 37.6, 39.37, 39.37]          # crown (ridge) X: shifted 1.8 to the thumb side over the palm
_Y_N = [-124, -100, -50, -16, -4]
_N_T = [2.6, 3.0, 3.0, 2.9, 2.6]                # top superellipse exponent (bigger = flatter top, steeper sides)
Z_W = -1.0                   # Z of maximum width
Z_BOT_EXT = Z_UNDER - 11.0   # section bottom extension (cut at Z_UNDER -> nearly vertical lower wall)
N_BOT = 4.0
# thumb groove (left side, where the side buttons are)
GROOVE_DEPTH = 2.6
GROOVE_ZC = 6.5
GROOVE_SZ = 5.0
GROOVE_Y = (-98.0, -88.0, -40.0, -30.0)    # ramp-in, full, full, ramp-out

_f_top = PchipInterpolator(_Y_TOP, _Z_TOP)
_f_al = PchipInterpolator(_Y_W, _A_L)
_f_ar = PchipInterpolator(_Y_W, _A_R)
_f_xc = PchipInterpolator(_Y_C, _X_C)
_f_nt = PchipInterpolator(_Y_N, _N_T)


def _smoothstep(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def groove_weight(y):
    a, b, c, d = GROOVE_Y
    return _smoothstep((y - a) / (b - a)) * _smoothstep((d - y) / (d - c))


def section_points(y, n=72):
    """Closed outer-skin section at Y=y as a list of (x, y, z) (before the Z_UNDER cut)."""
    zt = float(_f_top(y)); al = float(_f_al(y)); ar = float(_f_ar(y))
    xc = float(_f_xc(y)); nt = float(_f_nt(y))
    XL, XR = X_CL - al, X_CL + ar
    gw = groove_weight(y) * GROOVE_DEPTH
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        nn = nt if s >= 0 else N_BOT
        e = 2.0 / nn
        cx = math.copysign(abs(c) ** e, c)
        sz = abs(s) ** e
        x = xc + (XR - xc) * cx if c >= 0 else xc + (xc - XL) * cx
        z = Z_W + (zt - Z_W) * sz if s >= 0 else Z_W - (Z_W - Z_BOT_EXT) * sz
        if c < 0 and gw > 0:
            x += gw * math.exp(-((z - GROOVE_ZC) / GROOVE_SZ) ** 2)
        pts.append((x, y, z))
    return pts


Y_STATIONS = [-4.0, -5.0, -6.5, -8.5, -11.0, -14.0, -18.0, -24.0, -30.0, -38.0, -46.0, -54.0, -62.0, -70.0, -78.0,
              -86.0, -94.0, -102.0, -109.0, -115.0, -119.5, -122.5, -124.0]


def z_top(y):
    return float(_f_top(y))


# ====================================================================================================
# 4. Splits: parting plane, button split lines, windows
# ====================================================================================================
BTN_GAP = 0.50               # visible gap on every button split line (centre line +/- 0.25)
BTN_FRONT_GAP = 1.40         # gap at the nose split (Z = Z_BTN_LOW): button tip moves ~1.2 down at full travel
Z_BTN_LOW = 6.0              # nose split plane: below it the top-shell front band, above it the buttons
TONGUE_HW = 5.5              # top-shell centre tongue half width (between the main buttons): X 33.87..44.87
Y_BTN_REAR = -60.0           # rear split line of the main buttons
# outer (side) split line of the LEFT main button in plan, (x, y) points from rear to front; R is the mirror
BTN_SIDE_L = [(14.3, -60.0), (13.9, -45.0), (13.7, -30.0), (13.7, -15.0), (13.0, 10.0)]


def mirror_x(x):
    return 2 * X_CL - x


def btn_region_pts(side):
    """Plan polygon (split CENTRE lines) of a main button region, CCW. side 'L' or 'R'."""
    xin = X_CL - TONGUE_HW - BTN_GAP / 2.0
    pts = [(xin, Y_BTN_REAR), (xin, 10.0)] + [(x, y) for (x, y) in reversed(BTN_SIDE_L)]
    # pts: inner rear -> inner front -> side front -> ... -> side rear  (closing back to inner rear)
    if side == "R":
        pts = [(mirror_x(x), y) for (x, y) in reversed(pts)]
    return pts


# --- main buttons (WP-F) -----------------------------------------------------------------------------
NUB_REST_GAP = 0.10          # nub face to plunger top at rest
NUB_Z = PLUNGER_TOP_Z + NUB_REST_GAP      # 7.695 nub contact face
NUB_PAD = (3.5, 2.5)         # main nub pad X x Y (plunger 2.9 x 1.2)
TRAVEL_STOP = 0.80           # hard stop: total nub travel from rest (0.10 gap + 0.70 = PT 0.5 + 0.2 OT)
STOP_PAD_L = (15.2, -25.0, 16.9, -22.0)   # main-L stop post footprint, lands on the free PCB strip X 14.48..17.42
STOP_PAD_R = (mirror_x(16.9), -25.0, mirror_x(15.2), -22.0)
STOP_POST_Z = BOARD_Z1 + TRAVEL_STOP      # 2.31 stop post bottom at rest (on the 1.6 board: 2.31-1.60 = 0.71)
# rear flexure leaf (PETG), clamped under a top-shell pad with one M2 self-tap screw from below
LEAF_W = 16.0
LEAF_T = 1.0
LEAF_Z_TOP = 20.0            # leaf top face = clamp pad face (top shell)
LEAF_WEB_Y = (-59.4, -57.8)  # button web (drops from the panel to the leaf), 1.6 thick
LEAF_FREE_Y = (-67.4, -59.4) # free flexure length 8.0
LEAF_CLAMP_Y = (-73.4, -67.4)
LEAF_X_L = (15.5, 31.5)
LEAF_X_R = (mirror_x(31.5), mirror_x(15.5))
LEAF_SCREW_L = (23.5, -70.4)
LEAF_SCREW_R = (mirror_x(23.5), -70.4)
HINGE_PIVOT = (-63.4, 19.5)  # (Y, Z) of the flexure pivot line (along X)
LEAF_PIN_DX = 5.5            # 2 locating pins d1.5 x 1.0 on the clamp pad at screw X +/- 5.5 (leaf holes d1.7)
LEAF_PIN_D = 1.5
LEAF_SCREW_PILOT = (1.6, 5.0)  # pad pilot d, min depth (PLA); leaf hole d2.4; M2x6 + M2 washer from below
STOP_POST_XY = (1.7, 3.0)

# --- top-shell windows (WP-E cuts, WP-G / WP-H parts sit in them) ------------------------------------
WHEEL_D = 23.6               # incl. tyre (top Z 20.395, ~3.1 proud of the button surface)
WHEEL_W = 7.5
WHEEL_C = (X_CL, ENC_AXIS_Y, ENC_AXIS_Z)
WHEEL_X = (X_CL - WHEEL_W / 2, X_CL + WHEEL_W / 2)    # 35.62 .. 43.12
WHEEL_WIN = (X_CL - WHEEL_W / 2 - 0.30, ENC_AXIS_Y - 10.15, X_CL + WHEEL_W / 2 + 0.30, ENC_AXIS_Y + 10.15)
DPI_CAP = (SW_DPI[0] - 3.0, SW_DPI[1] - 2.5, SW_DPI[0] + 3.0, SW_DPI[1] + 2.5)    # 6 x 5 cap, plan
DPI_GAP = 0.30
DPI_WIN = (DPI_CAP[0] - DPI_GAP, DPI_CAP[1] - DPI_GAP, DPI_CAP[2] + DPI_GAP, DPI_CAP[3] + DPI_GAP)
DPI_NUB_PAD = (2.5, 3.5)     # X x Y (plunger 1.2 x 2.9)
DPI_GUIDE_Z = 13.5           # bottom of the guide sleeve hanging from the tongue
DPI_GUIDE_CLR = 0.15         # sleeve inner = DPI_CAP + 0.15 per side, sleeve wall 1.0
DPI_FLANGE = 1.0             # cap flange 1.0 wider per side, 1.0 thick, top at DPI_GUIDE_Z - 0.15 when the nub rests on the plunger
# side buttons: top-shell NOTCHES open at the rim (top shell drops on vertically over the face plates)
SIDE_GAP = 0.30
SIDE_BTNS = {
    "fwd": dict(plunger=SW_SIDE_FWD, y0=-57.8, y1=-43.8),
    "back": dict(plunger=SW_SIDE_BACK, y0=-75.6, y1=-61.6),
}
SIDE_FACE_Z = (3.0, 10.0)    # face plate Z range (centre 6.5 = groove centre, 12.35 above the floor)
SIDE_FACE_R = 2.5            # top corner radius of the face
SIDE_NOTCH_TOP = SIDE_FACE_Z[1] + SIDE_GAP       # notch in the top shell: Z_PART .. 10.3, Y y0-0.3 .. y1+0.3
SIDE_TAB_TOP = SIDE_FACE_Z[0] - SIDE_GAP         # bottom-shell wall rises to 2.7 under each face (fills the notch)
SIDE_PROUD = 1.0             # face stands 1.0 proud of the skin
SIDE_PIVOT = (12.2, -1.6)    # (X, Z) of the lever pivot axis (along Y); pin d2.0 in bottom-shell C-cradles
SIDE_PIN_D = 2.0
SIDE_CRADLE_ID = 2.30        # 0.15 radial clearance, 270 deg wrap, opening to +Z
SIDE_ARM_Z_MIN = 8.40        # lever arm underside (except the nub) at rest
SIDE_NUB_PAD = (3.5, 2.5)    # X x Y; centre 0.4 to -X of the plunger (nub slides +0.85 X over the travel)
SIDE_NUB_DX = -0.4
SIDE_CRADLE_LEN = 3.0        # two cradles per lever, centred at y0 + 1.8 and y1 - 1.8
SIDE_STOP_GAP = 0.22         # lever stop face to the board left edge (X 14.478) at Z 0.2..1.3 -> 0.8 nub travel
SIDE_BODY_X0 = 12.3          # lever body plate inside the wall starts at X >= 12.3 (cavity wall X 11.6 at Z 3)

# --- scroll wheel, axle, yoke (WP-G) -------------------------------------------------------------------
AXLE_D = 2.0
AXLE_X = (30.10, 52.30)      # hex end in the encoder (30.10..31.98+), free end rests on the middle plunger
MC_TRAVEL = 0.70             # middle click travel at the plunger (PT 0.5 + 0.2)
YOKE_X = (44.10, 45.30)      # yoke plate (separate part), stands in the PCB slot right of the wheel
YOKE_Y = (-31.90, -23.90)
YOKE_SOCKET = (43.95, -32.05, 45.45, -23.75)   # pocket in the bottom-shell floor, Z_INNER_FLOOR-1.5 .. floor
YOKE_SOCKET_DEPTH = 1.5
YOKE_SLOT_W = AXLE_D + 0.25
YOKE_SLOT_TOP = ENC_AXIS_Z + AXLE_D / 2 + 0.10                  # up-stop 9.695
_yx = (YOKE_X[0] + YOKE_X[1]) / 2
YOKE_SLOT_BOTTOM = ENC_AXIS_Z - AXLE_D / 2 - MC_TRAVEL * (_yx - ENC_PIVOT_X) / (SW_MIDDLE[0] - ENC_PIVOT_X)
YOKE_TOP_Z = 11.5            # yoke top (top-shell rail webs stop at Z 12.5)
AXLE_HEX_AF = 1.70           # printed/filed hex on the axle (rotor hole 1.73 +0.05/0)
AXLE_HEX_X = (30.10, 32.00)  # hex length 1.9 (rotor hex depth 1.7)
WHEEL_TYRE_T = 1.5           # optional TPU 95A tyre (or O-ring cord 2.0 in a 1.4 deep groove)
RAIL_WEB_Z = 12.5            # top-shell rail webs beside the wheel window end at this Z
WHEEL_POCKET = (X_CL - WHEEL_W / 2 - 0.6, -32.4, X_CL + WHEEL_W / 2 + 0.6, -23.4)  # bottom-shell pocket to Z -3.9
Z_WHEEL_POCKET = -4.10

# ====================================================================================================
# 5. Screws, skates, cable (WP-D / WP-E)
# ====================================================================================================
# PCB -> bottom shell: 4x M2x6 self-tap from above into bosses (top Z 0, OD 4.5, pilot 1.6 PLA / 1.7 PETG)
PCB_BOSS_OD = 4.5
PCB_BOSS_PILOT = 1.6
PCB_SCREW_HEAD_D = 3.5       # pan/button head max (front heads are 0.34 from the D2F bodies)
# top shell -> bottom shell: 3x M2 from below, heat-set insert M2x3 in top-shell bosses
TS_SCREWS = [(X_CL, -10.8), (27.37, -98.0), (51.37, -98.0)]
TS_BOSS_OD = 6.0
TS_INSERT_HOLE = (3.2, 4.0)  # d, depth (from the boss bottom face at Z_PART)
TS_CLEAR_D = 2.4             # bottom shell through hole
TS_CBORE = (4.4, -3.25)      # counterbore d, its top (head seat) Z - head top sits >= 0.2 below the skate recess floor
TS_SCREW = "M2x8 ISO 7380 / DIN 912, head d<=3.8"
# joint lip on the bottom shell (goes up inside the top-shell wall)
LIP_GAP = 0.15
LIP_T = 1.0
LIP_H = 1.5                  # Z_PART .. 2.5
LIP_NOTCH_EXTRA = 0.5        # lip stops 0.5 before/after each side notch
# skates (PTFE 0.8, recess 0.35, pocket = skate + 0.2): (kind, params)
SKATES = {
    "front": dict(kind="rrect", c=(X_CL, -10.6), size=(31.0, 6.4), r=3.0),
    "rear": dict(kind="rrect", c=(X_CL, -98.0), size=(36.0, 11.0), r=4.0),
    "sensor": dict(kind="ring", c=OPT_C, od=22.0, id=14.0),
}
# lens + optical hole (bottom shell) CONSTRAINTS.md section 1
LENS_POCKET = dict(c=OPT_C, size_x=19.6, size_y=22.2, r=7.0, z=Z_LENS_POCKET)
OPT_HOLE = dict(c=OPT_C, size_x=4.0, size_y=6.0, z_top=Z_LENS_POCKET, flare_deg=45.0)
# cable (Ø3.5 max, soldered to the header pins) - channel floor Z -3.9, width 4.0
CABLE_D = 3.5
CABLE_W = 4.0
Z_CABLE_FLOOR = -3.90
CABLE_PATH = [(24.1, -76.8), (24.1, -80.0), (66.6, -80.0), (66.6, -22.0), (66.5, -14.0), (60.0, -9.8), (46.5, -9.8),
              (46.5, -3.0)]   # centre line at Z -2.15; runs UNDER the board edge near (64.3,-15) (board is Z 0..1.51)
CABLE_EXIT = (46.5, Y_TIP, Z_CABLE_FLOOR + CABLE_D / 2)   # hole d3.8 through the front wall, axis +Y
CABLE_RELIEF_Y = (-50.0, -40.0, -30.0)                     # zig-zag posts in the right channel (alternate sides)
# PCB support ribs under the board (bottom shell, top Z 0) at the main-button stop pads
PCB_RIBS = [(15.2, -26.0, 16.9, -21.0), (mirror_x(16.9), -26.0, mirror_x(15.2), -21.0)]

# ====================================================================================================
# 6. Printing / clearance rules (used by self-checks)
# ====================================================================================================
MIN_WALL = 1.6
CLR_PCB = 1.0                # shell (any wall) to any PCB component
CLR_SLIDE = 0.25
OVERHANG_MAX_DEG = 45.0

PART_NAMES = ["bottom_shell", "top_shell", "button_L", "button_R", "wheel", "wheel_yoke", "dpi_button",
              "side_btn_fwd", "side_btn_back"]          # + optional "wheel_tyre"
TS_BOTTOM_BOSS_OD = 6.0      # bottom shell column under each TS screw: floor .. Z_PART


def part_dir(name):
    p = PARTS_DIR / name
    p.mkdir(parents=True, exist_ok=True)
    return p


# ====================================================================================================
# 7. Geometry helpers
# ====================================================================================================
def box(x0, y0, z0, x1, y1, z1):
    return Solid.make_box(x1 - x0, y1 - y0, z1 - z0).moved(Location((x0, y0, z0)))


def prism_xy(pts, z0, z1):
    """Vertical prism from a closed plan polygon [(x,y),...]."""
    w = Wire.make_polygon([Vector(x, y, z0) for x, y in pts], close=True)
    return Solid.extrude(Face(w), Vector(0, 0, z1 - z0))


def rrect_face_xy(cx, cy, sx, sy, r, z=0.0):
    from build123d import RectangleRounded
    f = RectangleRounded(sx, sy, r)
    return f.moved(Location((cx, cy, z)))


def _offset_section_points(y, d, n=72, h=0.25):
    """Section at y moved d INWARD along the true 3D surface normal of the loft (finite differences in t and y)."""
    P = np.array(section_points(y, n)); Pa = np.array(section_points(y + h, n)); Pb = np.array(section_points(y - h, n))
    dt = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    dy = Pa - Pb
    nrm = np.cross(dt, dy)
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    c = P.mean(axis=0)
    radial = P - c; radial[:, 1] = 0
    sgn = np.sign((nrm * radial).sum(axis=1).sum())   # make it point outward
    nrm *= sgn
    return P - d * nrm


def _build_offset_body(d):
    """Body bounded by the skin offset inward by d: lateral = normal-offset loft, bottom Z_UNDER+d,
    caps Y_TIP-d / Y_TAIL+d with fillets NOSE_R-d / TAIL_R-d. (OCC BRepOffset segfaults on this skin.)"""
    wires = []
    for y in Y_STATIONS:
        pts = _offset_section_points(y, d) if d > 0 else np.array(section_points(y))
        e = Edge.make_spline([Vector(*map(float, p)) for p in pts], periodic=True)
        wires.append(Wire([e]))
    loft = Solid.make_loft(wires, ruled=False)
    zb, yt, yr = Z_UNDER + d, Y_TIP - d, Y_TAIL + d
    s = loft & box(-20, yr, zb, 100, yt, 80)
    s = s.solids()[0] if hasattr(s, "solids") else s
    for yy, r in ((yt, NOSE_R - d), (yr, TAIL_R - d)):
        if r <= 0.2:
            continue
        cap = [f for f in s.faces() if abs(f.center().Y - yy) < 1e-3 and abs(f.normal_at().Y) > 0.99][0]
        edges = [e for e in cap.edges() if not (abs(e.center().Z - zb) < 1e-3 and
                                                abs(e.bounding_box().max.Z - zb) < 1e-3)]
        s = s.fillet(r, edges)
        s = s.solids()[0] if hasattr(s, "solids") else s
    return s


_SHAPE_KEYS = ["_Y_TOP", "_Z_TOP", "_Y_W", "_A_L", "_A_R", "_Y_C", "_X_C", "_Y_N", "_N_T", "Z_W", "Z_BOT_EXT", "N_BOT",
               "GROOVE_DEPTH", "GROOVE_ZC", "GROOVE_SZ", "GROOVE_Y", "Y_STATIONS", "Z_UNDER", "Y_TIP", "Y_TAIL",
               "NOSE_R", "TAIL_R", "WALL", "X_CL"]


def _param_hash():
    blob = json.dumps({k: globals()[k] for k in _SHAPE_KEYS}, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:12]


def _cached(name, builder):
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{name}_{_param_hash()}.brep"
    if f.exists():
        from OCP.BRepTools import BRepTools
        from OCP.BRep import BRep_Builder
        from OCP.TopoDS import TopoDS_Shape, TopoDS
        sh = TopoDS_Shape()
        BRepTools.Read_s(sh, str(f), BRep_Builder())
        from OCP.TopAbs import TopAbs_SOLID
        from OCP.TopExp import TopExp_Explorer
        ex = TopExp_Explorer(sh, TopAbs_SOLID)
        return Solid(TopoDS.Solid_s(ex.Current()))
    s = builder()
    from OCP.BRepTools import BRepTools
    BRepTools.Write_s(s.wrapped, str(f))
    return s


def _build_skin():
    return _build_offset_body(0.0)


def skin() -> Solid:
    """OUTER SKIN solid (underside at Z_UNDER, skates not included). Cached."""
    return _cached("skin", _build_skin)


def inner() -> Solid:
    """Skin offset inward by WALL (the cavity). Its bottom face is at Z_UNDER + WALL; the bottom shell sets its
    own floor (Z_INNER_FLOOR under the PCB)."""
    return _cached("inner", lambda: _build_offset_body(WALL))


def inner_offset(d) -> Solid:
    """Skin offset inward by d (d > 0). E.g. inner_offset(WALL + LIP_GAP) = lip outer face."""
    return _cached(f"inner_{d:.3f}", lambda: _build_offset_body(d))


def shell_wall() -> Solid:
    """Skin minus inner = the full 1.8 wall (top + sides + 1.8 bottom)."""
    return _cached("wall", lambda: (skin() - inner()).solids()[0])


def above(z, z1=80.0):
    return box(-20, -140, z, 100, 20, z1)


def below(z, z0=-20.0):
    return box(-20, -140, z0, 100, 20, z)


def button_prism(side, grow=0.0):
    """Main-button region prism. grow = -BTN_GAP/2 for the button itself, +BTN_GAP/2 for the top-shell cut.
    Includes the nose split: the prism starts at Z_BTN_LOW - grow_front."""
    pts = btn_region_pts(side)
    w = Wire.make_polygon([Vector(x, y, 0) for x, y in pts], close=True)
    if abs(grow) > 1e-9:
        w = w.offset_2d(grow, kind=Kind.INTERSECTION)
    gz = BTN_FRONT_GAP / 2 if grow < 0 else -BTN_FRONT_GAP / 2
    z0 = Z_BTN_LOW + gz
    return Solid.extrude(Face(w).moved(Location((0, 0, z0))), Vector(0, 0, 80 - z0))


def button_panel_raw(side):
    """Skin wall inside the button region (no nub, no leaf). WP-F adds features."""
    # (skin & prism) - inner is robust; wall & prism fails in OCC for this skin
    return ((skin() & button_prism(side, -BTN_GAP / 2)) - inner()).solids()[0]


def wheel_window_prism():
    x0, y0, x1, y1 = WHEEL_WIN
    return box(x0, y0, 10.0, x1, y1, 40.0)


def dpi_window_prism():
    x0, y0, x1, y1 = DPI_WIN
    return box(x0, y0, 10.0, x1, y1, 40.0)


def side_face_profile(name, grow=0.0, z_from=None):
    """YZ rounded-top rectangle of a side button face, extruded across X 0..20 (cuts the left wall only).
    grow > 0 enlarges. z_from overrides the bottom Z (notch: Z_PART-1)."""
    sb = SIDE_BTNS[name]
    y0, y1 = sb["y0"] - grow, sb["y1"] + grow
    z0 = (SIDE_FACE_Z[0] - grow) if z_from is None else z_from
    z1 = SIDE_FACE_Z[1] + grow
    r = SIDE_FACE_R + grow
    # rounded only at the top corners: union of box + 2 cylinders
    core = box(0, y0, z0, 20, y1, z1 - r) + box(0, y0 + r, z1 - r, 20, y1 - r, z1)
    for yc in (y0 + r, y1 - r):
        cyl = Solid.make_cylinder(r, 20, Plane(origin=(0, yc, z1 - r), x_dir=(0, 1, 0), z_dir=(1, 0, 0)))
        core = core + cyl
    return core.solids()[0] if hasattr(core, "solids") else core


def side_notch_prism(name):
    """Top-shell notch (open at the rim) for a side button."""
    return side_face_profile(name, grow=SIDE_GAP, z_from=Z_PART - 1.0)


def _one(shape, what):
    sols = shape.solids() if shape is not None else []
    if not sols:
        raise RuntimeError(f"{what}: boolean failed (no solid)")
    sols = sorted(sols, key=lambda q: -q.volume)
    return sols[0] if len(sols) == 1 else Compound(sols)


def top_shell_raw():
    """Top shell WITHOUT bosses/pads/ribs: wall above Z_PART minus button regions, wheel + DPI windows, side notches.
    (Boolean order matters: (skin & box) - cutters - inner. 'shell_wall() & x' fails in OCC for this skin.)"""
    s = skin() & above(Z_PART)
    for side in "LR":
        s = s - button_prism(side, +BTN_GAP / 2)
    s = s - wheel_window_prism() - dpi_window_prism()
    for n in SIDE_BTNS:
        s = s - side_notch_prism(n)
    s = s - inner()
    return _one(s, "top_shell_raw")


def bottom_shell_raw():
    """Bottom shell envelope WITHOUT features: skin below Z_PART, cavity floor at Z_INNER_FLOOR, + lip + notch tabs.
    (WP-D adds bosses, pockets, lens pocket, optical hole, skates, cable channel, side cradles, yoke socket...)"""
    zt = max(Z_PART + LIP_H, SIDE_TAB_TOP)
    s = skin() & box(-20, -140, -20, 100, 20, zt)
    # keep: below Z_PART everything outside the cavity floor; above Z_PART only the lip ring and the notch tabs
    keep_up = (inner_offset(WALL + LIP_GAP) - inner_offset(WALL + LIP_GAP + LIP_T)) & box(-20, -140, Z_PART - 0.01, 100, 20, Z_PART + LIP_H)
    for n, sb in SIDE_BTNS.items():          # lip interrupted behind the side-button notches (the tab fills the notch)
        keep_up = keep_up - box(-20, sb["y0"] - SIDE_GAP - LIP_NOTCH_EXTRA, -10, 30, sb["y1"] + SIDE_GAP + LIP_NOTCH_EXTRA, 20)
    for n in SIDE_BTNS:                       # wall tabs filling the lower part of each notch, up to SIDE_TAB_TOP
        keep_up = keep_up + (side_face_profile(n, grow=SIDE_GAP - 0.15, z_from=Z_PART - 0.5) & box(-20, -140, Z_PART - 0.5, 100, 20, SIDE_TAB_TOP))
    s = s - (above(Z_PART) - keep_up)          # remove everything above Z_PART except the lip/tabs
    s = s - (inner() & box(-20, -140, Z_INNER_FLOOR, 100, 20, zt + 1))   # cavity down to the floor
    return _one(s, "bottom_shell_raw")


# ----------------------------------------------------------------------------------------------------
# PCB helpers
# ----------------------------------------------------------------------------------------------------
_PCB = None


def pcb_data():
    global _PCB
    if _PCB is None:
        _PCB = json.loads(PCB_JSON.read_text())
    return _PCB


def load_pcb():
    """The original STEP (native coords, untouched) as a build123d shape. ~ seconds."""
    return import_step(str(PCB_STEP))


def board_solid():
    return prism_xy(BOARD_OUTLINE, BOARD_Z0, BOARD_Z1)


def pcb_keepout(margin=0.0, include_board=True):
    """List of (name, Solid) boxes: every component bbox (+margin), the board, the lead-tip slab under the board."""
    out = []
    for c in pcb_data()["components"]:
        x0, y0, z0, x1, y1, z1 = c["bbox"]
        z0 = max(z0, SEAT_Z)       # leads below the board handled by the slab
        out.append((c["name"], box(x0 - margin, y0 - margin, z0, x1 + margin, y1 + margin, z1 + margin)))
    if include_board:
        out.append(("board", board_solid()))
        x0, y0, x1, y1 = BOARD_BBOX
        out.append(("lead_tips", box(x0, y0, THT_TIP_Z - margin, x1, y1, 0.0)))
    return out


def min_dist(a, b):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value()


def ray_hits(shape, p, d):
    """All intersection points of the line through p with direction d and the shape's faces."""
    from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
    from OCP.gp import gp_Lin, gp_Pnt, gp_Dir
    inter = BRepIntCurveSurface_Inter()
    inter.Init(shape.wrapped, gp_Lin(gp_Pnt(*p), gp_Dir(*d)), 1e-6)
    out = []
    while inter.More():
        q = inter.Pnt(); out.append((q.X(), q.Y(), q.Z())); inter.Next()
    return out


_MESHES = {}


def _mesh_for(shape):
    k = id(shape)
    if k not in _MESHES:
        _MESHES[k] = (shape, mesh_of(shape, 0.02))
    return _MESHES[k][1]


def top_z(shape, x, y, exact=False):
    """Highest Z of the shape's surface above plan point (x, y), or None. Mesh ray (fast, ~0.02) unless exact."""
    if exact:
        h = ray_hits(shape, (x, y, 100.0), (0, 0, -1))
        return max(q[2] for q in h) if h else None
    m = _mesh_for(shape)
    loc, _, _ = m.ray.intersects_location([[x, y, 100.0]], [[0, 0, -1]])
    return float(loc[:, 2].max()) if len(loc) else None


_SK = {}


def _skin_c():
    if "s" not in _SK:
        _SK["s"] = skin(); _SK["i"] = inner()
    return _SK


def skin_z_at(x, y, z_hi=60.0):
    """Top Z of the outer skin at plan point (x, y) (ray cast downward). None if outside."""
    return top_z(_skin_c()["s"], x, y)


def inner_z_at(x, y):
    """Top Z of the cavity (= underside of the top shell / button panel) at (x, y)."""
    return top_z(_skin_c()["i"], x, y)


def skin_x_at(y, z, side="L"):
    """Outer skin X at (y, z) on the left (min) or right (max) side."""
    m = _mesh_for(_skin_c()["s"])
    loc, _, _ = m.ray.intersects_location([[-50, y, z]], [[1, 0, 0]])
    xs = list(loc[:, 0])
    if not xs:
        return None
    return min(xs) if side == "L" else max(xs)


def skin_y_at(x, z, end="front"):
    m = _mesh_for(_skin_c()["s"])
    loc, _, _ = m.ray.intersects_location([[x, -200, z]], [[0, 1, 0]])
    ys = list(loc[:, 1])
    if not ys:
        return None
    return max(ys) if end == "front" else min(ys)


def mesh_of(shape, tol=0.05):
    """trimesh of a build123d shape (via a temp STL)."""
    import tempfile, trimesh
    f = Path(tempfile.gettempdir()) / f"_m_{os.getpid()}_{id(shape)}.stl"
    export_stl(shape, str(f), tolerance=tol, angular_tolerance=0.1)
    m = trimesh.load(str(f)); f.unlink(missing_ok=True)
    return m


def box_points(b, step=0.5):
    x0, y0, z0, x1, y1, z1 = b
    xs = np.linspace(x0, x1, max(2, int((x1 - x0) / step) + 1))
    ys = np.linspace(y0, y1, max(2, int((y1 - y0) / step) + 1))
    zs = np.linspace(z0, z1, max(2, int((z1 - z0) / step) + 1))
    pts = []
    for X, Y in ((xs, ys),):
        g = np.array(np.meshgrid(xs, ys)).reshape(2, -1).T
        pts += [np.c_[g, np.full(len(g), z0)], np.c_[g, np.full(len(g), z1)]]
    g = np.array(np.meshgrid(xs, zs)).reshape(2, -1).T
    pts += [np.c_[g[:, 0], np.full(len(g), y0), g[:, 1]], np.c_[g[:, 0], np.full(len(g), y1), g[:, 1]]]
    g = np.array(np.meshgrid(ys, zs)).reshape(2, -1).T
    pts += [np.c_[np.full(len(g), x0), g[:, 0], g[:, 1]], np.c_[np.full(len(g), x1), g[:, 0], g[:, 1]]]
    return np.vstack(pts)


def pcb_clearances(cavity=None):
    """Signed distance (mm) from every PCB component box (+ board outline corners) to the cavity surface.
    Positive = inside the cavity with that clearance. Sorted ascending: [(d, name, [x0, y0, z1]), ...].
    The cavity bottom (Z_UNDER + WALL) is ignored: the real floor is Z_INNER_FLOOR (lead tips -1.905, 1.0 clear)."""
    import trimesh
    m = mesh_of(cavity if cavity is not None else inner())
    pq = trimesh.proximity.ProximityQuery(m)
    rows = []
    items = [(c["name"], [c["bbox"][0], c["bbox"][1], max(c["bbox"][2], SEAT_Z)] + c["bbox"][3:])
             for c in pcb_data()["components"]]
    x0, y0, x1, y1 = BOARD_BBOX
    items.append(("board", [x0, y0, BOARD_Z0, x1, y1, BOARD_Z1]))
    for nm, b in items:
        if b[5] < 2.5 and nm != "board":
            continue          # low SMD parts: never critical (top shell is > 8 above them)
        pts = box_points(b, 1.0)
        d = pq.signed_distance(pts)
        rows.append((float(d.min()), nm, [round(b[0], 2), round(b[1], 2), round(b[5], 2)]))
    rows.sort()
    return rows


_SEC_CACHE = {}


def cavity_section(z):
    """shapely (Multi)Polygon of the cavity (inner skin) cut at height z (mesh based, fast)."""
    import shapely
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    key = round(z, 3)
    if key in _SEC_CACHE:
        return _SEC_CACHE[key]
    if "mesh" not in _SEC_CACHE:
        _SEC_CACHE["mesh"] = mesh_of(inner(), 0.04)
    m = _SEC_CACHE["mesh"]
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    p2, T = sec.to_2D()
    polys = [Polygon(np_) for np_ in p2.polygons_full] if hasattr(p2, "polygons_full") else []
    g = unary_union(polys)
    # back to world XY (to_2D applies a transform)
    import shapely.affinity as aff
    a = T
    g = aff.affine_transform(g, [a[0, 0], a[0, 1], a[1, 0], a[1, 1], a[0, 3], a[1, 3]])
    _SEC_CACHE[key] = g
    return g


def room_at(x, y, z):
    """Distance from plan point (x, y) to the cavity wall at height z (negative = outside the cavity)."""
    from shapely.geometry import Point
    g = cavity_section(z)
    p = Point(x, y)
    d = g.exterior.distance(p) if g.geom_type == "Polygon" else g.boundary.distance(p)
    return d if g.contains(p) else -d


def check_part(shape, name=""):
    """Basic self-check for builders: single valid solid, volume, bbox. Returns dict."""
    sols = shape.solids() if hasattr(shape, "solids") else [shape]
    bb = shape.bounding_box()
    return dict(name=name, n_solids=len(sols), valid=bool(shape.is_valid), volume=round(shape.volume, 1),
                bbox=[round(v, 2) for v in (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)])


def export_part(shape, name):
    """Write <PARTS_DIR>/<name>/<name>.step and .stl (0.02 tol)."""
    d = part_dir(name)
    export_step(shape, str(d / f"{name}.step"))
    export_stl(shape, str(d / f"{name}.stl"), tolerance=0.02, angular_tolerance=0.15)
    return d


# ====================================================================================================
# self test
# ====================================================================================================
def _selftest():
    t0 = time.time()
    S = skin(); t1 = time.time()
    bb = S.bounding_box()
    print(f"skin: valid={S.is_valid} vol={S.volume:.0f} faces={len(S.faces())} built in {t1 - t0:.1f}s")
    print(f"  bbox X {bb.min.X:.2f}..{bb.max.X:.2f} ({bb.max.X - bb.min.X:.2f})  Y {bb.min.Y:.2f}..{bb.max.Y:.2f} "
          f"({bb.max.Y - bb.min.Y:.2f})  Z {bb.min.Z:.2f}..{bb.max.Z:.2f}")
    print(f"  height above floor {bb.max.Z - Z_FLOOR:.2f}; skate 0.45 proud -> floor {Z_FLOOR}; lens plane "
          f"{Z_LENS_PLANE} = {Z_LENS_PLANE - Z_FLOOR:.2f} above floor")
    I = inner(); t2 = time.time()
    print(f"inner: valid={I.is_valid} vol={I.volume:.0f} ({t2 - t1:.1f}s)")
    W = shell_wall(); t3 = time.time()
    print(f"wall: valid={W.is_valid} vol={W.volume:.0f} solids={len(W.solids())} ({t3 - t2:.1f}s)")
    res = {}
    # skin samples
    for (x, y) in [(X_CL, -4.5), (X_CL, -15), (X_CL, -27.9), (30.18, -23.1), (28, -32.7), (X_CL, -43.18),
                   (X_CL, -60), (X_CL, -74), (23.5, -66), (23.5, -73), (X_CL, -98), (27.37, -98)]:
        print(f"  skin top Z at ({x:.2f},{y:.2f}) = {skin_z_at(x, y)}")
    for y in (-15, -23.5, -40, -50.8, -60, -68.58, -76.45, -80):
        print(f"  skin X at Y {y}: L(z=0) {skin_x_at(y, 0, 'L'):.2f} L(z=6.5) {skin_x_at(y, 6.5, 'L'):.2f} "
              f"R(z=0) {skin_x_at(y, 0, 'R'):.2f}")
    # clearance: cavity surface vs every component box (mesh-based, exact closest point) - must be >= CLR_PCB
    rows = pcb_clearances()
    print("closest PCB items to the inner skin surface (mm):")
    for d, nm, p in rows[:8]:
        print(f"   {d:6.2f}  {nm} @ {p}")
    res["min_wall_to_pcb"] = rows[0][0]
    print(f"self-test done in {time.time() - t0:.1f}s")
    return res


if __name__ == "__main__":
    _selftest()
