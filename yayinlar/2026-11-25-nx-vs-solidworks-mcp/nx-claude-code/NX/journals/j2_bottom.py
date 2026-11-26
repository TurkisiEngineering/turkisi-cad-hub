"""J2: bottom shell in the design assembly (work part bottom_shell)."""
import os, sys, traceback
sys.path.insert(0, r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx\nx")
from common import *  # noqa
L = Log("j2_bottom")
try:
    assy, comp, wp, ctrl, pcbc = start("bottom_shell")
    interp_safe(wp, ["z_split", "z_base", "z_surf", "z_lens", "wall", "pcb_t", "opt_y", "so_d", "clr_d", "cb_d",
                     "ax_y", "ax_z", "z_pl"])
    xset(wp, "lens_l", "21.15", "mm", "LM19-LSI lens outline along Y (DS Fig.6)")
    xset(wp, "lens_w", "18.85", "mm", "LM19-LSI lens outline along X")
    xset(wp, "lens_clr", "0.2", "mm", "lens pocket clearance per side")
    xset(wp, "ap_w", "9", "mm", "aperture under the lens, X")
    xset(wp, "ap_l", "14", "mm", "aperture under the lens, Y (covers optical centre and LED path)")
    xset(wp, "fork_x0", "3.9", "mm", "wheel axle fork inner face x (0.4 from the wheel face, axial stop)")
    xset(wp, "fork_t", "1.5", "mm", "fork tine thickness in x")
    xset(wp, "fork_slot", "2.2", "mm", "fork slot width (axle 2.0)")
    xset(wp, "fork_top", "10.0", "mm", "fork tine top z")
    xset(wp, "snap", "0.15", "mm", "snap lip per side at the fork top")
    nxh.update()
    fH, H = link_body_by_name(wp, ctrl, "HOUSING")
    wd = nxh.Datums(wp)
    fpar, PART = nxf.datum_plane(wp, "offset", [wd.xy], "z_split", name="PARTING")
    nxf.trim_body(wp, H, keep_point=(0.0, -32.0, E(wp, "z_base") + 0.2), datum_plane=PART)
    bb = exact_bbox(H)
    L.check("trimmed below parting", abs(bb[5] - E(wp, "z_split")) < 0.05 and abs(bb[2] - E(wp, "z_base")) < 0.05, bb)
    v_tray = nxh.volume(wp, H)
    # standoffs on the PCB hole centres (WAVE-linked board -> arc-centre points)
    fP, PCBL = link_body_by_name(wp, pcbc, "PCB")
    pts = [p for p in nxa.arc_centre_points(wp, PCBL, radius=1.1, tol=0.01) if abs(p.Coordinates.Z) < 0.01]
    L.check("4 PCB hole centres linked", len(pts) == 4, [[round(p.Coordinates.X, 3), round(p.Coordinates.Y, 3)] for p in pts])
    for p in pts:
        f, _ = nxa.cylinder_at_point(wp, p, (0.0, 0.0, -1.0), "so_d", "-z_base", op=BOOL.Unite, target=H)
        f.SetName("STANDOFF")
    for p in pts:
        f, _ = nxa.cylinder_at_point(wp, p, (0.0, 0.0, -1.0), "clr_d", "-z_base+1", op=BOOL.Subtract, target=H)
        f.SetName("M2_CLEAR")
        q = nxa.offset_point(wp, p, (0.0, 0.0, 1.0), "z_base+3")
        f, _ = nxa.cylinder_at_point(wp, q, (0.0, 0.0, -1.0), "cb_d", "4", op=BOOL.Subtract, target=H)
        f.SetName("M2_CBORE")
    L.check("one solid after standoffs", len([b for b in wp.Bodies if b.IsSolidBody and b.Name == H.Name]) == 1, None)
    # lens pocket and aperture
    fpk, PK, st = rect_prism(wp, "0", "opt_y", "lens_w+2*lens_clr", "lens_l+2*lens_clr", "z_lens-0.15", "0", "LENS_POCKET")
    nxh.subtract(wp, H, [PK])
    fap, AP, st = rect_prism(wp, "0", "opt_y", "ap_w", "ap_l", "z_base-1", "0", "LENS_APERTURE")
    nxh.subtract(wp, H, [AP])
    # feet: bought PTFE mouse skates (foot_h = 0.8 thick) stuck flat on the floor underside -> the floor
    # prints flat on the bed; shallow 0.2 locating recesses would change nothing in height, so none are cut.
    # wheel axle fork through the PCB notch (two tines + snap lips)
    for sg in ("+", "-"):
        ff, T, st = rect_prism(wp, "fork_x0+fork_t/2", "ax_y%s(fork_slot/2+0.6)" % sg, "fork_t", "1.2", "z_base+0.5", "fork_top", "FORK_TINE")
        nxh.unite(wp, H, [T])
        ff, T, st = rect_prism(wp, "fork_x0+fork_t/2", "ax_y%s(fork_slot/2-snap/2)" % sg, "fork_t", "snap", "fork_top-0.4", "fork_top", "FORK_SNAP")
        nxh.unite(wp, H, [T])
    H.SetName("BOTTOM_SHELL")
    color(H, 1)
    sol = product(wp)
    L.check("bottom shell is one solid", len(sol) == 1, len(sol))
    errs = nxh.feature_errors(wp)
    L.check("no feature errors", not errs, errs)
    bb = exact_bbox(H)
    L.check("floor underside flat at z_base = z_surf + skate 0.8", abs(bb[2] - E(wp, "z_base")) < 0.01, bb)
    L.note("volume", nxh.volume(wp, H), "tray volume", v_tray)
    # probes
    L.check("standoff top at z=0 (PCB bottom)", nxh.dist_to(wp, H, (pts[0].Coordinates.X + 2.2, pts[0].Coordinates.Y, 0.0)) < 1e-3, None)
    L.check("lens pocket floor at z_lens-0.15", nxh.dist_to(wp, H, (9.6, E(wp, "opt_y"), E(wp, "z_lens") - 0.15)) < 1e-3, None)
    L.check("product body in MODEL reference set", to_model(wp, H), None)
    save_only(wp)
    L.finish(True)
except Exception:
    L.res["error"] = traceback.format_exc(); L.flush()
