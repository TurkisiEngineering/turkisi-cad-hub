import os, sys, traceback
sys.path.insert(0, r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx\nx")
from common import *
r={"result":"FAIL"}
try:
    imp = S.DexManager.CreateStep214Importer()
    r["attrs"]=[a for a in dir(imp) if not a.startswith("_")]
    imp.Destroy()
    part = nxh.new_part(os.path.join(OUT,"_probe.prt"))
    imp = S.DexManager.CreateStep214Importer()
    imp.SettingsFile = os.path.join(nxf.step_dir(), "step214ug.def")
    imp.ImportTo = NXOpen.Step214Importer.ImportToOption.WorkPart
    imp.ObjectTypes.Solids = True
    try:
        imp.FlattenAssembly = True; r["flat"]="set"
    except Exception as e: r["flat"]=str(e)
    imp.InputFile = os.path.join(WS,"intake","pcb_flat.step")
    imp.OutputFile = os.path.join(OUT,"_scratch2.prt")
    imp.FileOpenFlag = False
    imp.ProcessHoldFlag = True
    imp.Commit(); imp.Destroy()
    r["bodies"]=len(list(part.Bodies))
    rc=part.ComponentAssembly.RootComponent
    r["comps"]=len(rc.GetChildren()) if rc else 0
    r["result"]="PASS"
except Exception:
    r["error"]=traceback.format_exc()
nxh.write_json(os.path.join(OUT,"probe_import.json"),r)
