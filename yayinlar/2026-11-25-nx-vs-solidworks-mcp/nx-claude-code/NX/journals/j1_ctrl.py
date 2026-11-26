"""J1: pcb.prt (flattened KiCad STEP, named bodies), mouse_ctrl.prt (control part: masters, datums, skin,
housing, tool bodies) and mouse_design.prt (design assembly with empty components for every part)."""
import os, sys, json, math, traceback
sys.path.insert(0, r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx\nx")
from common import *  # noqa
import curvekit as ck

L = Log("j1_ctrl")


def exact_bbox(body):
    try:
        mn, dirs, dist = nxh.UFS.ModlGeneral.AskBoundingBoxExact(body.Tag, 0)
        return [mn[0], mn[1], mn[2], mn[0] + dist[0], mn[1] + dist[1], mn[2] + dist[2]]
    except Exception as e:  # noqa
        L.note("exact bbox failed", e)
        return nxh.bbox(body)
try:
    nxh.close_all()
    # ------------------------------------------------------------ 1 PCB part
    pcb = nxh.new_part(PRT["pcb"])
    rows = json.load(open(os.path.join(WS, "intake", "pcb_flat_bodies.json")))
    imp = S.DexManager.CreateStep214Importer()
    imp.SettingsFile = os.path.join(nxf.step_dir(), "step214ug.def")
    imp.ImportTo = NXOpen.Step214Importer.ImportToOption.WorkPart
    imp.ObjectTypes.Solids = True
    imp.FlattenAssembly = True
    imp.InputFile = os.path.join(WS, "intake", "pcb_flat.step")
    imp.OutputFile = os.path.join(OUT, "_scratch_pcb.prt")
    imp.FileOpenFlag = False
    imp.ProcessHoldFlag = True
    imp.Commit(); imp.Destroy()
    bodies = [b for b in pcb.Bodies if b.IsSolidBody]
    L.check("pcb bodies imported = STEP solids", len(bodies) == len(rows), [len(bodies), len(rows)])
    used = set()
    for b in bodies:
        bb = nxh.bbox(b)
        c = [(bb[i] + bb[i + 3]) / 2 for i in range(3)]
        best, bd = None, 1e9
        for k, r in enumerate(rows):
            rc = [(r["bb"][i] + r["bb"][i + 3]) / 2 for i in range(3)]
            dd = sum((a - q) ** 2 for a, q in zip(c, rc)) + abs(nxh.volume(pcb, b) - r["vol"]) * 1e-3
            if dd < bd:
                best, bd = k, dd
        used.add(best)
        b.SetName(rows[best]["name"].replace("=", "").replace(">", "").replace("[", "").replace("]", "").replace(":", "_"))
        n = b.Name
        color(b, 36 if n == "PCB" else (130 if n.startswith("SW") else (181 if n.startswith("U2") else 211)))
    L.check("pcb bodies uniquely named", len(used) == len(rows), len(used))
    names = {b.Name for b in pcb.Bodies}
    L.note("pcb names", sorted(names))
    L.check("key bodies present", all(k in names for k in ("PCB", "SW1", "SW2", "SW3", "SW4", "SW5", "SW6", "ENCODER1", "U2_0", "USB1")), sorted(names)[:12])
    board = [b for b in pcb.Bodies if b.Name == "PCB"][0]
    bb = nxh.bbox(board)
    L.check("board 49.784 x 61.722 x 1.51 centred", abs(bb[3] - bb[0] - 49.784) < 0.02 and abs(bb[4] - bb[1] - 61.722) < 0.02 and abs(bb[0] + 24.892) < 0.02, bb)
    nxh.save(pcb)

    # ------------------------------------------------------------ 2 control part
    part = nxh.new_part(PRT["mouse_ctrl"])
    X = lambda n, f, c="": nxh.expr(part, n, f, "mm", c)
    X("pcb_t", "1.6", "PCB nominal thickness (STEP board solid 1.51, parts seated at 1.595)")
    X("z_seat", "1.595", "component seat plane, measured in mouse_pcb.step")
    X("surf_to_pcbtop", "7.40", "PMW3360 DS Fig.4: top of PCB to navigation surface")
    X("lens_ref", "2.40", "PMW3360 DS Fig.4: bottom of lens flange to navigation surface (Z)")
    X("z_surf", "z_seat-surf_to_pcbtop", "navigation surface = bottom of the feet")
    X("foot_h", "0.8", "printed foot pad height")
    X("z_base", "z_surf+foot_h", "underside of the shell floor")
    X("z_lens", "z_surf+lens_ref", "lens reference plane (flange bottom)")
    X("wall", "1.8", "shell wall")
    X("z_split", "-1.0", "parting plane top / bottom shell")
    X("opt_y", "-11.497", "PMW3360 optical centre y (pin1 + 5.66 forward, DS Fig.3)")
    X("btn_gap", "0.6", "gap around separate keys")
    X("btn_z", "9.0", "lower cut level of the main buttons on the flank")
    X("btn_ry", "-2.0", "rear edge of the main buttons")
    X("btn_ix", "5.1", "inner edge of the main buttons beside the wheel")
    X("btn_fy", "30.5", "main buttons meet at the centre line in front of this y (wheel front at z=9 is y 28.69)")
    X("btn_mg", "0.3", "half gap between the buttons at the centre line")
    X("btn_xo", "40", "outer x limit of the button tools (outside the skin)")
    X("whl_d", "22", "scroll wheel diameter")
    X("whl_w", "7", "scroll wheel width")
    X("ax_y", "17.693", "wheel axis y = EC10E shaft axis (STEP)")
    X("ax_z", "8.595", "wheel axis z = EC10E shaft axis (STEP)")
    X("whl_slot", "1.0", "clearance wheel to slot")
    X("dpi_ry", "-30", "rear end of the DPI key strip slots")
    X("dpi_sw", "0.8", "DPI strip slot width")
    X("sk_x", "-27.5", "inner limit of the side key windows")
    X("sk_z0", "6.2", "side key window bottom (above the hinge lugs)")
    X("sk_z1", "13.5", "side key window top")
    X("skf_y0", "-10.4", "")
    X("skf_y1", "-3.2", "")
    X("skb_y0", "-27.5", "")
    X("skb_y1", "-16.5", "")
    X("z_pl", "7.595", "D2F plunger top, free position (STEP placeholder = OP 5.5 + PT 0.5 above seat)")
    X("nub_gap", "0.2", "nub to plunger gap at rest")
    X("nub_d", "3.0", "nub diameter")
    X("pl12_x", "19.05", "SW1/SW2 plunger x (mirror)")
    X("pl12_y", "22.063", "SW1/SW2 plunger y")
    X("pl3_x", "11.43", "SW3 (middle click) plunger x")
    X("pl3_y", "17.618", "SW3 plunger y")
    X("pl4_x", "0.67", "SW4 (DPI) plunger x")
    X("pl4_y", "2.413", "SW4 plunger y")
    X("pl56_x", "-18.38", "SW5/SW6 (side) plunger x")
    X("pl5_y", "-5.207", "SW5 plunger y")
    X("pl6_y", "-22.987", "SW6 plunger y")
    X("tg_x", "8.75", "main button tongue / screw x (mirror)")
    X("tg_y", "-10.0", "main button screw y")
    X("tg_y0", "-13.0", "tongue rear end")
    X("tg_w", "5.5", "tongue width")
    X("tg_z", "18.5", "tongue underside")
    X("tg_t", "1.0", "tongue (flexure) thickness")
    X("boss_d", "5.0", "screw boss diameter")
    X("clamp_d", "4.4", "PCB clamp boss diameter (top shell)")
    X("pilot_d", "1.7", "M2 thread-forming pilot")
    X("clr_d", "2.4", "M2 clearance hole")
    X("cb_d", "4.4", "M2 head counterbore")
    X("so_d", "5.0", "PCB standoff diameter (bottom shell)")
    X("pin_x", "-26.3", "side key hinge pin axis x")
    X("pin_z", "3.6", "side key hinge pin axis z (lugs stay 0.2 above the PCB top)")
    X("pin_hole", "1.95", "hole for a 1.75 mm filament pin")
    X("arm_x1", "-16.6", "side key arm inner end")
    X("lug_hw", "1.75", "side key hinge lug half width in x (0.78 wall around the 1.95 hole)")
    X("lug_z0", "pin_z-pin_hole/2-0.8", "hinge lug bottom (0.8 under the hole)")
    X("arm_z1", "10.3", "side key arm top")
    # skin sections (y, half width, top z, shoulder z)
    SEC = [(52, 19.0, 7.5, 2.0), (40, 27.0, 13.0, 5.0), (17, 29.5, 17.5, 8.0), (-8, 30.5, 26.0, 11.0),
           (-32, 31.0, 31.0, 13.0), (-52, 28.5, 25.0, 10.0), (-65, 18.0, 11.0, 3.0)]
    for i, (y, w, zt, zs) in enumerate(SEC):
        X("s%d_y" % i, str(y), "skin section %d y" % i)
        X("s%d_w" % i, str(w), "half width")
        X("s%d_zt" % i, str(zt), "top")
        X("s%d_zs" % i, str(zs), "shoulder")
    nxh.update()
    L.check("z_surf = -5.805", abs(E(part, "z_surf") + 5.805) < 1e-9, E(part, "z_surf"))
    L.check("z_lens = -3.405", abs(E(part, "z_lens") + 3.405) < 1e-9, E(part, "z_lens"))

    d = nxh.Datums(part)
    fpar, PARTING = nxf.datum_plane(part, "offset", [d.xy], "z_split", name="PARTING")
    fbase, BASE = nxf.datum_plane(part, "offset", [d.xy], "z_base", name="BASE")

    # skin sections: periodic studio splines through 16 expression-driven points of a two-exponent
    # superellipse: upper half exponent n_up (crown), lower half n_low (near-vertical sides), widest at the
    # shoulder height zs, bottom 3 mm below z_base (trimmed flat afterwards).
    X("n_up", "2.3", "crown superellipse exponent (unitless coefficient baked into the point formulas)")
    X("n_low", "5.0", "side superellipse exponent")
    secs = []
    NU, NL = 2.3, 5.0
    for i in range(len(SEC)):
        s = "s%d_" % i
        y = s + "y"
        pts = []
        for k in range(16):
            th = math.radians(-90 + 22.5 * k)
            c, sn = math.cos(th), math.sin(th)
            n = NU if sn > 1e-9 else NL
            fx = math.copysign(abs(c) ** (2.0 / n), c) if abs(c) > 1e-12 else 0.0
            fz = math.copysign(abs(sn) ** (2.0 / n), sn) if abs(sn) > 1e-12 else 0.0
            if fz >= 0:
                zf = "%s+(%s-%s)*(%.9f)" % (s + "zs", s + "zt", s + "zs", fz)
            else:
                zf = "%s+(%s-(z_base-3))*(%.9f)" % (s + "zs", s + "zs", fz)
            pts.append(("%s*(%.9f)" % (s + "w", fx), y, zf))
        sp_pts = [nxh.point(part, *p) for p in pts]
        f, spl = ck.studio_spline(part, sp_pts, degree=3, periodic=True)
        f.SetName("SKIN_SEC%d" % i)
        secs.append(nxh.section_feature(part, [f], help_point=(0.0, float(SEC[i][0]), E(part, "z_base") - 3)))
    L.note("BASE plane origin", [BASE.Origin.X, BASE.Origin.Y, BASE.Origin.Z], "normal", [BASE.Normal.X, BASE.Normal.Y, BASE.Normal.Z])
    tc = nxf.through_curves(part, secs, solid=True)
    tc.SetName("SKIN_LOFT")
    skin = tc.GetBodies()[0]
    L.check("loft is a solid", skin.IsSolidBody, None)
    v0 = nxh.volume(part, skin)
    L.note("loft volume", v0)
    ftrim, rev = nxf.trim_body(part, skin, keep_point=(0.0, -32.0, 30.0), datum_plane=BASE)
    v1 = nxh.volume(part, skin)
    bb = exact_bbox(skin)
    L.check("trimmed flat at z_base", abs(bb[2] - E(part, "z_base")) < 0.02 and v1 < v0, [bb, v0, v1])
    # blend the front and rear end faces
    def end_edges(yv):
        out = []
        for e in skin.GetEdges():
            eb = nxh.bbox(e)
            if abs(eb[1] - yv) < 0.05 and abs(eb[4] - yv) < 0.05 and eb[5] - eb[2] > 1.0:
                out.append(e)
        return out
    rep = nxf.blend_chains(part, [lambda: end_edges(52.0)], 3.0, smaller=(0.66, 0.4))
    L.note("front end blend", rep)
    rep = nxf.blend_chains(part, [lambda: end_edges(-65.0)], 4.0, smaller=(0.66, 0.4))
    L.note("rear end blend", rep)
    skin = [b for b in part.Bodies if b.IsSolidBody][0]
    L.check("one solid after blends", len([b for b in part.Bodies if b.IsSolidBody]) == 1, None)
    venv = nxh.volume(part, skin)
    bb = exact_bbox(skin)
    L.note("envelope bbox", bb, "volume", venv)
    L.check("envelope size L 117 x W 62 x H to 31", 115 < bb[4] - bb[1] < 119 and 61 < bb[3] - bb[0] < 64.5 and 30 < bb[5] < 32.5, bb)
    # ENVELOPE = extracted copy at this timestamp
    EF = NXOpen.Features.ExtractFaceBuilder
    b = part.Features.CreateExtractFaceBuilder(nxh.NULL_FEATURE)
    try:
        b.Type = EF.ExtractType.Body
        b.ExtractBodyCollector.ReplaceRules([part.ScRuleFactory.CreateRuleBodyDumb([skin], True)], False)
        b.Associative = True
        b.FixAtCurrentTimestamp = True
        b.HideOriginal = False
        fext = b.CommitFeature()
    finally:
        b.Destroy()
    env = fext.GetBodies()[0]
    env.SetName("ENVELOPE")
    fext.SetName("ENVELOPE")
    fsh = nxf.shell(part, skin, [], "wall")
    fsh.SetName("HOUSING_SHELL")
    skin.SetName("HOUSING")
    vh = nxh.volume(part, skin)
    L.check("closed shell hollow (vol drop, still 1 body)", 0.05 * venv < vh < 0.3 * venv, [venv, vh])
    L.check("ENVELOPE unchanged by shell", abs(nxh.volume(part, env) - venv) < 1e-3 * venv, nxh.volume(part, env))
    color(skin, 211)
    color(env, 211)

    # ------------------------------------------------------------ tool bodies (expression-driven prisms)
    tools = {}
    def tool(name, cx, cy, wx, wy, z0, z1):
        f, bd, st = rect_prism(part, cx, cy, wx, wy, z0, z1, name)
        L.check(name + " sketch DOF 0", st["dof"] == 0 and st["auto_dims"] == 0, st)
        tools[name] = bd
        return bd
    for side, sg in (("L", "-"), ("R", "")):
        a = tool("T_BTN_%s_A" % side, sg + "(btn_xo+btn_ix)/2", "(60+btn_ry)/2", "btn_xo-btn_ix", "60-btn_ry", "btn_z", "50")
        c = tool("T_BTN_%s_B" % side, sg + "(btn_ix+btn_mg)/2", "(60+btn_fy)/2", "btn_ix-btn_mg", "60-btn_fy", "btn_z", "50")
        nxh.unite(part, a, [c])
        a.SetName("T_BTN_" + side)
    tool("T_SKF", "(sk_x-40)/2", "(skf_y0+skf_y1)/2", "40+sk_x", "skf_y1-skf_y0", "sk_z0", "sk_z1")
    tool("T_SKB", "(sk_x-40)/2", "(skb_y0+skb_y1)/2", "40+sk_x", "skb_y1-skb_y0", "sk_z0", "sk_z1")
    tool("T_WHL", "0", "(ax_y-whl_d/2-0.8+btn_fy)/2", "whl_w+2*whl_slot", "btn_fy-(ax_y-whl_d/2-0.8)", "ax_z+1.5", "50")
    tool("T_DPI_L", "-(btn_ix-btn_gap+dpi_sw/2)", "(dpi_ry+btn_ry)/2", "dpi_sw", "btn_ry-dpi_ry", "0", "50")
    tool("T_DPI_R", "(btn_ix-btn_gap+dpi_sw/2)", "(dpi_ry+btn_ry)/2", "dpi_sw", "btn_ry-dpi_ry", "0", "50")
    for n in ("T_BTN_L", "T_BTN_R", "T_SKF", "T_SKB", "T_WHL", "T_DPI_L", "T_DPI_R"):
        bdy = [b for b in part.Bodies if b.Name == n]
        L.check("tool " + n, len(bdy) == 1 and bdy[0].IsSolidBody, len(bdy))
    # regeneration test: change a master, update, re-measure, restore
    vt0 = nxh.volume(part, [b for b in part.Bodies if b.Name == "T_SKF"][0])
    nxh.set_expr(part, "skf_y1", "-2.2"); nxh.update()
    vt1 = nxh.volume(part, [b for b in part.Bodies if b.Name == "T_SKF"][0])
    nxh.set_expr(part, "skf_y1", "-3.2"); nxh.update()
    L.check("regen: skf_y1 +1 grows T_SKF by 1 x (40+sk_x) x (sk_z1-sk_z0)", abs((vt1 - vt0) - 1.0 * (40 + E(part, "sk_x")) * (E(part, "sk_z1") - E(part, "sk_z0"))) < 1e-3, [vt0, vt1])
    vs0 = nxh.volume(part, skin)
    nxh.set_expr(part, "s4_zt", "33"); nxh.update()
    vs1 = nxh.volume(part, skin)
    nxh.set_expr(part, "s4_zt", "31"); nxh.update()
    vs2 = nxh.volume(part, skin)
    L.check("regen: s4_zt 31->33->31 changes housing and returns", vs1 != vs0 and abs(vs2 - vs0) < 1e-6 * vs0, [vs0, vs1, vs2])
    errs = nxh.feature_errors(part)
    L.check("ctrl feature errors none", not errs, errs)
    nxh.save(part)

    # ------------------------------------------------------------ 3 design assembly
    assy = nxa.new_assembly(PRT["mouse_design"])
    nxh.save(assy)
    cp = nxa.add_component(assy, PRT["pcb"], "PCB")
    cc = nxa.add_component(assy, PRT["mouse_ctrl"], "CTRL")
    comps = {}
    for n in ("bottom_shell", "top_shell", "btn_left", "btn_right", "key_fwd", "key_back", "wheel"):
        comps[n] = nxa.new_component(assy, PRT[n], n.upper())
    nxh.save(assy)
    L.check("design assembly components", len(assy.ComponentAssembly.RootComponent.GetChildren()) == 9, None)
    L.finish(True)
except Exception:
    L.res["error"] = traceback.format_exc()
    L.flush()
