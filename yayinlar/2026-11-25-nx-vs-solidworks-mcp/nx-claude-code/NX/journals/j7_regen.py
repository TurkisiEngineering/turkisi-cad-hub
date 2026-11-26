"""J7: regeneration checks on the saved control part (opened, edited, restored, NOT saved)."""
import os, sys, traceback
sys.path.insert(0, r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx\nx")
from common import *  # noqa
L = Log("j7_regen")
try:
    part = nxh.open_part(PRT["mouse_ctrl"])
    T = lambda n: [b for b in part.Bodies if b.Name == n][0]
    v0 = nxh.volume(part, T("T_SKF"))
    nxh.set_expr(part, "skf_y1", "-2.2"); nxh.update()
    v1 = nxh.volume(part, T("T_SKF"))
    nxh.set_expr(part, "skf_y1", "-3.2"); nxh.update()
    exp = 1.0 * (40 + E(part, "sk_x")) * (E(part, "sk_z1") - E(part, "sk_z0"))
    L.check("regen: skf_y1 +1 grows T_SKF by 1 x (40+sk_x) x (sk_z1-sk_z0)", abs((v1 - v0) - exp) < 1e-3, [v0, v1, exp])
    H = T("HOUSING")
    h0 = nxh.volume(part, H)
    nxh.set_expr(part, "s4_zt", "33"); nxh.update(); h1 = nxh.volume(part, H)
    nxh.set_expr(part, "wall", "2.0"); nxh.update(); h2 = nxh.volume(part, H)
    nxh.set_expr(part, "s4_zt", "31"); nxh.set_expr(part, "wall", "1.8"); nxh.update(); h3 = nxh.volume(part, H)
    L.check("regen: palm height 31->33 and wall 1.8->2.0 change HOUSING, nominal restores it", h1 > h0 and h2 > h1 and abs(h3 - h0) < 1e-6 * h0, [h0, h1, h2, h3])
    W = T("T_WHL")
    w0 = nxh.volume(part, W)
    nxh.set_expr(part, "whl_d", "24"); nxh.update(); w1 = nxh.volume(part, W)
    nxh.set_expr(part, "whl_d", "22"); nxh.update()
    L.check("regen: whl_d 22->24 lengthens the wheel slot by 1 mm (rear end at ax_y-whl_d/2-0.8)", abs((w1 - w0) - 1.0 * 9.0 * (50 - (8.595 + 1.5))) < 1e-3, [w0, w1])
    L.check("ctrl feature errors none", not nxh.feature_errors(part), None)
    L.finish(True)
except Exception:
    L.res["error"] = traceback.format_exc(); L.flush()
