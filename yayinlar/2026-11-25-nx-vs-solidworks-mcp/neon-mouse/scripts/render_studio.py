"""Blender 5.1 Cycles GPU Studio Renderer for the NX 2206 Gaming Mouse Mechanical Assembly."""
import bpy, sys, os, math
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
STL_DIR, PCB_STL_DIR, OUT_DIR = args[0], args[1], args[2]
os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 64
sc.cycles.use_denoising = True
try:
    sc.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
except Exception:
    pass

sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.view_settings.exposure = 1.1

# Studio soft gradient world
w = bpy.data.worlds.new("StudioWorld")
sc.world = w
w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.04, 0.045, 0.055, 1.0)
bg.inputs["Strength"].default_value = 0.8

def make_mat(name, color, roughness=0.35, metallic=0.0, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    return m

MATS = {
    "mouse_top_shell":    make_mat("TopShell",    (0.09, 0.095, 0.105), roughness=0.32, metallic=0.05),
    "mouse_base":         make_mat("BaseChassis", (0.045, 0.048, 0.055), roughness=0.42, metallic=0.05),
    "mouse_scroll_wheel": make_mat("ScrollWheel", (0.04, 0.58, 0.68),   roughness=0.28, metallic=0.35),
    "mouse_dpi_button":   make_mat("DpiButton",   (0.14, 0.145, 0.16),  roughness=0.25, metallic=0.15),
    "mouse_thumb_fwd":    make_mat("ThumbFwd",    (0.05, 0.52, 0.62),   roughness=0.28, metallic=0.20),
    "mouse_thumb_back":   make_mat("ThumbBack",   (0.05, 0.52, 0.62),   roughness=0.28, metallic=0.20),
    "mouse_skates":       make_mat("PtfeSkates",  (0.92, 0.94, 0.96),   roughness=0.18, metallic=0.00),
    # PCB groups
    "kart":    make_mat("PCB_Board",   (0.03, 0.30, 0.14), roughness=0.45, metallic=0.0),
    "tus":     make_mat("PCB_Switch",  (0.05, 0.05, 0.06), roughness=0.35, metallic=0.0),
    "sensor":  make_mat("PCB_Sensor",  (0.10, 0.10, 0.12), roughness=0.30, metallic=0.0),
    "encoder": make_mat("PCB_Encoder", (0.75, 0.62, 0.20), roughness=0.30, metallic=0.6),
    "diger":   make_mat("PCB_Other",   (0.22, 0.22, 0.25), roughness=0.40, metallic=0.2),
}
MAT_GLASS = make_mat("GlassShell", (0.75, 0.85, 0.95), roughness=0.12, metallic=0.0, alpha=0.22, transmission=0.65)

# Center mouse around origin: (39.37, -62.0, 14.0)
CENTER = Vector((39.37, -62.0, 14.0))

def import_stl(path, name, mat):
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    o.name = name
    o.data.materials.append(mat)
    bpy.ops.object.shade_auto_smooth(angle=math.radians(38))
    o.location = -CENTER
    return o

mech_objs = {}
for name in ["mouse_base", "mouse_top_shell", "mouse_scroll_wheel", "mouse_dpi_button",
             "mouse_thumb_fwd", "mouse_thumb_back", "mouse_skates"]:
    p = os.path.join(STL_DIR, name + ".stl")
    if os.path.exists(p):
        mech_objs[name] = import_stl(p, name, MATS[name])

pcb_objs = {}
for name in ["kart", "tus", "sensor", "encoder", "diger"]:
    p = os.path.join(PCB_STL_DIR, name + ".stl")
    if os.path.exists(p):
        pcb_objs[name] = import_stl(p, "pcb_" + name, MATS[name])

# 3-point studio lighting
def add_light(name, loc, size, energy, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    ob.location = Vector(loc)
    sc.collection.objects.link(ob)
    d = Vector((0, 0, 0)) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

add_light("Key",  (-120,  110, 160), 110, 130000, (1.0, 0.98, 0.95))
add_light("Fill", ( 150,   40,  80), 100,  55000, (0.80, 0.90, 1.0))
add_light("Rim",  (  20, -170, 110),  90,  85000, (1.0, 0.90, 0.80))
add_light("Under",(   0,    0,-160), 120,  45000, (0.95, 0.97, 1.0))

cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.lens = 75

def aim_and_render(filename, cam_pos, target=(0, 0, 0), lens=75):
    cam.data.lens = lens
    cam.location = Vector(cam_pos)
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT_DIR, filename)
    bpy.ops.render.render(write_still=True)

# 1. Hero Front-Left 3/4 Iso (shows split LMB/RMB, scroll wheel, sloped DPI, left thumb buttons!)
aim_and_render("01_hero_iso.png", (-170, 150, 120), target=(0, 0, -2), lens=70)

# 2. Top View (full nose-to-tail framing!)
aim_and_render("02_top.png", (0, -2, 340), target=(0, 0, 0), lens=65)

# 3. Left Side Profile (full ergonomic hump & thumb buttons!)
aim_and_render("03_side_left.png", (-295, 0, 8), target=(0, 0, -2), lens=70)

# 4. Bottom View (full sole showing front, rear, and sensor-ring PTFE skates + PMW3360 window!)
aim_and_render("04_bottom.png", (0, -2, -340), target=(0, 0, -16), lens=65)

# 5. Translucent X-Ray View (frosted glass top shell revealing PCB, 6 switches, encoder, scroll wheel, thumb bell-cranks!)
orig_top_mat = mech_objs["mouse_top_shell"].data.materials[0]
mech_objs["mouse_top_shell"].data.materials[0] = MAT_GLASS
aim_and_render("05_xray_pcb.png", (-165, 140, 130), target=(0, 2, -2), lens=70)
mech_objs["mouse_top_shell"].data.materials[0] = orig_top_mat

# 6. Exploded Engineering Assembly View (full stack with PTFE skates clearly visible!)
offsets = {
    "mouse_top_shell":    Vector((0, 0,  46)),
    "mouse_dpi_button":   Vector((0, 0,  64)),
    "mouse_scroll_wheel": Vector((0, 0,  22)),
    "mouse_thumb_fwd":    Vector((-24, 0, 26)),
    "mouse_thumb_back":   Vector((-24, 0, 26)),
    "mouse_base":         Vector((0, 0, -22)),
    "mouse_skates":       Vector((0, 0, -42)),
}
for k, off in offsets.items():
    if k in mech_objs:
        mech_objs[k].location = -CENTER + off
aim_and_render("06_exploded.png", (-255, 210, 165), target=(0, 0, 6), lens=62)
print("ALL RENDERS DONE")
