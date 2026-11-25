"""RV02 final: printability (A17) re-measure on the delivered *_print.stl files: bed contact + >45 deg overhang regions.
python rv02_print.py -> rv02_print.json"""
import json
from pathlib import Path
import numpy as np, trimesh, networkx as nx
P3 = Path(r"C:\Users\marya\Desktop\Mouse for PCB\work\03_parts")
PR = {"bottom_shell": "bottom_shell/bottom_shell_print.stl", "top_shell": "top_shell/top_shell_print.stl",
      "button_L": "button_L/button_L_print.stl", "button_R": "button_R/button_R_print.stl",
      "wheel_body": "wheel/wheel_print.stl", "wheel_yoke": "wheel_yoke/wheel_yoke_print.stl",
      "dpi_button": "dpi_button/dpi_button_print.stl", "side_btn_fwd": "side_btn_fwd/side_btn_fwd_print.stl",
      "side_btn_back": "side_btn_back/side_btn_back_print.stl"}
res = {}
for n, f in PR.items():
    m = trimesh.load(str(P3 / f), force="mesh")
    z0 = m.bounds[0, 2]; nz = m.face_normals[:, 2]; cz = m.triangles_center[:, 2]; ar = m.area_faces
    bed = (nz < -0.999) & (cz < z0 + 0.01)
    ov = (nz < -np.cos(np.radians(45.5))) & ~bed
    idx = np.where(ov)[0]; regs = []
    if len(idx):
        adj = m.face_adjacency; e = adj[np.isin(adj[:, 0], idx) & np.isin(adj[:, 1], idx)]
        g = nx.Graph(); g.add_nodes_from(idx.tolist()); g.add_edges_from(e.tolist())
        for comp in nx.connected_components(g):
            cc = np.array(list(comp)); a = float(ar[cc].sum())
            if a < 0.2: continue
            v = m.triangles[cc].reshape(-1, 3); lo, hi = v.min(0), v.max(0)
            regs.append(dict(area=round(a, 2), z=[round(float(lo[2] - z0), 2), round(float(hi[2] - z0), 2)],
                             span_xy=[round(float(hi[0] - lo[0]), 2), round(float(hi[1] - lo[1]), 2)], flat=bool(np.all(nz[cc] < -0.99))))
        regs.sort(key=lambda r: -r["area"])
    res[n] = dict(file=str(P3 / f), size=[round(float(x), 2) for x in (m.bounds[1] - m.bounds[0])], watertight=bool(m.is_watertight),
                  bed_contact_mm2=round(float(ar[bed].sum()), 2), overhang_total_mm2=round(float(ar[ov].sum()), 2), regions=regs[:8])
    print(n, res[n]["size"], "bed", res[n]["bed_contact_mm2"], "overhang", res[n]["overhang_total_mm2"], "top regions", regs[:3], flush=True)
json.dump(res, open(Path(__file__).with_name("rv02_print.json"), "w"), indent=1)
