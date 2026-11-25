"""render_bottom_shell.py - iso renders of the bottom shell + PCB (run with the cadgenbench venv python)."""
import pyvista as pv
from pathlib import Path

PARAMS = dict(size=(1600, 1100), shell_color="#3a3f4a", pcb_color="#2e8b57", bg="white")
W = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work")
shell = pv.read(str(W / "03_parts" / "bottom_shell" / "bottom_shell.stl"))
pcb = pv.read(str(W / "00_pcb" / "pcb.stl"))
out = W / "renders"

for tag, view, with_pcb in [("iso", (1.0, -0.9, 1.1), True), ("iso_bare", (1.0, -0.9, 1.1), False), ("under", (0.6, -0.5, -1.0), False)]:
    pl = pv.Plotter(off_screen=True, window_size=PARAMS["size"])
    pl.set_background(PARAMS["bg"])
    pl.add_mesh(shell, color=PARAMS["shell_color"], specular=0.3, smooth_shading=False)
    if with_pcb:
        pl.add_mesh(pcb, color=PARAMS["pcb_color"], opacity=0.55)
    c = shell.center
    pl.camera.focal_point = c
    pl.camera.position = (c[0] + 160 * view[0], c[1] + 160 * view[1], c[2] + 160 * view[2])
    pl.camera.up = (0, 0, 1) if view[2] > 0 else (0, 0, -1)
    pl.reset_camera(); pl.camera.zoom(1.25)
    pl.add_text(f"R02 bottom_shell - {tag}", font_size=12, color="black")
    pl.screenshot(str(out / f"R02_bottom_shell_{tag}.png"))
    pl.close()
print("ok")
