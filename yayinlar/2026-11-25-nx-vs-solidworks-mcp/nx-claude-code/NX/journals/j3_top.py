"""J3: top shell in the design assembly (work part top_shell)."""
import os, sys, traceback
sys.path.insert(0, r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx\nx")
from common import *  # noqa
L = Log("j3_top")
try:
    assy, comp, wp, ctrl, pcbc = start("top_shell")
    interp_safe(wp, ["z_split", "wall", "pcb_t", "btn_gap", "z_pl", "nub_gap", "nub_d", "pl4_x", "pl4_y", "pl5_y", "pl6_y",
                     "tg_x", "tg_y", "tg_z", "tg_t", "boss_d", "clamp_d", "pilot_d", "pin_x", "pin_z", "pin_hole", "lug_hw", "lug_z0"])
    xset(wp, "clamp_top", "8.0", "mm", "top of the PCB clamp bosses (below the button cut 8.4)")
    xset(wp, "lug_gap", "0.3", "mm", "side key lug to shell lug gap")
    xset(wp, "cable_d", "4.5", "mm", "USB cable exit")
    xset(wp, "cable_z", "4.0", "mm", "")
    nxh.update()
    fH, H = link_body_by_name(wp, ctrl, "HOUSING")
    fE, ENV = link_body_by_name(wp, ctrl, "ENVELOPE")
    wd = nxh.Datums(wp)
    fpar, PART = nxf.datum_plane(wp, "offset", [wd.xy], "z_split", name="PARTING")
    nxf.trim_body(wp, H, keep_point=(0.0, -32.0, 30.0), datum_plane=PART)
    bb = exact_bbox(H)
    L.check("trimmed above parting", abs(bb[2] - E(wp, "z_split")) < 0.02, bb)
    v = [nxh.volume(wp, H)]
    # openings for the separate keys: linked tools grown by btn_gap, subtracted
    for t in ("T_BTN_L", "T_BTN_R", "T_SKF", "T_SKB"):
        f, T = link_body_by_name(wp, ctrl, t)
        v0t = nxh.volume(wp, T)
        m = nxh.mark("offset", False)
        nxf.offset_region(wp, nxf.rule_faces(wp, "body", T), "btn_gap")
        if nxh.volume(wp, T) < v0t:
            nxh.undo_to(m)
            nxf.offset_region(wp, nxf.rule_faces(wp, "body", T), "-btn_gap")
        L.check("opening tool %s grown" % t, nxh.volume(wp, T) > v0t, [v0t, nxh.volume(wp, T)])
        nxh.subtract(wp, H, [T])
        v.append(nxh.volume(wp, H))
    for t in ("T_WHL", "T_DPI_L", "T_DPI_R"):
        f, T = link_body_by_name(wp, ctrl, t)
        nxh.subtract(wp, H, [T])
        v.append(nxh.volume(wp, H))
    L.note("volumes after cuts", v)
    L.check("one solid after openings", len([b for b in wp.Bodies if b.IsSolidBody and b.Tag == H.Tag]) == 1 and all(v[i + 1] < v[i] for i in range(len(v) - 1)), v)
    # PCB clamp bosses on the linked PCB hole centres + webs to the side wall
    fP, PCBL = link_body_by_name(wp, pcbc, "PCB")
    pts = [p for p in nxa.arc_centre_points(wp, PCBL, radius=1.1, tol=0.01) if abs(p.Coordinates.Z) < 0.01]
    L.check("4 PCB hole centres linked", len(pts) == 4, len(pts))
    for p in pts:
        q = nxa.offset_point(wp, p, (0.0, 0.0, 1.0), "pcb_t")
        fb, B = nxa.cylinder_at_point(wp, q, (0.0, 0.0, 1.0), "clamp_d", "clamp_top-pcb_t")
        fb.SetName("CLAMP_BOSS")
        x, y = p.Coordinates.X, p.Coordinates.Y
        sx = 1 if x > 0 else -1
        fw, Wb, st = rect_prism(wp, "%.4f" % (sx * (abs(x) + 34.0) / 2), "%.4f" % y, "%.4f" % (34.0 - abs(x)), "2.0", "pcb_t", "clamp_top", "CLAMP_WEB")
        nxh.unite(wp, B, [Wb])
        env_cut(wp, B, ENV)
        nxh.unite(wp, H, [B])
        nxa.cylinder_at_point(wp, q, (0.0, 0.0, 1.0), "pilot_d", "clamp_top-pcb_t-0.8", op=BOOL.Subtract, target=H)[0].SetName("M2_PILOT")
    L.check("one solid after clamp bosses", len([b for b in wp.Bodies if b.IsSolidBody and b.Tag == H.Tag]) == 1, None)
    # main button tongue bosses (screw M2 from below through the tongue)
    for sg in ("-", ""):
        fb, B = cyl(wp, (sg + "tg_x", "tg_y", "tg_z+tg_t"), (0.0, 0.0, 1.0), "boss_d", "25", name="TONGUE_BOSS")
        env_cut(wp, B, ENV)
        nxh.unite(wp, H, [B])
        cyl(wp, (sg + "tg_x", "tg_y", "tg_z+tg_t"), (0.0, 0.0, 1.0), "pilot_d", "6", op=BOOL.Subtract, target=H, name="M2_PILOT_TG")
    # DPI nub on the central strip
    fb, B = cyl(wp, ("pl4_x", "pl4_y", "z_pl+nub_gap"), (0.0, 0.0, 1.0), "nub_d", "30", name="DPI_NUB")
    env_cut(wp, B, ENV)
    nxh.unite(wp, H, [B])
    # side key hinge lugs + pin holes
    for key, yc in (("F", "pl5_y"), ("B", "pl6_y")):
        for sg in ("-", "+"):
            fl, LG, st = rect_prism(wp, "(pin_x+lug_hw-31)/2", "%s%s(1.5+lug_gap+1.5)" % (yc, sg), "pin_x+lug_hw+31", "3.0", "lug_z0", "pin_z+1.9", "SK_LUG_" + key)
            env_cut(wp, LG, ENV)
            nxh.unite(wp, H, [LG])
        cyl(wp, ("pin_x", yc + "-6", "pin_z"), (0.0, 1.0, 0.0), "pin_hole", "12", op=BOOL.Subtract, target=H, name="PIN_HOLE_" + key)
    # cable exit at the rear
    cyl(wp, ("0", "-50", "cable_z"), (0.0, -1.0, 0.0), "cable_d", "25", op=BOOL.Subtract, target=H, name="CABLE_EXIT")
    H.SetName("TOP_SHELL")
    color(H, 211)
    sol = [b for b in wp.Bodies if b.IsSolidBody and b.Name == "TOP_SHELL"]
    L.check("top shell one solid", len(sol) == 1, len(sol))
    L.check("no other product solids in MODEL", len(product(wp)) == 1, [b.Name for b in product(wp)])
    errs = nxh.feature_errors(wp)
    L.check("no feature errors", not errs, errs)
    L.note("volume", nxh.volume(wp, H), "bbox", exact_bbox(H))
    L.check("product body in MODEL reference set", to_model(wp, H), None)
    save_only(wp)
    L.finish(True)
except Exception:
    L.res["error"] = traceback.format_exc(); L.flush()
