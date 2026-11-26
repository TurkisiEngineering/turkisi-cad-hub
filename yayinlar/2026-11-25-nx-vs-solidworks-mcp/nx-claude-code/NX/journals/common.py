"""Shared helpers for the mouse NX journals (imported by every journal)."""
import os, sys, json, math, traceback
SK = r"C:\Users\USER\.claude\skills"
sys.path.insert(0, os.environ.get("NXH_DIR", SK + r"\nx-journal-core\scripts"))
sys.path.insert(0, SK + r"\nx-assemblies\scripts")
sys.path.insert(0, SK + r"\nx-curves-and-sketches\scripts")
import NXOpen, NXOpen.Features, NXOpen.Assemblies, NXOpen.GeometricUtilities  # noqa
import nxh, nxf, nxa  # noqa

S = nxh.S
WS = r"C:\NX_MCP_WORKSPACE\mouse_pcb_nx"
OUT = os.path.join(WS, "out")
PRT = {n: os.path.join(OUT, n + ".prt") for n in
       ("pcb", "mouse_ctrl", "mouse_design", "mouse_asm", "bottom_shell", "top_shell", "btn_left", "btn_right",
        "key_fwd", "key_back", "wheel", "axle_pin", "hinge_pin")}
BOOL = nxh.BOOL


class Log:
    def __init__(self, name):
        self.name = name
        self.res = {"result": "FAIL", "checks": [], "notes": []}
        self.path = os.path.join(OUT, name + "_result.json")

    def check(self, label, ok, value=None):
        self.res["checks"].append({"label": label, "ok": bool(ok), "value": value})
        self.flush()
        return ok

    def note(self, *a):
        self.res["notes"].append(" ".join(str(x) for x in a))
        self.flush()

    def flush(self):
        nxh.write_json(self.path, self.res)

    def finish(self, ok=True):
        bad = [c for c in self.res["checks"] if not c["ok"]]
        self.res["n_checks"] = len(self.res["checks"])
        self.res["n_fail"] = len(bad)
        self.res["result"] = "PASS" if ok and not bad else "FAIL"
        self.flush()


def E(part, name):
    return part.Expressions.FindObject(name).Value


def rect_prism(part, cx, cy, wx, wy, z0, z1, name=None, plane=None, op=None, target=None):
    """Expression-driven prism: centred rectangle (formulas) on the XY datum, extruded z0..z1 (formulas).
    Returns (extrude feature, body, sketch)."""
    d = nxh.Datums(part)
    sk = nxf.new_sketch(part, plane or d.xy, d.x, d.origin)
    c = nxh.point(part, cx, cy, "0")
    lines = nxf.sketch_rect_centered(part, sk, c, wx, wy)
    st = nxf.finish_sketch(sk)
    if name:
        sk.Feature.SetName(name + "_SK")
    sec = nxh.section(part, curves=lines)
    f = nxh.extrude(part, sec, (0.0, 0.0, 1.0), z0, z1, op=op, target=target)
    if op is not None:
        if name:
            f.SetName(name)
        return f, target, st
    b = f.GetBodies()[0]
    if name:
        f.SetName(name)
        b.SetName(name)
    return f, b, st


def link_body_by_name(wp, comp, name):
    """WAVE link (body) of the named body of component comp into the work part wp; kept out of MODEL."""
    proto = comp.Prototype
    src = [b for b in proto.Bodies if b.Name == name]
    if len(src) != 1:
        raise RuntimeError("body %s: %d found in %s" % (name, len(src), proto.Leaf))
    o = comp.FindOccurrence(src[0])
    if o is None:
        raise RuntimeError("no occurrence of %s (reference set?)" % name)
    f, bodies = nxa.wave_link(wp, o, kind="body", keep_out_of_model=True)
    f.SetName("LINK_" + name)
    bodies[0].SetName("LNK_" + name)
    return f, bodies[0]


def comp_by_leaf(assy, leaf):
    for c in assy.ComponentAssembly.RootComponent.GetChildren():
        if c.DisplayName.lower() == leaf.lower():
            return c
    raise RuntimeError("component %s not found" % leaf)


def open_design():
    """Open the design assembly with full loading (links follow)."""
    import nxw
    assy = nxw.open_for_linked_edit(PRT["mouse_design"])
    for c in assy.ComponentAssembly.RootComponent.GetChildren():
        p = c.Prototype
        if p is not None and not p.IsFullyLoaded:
            p.LoadThisPartFully().Dispose()
    return assy


def save_only(part):
    part.Save(NXOpen.BasePart.SaveComponents.FalseValue, NXOpen.BasePart.CloseAfterSave.FalseValue).Dispose()


def interp(wp, names):
    for n in names:
        nxa.interpart_expr(wp, n, "mouse_ctrl")


def color(body, idx):
    try:
        dm = S.DisplayManager
        mod = dm.NewDisplayModification()
        mod.ApplyToAllFaces = True
        mod.NewColor = idx
        mod.Apply([body])
        mod.Dispose()
    except Exception:  # noqa
        pass


def ctrl_bodies(ctrl_part):
    return {b.Name: b for b in ctrl_part.Bodies}


def export_stl(part, bodies, path, chord=0.02, angle=3.0):
    """Binary STL of the given bodies (part must be the display part)."""
    if os.path.exists(path):
        os.remove(path)
    if S.Parts.Display is None or S.Parts.Display.Tag != part.Tag:
        S.Parts.SetDisplay(part, False, True)
    c = S.DexManager.CreateStlCreator()
    try:
        c.AutoNormalGen = True
        c.ChordalTol = chord
        c.AdjacencyTol = 0.02
        try:
            c.AngularTol = angle
        except Exception:  # noqa
            pass
        c.OutputType = NXOpen.STLCreator.OutputTypeEnum.Binary
        c.OutputFile = path
        for b in bodies:
            c.ExportSelectionBlock.Add(b)
        c.Commit()
    finally:
        c.Destroy()
    return path


def reset_part(wp):
    """Delete every feature of the work part except the template Datum CSYS (re-runnable journals)."""
    feats = [f for f in wp.Features.GetFeatures() if f.FeatureType != "DATUM_CSYS"]
    if not feats:
        return 0
    m = S.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "reset")
    S.UpdateManager.ClearErrorList()
    S.UpdateManager.AddObjectsToDeleteList(feats)
    S.UpdateManager.DoUpdate(m)
    return len(feats)


def interp_safe(wp, names):
    for n in names:
        try:
            wp.Expressions.FindObject(n)
            continue
        except Exception:  # noqa
            pass
        nxa.interpart_expr(wp, n, "mouse_ctrl")


def start(part_key):
    assy = open_design()
    comp = comp_by_leaf(assy, part_key)
    wp = nxa.set_work(comp)
    reset_part(wp)
    ctrl = comp_by_leaf(assy, "mouse_ctrl")
    pcbc = comp_by_leaf(assy, "pcb")
    return assy, comp, wp, ctrl, pcbc


def cyl(wp, origin, vec, d, h, op=None, target=None, name=None):
    f, b = nxh.cylinder(wp, origin, vec, d, h, op=op, target=target)
    if name:
        f.SetName(name)
    return f, b


def env_cut(wp, tool_body, env):
    """tool_body := tool_body INTERSECT envelope (envelope kept)."""
    nxh.intersect(wp, tool_body, [env], keep_tool=True)
    return tool_body


def product(wp):
    sol = [b for b in wp.Bodies if b.IsSolidBody and not b.Name.startswith("LNK") and b.Name not in ("ENVELOPE",)]
    return sol


def exact_bbox(body):
    try:
        mn, dirs, dist = nxh.UFS.ModlGeneral.AskBoundingBoxExact(body.Tag, 0)
        return [mn[0], mn[1], mn[2], mn[0] + dist[0], mn[1] + dist[1], mn[2] + dist[2]]
    except Exception:  # noqa
        return nxh.bbox(body)


def xset(part, name, formula, unit="mm", comment=""):
    try:
        e = part.Expressions.FindObject(name)
        part.Expressions.EditWithUnits(e, nxh.units(part)[unit], str(formula))
        return e
    except Exception:  # noqa
        return nxh.expr(part, name, formula, unit, comment)


def to_model(wp, body):
    """The product body started as a WAVE copy that nxa.wave_link kept out of MODEL: put it back."""
    rs = [r for r in wp.GetAllReferenceSets() if r.Name == "MODEL"][0]
    rs.AddObjectsToReferenceSet([body])
    members = {x.Tag for x in rs.AskAllDirectMembers()}
    return body.Tag in members
