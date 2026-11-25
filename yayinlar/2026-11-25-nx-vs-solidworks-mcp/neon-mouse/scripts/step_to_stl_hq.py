"""mouse_assembly_full.step -> ince tessellasyonlu STL grupları (render_studio_hq.py girdisi).
Kullanım: python step_to_stl_hq.py <mouse_assembly_full.step> <cikti_klasoru>
Montaj konumları STEP'teki gibi aynen korunur (yeniden konumlandırma yok)."""
import sys, os
from collections import defaultdict
from build123d import import_step, Compound, export_stl

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
root = import_step(src)

def pcb_group(label):
    l = label.lower()
    if "pcb_girdi_pcb" in l: return "kart"
    if "d2f" in l: return "tus"
    if "pixart" in l: return "sensor"
    if "ec10e" in l: return "encoder"
    if l.startswith(("c_0603", "r_0603")): return "pasif"
    if "pinheader" in l: return "header"
    return "ic"

groups = defaultdict(list)
for ch in root.children:
    if ch.label == "mouse_pcb_ref":
        for c in ch.children:
            groups[pcb_group(c.label)].append(c)
    else:
        groups[ch.label].append(ch)

for name, shapes in groups.items():
    comp = Compound(children=[s for s in shapes]) if len(shapes) > 1 else shapes[0]
    fine = name in ("mouse_top_shell", "mouse_base", "mouse_scroll_wheel")
    export_stl(comp, os.path.join(out, name + ".stl"),
               tolerance=0.006 if fine else 0.01, angular_tolerance=0.05 if fine else 0.08)
    bb = comp.bounding_box()
    print(f"{name:20s} n={len(shapes):3d} bb=({bb.min.X:.2f},{bb.min.Y:.2f},{bb.min.Z:.2f})-({bb.max.X:.2f},{bb.max.Y:.2f},{bb.max.Z:.2f})")
print("OK")
