"""Neon Mouse - Blender 5.1 Cycles HQ stüdyo render'ı (render_studio.py'nin yüksek kaliteli sürümü).

Kullanım:
  blender.exe --background --python render_studio_hq.py -- <STL_DIR> <OUT_DIR> [preview] [only=01_hero_iso,07_hero_neon]

STL_DIR: step_to_stl_hq.py ile mouse_assembly_full.step'ten ince tessellasyonla üretilen grup STL'leri
         (7 mekanik parça + kart/tus/sensor/encoder/ic/pasif/header PCB grupları; montaj konumları STEP'teki gibi).
Birim: STL mm -> sahne metre (0.001), ışık gücü ve alan derinliği fiziksel ölçekte.
"""
import bpy, sys, os, math, time
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
STL_DIR, OUT_DIR = os.path.abspath(argv[0]), os.path.abspath(argv[1])
PREVIEW = "preview" in argv
ONLY = None
for a in argv:
    if a.startswith("only="):
        ONLY = set(a[5:].split(","))
os.makedirs(OUT_DIR, exist_ok=True)

MM = 0.001
CENTER = Vector((39.37, -62.0, 14.0)) * MM          # render_studio.py ile aynı merkez
FLOOR_Z = (-4.70 * MM) - CENTER.z                    # PTFE ayakların alt yüzü = zemin

# ---------------------------------------------------------------- sahne / render ayarları
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
cy = sc.cycles
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = (d.type == "OPTIX")
    cy.device = "GPU"
except Exception as e:
    print("GPU ayarı başarısız:", e)

if PREVIEW:
    RES = (960, 540); cy.samples = 48; cy.adaptive_threshold = 0.05
else:
    RES = (2560, 1440); cy.samples = 1024; cy.adaptive_threshold = 0.008
cy.use_adaptive_sampling = True
cy.adaptive_min_samples = 64 if not PREVIEW else 16
cy.use_denoising = True
cy.denoiser = "OPENIMAGEDENOISE"
cy.denoising_use_gpu = True
cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
cy.denoising_prefilter = "ACCURATE"
cy.max_bounces = 16
cy.diffuse_bounces = 6
cy.glossy_bounces = 8
cy.transmission_bounces = 12
cy.transparent_max_bounces = 32
cy.sample_clamp_direct = 0.0
cy.sample_clamp_indirect = 4.0          # ateşböceği bastırma
cy.blur_glossy = 0.5
cy.use_light_tree = True
cy.film_exposure = 1.0
sc.render.use_persistent_data = True
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.render.filter_size = 1.2
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "8"
sc.render.image_settings.compression = 15
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.view_settings.exposure = 0.0
sc.unit_settings.system = "METRIC"


def hexlin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


CYAN = hexlin("#00E5FF")
NEON_RED = hexlin("#FF3347")
DERIN = hexlin("#0D161F")

# ---------------------------------------------------------------- dünya
world = bpy.data.worlds.new("Studio")
sc.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wbg = wn["Background"]
wbg.inputs["Color"].default_value = (*DERIN, 1)
wbg.inputs["Strength"].default_value = 0.6
# kamera ışınlarında fon tam koyu (zemin uzak kenarıyla birleşir, ufuk çizgisi görünmez); aydınlatmada DERIN tonu
_lp = wn.new("ShaderNodeLightPath")
_bk = wn.new("ShaderNodeBackground"); _bk.inputs["Color"].default_value = (0, 0, 0, 1)
_mx = wn.new("ShaderNodeMixShader")
world.node_tree.links.new(_lp.outputs["Is Camera Ray"], _mx.inputs["Fac"])
world.node_tree.links.new(wbg.outputs["Background"], _mx.inputs[1])
world.node_tree.links.new(_bk.outputs["Background"], _mx.inputs[2])
world.node_tree.links.new(_mx.outputs["Shader"], wn["World Output"].inputs["Surface"])


# ---------------------------------------------------------------- malzemeler
def principled(name, color, rough, metal=0.0, coat=0.0, coat_rough=0.1, spec=0.5,
               bevel=0.00030, micro=0.0, micro_scale=2500.0):
    """Principled BSDF + Bevel node'lu normal (ince kenar vurgusu) + isteğe bağlı mikro doku bump."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    n = nt.nodes
    b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if coat > 0:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = coat_rough
    normal_src = None
    if bevel > 0:
        bv = n.new("ShaderNodeBevel")
        bv.samples = 8
        bv.inputs["Radius"].default_value = bevel
        normal_src = bv.outputs["Normal"]
    if micro > 0:
        tc = n.new("ShaderNodeTexCoord")
        nz = n.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = micro_scale
        nz.inputs["Detail"].default_value = 3.0
        nz.inputs["Roughness"].default_value = 0.6
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        bp = n.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = micro
        bp.inputs["Distance"].default_value = 0.00002
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        if normal_src is not None:
            nt.links.new(normal_src, bp.inputs["Normal"])
        normal_src = bp.outputs["Normal"]
        # pürüzlülükte çok hafif varyasyon (plastik doku hissi)
        mr = n.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = rough - 0.04
        mr.inputs["To Max"].default_value = rough + 0.04
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    if normal_src is not None:
        nt.links.new(normal_src, b.inputs["Normal"])
        if coat > 0:
            nt.links.new(normal_src, b.inputs["Coat Normal"])
    return m


# Parça renkleri render_studio.py ile aynı aile: kömür kabuk, cyan tekerlek/başparmak, beyaz PTFE
MATS = {
    "mouse_top_shell":    principled("TopShell",    (0.060, 0.063, 0.070), 0.36, 0.0, coat=0.25, coat_rough=0.22, micro=0.35),
    "mouse_base":         principled("BaseChassis", (0.030, 0.032, 0.037), 0.48, 0.0, micro=0.45),
    "mouse_scroll_wheel": principled("ScrollWheel", (0.040, 0.580, 0.680), 0.30, 0.15, coat=0.3, bevel=0.00020, micro=0.2),
    "mouse_dpi_button":   principled("DpiButton",   (0.120, 0.125, 0.140), 0.26, 0.10, coat=0.4, bevel=0.00025),
    "mouse_thumb_fwd":    principled("ThumbFwd",    (0.050, 0.520, 0.620), 0.28, 0.10, coat=0.35, bevel=0.00025, micro=0.15),
    "mouse_thumb_back":   principled("ThumbBack",   (0.050, 0.520, 0.620), 0.28, 0.10, coat=0.35, bevel=0.00025, micro=0.15),
    "mouse_skates":       principled("PtfeSkates",  (0.880, 0.900, 0.920), 0.30, 0.0, bevel=0.00015),
    # PCB grupları
    "kart":    principled("PCB_Board",   (0.020, 0.200, 0.080), 0.32, 0.0, coat=0.5, coat_rough=0.15, bevel=0.0001),
    "tus":     principled("PCB_Switch",  (0.035, 0.035, 0.040), 0.38, 0.0, bevel=0.00015),
    "sensor":  principled("PCB_Sensor",  (0.060, 0.060, 0.070), 0.30, 0.0, bevel=0.00015),
    "encoder": principled("PCB_Encoder", (0.750, 0.620, 0.200), 0.28, 0.6, bevel=0.00015),
    "ic":      principled("PCB_IC",      (0.025, 0.025, 0.028), 0.45, 0.0, bevel=0.00008),
    "pasif":   principled("PCB_Passive", (0.400, 0.300, 0.180), 0.40, 0.0, bevel=0.00005),
    "header":  principled("PCB_Header",  (0.030, 0.030, 0.035), 0.40, 0.0, bevel=0.0001),
}


def glass_mat():
    """X-ray kabuk: buzlu şeffaf, kenarlarda Fresnel ile belirginleşen alfa (ucuz, kostik gürültüsüz)."""
    m = bpy.data.materials.new("GlassShell")
    m.use_nodes = True
    nt = m.node_tree; n = nt.nodes
    b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.80, 0.88, 0.95, 1)
    b.inputs["Roughness"].default_value = 0.12
    b.inputs["Coat Weight"].default_value = 0.6
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    mr = n.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.10
    mr.inputs["To Max"].default_value = 0.55
    nt.links.new(lw.outputs["Facing"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Alpha"])
    return m


MAT_GLASS = glass_mat()


def floor_mat():
    """Koyu stüdyo zemini; merkezden uzaklaştıkça siyaha karışır (ufuk çizgisi görünmez, sonsuz fon hissi)."""
    m = bpy.data.materials.new("Floor")
    m.use_nodes = True
    nt = m.node_tree; n = nt.nodes
    b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.030, 0.036, 0.045, 1)
    b.inputs["Roughness"].default_value = 0.30
    b.inputs["Specular IOR Level"].default_value = 0.45
    out = n["Material Output"]
    tc = n.new("ShaderNodeTexCoord")
    vl = n.new("ShaderNodeVectorMath"); vl.operation = "LENGTH"
    nt.links.new(tc.outputs["Object"], vl.inputs[0])
    mr = n.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs["From Min"].default_value = 0.18
    mr.inputs["From Max"].default_value = 0.70
    nt.links.new(vl.outputs["Value"], mr.inputs["Value"])
    blk = n.new("ShaderNodeBsdfDiffuse"); blk.inputs["Color"].default_value = (0, 0, 0, 1)
    mx = n.new("ShaderNodeMixShader")
    nt.links.new(mr.outputs["Result"], mx.inputs["Fac"])
    nt.links.new(b.outputs["BSDF"], mx.inputs[1])
    nt.links.new(blk.outputs["BSDF"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    return m, b


MAT_FLOOR, FLOOR_BSDF = floor_mat()

# ---------------------------------------------------------------- geometri
objs = {}
MECH = ["mouse_base", "mouse_top_shell", "mouse_scroll_wheel", "mouse_dpi_button",
        "mouse_thumb_fwd", "mouse_thumb_back", "mouse_skates"]
PCB = ["kart", "tus", "sensor", "encoder", "ic", "pasif", "header"]
for name in MECH + PCB:
    p = os.path.join(STL_DIR, name + ".stl")
    if not os.path.exists(p):
        print("EKSIK STL:", p)
        continue
    bpy.ops.wm.stl_import(filepath=p, global_scale=MM)
    o = bpy.context.selected_objects[0]
    o.name = name if name in MECH else "pcb_" + name
    o.data.transform(o.matrix_basis)                 # importer ölçeği nesne dönüşümünde tutar -> köşelere işle
    o.matrix_basis = Matrix.Identity(4)
    o.data.transform(Matrix.Translation(-CENTER))
    o.data.shade_smooth()
    o.data.set_sharp_from_angle(angle=math.radians(30))
    o.data.materials.append(MATS[name])
    objs[name] = o
print("Yüklenen parçalar:", sorted(objs))
assert all(n in objs for n in MECH), "mekanik parça eksik"
assert all(n in objs for n in ("kart", "tus", "encoder")), "PCB eksik"

# zemin (yumuşak temas gölgesi + hafif yansıma; şeffaf çıktılarda shadow catcher)
bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0, 0, FLOOR_Z))
floor = bpy.context.active_object
floor.name = "Floor"
floor.data.materials.append(MAT_FLOOR)

# ---------------------------------------------------------------- ışıklar
LIGHTS = {}
E_SCALE = 0.04  # tüm ışık güçleri için ortak ölçek (metre ölçeğinde sahne)


def add_area(name, loc, size, energy, color=(1, 1, 1), size_y=None, spread=180, target=(0, 0, 0)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy * E_SCALE
    ld.color = color
    if size_y is None:
        ld.shape = "DISK"; ld.size = size
    else:
        ld.shape = "RECTANGLE"; ld.size = size; ld.size_y = size_y
    ld.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(ob)
    ob.location = Vector(loc)
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    ob.visible_camera = False
    LIGHTS[name] = ob
    return ob


# 3 nokta yumuşak stüdyo + geniş tepe softbox + neon rim (cyan sol-arka, neon kırmızı sağ-arka)
add_area("Key",      (-0.34, 0.26, 0.40), 0.55, 72.0, (1.0, 0.97, 0.93), size_y=0.40)
add_area("Fill",     (0.42, 0.10, 0.18), 0.60, 22.0, (0.86, 0.92, 1.00), size_y=0.45)
add_area("Softbox",  (0.00, -0.02, 0.62), 1.10, 44.0, (1.0, 1.0, 1.0), size_y=0.70)
add_area("RimCyan",  (-0.26, -0.34, 0.08), 0.25, 1.0, CYAN, size_y=0.03, spread=40, target=(0, 0, 0.008))
add_area("RimRed",   (0.30, -0.28, 0.08), 0.25, 0.8, NEON_RED, size_y=0.03, spread=40, target=(0, 0, 0.008))
add_area("Under",    (0.0, 0.0, -0.45), 0.8, 0.0, (0.95, 0.97, 1.0))   # yalnız alt görünümde
BASE_ENERGY = {k: v.data.energy for k, v in LIGHTS.items()}

# Light linking: neon rim ışıkları yalnız ürünü aydınlatır (zemini renkli lekeye boğmaz)
rim_rx = bpy.data.collections.new("RimReceivers")
for o in objs.values():
    rim_rx.objects.link(o)
for k in ("RimCyan", "RimRed", "Fill"):   # Fill de zeminde ayna yansıması bırakmasın
    LIGHTS[k].light_linking.receiver_collection = rim_rx


def place_rims(direction, up):
    """Rim ışıklarını her kadrajda kameraya göre ürünün ARKASINA, sol (cyan) ve sağ (neon kırmızı) yanlara koy."""
    d = Vector(direction).normalized()
    dh = Vector((d.x, d.y, 0))
    back = (-dh).normalized() if dh.length > 0.2 else Vector(up).normalized()
    side = back.cross(Vector((0, 0, 1))).normalized()       # kameradan bakınca sağ taraf
    for k, sgn, h in (("RimCyan", -1, 0.045), ("RimRed", 1, 0.05)):
        ob = LIGHTS[k]
        ob.location = back * 0.32 + side * (0.14 * sgn) + Vector((0, 0, h))
        t = Vector((0, 0, 0.008)) - ob.location
        ob.rotation_euler = t.to_track_quat("-Z", "Y").to_euler()


def light_preset(preset):
    for k, ob in LIGHTS.items():
        ob.data.energy = BASE_ENERGY[k]
    wbg.inputs["Strength"].default_value = 0.6
    FLOOR_BSDF.inputs["Roughness"].default_value = 0.30
    FLOOR_BSDF.inputs["Base Color"].default_value = (0.055, 0.062, 0.075, 1)
    floor.hide_render = False
    floor.is_shadow_catcher = False
    sc.render.film_transparent = False
    if preset == "bottom":
        floor.hide_render = True
        LIGHTS["Under"].data.energy = 40.0 * E_SCALE
        LIGHTS["Softbox"].data.energy = 10.0 * E_SCALE
    elif preset == "neon":
        LIGHTS["Key"].data.energy = 20.0 * E_SCALE
        LIGHTS["Fill"].data.energy = 0.0 * E_SCALE
        LIGHTS["Softbox"].data.energy = 8.0 * E_SCALE
        LIGHTS["RimCyan"].data.energy = 16.0 * E_SCALE
        LIGHTS["RimRed"].data.energy = 13.0 * E_SCALE
        wbg.inputs["Strength"].default_value = 0.15
        FLOOR_BSDF.inputs["Roughness"].default_value = 0.16
        FLOOR_BSDF.inputs["Base Color"].default_value = (0.012, 0.015, 0.020, 1)
    elif preset == "transparent":
        sc.render.film_transparent = True
        floor.is_shadow_catcher = True


# ---------------------------------------------------------------- kamera + otomatik kadraj
cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
cam_data.sensor_fit = "HORIZONTAL"
cam_data.sensor_width = 36.0
cam_data.clip_start = 0.005
cam_data.clip_end = 50.0


def world_points(names):
    pts = []
    for n in names:
        o = objs[n]
        me = o.data
        co = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)[::3]
        M = np.array(o.matrix_world)
        co = co @ M[:3, :3].T + M[:3, 3]
        pts.append(co)
    return np.concatenate(pts)


def look_rot(fwd, up):
    f = fwd.normalized()
    r = f.cross(up).normalized()
    u = r.cross(f).normalized()
    M = Matrix((r, u, -f)).transposed()
    return M.to_euler()


def frame(direction, lens, fill=(0.80, 0.80), up=Vector((0, 0, 1)), names=None, fstop=None):
    """direction: hedeften kameraya vektör. Ürün kadrajı doldurup ortalayana kadar mesafe + lens shift ayarlanır."""
    names = names or list(objs)
    bpy.context.view_layer.update()          # konum değişikliklerinden sonra matrix_world güncel olsun
    P = world_points(names)
    tgt = Vector(P.min(0) + P.max(0)) / 2
    d = Vector(direction).normalized()
    fwd = -d
    r = fwd.cross(up).normalized(); u = r.cross(fwd).normalized()
    W, H = RES
    k = lens / 36.0
    dist = 0.5
    for _ in range(8):
        C = np.array(tgt + d * dist)
        rel = P - C
        z = rel @ np.array(fwd)
        x = (rel @ np.array(r)) / z * k
        y = (rel @ np.array(u)) / z * k * (W / H)
        s = max((x.max() - x.min()) / fill[0], (y.max() - y.min()) / fill[1])
        dist *= s
    C = np.array(tgt + d * dist)
    rel = P - C
    z = rel @ np.array(fwd)
    x = (rel @ np.array(r)) / z * k
    y = (rel @ np.array(u)) / z * k * (W / H)
    cam_data.lens = lens
    cam.location = Vector(C)
    cam.rotation_euler = look_rot(fwd, up)
    cam_data.shift_x = float((x.max() + x.min()) / 2)
    cam_data.shift_y = float((y.max() + y.min()) / 2) * (H / W)
    if fstop:
        cam_data.dof.use_dof = True
        cam_data.dof.focus_distance = float((np.array(tgt) - C) @ np.array(fwd))
        cam_data.dof.aperture_fstop = fstop
        cam_data.dof.aperture_blades = 7
    else:
        cam_data.dof.use_dof = False
    return dist


TIMES = {}


def render(fname, preset, direction, lens, fill=(0.80, 0.80), up=Vector((0, 0, 1)), fstop=None, names=None):
    stem = os.path.splitext(fname)[0]
    if ONLY and stem not in ONLY:
        return
    light_preset(preset)
    place_rims(direction, up)
    vis = names or list(objs)
    for n, o in objs.items():
        o.hide_render = n not in vis
    dist = frame(direction, lens, fill, up, vis, fstop)
    sc.render.image_settings.color_mode = "RGBA" if sc.render.film_transparent else "RGB"
    sc.render.filepath = os.path.join(OUT_DIR, fname)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    TIMES[fname] = time.time() - t
    print(f"RENDER {fname}: {TIMES[fname]:.1f}s  dist={dist*1000:.0f}mm lens={lens}")


ALL = list(objs)
EXT = [n for n in ALL]   # dış görünüm: PCB kabuk içinde zaten görünmez, montaj tam

# 1. Hero 3/4 (render_studio.py ile aynı yön: ön-sol üst)
render("01_hero_iso.png", "studio", (-170, 150, 120), 70, fill=(0.80, 0.82), fstop=11)
# 1b. Şeffaf zeminli hero (slayt bindirme; gölge shadow catcher ile)
render("01_hero_iso_seffaf.png", "transparent", (-170, 150, 120), 70, fill=(0.80, 0.82), fstop=11)
# 2. Üst görünüm (burun sola, 16:9 kadraja yatay)
render("02_top.png", "studio", (0, -0.006, 1), 85, fill=(0.82, 0.84), up=Vector((1, 0, 0)))
# 3. Sol profil
render("03_side_left.png", "studio", (-1, 0, 0.018), 85, fill=(0.84, 0.80))
# 4. Alt görünüm (zemin gizli, alttan ışık)
render("04_bottom.png", "bottom", (0, -0.006, -1), 85, fill=(0.82, 0.84), up=Vector((-1, 0, 0)))
# 5. X-ray: buzlu şeffaf üst kabuk, PCB görünür
objs["mouse_top_shell"].data.materials[0] = MAT_GLASS
render("05_xray_pcb.png", "studio", (-165, 140, 130), 70, fill=(0.80, 0.82), fstop=14)
objs["mouse_top_shell"].data.materials[0] = MATS["mouse_top_shell"]

# 6. Patlatılmış montaj — ofsetler render_studio.py'deki ile birebir (PCB yerinde)
offsets = {
    "mouse_top_shell":    Vector((0, 0, 46)),
    "mouse_dpi_button":   Vector((0, 0, 64)),
    "mouse_scroll_wheel": Vector((0, 0, 22)),
    "mouse_thumb_fwd":    Vector((-24, 0, 26)),
    "mouse_thumb_back":   Vector((-24, 0, 26)),
    "mouse_base":         Vector((0, 0, -22)),
    "mouse_skates":       Vector((0, 0, -42)),
}
need_explode = (ONLY is None) or bool(ONLY & {"06_exploded", "06_exploded_seffaf"})
if need_explode:
    for k, off in offsets.items():
        objs[k].location = off * MM
    floor.location.z = FLOOR_Z - 42 * MM          # en alttaki PTFE ayakların altı
    render("06_exploded.png", "studio", (-255, 210, 165), 62, fill=(0.66, 0.88))
    render("06_exploded_seffaf.png", "transparent", (-255, 210, 165), 62, fill=(0.66, 0.88))
    for k in offsets:
        objs[k].location = (0, 0, 0)
    floor.location.z = FLOOR_Z

# 7. Neon kahraman çekim: koyu, alçak açı, cyan + neon kırmızı rim
render("07_hero_neon.png", "neon", (-150, 165, 62), 85, fill=(0.76, 0.78), fstop=10)

print("SURELER:", {k: round(v, 1) for k, v in TIMES.items()}, "TOPLAM", round(sum(TIMES.values()), 1))
print("ALL RENDERS DONE")
