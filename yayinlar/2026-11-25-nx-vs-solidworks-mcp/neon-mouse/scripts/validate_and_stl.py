import os, subprocess, json
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer

stp_dir = r"C:\NX_MCP_WORKSPACE\mouse_design\out\step"
stl_dir = r"C:\NX_MCP_WORKSPACE\mouse_design\out\stl"
os.makedirs(stl_dir, exist_ok=True)
gate = r"H:\My Drive\NX HARNESS VERSIONS\v2\harness\tools\validate_step.py"
py = r"C:\Users\marya\.venvs\cadgenbench\Scripts\python.exe"

names = [
    "mouse_base", "mouse_top_shell", "mouse_scroll_wheel",
    "mouse_dpi_button", "mouse_thumb_fwd", "mouse_thumb_back", "mouse_skates"
]
gate_results = {}
for name in names:
    stp = os.path.join(stp_dir, name + ".step")
    p = subprocess.run([py, gate, stp], capture_output=True, text=True)
    try:
        j = json.loads(p.stdout)
    except Exception:
        j = {"raw": p.stdout[:200], "stderr": p.stderr[:200]}
    gate_results[name] = {
        "exit": p.returncode,
        "valid": j.get("valid", p.returncode == 0),
        "solids": j.get("num_solids"),
        "betti": j.get("betti"),
        "volume": j.get("volume"),
        "bbox_exact_size": j.get("bbox_exact_size"),
    }
    print(f"{name:20s}: exit={p.returncode} valid={j.get('valid')} solids={j.get('num_solids')} betti={j.get('betti')} vol={j.get('volume')}")
    r = STEPControl_Reader()
    r.ReadFile(stp)
    r.TransferRoots()
    sh = r.OneShape()
    BRepMesh_IncrementalMesh(sh, 0.035, False, 0.18, True)
    w = StlAPI_Writer()
    w.ASCIIMode = False
    w.Write(sh, os.path.join(stl_dir, name + ".stl"))

with open(r"C:\NX_MCP_WORKSPACE\mouse_design\out\step_gate.json", "w") as f:
    json.dump(gate_results, f, indent=2)
print("VALIDATION AND STL EXPORT COMPLETE")
