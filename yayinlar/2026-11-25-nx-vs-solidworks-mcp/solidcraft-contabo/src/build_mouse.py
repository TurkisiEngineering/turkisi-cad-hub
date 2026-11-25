#!/usr/bin/env python3
"""Generate the SolidCraft command script for the DIY gaming mouse shell.

Mouse frame (mm): table plane z = 0, +Y = front, X across, origin at the PCB centre in plan.
PCB STEP frame -> mouse frame: x = X - 39.37, y = Y + 45.59, z = Z + PCB_Z.
All PCB-derived numbers below were measured from mouse_pcb.step (see DESIGN_NOTES.md).
"""
import json
import math
import sys

# ---------------------------------------------------------------- parameters
P = dict(
    pcb_z=5.8,        # PCB underside above table: PMW3360 lens ref plane 2.40 + 3.40 lens stack (assumed)
    zb=0.8,           # shell underside above table (0.8 mm PTFE skates)
    floor_top=2.8,    # floor 2.0 thick
    lens_ref=2.4,     # lens seat pocket floor = lens reference plane above table (PMW3360 Z = 2.40)
    wall=2.0,
    z_part=10.0,      # bottom / top shell parting plane
    y_btn=3.5,        # button / top shell boundary (gap +-0.25)
    gap=0.25,
    plunger_gap=0.15,
)
PX0, PY0 = 39.37, -45.59
PCB_Z = P["pcb_z"]

def mx(X): return round(X - PX0, 3)
def my(Y): return round(Y - PY0, 3)
def mz(Z): return round(Z + PCB_Z, 3)

# PCB-derived features (mouse frame)
PCB_HALF_W, PCB_HALF_L = 24.89, 30.86
M2_HOLES = [(sx * 22.86, sy * 28.83) for sx in (-1, 1) for sy in (-1, 1)]
PLUNGER_TOP = mz(7.59)                            # 13.39
SW = {  # plunger centres
    "L": (mx(20.32), my(-23.53)), "R": (mx(58.42), my(-23.53)),
    "M": (mx(50.80), my(-27.975)), "DPI": (mx(40.04), my(-43.18)),
    "SF": (mx(20.99), my(-50.80)), "SR": (mx(20.99), my(-68.58)),
}
ENC_AXIS_Y, ENC_AXIS_Z = my(-27.90), mz(8.60)    # 17.69, 14.40
ENC_FACE_X = mx(31.98)                             # encoder boss face, -7.39
SENSOR = (mx(39.37), my(-56.52))                   # 0, -10.93 (optical centre assumed at package centre)

# ---------------------------------------------------------------- outer shape
N_EXP = 2.8
OUT = [  # y, half width, height (top of the outer surface at x = 0)
    (44.0, 21.0, 14.0), (38.0, 25.0, 17.5), (28.0, 28.5, 20.5), (14.0, 30.5, 23.5),
    (0.0, 31.5, 29.0), (-16.0, 32.0, 35.0), (-30.0, 32.0, 37.5), (-44.0, 31.0, 36.0),
    (-56.0, 28.0, 30.5), (-66.0, 23.0, 23.0), (-72.0, 17.0, 16.0), (-75.5, 10.0, 10.0)]

def interp(y):
    for (y0, w0, h0), (y1, w1, h1) in zip(OUT, OUT[1:]):
        if y1 <= y <= y0:
            f = (y0 - y) / (y0 - y1)
            return w0 + f * (w1 - w0), h0 + f * (h1 - h0)
    raise ValueError(y)

# cavity: same sections shrunk by the wall, ends pulled in so the end walls stay >= wall thick
INNER_Y = [42.0, 38.0, 28.0, 14.0, 0.0, -16.0, -30.0, -44.0, -56.0, -66.0, -68.0]
END_EXTRA = {-68.0: 1.0}   # the rear taper is steep: shrink the last cavity section more so the end wall stays >= 2 mm

def profile(w, h, zb, n=13):
    pts = []
    for i in range(n):
        t = math.pi * i / (n - 1)
        c, s = math.cos(t), math.sin(t)
        x = w * math.copysign(abs(c) ** (2 / N_EXP), c)
        z = zb + (h - zb) * abs(s) ** (2 / N_EXP)
        pts.append([round(x, 4), round(z, 4)])
    pts[0], pts[-1] = [w, zb], [-w, zb]
    return pts


class Script:
    def __init__(self):
        self.c = []
        self.names = set()

    def cmd(self, command, **params):
        n = params.get("name")
        if n and (command.startswith(("solid.", "sketch.create", "surface.", "file.insert"))):
            assert n not in self.names, n
            self.names.add(n)
        self.c.append({"command": command, "params": params})

    def inspect(self):
        self.cmd("document.inspect", measure=True, timeline="summary")

    def section(self, name, y, w, h, zb):
        self.cmd("sketch.create", plane={"origin": [0, y, 0], "x_dir": [1, 0, 0], "y_dir": [0, 0, 1]}, name=name)
        pts = profile(w, h, zb)
        self.cmd("sketch.spline.fit_point", points=pts)
        self.cmd("sketch.line", points=[[-w, zb], [w, zb]])
        self.cmd("sketch.constraint.fix", entities=["l1"] + [f"p{i + 1}" for i in range(len(pts))])
        self.cmd("sketch.finish")

    def box(self, name, x0, x1, y0, y1, z0, z1, op="new", body=None, targets=None):
        p = dict(length=round(x1 - x0, 4), width=round(y1 - y0, 4), height=round(z1 - z0, 4),
                 corner=[round(x0, 4), round(y0, 4), round(z0, 4)], operation=op, name=name)
        if body:
            p["body_name"] = body
        if targets:
            p["targets"] = targets
        self.cmd("solid.box", **p)

    def cyl(self, name, base, axis, d, h, op="new", body=None, targets=None):
        p = dict(diameter=d, height=round(h, 4), base=[round(v, 4) for v in base], axis=axis, operation=op, name=name)
        if body:
            p["body_name"] = body
        if targets:
            p["targets"] = targets
        self.cmd("solid.cylinder", **p)

    def combine(self, target, tools, op, keep=False):
        self.cmd("solid.combine", target=target, tools=tools, operation=op, keep_tools=keep)


def build(stage):
    s = Script()
    # ---------------- parameters (documented; the generator also uses them as numbers)
    for k, v in P.items():
        s.cmd("parameters.add", name=k, expression=f"{v} mm" if k not in () else str(v))

    # ---------------- A. outer body, reference copy, cavity
    names = []
    for i, (y, w, h) in enumerate(OUT):
        s.section(f"OS{i}", y, w, h, P["zb"])
        names.append(f"OS{i}")
    s.cmd("solid.loft", sections=[{"sketch": n} for n in names], name="OuterLoft", body_name="Shell")
    s.cmd("solid.loft", sections=[{"sketch": n} for n in names], name="OuterRefLoft", body_name="OuterRef")
    inames = []
    for i, y in enumerate(INNER_Y):
        w, h = interp(y)
        e = END_EXTRA.get(y, 0.0)
        s.section(f"IS{i}", y, w - P["wall"] - e, h - P["wall"] - e, P["floor_top"])
        inames.append(f"IS{i}")
    s.cmd("solid.loft", sections=[{"sketch": n} for n in inames], name="CavityLoft", body_name="Cavity")
    s.combine("Shell", ["Cavity"], "cut", keep=True)
    if stage == "A":
        s.inspect(); return s

    # ---------------- B. columns through both shells (top-shell screws) and bottom-only features
    zf, zp = P["floor_top"], P["z_part"]
    SCREWS = [(0.0, -55.0), (-18.0, -42.0), (18.0, -42.0)]
    for i, (x, y) in enumerate(SCREWS):
        s.cyl(f"ScrewCol{i}", [x, y, zf - 0.5], [0, 0, 1], 5.6, 40, op="join", targets=["Shell"])
    for i, (x, y) in enumerate(M2_HOLES):   # PCB standoffs
        s.cyl(f"Standoff{i}", [x, y, zf - 0.5], [0, 0, 1], 4.6, PCB_Z - zf + 0.5, op="join", targets=["Shell"])
    s.combine("Shell", ["OuterRef"], "intersect", keep=True)     # trim columns to the outer skin
    # screw holes: clearance + counterbore in the bottom shell, pilot in the top shell
    for i, (x, y) in enumerate(SCREWS):
        s.cyl(f"ScrewClr{i}", [x, y, -1], [0, 0, 1], 2.4, zp + 1, op="cut", targets=["Shell"])
        s.cyl(f"ScrewCbore{i}", [x, y, -1], [0, 0, 1], 4.2, 1 + P["zb"] + 1.8, op="cut", targets=["Shell"])
        s.cyl(f"ScrewPilot{i}", [x, y, zp - 0.01], [0, 0, 1], 1.6, 9, op="cut", targets=["Shell"])
    for i, (x, y) in enumerate(M2_HOLES):
        s.cyl(f"StandoffPilot{i}", [x, y, PCB_Z - 4.5], [0, 0, 1], 1.6, 5, op="cut", targets=["Shell"])
    # sensor: lens seat pocket (floor at the lens reference plane) + optical window
    sx, sy = SENSOR
    s.box("LensPocket", sx - 6.0, sx + 6.0, sy - 10.5, sy + 10.5, P["lens_ref"], zf + 0.5, op="cut", targets=["Shell"])
    s.box("LensWindow", sx - 3.5, sx + 3.5, sy - 6.0, sy + 6.0, -1, zf, op="cut", targets=["Shell"])
    # wheel clearance pocket in the floor
    s.box("WheelPocket", -4.8, 4.8, ENC_AXIS_Y - 12.4, ENC_AXIS_Y + 12.4, 2.0, zf + 0.5, op="cut", targets=["Shell"])
    # USB cable exit, front right, through the front wall (cable routed along the right wall)
    s.cyl("CableExit", [12.0, 36.0, 5.4], [0, 1, 0], 3.8, 12, op="cut", targets=["Shell"])
    if stage == "B":
        s.inspect(); return s

    # ---------------- C. split the shell into parts by region bodies
    yb, g = P["y_btn"], P["gap"]
    # bottom shell
    s.box("RegBottom", -50, 50, -90, 60, -5, zp, body="BottomShell")
    s.combine("BottomShell", ["Shell"], "intersect", keep=True)
    # top shell = rear part + spine behind the wheel
    s.box("RegTop", -50, 50, -90, yb - g, zp, 60, body="TopShell")
    s.box("RegSpine", -5.0, 5.0, yb - g - 1, 6.0, zp, 60, op="join", targets=["TopShell"])
    s.combine("TopShell", ["Shell"], "intersect", keep=True)
    # left main button: region with a tilted lower edge (gap grows toward the front, it is the travel stop)
    s.box("RegBtnL", -50, -0.3, yb + g, 60, zp, 60, body="ButtonL")
    s.box("BtnGapTool", -60, 60, yb + g - 5, 70, zp - 20, zp + 0.3, body="BtnGapTool")
    s.cmd("solid.move", bodies=["BtnGapTool"], axis=[1, 0, 0], angle="1.9 deg", origin=[0, yb + g, zp + 0.3],
          name="TiltGapTool")
    s.combine("ButtonL", ["BtnGapTool"], "cut", keep=True)
    s.box("WheelSlotL", -5.5, 0, yb, 30.5, zp, 60, op="cut", targets=["ButtonL"])
    s.combine("ButtonL", ["Shell"], "intersect", keep=True)
    if stage == "C":
        s.inspect(); return s

    # ---------------- D. part details
    pg = P["plunger_gap"]
    # D1. left main button: plunger post + flex tongue (screwed under the top shell)
    lx, ly = SW["L"]
    s.cyl("PostL", [lx, ly, PLUNGER_TOP + pg], [0, 0, 1], 3.0, 15, op="join", targets=["ButtonL"])
    TX0, TX1 = -14.5, -7.5          # tongue x range (left button)
    s.box("TongueWebL", TX0, TX1, yb + 0.65, yb + 2.85, 23.2, 29.5, op="join", targets=["ButtonL"])
    s.box("TongueFlexL", TX0, TX1, yb - 4.75, yb + 0.85, 23.2, 24.1, op="join", targets=["ButtonL"])
    s.box("TonguePadL", TX0, TX1, yb - 10.75, yb - 4.75, 22.1, 24.1, op="join", targets=["ButtonL"])
    s.cyl("TongueHoleL", [-11.0, yb - 7.75, 21.1], [0, 0, 1], 2.3, 4, op="cut", targets=["ButtonL"])
    s.combine("ButtonL", ["OuterRef"], "intersect", keep=True)
    # D2. top shell: tongue bosses (both sides), alignment tabs, DPI hole, thumb-button windows
    for sx, nm in ((-1, "L"), (1, "R")):
        s.cyl(f"TongueBoss{nm}", [sx * 11.0, yb - 7.75, 24.1], [0, 0, 1], 5.0, 15, op="join", targets=["TopShell"])
    # alignment tabs: grow from the bottom shell wall and rise 3 mm into the top shell, 0.2 mm clear of its wall
    tnames = []
    for i, y in enumerate(INNER_Y):
        w, h = interp(y)
        e = END_EXTRA.get(y, 0.0)
        s.section(f"TS{i}", y, w - P["wall"] - 0.2 - e, h - P["wall"] - 0.2 - e, P["floor_top"])
        tnames.append(f"TS{i}")
    s.cmd("solid.loft", sections=[{"sketch": n} for n in tnames], name="CavityTightLoft", body_name="CavityTight")
    for sx, nm in ((-1, "L"), (1, "R")):
        xa, xb = sorted((sx * 25.2, sx * 33.0))
        s.box(f"TabLow{nm}", xa, xb, -16.5, -11.5, 7.5, zp + 0.01, body=f"TabLow{nm}")
        s.combine(f"TabLow{nm}", ["Cavity"], "intersect", keep=True)
        s.box(f"TabHigh{nm}", xa, xb, -16.5, -11.5, zp - 0.5, 13.0, body=f"TabHigh{nm}")
        s.combine(f"TabHigh{nm}", ["CavityTight"], "intersect", keep=True)
        s.combine("BottomShell", [f"TabLow{nm}", f"TabHigh{nm}"], "join")
    s.combine("TopShell", ["OuterRef"], "intersect", keep=True)
    for sx, nm in ((-1, "L"), (1, "R")):
        s.cyl(f"TongueBossPilot{nm}", [sx * 11.0, yb - 7.75, 24.0], [0, 0, 1], 1.6, 4.4, op="cut", targets=["TopShell"])
    dx, dy = SW["DPI"]
    HOLE = (dx - 2.55, dx + 2.55, -1.0, 4.0)
    s.box("DPIHole", HOLE[0], HOLE[1], HOLE[2], HOLE[3], zp - 1, 60, op="cut", targets=["TopShell"])
    SIDE = {"F": SW["SF"][1], "R": SW["SR"][1]}
    for nm, yc in SIDE.items():
        s.box(f"SideWindow{nm}", -50, -18, yc - 5.5, yc + 5.5, zp - 0.1, 24.0, op="cut", targets=["TopShell"])
    # D3. DPI button: cap plug + retaining flange + post
    s.box("DPICap", HOLE[0] + 0.25, HOLE[1] - 0.25, HOLE[2] + 0.25, HOLE[3] - 0.25, 23.2, 60, body="DPIButton")
    s.combine("DPIButton", ["OuterRef"], "intersect", keep=True)
    s.box("DPIFlange", HOLE[0] - 1.2, HOLE[1] + 1.2, HOLE[2] - 1.2, HOLE[3] + 1.2, 23.2, 24.4, op="join", targets=["DPIButton"])
    s.cyl("DPIPost", [dx, dy, PLUNGER_TOP + 0.05], [0, 0, 1], 3.0, 23.4 - PLUNGER_TOP, op="join", targets=["DPIButton"])
    # D4. thumb buttons: wall pad + lever on a 1.75 mm filament pin carried by two bottom-shell posts
    PIV_X, PIV_Z = -26.6, 14.4
    for nm, yc in SIDE.items():
        b = f"SideBtn{nm}"
        s.box(f"SidePad{nm}", -50, -18, yc - 5.1, yc + 5.1, zp + 0.15, 23.6, body=b)
        s.combine(b, ["Shell"], "intersect", keep=True)
        s.box(f"SideWeb{nm}", -29.8, -25.6, yc - 3.0, yc + 3.0, PIV_Z, 21.0, op="join", targets=[b])
        s.combine(b, ["OuterRef"], "intersect", keep=True)
        s.cyl(f"SideHub{nm}", [PIV_X, yc - 3.0, PIV_Z], [0, 1, 0], 3.4, 6.0, op="join", targets=[b])
        s.box(f"SideArm{nm}", PIV_X, SW["SF"][0] + 0.75, yc - 1.4, yc + 1.4, PIV_Z, 16.0, op="join", targets=[b])
        s.box(f"SideNub{nm}", SW["SF"][0] - 0.6, SW["SF"][0] + 0.75, yc - 1.4, yc + 1.4, PLUNGER_TOP + 0.02, PIV_Z + 0.01,
              op="join", targets=[b])
        s.cyl(f"SidePinHole{nm}", [PIV_X, yc - 4.0, PIV_Z], [0, 1, 0], 1.85, 8.0, op="cut", targets=[b])
        for k, (ya, yb2) in enumerate(((yc + 3.3, yc + 5.3), (yc - 5.3, yc - 3.3))):
            s.box(f"SidePost{nm}{k}", -27.3, -25.3, ya, yb2, zf - 0.3, 15.8, op="join", targets=["BottomShell"])
        s.cyl(f"SidePostHole{nm}", [PIV_X, yc - 6.0, PIV_Z], [0, 1, 0], 1.85, 12.0, op="cut", targets=["BottomShell"])
    # D5. wheel fork in the PCB notch (snap neck holds the 2 mm axle pin over the wheel-click switch)
    s.box("WheelFork", 4.3, 5.9, ENC_AXIS_Y - 2.5, ENC_AXIS_Y + 2.5, 1.6, 16.6, op="join", targets=["BottomShell"])
    s.box("ForkSlot", 4.0, 6.2, ENC_AXIS_Y - 1.05, ENC_AXIS_Y + 1.05, 12.2, ENC_AXIS_Z + 1.05, op="cut", targets=["BottomShell"])
    s.box("ForkNeck", 4.0, 6.2, ENC_AXIS_Y - 0.9, ENC_AXIS_Y + 0.9, ENC_AXIS_Z + 1.0, 17.0, op="cut", targets=["BottomShell"])
    # D6. wheel: 23 mm disc, 7 mm wide, grip grooves, encoder key on the left, 2 mm steel pin on the right
    WR, WW = 11.5, 7.0
    s.cyl("WheelDisc", [-WW / 2, ENC_AXIS_Y, ENC_AXIS_Z], [1, 0, 0], 2 * WR, WW, body="Wheel")
    s.cyl("WheelNeck", [ENC_FACE_X + 0.2, ENC_AXIS_Y, ENC_AXIS_Z], [1, 0, 0], 3.0, -WW / 2 - ENC_FACE_X - 0.2 + 0.2,
          op="join", targets=["Wheel"])
    s.box("WheelKey", ENC_FACE_X - 3.8, ENC_FACE_X + 0.3, ENC_AXIS_Y - 1.15, ENC_AXIS_Y + 1.15,
          ENC_AXIS_Z - 1.15, ENC_AXIS_Z + 1.15, op="join", targets=["Wheel"])
    s.cmd("sketch.create", plane="YZ", offset=str(-WW / 2 - 0.1), name="GripSketch")
    s.cmd("sketch.rectangle.two_point", p0=[ENC_AXIS_Y - 0.45, ENC_AXIS_Z + WR - 0.6], p1=[ENC_AXIS_Y + 0.45, ENC_AXIS_Z + WR + 0.5])
    s.cmd("sketch.constraint.fix", entities=["l1", "l2", "l3", "l4"])
    s.cmd("sketch.finish")
    s.cmd("solid.extrude", sketch="GripSketch", distance=WW + 0.2, operation="cut", targets=["Wheel"], name="GripCut")
    s.cmd("solid.pattern.circular", features=["GripCut"], axis={"origin": [0, ENC_AXIS_Y, ENC_AXIS_Z], "dir": [1, 0, 0]},
          count=30, name="GripPattern")
    s.cyl("PinBore", [-0.5, ENC_AXIS_Y, ENC_AXIS_Z], [1, 0, 0], 1.95, WW / 2 + 0.6, op="cut", targets=["Wheel"])
    s.cyl("WheelPinBody", [-0.4, ENC_AXIS_Y, ENC_AXIS_Z], [1, 0, 0], 2.0, 13.4, body="WheelPin")
    # D7. right button = mirror of the left one
    s.cmd("solid.mirror", bodies=["ButtonL"], plane="YZ", name="MirrorButton")
    s.cmd("body.rename", body="ButtonL (2)", name="ButtonR")
    if stage == "D":
        s.inspect(); return s

    # ---------------- E. helpers merged into one body; PCB inserted for the fit checks
    s.combine("BtnGapTool", ["Shell", "OuterRef", "Cavity", "CavityTight"], "join")
    s.cmd("body.rename", body="BtnGapTool", name="ZZ_Helpers")
    if stage in ("E", "F"):
        s.cmd("file.insert_step", path="/root/hub/projects/mouse-pcb/girdi/mouse_pcb.step", name="PCB", flatten=True)
        s.cmd("occurrence.move", occurrence="PCB:1", space="world", translate=[-PX0, -PY0, PCB_Z], move_grounded=True)
    if stage in ("E", "F"):
        # the construction helpers are consumed by one cut, so the design holds only the parts and the PCB
        s.box("EraserBox", -200, 200, -200, 200, -200, 200, body="Eraser")
        s.combine("ZZ_Helpers", ["Eraser"], "cut")
        s.cmd("inspect.measure", names_only=True)
        s.cmd("inspect.interference", budget_s=600)
    if stage == "F":
        for body, col in COLORS.items():
            s.cmd("appearance.assign", bodies=[body], color=col)
        s.cmd("component.from_bodies", bodies=PARTS)
        s.cmd("document.inspect", measure=True, timeline="summary")
        out = "/root/hub/projects/mouse-pcb/solidcraft/out"
        s.cmd("file.export_step", path=f"{out}/mouse_assembly_with_pcb.step")   # every body -> STEP assembly
    return s


PCB_NAMES = __file__.rsplit("build_mouse.py", 1)[0] + "pcb_body_names.json"
COLORS = {"BottomShell": "#2b2f36", "TopShell": "#d9dde3", "ButtonL": "#e8eaee", "ButtonR": "#e8eaee",
          "DPIButton": "#e0452b", "SideBtnF": "#3c4250", "SideBtnR": "#3c4250", "Wheel": "#e0452b",
          "WheelPin": "#9aa0a8"}


PARTS = ["BottomShell", "TopShell", "ButtonL", "ButtonR", "DPIButton", "SideBtnF", "SideBtnR", "Wheel", "WheelPin"]


if __name__ == "__main__":
    stage = sys.argv[1]
    out = sys.argv[2]
    s = build(stage)
    json.dump({"commands": s.c}, open(out, "w"), indent=1)
    print(len(s.c), "commands")
