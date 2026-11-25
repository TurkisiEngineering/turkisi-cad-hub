# Blender 5.1 headless hero renders of the mouse assembly.
# run: blender.exe --background --python render_hero.py -- [shot ...]
import bpy, sys, os, math
from mathutils import Vector

W = r"C:\Users\marya\Desktop\Mouse for PCB\work"
OUT = r"C:\Users\marya\Desktop\Mouse for PCB\TESLIM\renders"
os.makedirs(OUT, exist_ok=True)
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SHOTS = args or ["hero", "top", "side", "exploded", "underside", "cutaway"]
SAMPLES = 96
S = 0.001  # mm -> m

# (file, material, explode dz mm, cut in cutaway)
P = W + r"\03_parts"
M = W + r"\00_pcb\mesh"
PARTS = {
    "bottom_shell": (P + r"\bottom_shell\bottom_shell.stl", "dark", 0, True),
    "top_shell": (P + r"\top_shell\top_shell.stl", "shell", 75, True),
    "button_L": (P + r"\button_L\button_L.stl", "shell", 95, True),
    "button_R": (P + r"\button_R\button_R.stl", "shell", 95, False),
    "dpi_button": (P + r"\dpi_button\dpi_button.stl", "shell", 105, False),
    "side_btn_back": (P + r"\side_btn_back\side_btn_back.stl", "shell", 45, True),
    "side_btn_fwd": (P + r"\side_btn_fwd\side_btn_fwd.stl", "shell", 45, True),
    "wheel_body": (P + r"\wheel\wheel_body.stl", "wheel", 55, False),
    "axle_pin": (P + r"\wheel\axle_pin.stl", "steel", 55, False),
    "wheel_yoke": (P + r"\wheel_yoke\wheel_yoke.stl", "dark", 30, False),
    "board": (M + r"\board.stl", "pcb", 22, False),
    "smd": (M + r"\smd.stl", "smd", 22, False),
    "switch": (M + r"\switch.stl", "comp", 22, False),
    "encoder": (M + r"\encoder.stl", "comp", 22, False),
    "sensor": (M + r"\sensor.stl", "comp", 22, False),
    "usb_header": (M + r"\usb_header.stl", "steel", 22, False),
}
SHELLISH = {"bottom_shell", "top_shell", "button_L", "button_R", "dpi_button", "side_btn_back", "side_btn_fwd"}


def mat(name, col, rough, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    return m


def build_mats():
    return {
        "shell": mat("PLA_offwhite", (0.80, 0.78, 0.74), 0.55),
        "dark": mat("PLA_graphite", (0.035, 0.037, 0.042), 0.6),
        "wheel": mat("wheel_black", (0.015, 0.015, 0.017), 0.45),
        "steel": mat("steel", (0.75, 0.75, 0.76), 0.25, 1.0),
        "pcb": mat("pcb_green", (0.02, 0.20, 0.06), 0.35, 0.0, 0.4),
        "smd": mat("smd", (0.03, 0.03, 0.03), 0.4),
        "comp": mat("components", (0.06, 0.06, 0.065), 0.5),
        "ground": mat("ground", (0.62, 0.63, 0.65), 0.8),
        "cap": mat("cut_cap", (0.85, 0.25, 0.12), 0.6),
    }


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        for dev in ("OPTIX", "CUDA"):
            try:
                pr.compute_device_type = dev
                pr.get_devices()
                for d in pr.devices:
                    d.use = True
                sc.cycles.device = "GPU"
                break
            except Exception:
                continue
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "Filmic"
    except Exception:
        sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "None"
    w = bpy.data.worlds.new("w"); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.80, 0.82, 0.86, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25
    return sc


def load_parts(mats):
    objs = {}
    for k, (f, mname, dz, cut) in PARTS.items():
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.wm.stl_import(filepath=f, global_scale=S)
        o = bpy.context.selected_objects[0]
        bpy.context.view_layer.objects.active = o
        o.name = k
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        o.data.materials.append(mats[mname])
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
        objs[k] = o
    return objs


def bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        if o.hide_render:
            continue
        for v in o.bound_box:
            p = o.matrix_world @ Vector(v)
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    return lo, hi


def add_area(name, loc, target, size, energy, col=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA"); l.size = size; l.energy = energy; l.color = col
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def lights(c, r, below=False):
    sgn = -1 if below else 1
    c = Vector(c)
    L = [add_area("key", c + Vector((-2.2, 1.6, 2.6 * sgn)) * r, c, 3.0 * r, 80 * r * r),
         add_area("fill", c + Vector((2.6, 1.2, 1.2 * sgn)) * r, c, 4.0 * r, 30 * r * r),
         add_area("rim", c + Vector((0.5, -3.0, 1.8 * sgn)) * r, c, 2.5 * r, 70 * r * r)]
    return L


def ground(z):
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0.04, -0.064, z))
    g = bpy.context.active_object; g.name = "ground"
    return g


def camera(c, direction, r, lens=70, up=(0, 0, 1), aspect=4 / 3, dist=None):
    cam_d = bpy.data.cameras.new("cam"); cam_d.lens = lens
    cam_d.sensor_fit = "HORIZONTAL"; cam_d.sensor_width = 36
    cam = bpy.data.objects.new("cam", cam_d); bpy.context.collection.objects.link(cam)
    fov_v = 2 * math.atan(36 / aspect / 2 / lens)
    if dist is None:
        dist = r / math.sin(fov_v / 2) * 1.08
    d = Vector(direction).normalized()
    cam.location = Vector(c) + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y" if abs(d.z) < 0.99 else "Y").to_euler()
    if abs(d.z) > 0.99:  # top/bottom: front (+Y) at image top
        cam.rotation_euler = (0, 0, 0) if d.z > 0 else (math.pi, 0, math.pi)
    cam_d.clip_start = 0.005; cam_d.clip_end = 20
    bpy.context.scene.camera = cam
    return cam


def cut(o, mats, xcut):
    """remove material X < xcut (thumb half) with an exact boolean; caps get the cap colour."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    b = bpy.context.active_object
    b.scale = (0.2, 0.4, 0.2); b.location = (xcut - 0.1, -0.06, 0.0)
    b.data.materials.append(mats["cap"])
    m = o.modifiers.new("cut", "BOOLEAN"); m.operation = "DIFFERENCE"; m.object = b
    m.solver = "EXACT"; m.material_mode = "TRANSFER"
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(b, do_unlink=True)
    o.data.materials.clear() if False else None


def render(name):
    sc = bpy.context.scene
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("WROTE", sc.render.filepath)


for shot in SHOTS:
    setup_scene()
    mats = build_mats()
    objs = load_parts(mats)
    zfloor = -5.85 * S
    if shot == "exploded":
        for k, o in objs.items():
            o.location.z += PARTS[k][2] * S
    if shot == "cutaway":
        xc = 40.0 * S  # centre plane of the shell, thumb half removed
        for k in [k for k in PARTS if PARTS[k][3]]:
            cut(objs[k], mats, xc)
    bpy.context.view_layer.update()
    lo, hi = bounds(objs.values())
    print("BOUNDS", tuple(lo), tuple(hi), [o.scale[0] for o in objs.values()][:2])
    c = (lo + hi) / 2
    c.z = lo.z + (hi.z - lo.z) * 0.40
    r = (hi - lo).length / 2
    if shot != "underside":
        g = ground(min(zfloor, lo.z) - 0.0002)
        g.data.materials.append(mats["ground"])
    views = {
        "hero": ((-1.0, 1.25, 0.95), 70),
        "top": ((0, 0, 1), 80),
        "side": ((-1, 0, 0.12), 80),
        "exploded": ((-1.0, 1.3, 0.75), 60),
        "underside": ((-0.55, 0.55, -1.0), 70),
        "cutaway": ((-1.15, 0.85, 0.75), 70),
    }
    d, lens = views[shot]
    if shot == "side":
        r = max(hi.y - lo.y, (hi.z - lo.z) * 4 / 3) / 2 * 0.80
    if shot == "top":
        r = max((hi.y - lo.y), (hi.x - lo.x) * 4 / 3) / 2 * 0.85
    lights(c, max(r, 0.06), below=(shot == "underside"))
    fac = {"hero": 0.74, "cutaway": 0.80, "underside": 0.80, "exploded": 0.92}
    if shot in ("top", "side"):
        fov_v = 2 * math.atan(36 / (4 / 3) / 2 / lens)
        half = (hi.y - lo.y) / 2 * 1.12
        near = (hi.z - c.z) if shot == "top" else (c.x - lo.x)
        camera(c, d, r, lens, dist=half / math.tan(fov_v / 2) / (4 / 3 if shot == "side" else 1) + near)
    else:
        camera(c, d, r * fac[shot], lens)
    if shot == "underside":
        w = bpy.context.scene.world.node_tree.nodes["Background"]
        w.inputs["Color"].default_value = (0.55, 0.57, 0.61, 1)
        w.inputs["Strength"].default_value = 0.6
    render("mouse_" + shot)
