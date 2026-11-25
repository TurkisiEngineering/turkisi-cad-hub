"""Iso render of WP-G parts with the PCB (pyvista offscreen).
Run with: C:\\Users\\marya\\.venvs\\cadgenbench\\Scripts\\python.exe render_wheel.py"""
import pyvista as pv
from pathlib import Path

W = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work")
PARTS = [(W / "00_pcb" / "pcb.stl", "#2e7d32", 1.0), (W / "02_master" / "out" / "bottom_shell_raw.stl", "#607d8b", 0.25),
         (W / "03_parts" / "wheel" / "wheel_body.stl", "#ff8f00", 1.0), (W / "03_parts" / "wheel" / "axle_pin.stl", "#e53935", 1.0),
         (W / "03_parts" / "wheel_yoke" / "wheel_yoke.stl", "#1e88e5", 1.0)]
FOCUS = (39.4, -28.0, 6.0)

for name, cam in [("R02_wheel_iso.png", (FOCUS[0] + 55, FOCUS[1] + 60, FOCUS[2] + 45)),
                  ("R02_wheel_iso_rear.png", (FOCUS[0] - 50, FOCUS[1] - 65, FOCUS[2] + 40))]:
    p = pv.Plotter(off_screen=True, window_size=(1600, 1100))
    p.set_background("#1a237e")
    for f, col, op in PARTS:
        p.add_mesh(pv.read(str(f)), color=col, opacity=op, smooth_shading=True, specular=0.3)
    p.camera_position = [cam, FOCUS, (0, 0, 1)]
    p.camera.zoom(1.0)
    p.add_text("WP-G: wheel (PLA) + steel pin + yoke (PETG) on the PCB", font_size=12, color="white")
    p.screenshot(str(W / "renders" / name)); p.close()
    print("wrote", name)
