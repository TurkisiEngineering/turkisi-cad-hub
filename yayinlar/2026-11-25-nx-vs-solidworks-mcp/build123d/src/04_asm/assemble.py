"""WP-I step 1: build mouse_assembly.step (original PCB unmoved + every part STEP, named + coloured)
and write fine meshes (rest + motion poses) for the mesh checks.   python assemble.py"""
import time, json
from asm_common import *     # noqa

t0 = time.time()
pcb, psol = pcb_solids()
print(f"PCB: {len(psol)} solids  ({time.time()-t0:.1f}s)")
json.dump([{k: v for k, v in d.items() if k != "solid"} for d in psol], open(ASM / "pcb_solids.json", "w"), indent=1)

parts = {}
for n, f, c, mat in PARTS_LIST:
    s = load_part(n)
    chk = ML.check_part(s, n)
    print(n, chk)
    parts[n] = s

# ------------------------------------------------------------------ assembly STEP
children = []
for d in psol:
    d["solid"].label = f"pcb{d['idx']:02d}_{d['label']}"
pcb_c = Compound(children=[d["solid"] for d in psol], label="mouse_pcb (original STEP, unmoved)")
pcb_c.color = Color(0.10, 0.45, 0.20)
children.append(pcb_c)
for n, f, c, mat in PARTS_LIST:
    s = parts[n]
    s.label = n
    s.color = Color(*c)
    children.append(s)
asm = Compound(children=children, label="mouse_assembly")
export_step(asm, str(ASM / "mouse_assembly.step"))
print(f"assembly STEP written ({time.time()-t0:.1f}s)")

# ------------------------------------------------------------------ meshes (rest + poses)
def stl(shape, name):
    export_stl(shape, str(MESH / f"{name}.stl"), tolerance=0.01, angular_tolerance=0.1)

for n in parts:
    stl(parts[n], n)
for d in psol:
    stl(d["solid"], f"pcb_{d['idx']:02d}")
poses = {}
a_btn = btn_stop_deg(); a_wh = wheel_stop_deg(); a_side = 5.15   # RV02: WP-H stop face lands at 5.15 deg
poses["button_L"] = ("rot", BTN_AXIS, a_btn); poses["button_R"] = ("rot", BTN_AXIS, a_btn)
poses["wheel_body"] = ("rot", WHEEL_AXIS, a_wh); poses["axle_pin"] = ("rot", WHEEL_AXIS, a_wh)
poses["side_btn_fwd"] = ("rot", SIDE_AXIS, a_side); poses["side_btn_back"] = ("rot", SIDE_AXIS, a_side)
poses["dpi_button"] = ("tz", None, -0.70)
for n, (k, ax, v) in poses.items():
    s = parts[n].rotate(ax, v) if k == "rot" else parts[n].translate((0, 0, v))
    stl(s, n + "_pose")
json.dump(dict(btn_stop_deg=a_btn, wheel_stop_deg=a_wh, side_stop_deg=a_side, dpi_press=0.70),
          open(ASM / "poses.json", "w"), indent=1)
print(f"meshes written ({time.time()-t0:.1f}s); poses btn {a_btn:.4f} deg, wheel {a_wh:.4f} deg, side {a_side}")
