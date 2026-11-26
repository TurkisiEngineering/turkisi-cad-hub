"""Mouse for PCB (NX build) - Blender 5.1 Cycles studio renders.

blender --background --python render_bl.py -- <ASM_STL_DIR> <PRINT_STL_DIR> <OUT_DIR> [preview] [only=a,b] [nolayers]

ASM_STL_DIR : groups from mesh.py (assembly position, mm)
PRINT_STL_DIR: TESLIM_NX/STL (print orientation, z=0 bed)
Frame: +y = front (buttons), -x = thumb side (side keys), +z = up. Scene in metres.
"""
import bpy, sys, os, math, time, glob
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
ASM, PRN, OUT = (os.path.abspath(a) for a in argv[:3])
PREVIEW = "preview" in argv
LAYERS = "nolayers" not in argv
ONLY = None
for a in argv:
    if a.startswith("only="):
        ONLY = set(a[5:].split(","))
os.makedirs(OUT, exist_ok=True)
MM = 0.001

# ------------------------------------------------------------------ render settings
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
cy = sc.cycles
try:
    pr = bpy.context.preferences.addons["cycles"].preferences
    pr.compute_device_type = "OPTIX"; pr.get_devices()
    for d in pr.devices:
        d.use = d.type == "OPTIX"
    cy.device = "GPU"
except Exception as e:
    print("GPU setup failed:", e)
RES = (1280, 720) if PREVIEW else (2560, 1440)
cy.samples = 96 if PREVIEW else 900
cy.use_adaptive_sampling = True
cy.adaptive_threshold = 0.03 if PREVIEW else 0.007
cy.adaptive_min_samples = 16 if PREVIEW else 64
cy.use_denoising = True
cy.denoiser = "OPENIMAGEDENOISE"
cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
cy.denoising_prefilter = "ACCURATE"
cy.max_bounces = 14; cy.diffuse_bounces = 5; cy.glossy_bounces = 8
cy.transmission_bounces = 12; cy.transparent_max_bounces = 32
cy.sample_clamp_indirect = 4.0
cy.blur_glossy = 0.5
sc.render.use_persistent_data = True
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.filter_size = 1.2
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"


def hexlin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


CYAN, RED, DEEP = hexlin("#00E5FF"), hexlin("#FF3347"), hexlin("#0B131B")

# ------------------------------------------------------------------ world
world = bpy.data.worlds.new("Studio"); sc.world = world; world.use_nodes = True
wn = world.node_tree.nodes; wl = world.node_tree.links
wbg = wn["Background"]; wbg.inputs["Color"].default_value = (*DEEP, 1); wbg.inputs["Strength"].default_value = 0.5
lp = wn.new("ShaderNodeLightPath")
camcol = wn.new("ShaderNodeBackground"); camcol.inputs["Color"].default_value = (0, 0, 0, 1)
mx = wn.new("ShaderNodeMixShader")
wl.new(lp.outputs["Is Camera Ray"], mx.inputs["Fac"])
wl.new(wbg.outputs["Background"], mx.inputs[1]); wl.new(camcol.outputs["Background"], mx.inputs[2])
wl.new(mx.outputs["Shader"], wn["World Output"].inputs["Surface"])


# ------------------------------------------------------------------ materials
def principled(name, color, rough, metal=0.0, coat=0.0, coat_rough=0.15, bevel=0.00025,
               micro=0.0, layer_axis=None, layer_str=0.0, sss=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; n = nt.nodes; L = nt.links
    b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = coat_rough
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.6, 0.6, 0.6)
        b.inputs["Subsurface Scale"].default_value = 0.0006
    nrm = None
    if bevel:
        bv = n.new("ShaderNodeBevel"); bv.samples = 8; bv.inputs["Radius"].default_value = bevel
        nrm = bv.outputs["Normal"]
    tc = n.new("ShaderNodeTexCoord")
    if micro:
        nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2600.0
        nz.inputs["Detail"].default_value = 3.0
        L.new(tc.outputs["Object"], nz.inputs["Vector"])
        bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = micro
        bp.inputs["Distance"].default_value = 0.00002
        L.new(nz.outputs["Fac"], bp.inputs["Height"])
        if nrm is not None: L.new(nrm, bp.inputs["Normal"])
        nrm = bp.outputs["Normal"]
        mr = n.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = rough - 0.04; mr.inputs["To Max"].default_value = rough + 0.04
        L.new(nz.outputs["Fac"], mr.inputs["Value"]); L.new(mr.outputs["Result"], b.inputs["Roughness"])
    if layer_axis is not None and LAYERS and layer_str > 0:
        # FDM layer lines: 0.2 mm period along the print z axis (object coords, metres)
        sep = n.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
        mm_ = n.new("ShaderNodeMath"); mm_.operation = "MULTIPLY"; mm_.inputs[1].default_value = 1.0 / 0.0002
        L.new(sep.outputs["XYZ"[layer_axis]], mm_.inputs[0])
        fr = n.new("ShaderNodeMath"); fr.operation = "PINGPONG"; fr.inputs[1].default_value = 0.5
        L.new(mm_.outputs[0], fr.inputs[0])
        sm = n.new("ShaderNodeMapRange"); sm.interpolation_type = "SMOOTHSTEP"
        sm.inputs["From Min"].default_value = 0.0; sm.inputs["From Max"].default_value = 0.5
        L.new(fr.outputs[0], sm.inputs["Value"])
        bp2 = n.new("ShaderNodeBump"); bp2.inputs["Strength"].default_value = layer_str
        bp2.inputs["Distance"].default_value = 0.00003
        L.new(sm.outputs["Result"], bp2.inputs["Height"])
        if nrm is not None: L.new(nrm, bp2.inputs["Normal"])
        nrm = bp2.outputs["Normal"]
    if nrm is not None:
        L.new(nrm, b.inputs["Normal"])
        if coat: L.new(nrm, b.inputs["Coat Normal"])
    return m


SHELL = (0.052, 0.055, 0.062)
ACC = (0.020, 0.50, 0.62)           # teal accent
LS = 0.10                            # layer-line bump strength
MAT = {
    "top_shell":    principled("TopShell", SHELL, 0.42, coat=0.15, coat_rough=0.3, micro=0.30, layer_axis=2, layer_str=LS),
    "btn_left":     principled("BtnL", (0.060, 0.063, 0.071), 0.34, coat=0.25, coat_rough=0.2, micro=0.2, layer_axis=2, layer_str=LS),
    "btn_right":    principled("BtnR", (0.060, 0.063, 0.071), 0.34, coat=0.25, coat_rough=0.2, micro=0.2, layer_axis=2, layer_str=LS),
    "bottom_shell": principled("Bottom", (0.026, 0.028, 0.032), 0.50, micro=0.4, layer_axis=2, layer_str=LS),
    "wheel":        principled("Wheel", ACC, 0.32, coat=0.3, bevel=0.00018, micro=0.15, layer_axis=0, layer_str=LS),
    "key_fwd":      principled("KeyF", ACC, 0.30, coat=0.35, micro=0.15, layer_axis=2, layer_str=LS),
    "key_back":     principled("KeyB", ACC, 0.30, coat=0.35, micro=0.15, layer_axis=2, layer_str=LS),
    "axle_pin":     principled("Steel", (0.80, 0.80, 0.82), 0.22, metal=1.0, bevel=0.0001),
    "hinge_pin_f":  principled("Filament", (0.92, 0.45, 0.08), 0.35, bevel=0.0001),
    "hinge_pin_b":  principled("Filament2", (0.92, 0.45, 0.08), 0.35, bevel=0.0001),
    "pcb_board":    principled("PCB", (0.012, 0.16, 0.06), 0.30, coat=0.6, coat_rough=0.12, bevel=0.0001),
    "pcb_switch":   principled("D2F", (0.03, 0.03, 0.035), 0.40, bevel=0.00012),
    "pcb_encoder":  principled("EC10E", (0.72, 0.60, 0.22), 0.30, metal=0.7, bevel=0.00012),
    "pcb_sensor":   principled("Sensor", (0.05, 0.05, 0.06), 0.30, bevel=0.0001),
    "pcb_pins":     principled("Pins", (0.85, 0.75, 0.45), 0.25, metal=1.0, bevel=0.0),
    "pcb_ic":       principled("IC", (0.022, 0.022, 0.025), 0.45, bevel=0.00006),
    "pcb_passive":  principled("Passive", (0.42, 0.32, 0.20), 0.40, bevel=0.00004),
    "pcb_crystal":  principled("Xtal", (0.75, 0.75, 0.78), 0.25, metal=1.0, bevel=0.00005),
    "pcb_header":   principled("Header", (0.03, 0.03, 0.035), 0.40, bevel=0.0001),
}


def glass():
    m = bpy.data.materials.new("Glass"); m.use_nodes = True
    nt = m.node_tree; n = nt.nodes; L = nt.links
    b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.75, 0.86, 0.95, 1)
    b.inputs["Roughness"].default_value = 0.10
    b.inputs["Coat Weight"].default_value = 0.6
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    mr = n.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.08; mr.inputs["To Max"].default_value = 0.55
    L.new(lw.outputs["Facing"], mr.inputs["Value"]); L.new(mr.outputs["Result"], b.inputs["Alpha"])
    return m


GLASS = glass()


def floor_material():
    m = bpy.data.materials.new("Floor"); m.use_nodes = True
    nt = m.node_tree; n = nt.nodes; L = nt.links
    b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.03, 0.036, 0.045, 1)
    b.inputs["Roughness"].default_value = 0.25
    tc = n.new("ShaderNodeTexCoord")
    ln = n.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; L.new(tc.outputs["Object"], ln.inputs[0])
    mr = n.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs["From Min"].default_value = 0.16; mr.inputs["From Max"].default_value = 0.65
    L.new(ln.outputs["Value"], mr.inputs["Value"])
    blk = n.new("ShaderNodeBsdfDiffuse"); blk.inputs["Color"].default_value = (0, 0, 0, 1)
    mx_ = n.new("ShaderNodeMixShader")
    L.new(mr.outputs["Result"], mx_.inputs["Fac"]); L.new(b.outputs["BSDF"], mx_.inputs[1]); L.new(blk.outputs["BSDF"], mx_.inputs[2])
    L.new(mx_.outputs["Shader"], n["Material Output"].inputs["Surface"])
    return m, b, mr


FLOOR_MAT, FLOOR_B, FLOOR_FADE = floor_material()


def pei_material():
    """Textured PEI spring-steel sheet (gold-bronze powder coat)."""
    m = bpy.data.materials.new("PEI"); m.use_nodes = True
    nt = m.node_tree; n = nt.nodes; L = nt.links
    b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hexlin("#5E4820"), 1)
    b.inputs["Metallic"].default_value = 0.55
    b.inputs["Roughness"].default_value = 0.55
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1800.0; nz.inputs["Detail"].default_value = 6.0
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6; bp.inputs["Distance"].default_value = 0.00004
    L.new(nz.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ------------------------------------------------------------------ geometry
def load_stl(path, name, mat, offset=Vector((0, 0, 0))):
    bpy.ops.wm.stl_import(filepath=path, global_scale=MM)
    o = bpy.context.selected_objects[0]
    o.name = name
    o.data.transform(o.matrix_basis); o.matrix_basis = Matrix.Identity(4)
    o.data.transform(Matrix.Translation(offset))
    o.data.shade_smooth(); o.data.set_sharp_from_angle(angle=math.radians(28))
    o.data.materials.append(mat)
    return o


objs = {}
CENTER = Vector((0.0, -6.5, 13.0)) * MM
for p in sorted(glob.glob(os.path.join(ASM, "*.stl"))):
    nm = os.path.splitext(os.path.basename(p))[0]
    if nm.startswith("lm19"):
        continue                                     # placement-check block only, not a real part
    objs[nm] = load_stl(p, nm, MAT[nm], -CENTER)
FLOOR_Z = -5.005 * MM - CENTER.z                    # underside of the bottom shell
print("loaded", sorted(objs))
for k,o in objs.items(): print("DIM", k, o.name, tuple(round(v*1000,1) for v in o.dimensions), len(o.data.vertices))
bpy.context.view_layer.update()   # last import keeps a stale matrix_world otherwise
HOME = {k: Matrix.Identity(4) for k in objs}

bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0, 0, FLOOR_Z))
floor = bpy.context.active_object; floor.name = "Floor"; floor.data.materials.append(FLOOR_MAT)

# print plate scene (built later, hidden by default)
plate_objs = []

# ------------------------------------------------------------------ lights
LIGHTS = {}
E = 0.04


def area(name, loc, size, energy, color=(1, 1, 1), size_y=None, spread=180, target=(0, 0, 0)):
    ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy * E; ld.color = color
    if size_y is None: ld.shape = "DISK"; ld.size = size
    else: ld.shape = "RECTANGLE"; ld.size = size; ld.size_y = size_y
    ld.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob)
    aim(ob, loc, target); ob.visible_camera = False
    LIGHTS[name] = ob
    return ob


def aim(ob, loc, target=(0, 0, 0)):
    ob.location = Vector(loc)
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()


area("Key", (-0.30, 0.30, 0.42), 0.50, 70.0, (1.0, 0.97, 0.93), size_y=0.36)
area("Fill", (0.42, 0.10, 0.18), 0.60, 20.0, (0.86, 0.92, 1.0), size_y=0.45)
area("Softbox", (0.0, -0.02, 0.62), 1.0, 40.0, size_y=0.7)
area("RimCyan", (-0.26, -0.34, 0.08), 0.25, 1.0, CYAN, size_y=0.03, spread=40)
area("RimRed", (0.30, -0.28, 0.08), 0.25, 1.0, RED, size_y=0.03, spread=40)
area("Front", (0, 0, 0.3), 0.5, 0.0, (0.9, 0.95, 1.0), size_y=0.35)
area("Under", (0, 0, -0.45), 0.8, 0.0)
BASE = {k: v.data.energy for k, v in LIGHTS.items()}
BASE_LOC = {k: Vector(v.location) for k, v in LIGHTS.items()}
rx = bpy.data.collections.new("Receivers")
for o in objs.values(): rx.objects.link(o)
for k in ("RimCyan", "RimRed", "Fill", "Front"):
    LIGHTS[k].light_linking.receiver_collection = rx


def place_rims(direction, up, dist=0.32):
    d = Vector(direction).normalized(); dh = Vector((d.x, d.y, 0))
    back = (-dh).normalized() if dh.length > 0.2 else Vector(up).normalized()
    side = back.cross(Vector((0, 0, 1))).normalized()
    for k, s, h in (("RimCyan", -1, 0.045), ("RimRed", 1, 0.05)):
        aim(LIGHTS[k], back * dist + side * (0.15 * s) + Vector((0, 0, h)), (0, 0, 0.006))


def preset(p):
    for k, ob in LIGHTS.items():
        ob.data.energy = BASE[k]; aim(ob, BASE_LOC[k]) if k not in ("RimCyan", "RimRed", "Front") else None
    wbg.inputs["Strength"].default_value = 0.5
    camcol.inputs["Color"].default_value = (0, 0, 0, 1)
    FLOOR_B.inputs["Roughness"].default_value = 0.25
    FLOOR_B.inputs["Base Color"].default_value = (0.05, 0.057, 0.07, 1)
    floor.hide_render = False
    sc.render.film_transparent = False
    if p == "neon":
        LIGHTS["Key"].data.energy = 18 * E; LIGHTS["Fill"].data.energy = 0
        LIGHTS["Front"].data.energy = 12 * E; LIGHTS["Softbox"].data.energy = 7 * E
        LIGHTS["RimCyan"].data.energy = 17 * E; LIGHTS["RimRed"].data.energy = 14 * E
        wbg.inputs["Strength"].default_value = 0.12
        FLOOR_B.inputs["Roughness"].default_value = 0.14
        FLOOR_B.inputs["Base Color"].default_value = (0.010, 0.013, 0.018, 1)
    elif p == "studio":
        LIGHTS["Front"].data.energy = 6 * E
        LIGHTS["RimCyan"].data.energy = 5 * E; LIGHTS["RimRed"].data.energy = 4 * E
    elif p == "top":
        LIGHTS["Softbox"].data.energy = 2 * E; LIGHTS["Softbox"].data.size = 0.1; LIGHTS["Softbox"].data.size_y = 0.07
        aim(LIGHTS["Key"], (-0.46, 0.30, 0.22)); LIGHTS["Key"].data.energy = 22 * E
        LIGHTS["Fill"].data.energy = 12 * E
        LIGHTS["RimCyan"].data.energy = 4 * E; LIGHTS["RimRed"].data.energy = 3 * E
        FLOOR_B.inputs["Base Color"].default_value = (0.012, 0.015, 0.02, 1)
    elif p == "bottom":
        floor.hide_render = True
        aim(LIGHTS["Under"], (0.12, 0.10, -0.45)); LIGHTS["Under"].data.energy = 70 * E
        LIGHTS["Softbox"].data.energy = 8 * E
        LIGHTS["RimCyan"].data.energy = 6 * E; LIGHTS["RimRed"].data.energy = 5 * E
    elif p == "xray":
        LIGHTS["Front"].data.energy = 8 * E
        LIGHTS["RimCyan"].data.energy = 8 * E; LIGHTS["RimRed"].data.energy = 6 * E
        FLOOR_B.inputs["Base Color"].default_value = (0.02, 0.024, 0.03, 1)


# ------------------------------------------------------------------ camera
cd = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(cam)
sc.camera = cam; cd.sensor_fit = "HORIZONTAL"; cd.sensor_width = 36.0; cd.clip_start = 0.005; cd.clip_end = 50


def pts(names):
    out = []
    for nm in names:
        o = bpy.data.objects[nm]; me = o.data
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)[::2]; M = np.array(o.matrix_world)
        out.append(co @ M[:3, :3].T + M[:3, 3])
    return np.concatenate(out)


def frame(direction, lens, fill, up, names, fstop, focus_shift=0.0):
    bpy.context.view_layer.update()
    P = pts(names); tgt = Vector(P.min(0) + P.max(0)) / 2
    d = Vector(direction).normalized(); f = -d
    r = f.cross(up).normalized(); u = r.cross(f).normalized()
    W, H = RES; k = lens / 36.0; dist = 0.5
    for _ in range(10):
        C = np.array(tgt + d * dist); rel = P - C; z = rel @ np.array(f)
        x = (rel @ np.array(r)) / z * k; y = (rel @ np.array(u)) / z * k * (W / H)
        dist *= max((x.max() - x.min()) / fill[0], (y.max() - y.min()) / fill[1])
    C = np.array(tgt + d * dist); rel = P - C; z = rel @ np.array(f)
    x = (rel @ np.array(r)) / z * k; y = (rel @ np.array(u)) / z * k * (W / H)
    cd.lens = lens; cam.location = Vector(C)
    cam.rotation_euler = Matrix((r, u, -f)).transposed().to_euler()
    cd.shift_x = float((x.max() + x.min()) / 2); cd.shift_y = float((y.max() + y.min()) / 2) * (H / W)
    cd.dof.use_dof = bool(fstop)
    if fstop:
        cd.dof.focus_distance = float((np.array(tgt) - C) @ np.array(f)) + focus_shift
        cd.dof.aperture_fstop = fstop; cd.dof.aperture_blades = 7
    print("FRAME tgt", tuple(round(v*1000,1) for v in tgt), "cam", tuple(round(v*1000,1) for v in cam.location), "lens", lens, "names", names[:3])
    return tgt


# ------------------------------------------------------------------ poses
SHELL_PARTS = ["top_shell", "btn_left", "btn_right"]
EXPLODE = {   # mm offsets
    "top_shell": (0, 0, 58), "btn_left": (0, 14, 86), "btn_right": (0, 14, 86),
    "wheel": (0, 0, 32), "axle_pin": (20, 0, 32),
    "key_fwd": (-30, 0, 8), "key_back": (-30, 0, 8), "hinge_pin_f": (-46, 0, 8), "hinge_pin_b": (-46, 0, 8),
}
for k in objs:
    if k.startswith("pcb_"): EXPLODE[k] = (0, 0, 16)


def pose(kind):
    for k, o in objs.items():
        o.matrix_world = HOME[k]
        if kind == "explode" and k in EXPLODE:
            o.matrix_world = Matrix.Translation(Vector(EXPLODE[k]) * MM) @ HOME[k]
        o.data.materials[0] = MAT[k]
        if kind == "xray" and k in SHELL_PARTS:
            o.data.materials[0] = GLASS


TIMES = {}


def render(fname, p, direction, lens, fill=(0.78, 0.78), up=Vector((0, 0, 1)), fstop=None, ev=0.0,
           kind="home", names=None, focus_shift=0.0, front=(0.45, 0.10), frame_on=None):
    stem = os.path.splitext(fname)[0]
    if ONLY and stem not in ONLY:
        return
    for o in plate_objs: o.hide_render = True
    preset(p); pose(kind); place_rims(direction, up)
    fd = Vector(direction).normalized(); fs = fd.cross(Vector((0, 0, 1)))
    fs = fs.normalized() if fs.length > 1e-6 else Vector((0, 1, 0))
    aim(LIGHTS["Front"], fd * front[0] + Vector((0, 0, front[1])) - fs * 0.10, (0, 0, 0.006))
    sc.view_settings.exposure = ev
    vis = names or list(objs)
    for k, o in objs.items(): o.hide_render = k not in vis
    frame(direction, lens, fill, up, frame_on or vis, fstop, focus_shift)
    sc.render.filepath = os.path.join(OUT, fname)
    t = time.time(); bpy.ops.render.render(write_still=True); TIMES[fname] = time.time() - t
    print(f"RENDER {fname} {TIMES[fname]:.0f}s", flush=True)


def plate_scene():
    """Printed parts in print orientation on a textured PEI sheet (220 x 220 mm bed)."""
    files = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(os.path.join(PRN, "*.stl"))}
    order = [("top_shell", -62, 12), ("bottom_shell", 6, 12), ("btn_left", 64, 38), ("btn_right", 64, -30),
             ("wheel", -62, -78), ("key_fwd", -28, -82), ("key_back", -6, -82)]
    pei = pei_material()
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, -0.5 * MM))
    pl = bpy.context.active_object; pl.name = "Plate"
    pl.scale = (220 * MM, 220 * MM, 1.0 * MM)
    bpy.ops.object.transform_apply(scale=True)
    bv = pl.modifiers.new("b", "BEVEL"); bv.width = 0.0004; bv.segments = 3
    pl.data.materials.append(pei); plate_objs.append(pl)
    for nm, x, y in order:
        o = load_stl(files[nm], "print_" + nm, MAT[nm], Vector((x, y, 0)) * MM)
        if nm == "wheel":   # print axis is z on the bed
            o.data.materials[0] = principled("WheelPrint", ACC, 0.32, coat=0.3, micro=0.15, layer_axis=2, layer_str=LS)
        plate_objs.append(o)
    return [o.name for o in plate_objs]


def render_plate(fname, direction, lens, fill, fstop, ev=0.0):
    if ONLY and os.path.splitext(fname)[0] not in ONLY:
        return
    names = plate_scene() if not plate_objs else [o.name for o in plate_objs]
    for o in objs.values(): o.hide_render = True
    for o in plate_objs: o.hide_render = False
    preset("studio")
    floor.location.z = -1.0 * MM
    LIGHTS["Front"].data.energy = 0
    for k in ("RimCyan", "RimRed"):
        LIGHTS[k].light_linking.receiver_collection = None
    place_rims(direction, Vector((0, 0, 1)), dist=0.45)
    LIGHTS["RimCyan"].data.energy = 5 * E; LIGHTS["RimRed"].data.energy = 4 * E
    FLOOR_B.inputs["Base Color"].default_value = (0.012, 0.015, 0.02, 1)
    FLOOR_B.inputs["Roughness"].default_value = 0.6
    sc.view_settings.exposure = ev
    frame(direction, lens, fill, Vector((0, 0, 1)), names, fstop)
    sc.render.filepath = os.path.join(OUT, fname)
    t = time.time(); bpy.ops.render.render(write_still=True); TIMES[fname] = time.time() - t
    print(f"RENDER {fname} {TIMES[fname]:.0f}s", flush=True)
    floor.location.z = FLOOR_Z
    for k in ("RimCyan", "RimRed"):
        LIGHTS[k].light_linking.receiver_collection = rx


# ------------------------------------------------------------------ shot list
ALL = list(objs)
SHELL_VIEW = [k for k in ALL if not k.startswith("pcb_") and k not in ("axle_pin",)]
render("01_hero_neon.png", "neon", (-1.0, 0.62, 0.42), 85, fill=(0.74, 0.76), fstop=9, ev=1.1)
render("02_hero_studio.png", "studio", (-0.85, 1.0, 0.62), 70, fill=(0.72, 0.76), fstop=12, ev=0.3)
render("03_top.png", "top", (0.004, 0, 1), 85, fill=(0.82, 0.80), up=Vector((-1, 0, 0)), ev=0.9)
render("04_side_thumb.png", "studio", (-1, 0.0, 0.10), 85, fill=(0.84, 0.70), ev=0.3)
render("05_bottom.png", "bottom", (0.10, 0.06, -1), 85, fill=(0.80, 0.74), up=Vector((1, 0, 0)), ev=0.55)
render("06_xray.png", "xray", (-0.8, 0.95, 0.75), 70, fill=(0.74, 0.78), ev=0.5, kind="xray")
render("07_exploded.png", "studio", (-0.95, 0.80, 0.78), 60, fill=(0.66, 0.88), ev=0.4, kind="explode")
render("08_detail_wheel.png", "neon", (-0.55, 0.95, 0.55), 100, fstop=4.0, ev=1.0,
       frame_on=["wheel"], front=(0.30, 0.08), fill=(0.50, 0.50))
render_plate("09_print_plate.png", (-0.45, -0.70, 0.80), 60, (1.06, 1.06), fstop=11, ev=0.3)
print("TIMES", {k: round(v) for k, v in TIMES.items()}, "TOTAL", round(sum(TIMES.values())))
print("ALL RENDERS DONE")
