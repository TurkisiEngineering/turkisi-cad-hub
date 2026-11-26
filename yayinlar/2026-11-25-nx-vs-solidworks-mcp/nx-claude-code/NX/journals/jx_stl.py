"""Export STL of parts: argv = list of 'part:bodyname1,bodyname2|*:outfile' specs."""
import os, sys, traceback
sys.path.insert(0, r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx\nx")
from common import *
L = Log("jx_stl")
try:
    specs = [a for a in sys.argv[1:] if "|" in a]
    for spec in specs:
        pn, names, out = spec.split("|")
        p = nxh.open_part(PRT[pn])
        if names == "*":
            bs = [b for b in p.Bodies if b.IsSolidBody and not b.IsBlanked]
        else:
            want = names.split(",")
            bs = [b for b in p.Bodies if b.Name in want]
        export_stl(p, bs, os.path.join(WS, "render", out))
        L.check(out, os.path.exists(os.path.join(WS, "render", out)), len(bs))
    L.finish(True)
except Exception:
    L.res["error"] = traceback.format_exc(); L.flush()
