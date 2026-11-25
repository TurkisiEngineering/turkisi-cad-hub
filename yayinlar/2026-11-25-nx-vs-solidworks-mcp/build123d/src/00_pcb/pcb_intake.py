# WP-A PCB intake: mechanical interface data of mouse_pcb.step (native STEP coords, no transform).
# usage: python pcb_intake.py   (paths fixed relative to this file)
# writes: PCB_DATA.json, keepout grid inside it, pcb.stl, mesh/*.stl (per group, for renders)
import json, math, os, hashlib
from collections import defaultdict
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopLoc import TopLoc_Location
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_WIRE, TopAbs_EDGE
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.BRep import BRep_Tool

HERE = os.path.dirname(os.path.abspath(__file__))
STEP = os.path.normpath(os.path.join(HERE, "..", "..", "mouse_pcb.step"))
R = lambda v, n=3: round(float(v), n)

doc = TDocStd_Document(TCollection_ExtendedString("doc"))
rd = STEPCAFControl_Reader(); rd.SetNameMode(True); rd.ReadFile(STEP); rd.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

def name(l):
    n = TDataStd_Name(); return n.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), n) else "?"
def bb(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b, False); return [R(v) for v in b.Get()]
leaves = []
def walk(lab, loc):
    if st.IsAssembly_s(lab):
        cs = TDF_LabelSequence(); st.GetComponents_s(lab, cs)
        for i in range(1, cs.Length() + 1):
            c = cs.Value(i); ref = TDF_Label(); st.GetReferredShape_s(c, ref)
            walk(ref, loc.Multiplied(st.GetLocation_s(c)))
    else:
        t = loc.Transformation().TranslationPart()
        leaves.append(dict(name=name(lab), shape=st.GetShape_s(lab).Moved(loc), origin=[R(t.X()), R(t.Y()), R(t.Z())]))
fr = TDF_LabelSequence(); st.GetFreeShapes(fr)
for i in range(1, fr.Length() + 1): walk(fr.Value(i), TopLoc_Location())

def faces(s):
    e = TopExp_Explorer(s, TopAbs_FACE)
    while e.More():
        yield TopoDS.Face_s(e.Current()); e.Next()
def area(f):
    g = GProp_GProps(); BRepGProp.SurfaceProperties_s(f, g); return g.Mass()
def union(bbs):
    return [min(b[0] for b in bbs), min(b[1] for b in bbs), min(b[2] for b in bbs),
            max(b[3] for b in bbs), max(b[4] for b in bbs), max(b[5] for b in bbs)]
def ctr(b): return [R((b[0] + b[3]) / 2), R((b[1] + b[4]) / 2), R((b[2] + b[5]) / 2)]
def size(b): return [R(b[3] - b[0]), R(b[4] - b[1]), R(b[5] - b[2])]

board = next(l for l in leaves if l["name"].startswith("pcb_girdi"))
comps = [l for l in leaves if l is not board]
BB = bb(board["shape"])
Z_TOP = BB[5]; Z_BOT = BB[2]
Z_SEAT = min(bb(l["shape"])[2] for l in comps if bb(l["shape"])[2] > 1.0)  # component seating plane

# ---------------- 1. board outline ----------------
def wire_pts(w):
    pts = []
    ex = BRepTools_WireExplorer(w)
    while ex.More():
        v = ex.CurrentVertex(); p = BRep_Tool.Pnt_s(v); pts.append([R(p.X()), R(p.Y())]); ex.Next()
    return pts
def poly_area(p):
    return 0.5 * sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))
top_face = None
for f in faces(board["shape"]):
    a = BRepAdaptor_Surface(f)
    if a.GetType() == GeomAbs_Plane and abs(a.Plane().Axis().Direction().Z()) > 0.99 and bb(f)[2] > Z_TOP - 0.01:
        top_face = f
ow = BRepTools.OuterWire_s(top_face)
outer = wire_pts(ow)
if poly_area(outer) < 0: outer = outer[::-1]
cutouts, holes = [], []
e = TopExp_Explorer(top_face, TopAbs_WIRE)
while e.More():
    w = TopoDS.Wire_s(e.Current())
    if not w.IsSame(ow):
        wb = bb(w)
        ee = TopExp_Explorer(w, TopAbs_EDGE); circ = None; n = 0
        while ee.More():
            c = BRepAdaptor_Curve(TopoDS.Edge_s(ee.Current())); n += 1
            if c.GetType() == 1: circ = c.Circle()
            ee.Next()
        if circ is not None and max(wb[3] - wb[0], wb[4] - wb[1]) < 3:
            holes.append(dict(x=R(circ.Location().X()), y=R(circ.Location().Y()), d=R(2 * circ.Radius()),
                              slot=[R(wb[3] - wb[0]), R(wb[4] - wb[1])]))
        else:
            p = wire_pts(w); cutouts.append(dict(poly=p, bbox_xy=[wb[0], wb[1], wb[3], wb[4]], area=R(abs(poly_area(p)), 2)))
    e.Next()
g = GProp_GProps(); BRepGProp.VolumeProperties_s(board["shape"], g)
board_out = dict(
    thickness=R(Z_TOP - Z_BOT), z_bottom=Z_BOT, z_top=Z_TOP, component_seat_z=Z_SEAT,
    bbox_xy=[BB[0], BB[1], BB[3], BB[4]], size_xy=[R(BB[3] - BB[0]), R(BB[4] - BB[1])],
    outline_ccw=outer, outline_area=R(poly_area(outer), 2), cutouts=cutouts, volume=R(g.Mass(), 2),
    note="STEP board is 1.51 thick (brief says 1.6). Components sit at Z 1.595 (0.085 above board top: copper/mask not modelled). "
         "Front notch X 33.02..45.72 to Y -39.37 = scroll-wheel slot. Inner cutout = PMW3360 aperture (lens goes through from below).")

# ---------------- 2. holes ----------------
# group drilled holes; mounting holes = largest, at the 4 corners
holes.sort(key=lambda h: (-h["d"], h["y"], h["x"]))
mount = [h for h in holes if h["d"] >= 2.0]
groups = defaultdict(list)
for h in holes: groups[h["d"]].append([h["x"], h["y"]] + ([h["slot"]] if abs(h["slot"][0] - h["slot"][1]) > 0.05 else []))
holes_out = dict(mounting=[dict(x=h["x"], y=h["y"], drill_d=h["d"]) for h in mount],
                 mounting_note="Drill 2.2 = M2 clearance. Boss/screw axis vertical (Z). No pad/keepout ring in STEP; assume Ø4.5 copper-free ring for boss face.",
                 all_by_diameter={str(k): v for k, v in sorted(groups.items(), key=lambda kv: -kv[0])})

# ---------------- 3. switches ----------------
def holes_in(b, d=None):
    return sorted([[h["x"], h["y"]] for h in holes if b[0] - 0.5 <= h["x"] <= b[3] + 0.5 and b[1] - 0.5 <= h["y"] <= b[4] + 0.5
                   and (d is None or abs(h["d"] - d) < 0.01)])

def analyse_switch(l):
    fb = [(f, bb(f), BRepAdaptor_Surface(f)) for f in faces(l["shape"])]
    tops = [(area(f), b[5]) for f, b, a in fb if a.GetType() == GeomAbs_Plane and abs(a.Plane().Axis().Direction().Z()) > 0.99 and b[5] > Z_SEAT + 0.5]
    body_top = max(tops)[1]
    body = union([b for f, b, a in fb if b[2] >= Z_SEAT - 1e-3 and b[5] <= body_top + 1e-3])
    plunger = union([b for f, b, a in fb if b[2] >= body_top - 1e-3 and b[5] > body_top + 1e-3])
    pins = defaultdict(list)
    for f, b, a in fb:
        if b[5] <= Z_SEAT + 1e-3 and b[2] < Z_SEAT - 0.1:
            pins[(round((b[0] + b[3]) / 2, 1), round((b[1] + b[4]) / 2, 1))].append(b)
    pin_list = [union(v) for v in pins.values()]
    pin_c = holes_in(body)
    lx, ly = body[3] - body[0], body[4] - body[1]
    o = l["origin"]
    if ly > lx:
        runs = "along Y (long axis front-back); body extends %s from footprint origin" % ("-Y (rearward)" if body[1] < o[1] - 2 else "+Y")
    else:
        runs = "along X (long axis left-right); body extends %s from footprint origin" % ("+X (inboard)" if body[3] > o[0] + 2 else "-X")
    return dict(origin=o, body_box=body, body_size=size(body), body_top_z=body_top, runs=runs,
                plunger_box=plunger, plunger_size=size(plunger),
                actuator_top=[ctr(plunger)[0], ctr(plunger)[1], plunger[5]],
                plunger_travel_note="modelled as fixed block 1.0 above body; real D2F: OP 7.3+/-? from PCB not given here, assume pretravel 0.5, OT 0.5",
                pins=sorted(pin_c), pin_bottom_z=min(p[2] for p in pin_list))

roles = {(20.32, -20.32): "main LEFT (front-left)", (58.42, -20.32): "main RIGHT (front-right)",
         (50.8, -24.765): "MIDDLE click (plunger sits under the wheel axle line Y -27.9, right of wheel slot)",
         (36.83, -43.18): "DPI (behind wheel slot, top centre)",
         (17.78, -50.8): "SIDE FORWARD (left/thumb edge, front one)", (17.78, -68.58): "SIDE BACK (left/thumb edge, rear one)"}
switches = []
for l in comps:
    if l["name"].startswith("SW_Tactile"):
        s = analyse_switch(l)
        key = min(roles, key=lambda k: math.hypot(k[0] - l["origin"][0], k[1] - l["origin"][1]))
        s["role"] = roles[key]
        switches.append(s)
order = list(roles)
switches.sort(key=lambda s: order.index(min(roles, key=lambda k: math.hypot(k[0] - s["origin"][0], k[1] - s["origin"][1]))))
for s in switches:
    if "SIDE" in s["role"]:
        s["side_note"] = ("Plunger points +Z (top-actuated, not right-angle). Side button needs a lever/rocker in the top shell that "
                          "turns sideways thumb push into a downward push at actuator_top. Board left edge X 14.478; plunger centre %.2f mm inboard." % (s["actuator_top"][0] - BB[0]))

# ---------------- 4. encoder ----------------
enc_l = next(l for l in comps if l["name"].startswith("Alps"))
fb = [(f, bb(f), BRepAdaptor_Surface(f)) for f in faces(enc_l["shape"])]
cyl = [(a.Cylinder(), b) for f, b, a in fb if a.GetType() == GeomAbs_Cylinder]
hub = [(c, b) for c, b in cyl if c.Radius() > 2]
bore = [(c, b) for c, b in cyl if c.Radius() < 2]
ax = hub[0][0].Axis()
enc_body = union([b for f, b, a in fb if a.GetType() == GeomAbs_Plane and b[2] >= Z_SEAT - 1e-3 and b[3] <= 30.2 and b[0] >= 25.7])
hub_x = [min(b[0] for c, b in hub), max(b[3] for c, b in hub)]
enc_pins = defaultdict(list)
for f, b, a in fb:
    if b[5] <= Z_SEAT + 1e-3 and b[2] < Z_SEAT - 0.1:
        enc_pins[(round((b[0] + b[3]) / 2, 0), round((b[1] + b[4]) / 2, 0))].append(b)
enc_pins = [union(v) for v in enc_pins.values()]
mid = next(s for s in switches if "MIDDLE" in s["role"])
dpi = next(s for s in switches if "DPI" in s["role"])
notch = dict(x=[33.02, 45.72], y_front=BB[4], y_back=-39.37)
axis_z = R(ax.Location().Z()); axis_y = R(ax.Location().Y())
encoder = dict(
    origin=enc_l["origin"], body_box=enc_body, body_size=size(enc_body), overall_bbox=bb(enc_l["shape"]),
    shaft_axis=dict(point=[R(ax.Location().X()), axis_y, axis_z], direction=[1, 0, 0]),
    hub=dict(outer_d=R(2 * hub[0][0].Radius()), x_range=hub_x, note="Ø5.2 boss sticks out 1.8 on both sides of the body (X 23.98..25.78 and 30.18..31.98)"),
    bore=dict(d=R(2 * bore[0][0].Radius()), through_x=[min(b[0] for c, b in bore), max(b[3] for c, b in bore)],
              note="hollow shaft modelled as ROUND Ø3.6 bore, no flat/D. Real EC10E (mouse type) takes a keyed axle; placeholder - design the wheel axle Ø3.5 with a D-flat 3.0 and check against a real part"),
    pins=[dict(x=h["x"], y=h["y"], drill_d=h["d"], slot=h["slot"]) for h in holes if 23.9 <= h["x"] <= 32 and -33.3 <= h["y"] <= -22.5], pin_bottom_z=min(p[2] for p in enc_pins),
    wheel_space=dict(
        x_free=[hub_x[1], mid["body_box"][0]], x_free_width=R(mid["body_box"][0] - hub_x[1]),
        board_notch=notch, notch_width=R(notch["x"][1] - notch["x"][0]),
        wheel_centre_suggest=[R((notch["x"][0] + notch["x"][1]) / 2), axis_y, axis_z],
        max_diameter_in_notch=R(2 * min(axis_y - notch["y_back"], notch["y_front"] - axis_y) - 1.0, 1),
        dpi_switch_body_front_y=dpi["body_box"][4],
        middle_click=dict(plunger_box=mid["plunger_box"], actuator_top=mid["actuator_top"],
                          gap_axis_to_plunger_top=R(axis_z - mid["plunger_box"][5]),
                          lever_from_encoder_centre=R(mid["actuator_top"][0] - (enc_body[0] + enc_body[3]) / 2)),
        note=("Wheel goes in the board notch (X 33.02..45.72, from front edge to Y -39.37) so it can dip below the board. "
              "Axle: left end in the encoder bore (X<=31.98), right end over the MIDDLE switch plunger (X 49.35..52.25, top Z 7.595, "
              "1.0 below axis) - wheel press pivots about the encoder. Wheel width <= notch 12.7 minus clearance (<= ~10.5)."))
)

# ---------------- 5. sensor ----------------
sen_l = next(l for l in comps if l["name"].startswith("PixArt"))
fb = [(f, bb(f)) for f in faces(sen_l["shape"])]
sbody = union([b for f, b in fb if b[2] >= Z_SEAT - 1e-3])
sp = defaultdict(list)
for f, b in fb:
    if b[5] <= Z_SEAT + 1e-3: sp[(round((b[0] + b[3]) / 2, 2), round((b[1] + b[4]) / 2, 2))].append(b)
spins = holes_in(sbody, 0.7)
rowA = sorted([p for p in spins if p[0] > 40], key=lambda p: p[1]); rowB = sorted([p for p in spins if p[0] < 40], key=lambda p: p[1])
pin_c = [R(sum(p[0] for p in spins) / len(spins)), R(sum(p[1] for p in spins) / len(spins))]
cut = cutouts[0] if cutouts else None
sensor = dict(
    origin_pin1=sen_l["origin"], body_box=sbody, body_size=size(sbody), pins_bottom_z=min(union(v)[2] for v in sp.values()),
    pin_rows=dict(row_pin1_x=rowA[0][0], row2_x=rowB[0][0], row_spacing=R(rowA[0][0] - rowB[0][0]), pitch=R(abs(rowA[1][1] - rowA[0][1])),
                  row_pin1_y_range=[rowA[0][1], rowA[-1][1]], row2_y_range=[rowB[0][1], rowB[-1][1]],
                  stagger=R(rowB[0][1] - rowA[0][1]), pins_per_row=len(rowA), pin_d=0.5, drill_d=0.7),
    optical_centre_xy=pin_c,
    optical_centre_source=("PixArt PMW3360DM-T2QU datasheet: optical aperture is on the package centre (lens LM19-LSI centres on it); the KiCad footprint "
                           "PixArt_PDIP-16_10.9x16.2mm is symmetric about the package centre with the two pin rows staggered by half a pitch. "
                           "Taken here = centroid of the 16 THT pads. Cross-check: placeholder body centre Y %.3f (0.1 off), PCB aperture centre Y %.3f "
                           "(0.8 off, aperture is longer to the rear). X certain (39.37 everywhere). Confidence MEDIUM-HIGH (+/-0.3 in Y). "
                           "Make the shell lens window >= 8 x 10 mm around it." % (ctr(sbody)[1], (cut["bbox_xy"][1] + cut["bbox_xy"][3]) / 2 if cut else float('nan'))),
    pcb_aperture=cut,
    lens=dict(modelled=False, part="PixArt LM19-LSI (clips into the sensor from below through the PCB aperture)",
              z_lens_ref_to_surface="2.4 typ (2.2 min / 2.6 max) per PMW3360 datasheet",
              note="Lens body + its plate sit UNDER the board around the aperture; the bottom shell must give a window and set the floor plane. "
                   "Lens height below PCB is not in this STEP - WP owner must take it from the LM19-LSI drawing; do not guess the floor Z from this file."))

# ---------------- 6. USB header ----------------
hdr = next(l for l in comps if l["name"].startswith("PinHeader"))
fb = [(f, bb(f)) for f in faces(hdr["shape"])]
hb = bb(hdr["shape"])
housing = union([b for f, b in fb if b[2] >= Z_SEAT - 1e-3 and b[5] <= 4.2])
hp = defaultdict(list)
for f, b in fb:
    if (b[3] - b[0]) < 1 and (b[4] - b[1]) < 1: hp[round((b[0] + b[3]) / 2, 1)].append(b)
hpins = holes_in(hb, 1.0)
usb = dict(origin_pin1=hdr["origin"], pins_xy=hpins, pin_square=0.64, pitch=2.54, housing_box=housing,
           pin_top_z=hb[5], pin_bottom_z=hb[2], row_direction="X", centre_xy=[R((hpins[0][0] + hpins[-1][0]) / 2), hpins[0][1]],
           dist_to_back_edge=R(hpins[0][1] - BB[1]), dist_to_left_edge=R(hpins[0][0] - BB[0]),
           note=("Vertical 1x4 2.54 header at the REAR-LEFT corner, 1.78 from the back edge. Dupont 1x4 housing (2.54x10.2, ~14 long) pushed on "
                 "reaches Z ~18 and needs a 90 deg wire bend above it -> either solder the cable straight to the pins or plan >=20 mm Z there. "
                 "Natural cable exit: rear wall at X ~24.1, Z just above board; strain relief (cable clamp/zigzag) in the bottom shell behind/beside "
                 "the header, Y < -73 region, between mounting hole (16.51,-74.42) and SOT-223 (X>=31.9)."))

# ---------------- 7. keep-out map ----------------
groups_of = lambda n: ("switch" if n.startswith("SW_") else "encoder" if n.startswith("Alps") else "sensor" if n.startswith("PixArt")
                       else "usb_header" if n.startswith("PinHeader") else "smd")
CELL = 1.0
nx = int(math.ceil((BB[3] - BB[0]) / CELL)); ny = int(math.ceil((BB[4] - BB[1]) / CELL))
top = [[Z_TOP] * nx for _ in range(ny)]; bot = [[Z_BOT] * nx for _ in range(ny)]
def stamp(b, grid, val, fn):
    i0 = max(0, int((b[0] - BB[0]) / CELL)); i1 = min(nx - 1, int((b[3] - BB[0] - 1e-6) / CELL))
    j0 = max(0, int((b[1] - BB[1]) / CELL)); j1 = min(ny - 1, int((b[4] - BB[1] - 1e-6) / CELL))
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1): grid[j][i] = fn(grid[j][i], val)
comp_list = []
for l in comps:
    b = bb(l["shape"])
    comp_list.append(dict(name=l["name"], group=groups_of(l["name"]), origin=l["origin"], bbox=b))
    for f in faces(l["shape"]):
        fbx = bb(f)
        if fbx[5] > Z_SEAT: stamp(fbx, top, fbx[5], max)
        if fbx[2] < Z_BOT: stamp(fbx, bot, fbx[2], min)
zones = {
    "front_left_button (X<33.02, Y>-39.37)": (BB[0], 33.02, -39.37, BB[4]),
    "wheel_slot (X 33.02..45.72, Y>-39.37)": (33.02, 45.72, -39.37, BB[4]),
    "front_right_button (X>45.72, Y>-39.37)": (45.72, BB[3], -39.37, BB[4]),
    "mid_band (Y -39.37..-48)": (BB[0], BB[3], -48.0, -39.37),
    "thumb_edge (X<30, Y<-48)": (BB[0], 30.0, BB[1], -48.0),
    "sensor_zone (X 30..46, Y<-48)": (30.0, 46.0, BB[1], -48.0),
    "rear_right_MCU (X>46, Y<-48)": (46.0, BB[3], BB[1], -48.0),
}
zone_out = {}
for zn, (x0, x1, y0, y1) in zones.items():
    inz = [c for c in comp_list if c["bbox"][3] > x0 and c["bbox"][0] < x1 and c["bbox"][4] > y0 and c["bbox"][1] < y1]
    zt = max([c["bbox"][5] for c in inz] + [Z_TOP]); zb = min([c["bbox"][2] for c in inz] + [Z_BOT])
    tall = sorted(inz, key=lambda c: -c["bbox"][5])[:3]
    zone_out[zn] = dict(max_top_z=zt, height_above_board=R(zt - Z_TOP), min_bottom_z=zb,
                        tallest=[f"{c['name'][:22]}@({c['origin'][0]},{c['origin'][1]}) z{c['bbox'][5]}" for c in tall])
bottom_protrusions = sorted({(c["name"].split("_")[0] + "_" + c["name"].split("_")[1], c["bbox"][2]) for c in comp_list if c["bbox"][2] < Z_BOT}, key=lambda t: t[1])
keepout = dict(cell_mm=CELL, x0=BB[0], y0=BB[1], nx=nx, ny=ny,
               top_max_z=[[R(v, 2) for v in row] for row in top], bottom_min_z=[[R(v, 2) for v in row] for row in bot],
               grid_note="row j = Y from y0 upward (j*cell), col i = X from x0; value = max Z of component faces in that cell (board top 1.51 if empty).",
               zones=zone_out,
               bottom_side=dict(smd_on_bottom=False, protrusions=[dict(part=p, min_z=z, below_board=R(Z_BOT - z)) for p, z in bottom_protrusions],
                                note="All parts are top-side. Only THT leads stick out below: D2F + EC10E leads to Z -1.905 (1.9 below), sensor + header leads to -1.405. "
                                     "Bottom shell floor inside must be <= -2.4 under those leads (0.5 clearance), or clipped leads assumed. Plus the LM19 lens (not modelled)."),
               tallest_overall=sorted([dict(name=c["name"], origin=c["origin"], top_z=c["bbox"][5]) for c in comp_list], key=lambda d: -d["top_z"])[:8])

sha = hashlib.sha256(open(STEP, "rb").read()).hexdigest()
data = dict(source=dict(step=STEP, sha256=sha, frame="native STEP coords: +X right, +Y FRONT, +Z up (component side). mm."),
            board=board_out, holes=holes_out, switches=switches, encoder=encoder, sensor=sensor, usb_header=usb, keepout=keepout,
            components=comp_list)
json.dump(data, open(os.path.join(HERE, "PCB_DATA.json"), "w"), indent=1)

# ---------------- meshes ----------------
os.makedirs(os.path.join(HERE, "mesh"), exist_ok=True)
def write_stl(shapes, path, defl=0.05):
    b = BRep_Builder(); c = TopoDS_Compound(); b.MakeCompound(c)
    for s in shapes: b.Add(c, s)
    BRepMesh_IncrementalMesh(c, defl, False, 0.5, True)
    w = StlAPI_Writer(); w.ASCIIMode = False; w.Write(c, path)
write_stl([board["shape"]] + [l["shape"] for l in comps], os.path.join(HERE, "pcb.stl"), 0.08)
gl = defaultdict(list)
for l in comps: gl[groups_of(l["name"])].append(l["shape"])
gl["board"] = [board["shape"]]
for k, v in gl.items(): write_stl(v, os.path.join(HERE, "mesh", k + ".stl"))
print("sha", sha)
print("board", board_out["size_xy"], "t", board_out["thickness"], "cutouts", len(cutouts), "holes", len(holes), "mount", holes_out["mounting"])
for s in switches: print(s["role"][:22], "act", s["actuator_top"], "plunger", s["plunger_size"], s["runs"][:12])
print("enc axis", encoder["shaft_axis"], "wheel", encoder["wheel_space"]["x_free"], encoder["wheel_space"]["max_diameter_in_notch"])
print("sensor oc", sensor["optical_centre_xy"], sensor["pin_rows"])
print("usb", usb["pins_xy"], usb["housing_box"])
for k, v in zone_out.items(): print(k, v["max_top_z"], v["tallest"][:1])
print(keepout["bottom_side"]["protrusions"])
