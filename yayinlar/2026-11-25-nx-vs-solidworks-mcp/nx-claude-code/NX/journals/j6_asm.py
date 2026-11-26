"""J6: bought/reference parts, production assembly mouse_asm.prt, clearance analysis, measured gaps,
pressed-wheel pose, STEP + STL export."""
import os, sys, math, traceback
sys.path.insert(0, r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx\nx")
from common import *  # noqa
import NXOpen.Assemblies as NA  # noqa
L = Log("j6_asm")
DEL = r"C:\Users\USER\Desktop\Mouse for PCB\TESLIM_NX"
R = os.path.join(WS, "render")
try:
    nxh.close_all()
    # ---- simple bought / reference parts (numeric, datasheet / BOM sizes)
    p = nxh.new_part(PRT["axle_pin"])
    nxh.expr(p, "pin_d", "2.0", "mm", "ISO 2338 dowel 2 m6 x 14 (steel), wheel axle")
    nxh.expr(p, "pin_l", "14", "mm", "")
    f, b = nxh.cylinder(p, ("-0.8", "17.693", "8.595"), (1.0, 0.0, 0.0), "pin_d", "pin_l")  # x -0.8..13.2; b.SetName("AXLE_PIN"); color(b, 130)
    nxh.save(p)
    p = nxh.new_part(PRT["hinge_pin"])
    nxh.expr(p, "hp_d", "1.75", "mm", "1.75 mm filament piece as hinge pin")
    nxh.expr(p, "hp_l", "9", "mm", "")
    f, b = nxh.cylinder(p, ("-26.3", "-hp_l/2", "3.6"), (0.0, 1.0, 0.0), "hp_d", "hp_l"); b.SetName("HINGE_PIN"); color(b, 130)
    nxh.save(p)
    lens_path = os.path.join(OUT, "lm19_lens_envelope.prt")
    p = nxh.new_part(lens_path)
    nxh.expr(p, "lens_w", "18.85", "mm", "LM19-LSI flange X (DS Fig.6)")
    nxh.expr(p, "lens_l", "21.15", "mm", "LM19-LSI flange Y")
    nxh.expr(p, "z_lens", "-3.405", "mm", "lens reference plane = PCB top - 7.40 + 2.40")
    f, b, st = rect_prism(p, "0", "-11.497", "lens_w", "lens_l", "z_lens", "-1.5", "LM19_LSI_ENVELOPE"); color(b, 186)
    f2, b2, st = rect_prism(p, "0", "-11.497", "8.0", "16.6", "-1.6", "1.5", "LENS_COLUMN")
    nxh.unite(p, b, [b2])
    nxh.save(p)
    # ---- production assembly
    assy = nxa.new_assembly(PRT["mouse_asm"])
    nxh.save(assy)
    C = {}
    for k in ("pcb", "bottom_shell", "top_shell", "btn_left", "btn_right", "key_fwd", "key_back", "wheel", "axle_pin"):
        C[k] = nxa.add_component(assy, PRT[k], k.upper())
    C["hinge_f"] = nxa.add_component(assy, PRT["hinge_pin"], "HINGE_PIN_F", origin=(0.0, -5.207, 0.0))
    C["hinge_b"] = nxa.add_component(assy, PRT["hinge_pin"], "HINGE_PIN_B", origin=(0.0, -22.987, 0.0))
    C["lens"] = nxa.add_component(assy, lens_path, "LM19_LSI_LENS_ENVELOPE")
    for c in C.values():
        if not c.Prototype.IsFullyLoaded:
            c.Prototype.LoadThisPartFully().Dispose()
    nxh.update()
    nxh.save(assy)

    def body(k, name=None):
        pr = C[k].Prototype
        bs = [b for b in pr.Bodies if b.IsSolidBody and (name is None or b.Name == name)]
        if name is None:
            bs = [b for b in bs if not b.Name.startswith("LNK")]
        o = C[k].FindOccurrence(bs[0])
        if o is None:
            raise RuntimeError("no occurrence %s %s" % (k, name))
        return o

    # ---- clearance analysis, all components
    cs = nxa.clearance_set(assy, "ALL", 0.0)
    res = nxa.run_clearance(cs)
    L.res["clearance_all"] = res
    # ---- detailed body pairs: overlap volume / type
    pcb_names = [b.Name for b in C["pcb"].Prototype.Bodies if b.IsSolidBody]
    parts = ["bottom_shell", "top_shell", "btn_left", "btn_right", "key_fwd", "key_back", "wheel", "axle_pin",
             "hinge_f", "hinge_b", "lens"]
    pairs = []
    for i, a in enumerate(parts):
        for bk in parts[i + 1:]:
            pairs.append((a, None, bk, None))
        for n in pcb_names:
            pairs.append((a, None, "pcb", n))
    detail = []
    for a, an, bk, bn in pairs:
        try:
            oa, ob = body(a, an), body(bk, bn)
            d = nxh.min_dist(oa, ob)
            if d > 1.5:
                continue
            r, vols = nxa.simple_interference(assy, oa, ob)
            detail.append({"a": a, "b": bk if bn is None else "pcb:" + bn, "min_dist": round(d, 4), "result": r,
                           "overlap": [round(v, 4) for v in vols]})
        except Exception as e:  # noqa
            detail.append({"a": a, "b": bk if bn is None else "pcb:" + bn, "error": str(e)[:200]})
    L.res["pairs_within_1_5mm"] = detail
    L.flush()
    hard = [d for d in detail if d.get("result") == "InterferenceExists"]
    press = [d for d in hard if {d["a"], d["b"]} == {"wheel", "axle_pin"}]
    L.res["intended_press_fits"] = press
    L.check("only intended overlap: 2.0 pin pressed in the 1.95 wheel bore", len(press) == 1 and len(hard) == 1, hard)

    # ---- measured key gaps (rest pose)
    def gap(a, bk, bn):
        return round(nxh.min_dist(body(a), body(bk, bn)), 4)
    gaps = {"btn_left-SW1": gap("btn_left", "pcb", "SW1"), "btn_right-SW2": gap("btn_right", "pcb", "SW2"),
            "key_fwd-SW5": gap("key_fwd", "pcb", "SW5"), "key_back-SW6": gap("key_back", "pcb", "SW6"),
            "top_shell(DPI nub)-SW4": gap("top_shell", "pcb", "SW4"), "axle_pin-SW3": gap("axle_pin", "pcb", "SW3"),
            "wheel-ENCODER1": gap("wheel", "pcb", "ENCODER1"), "bottom_shell-lens_envelope": gap("bottom_shell", "lens", None),
            "bottom_shell-U2_0(sensor)": gap("bottom_shell", "pcb", "U2_0"), "top_shell-USB1": gap("top_shell", "pcb", "USB1"),
            "top_shell-ENCODER1": gap("top_shell", "pcb", "ENCODER1"), "wheel-top_shell": gap("wheel", "top_shell", None),
            "wheel-bottom_shell": gap("wheel", "bottom_shell", None),
            "axle_pin-bottom_shell(fork)": gap("axle_pin", "bottom_shell", None),
            "btn_left-top_shell": gap("btn_left", "top_shell", None), "key_fwd-top_shell": gap("key_fwd", "top_shell", None),
            "key_back-top_shell": gap("key_back", "top_shell", None)}
    L.res["gaps"] = gaps
    L.flush()
    for k in ("btn_left-SW1", "btn_right-SW2", "key_fwd-SW5", "key_back-SW6", "top_shell(DPI nub)-SW4"):
        L.check("nub gap %s = 0.20" % k, abs(gaps[k] - 0.2) < 0.01, gaps[k])
    L.check("axle pin rests on SW3 plunger (0)", abs(gaps["axle_pin-SW3"]) < 0.01, gaps["axle_pin-SW3"])

    # ---- pressed wheel pose: tilt wheel + pin about the encoder pivot, pin 0.75 below the plunger top
    piv = ((-12.0 - 7.39) / 2, 17.693, 8.595)          # middle of the stub engagement in the encoder bore
    ang = math.atan2(0.75, 11.43 - piv[0])
    ca, sa = math.cos(ang), math.sin(ang)
    Rm = [[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]]
    Rp = [sum(Rm[i][j] * piv[j] for j in range(3)) for i in range(3)]
    tr = [piv[i] - Rp[i] for i in range(3)]
    for k in ("wheel", "axle_pin"):
        assy.ComponentAssembly.MoveComponent(C[k], NXOpen.Vector3d(*tr), nxa.to_nx(Rm))
    nxh.update()
    zt = exact_bbox(body("axle_pin"))
    pressed = {"tilt_deg": round(math.degrees(ang), 3), "pin_bbox": [round(v, 3) for v in zt],
               "axle_pin-SW3": nxa.simple_interference(assy, body("axle_pin"), body("pcb", "SW3")),
               "wheel-ENCODER1": [round(nxh.min_dist(body("wheel"), body("pcb", "ENCODER1")), 4)] + list(nxa.simple_interference(assy, body("wheel"), body("pcb", "ENCODER1"))),
               "wheel-bottom_shell": [round(nxh.min_dist(body("wheel"), body("bottom_shell")), 4)] + list(nxa.simple_interference(assy, body("wheel"), body("bottom_shell"))),
               "axle_pin-bottom_shell": [round(nxh.min_dist(body("axle_pin"), body("bottom_shell")), 4)] + list(nxa.simple_interference(assy, body("axle_pin"), body("bottom_shell"))),
               "wheel-top_shell": [round(nxh.min_dist(body("wheel"), body("top_shell")), 4)] + list(nxa.simple_interference(assy, body("wheel"), body("top_shell"))),
               "wheel-PCB": [round(nxh.min_dist(body("wheel"), body("pcb", "PCB")), 4)]}
    L.res["pressed_wheel"] = pressed
    L.flush()
    Ri = [[ca, 0, -sa], [0, 1, 0], [sa, 0, ca]]
    ti = [-sum(Ri[i][j] * tr[j] for j in range(3)) for i in range(3)]
    for k in ("wheel", "axle_pin"):
        assy.ComponentAssembly.MoveComponent(C[k], NXOpen.Vector3d(*ti), nxa.to_nx(Ri))
    nxh.update()
    o, m = C["wheel"].GetPosition()
    L.check("wheel back at rest", abs(o.X) + abs(o.Y) + abs(o.Z) < 1e-6 and abs(m.Xx - 1) < 1e-9, [o.X, o.Y, o.Z, m.Xx])
    nxh.save(assy)
    # ---- STEP of the assembly
    stp = os.path.join(DEL, "mouse_assembly.step")
    nxf.step_export(assy, stp, ap242=False)
    L.check("assembly STEP written", os.path.getsize(stp) > 100000, os.path.getsize(stp))
    # ---- STL per printed part (assembly coordinates; oriented for print afterwards in Python)
    for k in ("bottom_shell", "top_shell", "btn_left", "btn_right", "key_fwd", "key_back", "wheel"):
        pr = C[k].Prototype
        bs = [b for b in pr.Bodies if b.IsSolidBody and b.Name == k.upper()]
        export_stl(pr, bs, os.path.join(R, k + ".stl"), chord=0.01, angle=2.0)
        S.Parts.SetDisplay(assy, False, True)
    for k, nm in (("axle_pin", "AXLE_PIN"), ("lens", "LM19_LSI_ENVELOPE"), ("hinge_f", "HINGE_PIN")):
        pr = C[k].Prototype
        export_stl(pr, [b for b in pr.Bodies if b.Name == nm], os.path.join(R, k + ".stl"))
        S.Parts.SetDisplay(assy, False, True)
    L.finish(True)
except Exception:
    L.res["error"] = traceback.format_exc(); L.flush()
