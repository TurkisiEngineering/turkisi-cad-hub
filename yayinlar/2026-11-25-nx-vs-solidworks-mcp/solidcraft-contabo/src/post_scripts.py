"""Scripts run on the finished design (--in mouse_shell.sc), not saved:
print_stl.json  - each printed part moved to its print orientation, one STL each
exploded.json   - parts moved apart, exported as STEP for the exploded render
"""
import json
import sys

OUT = "/root/hub/projects/mouse-pcb/solidcraft/out"
d = sys.argv[1]

def mv(bodies, **kw):
    return {"command": "solid.move", "params": dict(bodies=bodies, **kw)}

def stl(body, name):
    return {"command": "file.export", "params": {"path": f"{OUT}/stl/{name}.stl", "bodies": [body], "quality": "fine"}}

c = []
# bottom shell: floor on the bed
c += [mv(["BottomShell"], translate=[0, 0, -0.8]), stl("BottomShell", "01_bottom_shell")]
# top shell: parting plane on the bed, open side down
c += [mv(["TopShell"], translate=[0, 0, -10.0]), stl("TopShell", "02_top_shell")]
# main buttons: tilt back 1.9 deg so the skirt edge lies flat, open side down
for b, n in (("ButtonL", "03_button_left"), ("ButtonR", "04_button_right")):
    c += [mv([b], axis=[1, 0, 0], angle="-1.9 deg", origin=[0, 3.75, 10.3]), mv([b], translate=[0, 0, -10.3]), stl(b, n)]
# DPI button: upside down, cap face on the bed
# (the cap face follows the roof, tilted 23.49 deg: turn it face down and level)
c += [mv(["DPIButton"], axis=[1, 0, 0], angle="-156.51 deg", origin=[0.67, 1.5, 20]),
      mv(["DPIButton"], translate=[0, 0, -12.3436]), stl("DPIButton", "05_dpi_button")]
# thumb buttons: as installed, pad edge on the bed (support under the lever arm)
c += [mv(["SideBtnF"], translate=[0, 0, -10.15]), stl("SideBtnF", "06_thumb_button_front")]
c += [mv(["SideBtnR"], translate=[0, 0, -10.15]), stl("SideBtnR", "07_thumb_button_rear")]
# wheel: pin-bore face on the bed, encoder key up
c += [mv(["Wheel"], axis=[0, 1, 0], angle="90 deg", origin=[3.5, 17.69, 0]), stl("Wheel", "08_wheel")]
json.dump({"commands": c}, open(f"{d}/print_stl.json", "w"), indent=1)

# exploded view
e = [mv(["TopShell"], translate=[0, 0, 30]), mv(["ButtonL"], translate=[-6, 0, 40]), mv(["ButtonR"], translate=[6, 0, 40]),
     mv(["DPIButton"], translate=[0, 0, 55]), mv(["Wheel", "WheelPin"], translate=[0, 0, 22]),
     mv(["SideBtnF", "SideBtnR"], translate=[-25, 0, 8])]
pcb = json.load(open(f"{d}/pcb_body_names.json"))
e.append({"command": "occurrence.move", "params": {"occurrence": "PCB:1", "space": "world", "translate": [0, 0, 12], "move_grounded": True}})
PARTS = ["BottomShell", "TopShell", "ButtonL", "ButtonR", "DPIButton", "SideBtnF", "SideBtnR", "Wheel", "WheelPin"]
e.append({"command": "file.export_step", "params": {"path": f"{OUT}/render_exploded.step"}})
json.dump({"commands": e}, open(f"{d}/exploded.json", "w"), indent=1)
print("ok")
