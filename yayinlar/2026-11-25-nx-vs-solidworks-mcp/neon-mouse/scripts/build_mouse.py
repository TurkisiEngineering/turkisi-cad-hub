"""Parametric Siemens NX 2206 Journal: Complete Ergonomic Gaming Mouse Mechanical Design
Driven directly from C:\\scan-canli\\mouse\\GIRDI\\mouse_pcb.step.

Produces:
  - mouse_base.prt           (Bottom chassis with PCB standoffs, PMW3360 window, scroll cradle, skate pockets, M2 bosses)
  - mouse_top_shell.prt      (Compound-curved ergonomic upper shell, split LMB/RMB triggers, striker posts, thumb cradles)
  - mouse_scroll_wheel.prt   (D23 tactile 24-groove scroll wheel + Alps EC10E drive shaft + MMB actuator axle)
  - mouse_dpi_button.prt     (Top center DPI button + retention flange + offset SW S48 plunger stem)
  - mouse_thumb_fwd.prt      (M5 forward thumb button + 90-deg bell-crank lever -> SW S37)
  - mouse_thumb_back.prt     (M4 back thumb button + 90-deg bell-crank lever -> SW S38)
  - mouse_skates.prt         (Front, rear, and sensor-ring chamfered PTFE glide skates)
  - mouse_pcb_ref.prt        (Imported mouse_pcb.step reference component)
  - mouse_asm.prt            (Complete 8-component top-level NX assembly)
  - step/*.step              (Individual part STEPs + full assembly STEP + mechanical-only STEP)
"""
import math
import os
import sys
import traceback

sys.path.insert(0, os.environ.get("NXH_DIR", r"H:\My Drive\NX HARNESS VERSIONS\v2\skills\nx-journal-core\scripts"))
import NXOpen
import NXOpen.Features
import nxh
import nxf
import nxa

# =============================================================================
# EXACT MEASURED PCB INTERFACE CONSTANTS (from mouse_pcb.step, mm)
# =============================================================================
XC = 39.370                  # Exact PCB centerline X
PCB_X0, PCB_X1 = 14.478, 64.262
PCB_Y0, PCB_Y1 = -76.454, -14.732
PCB_Z0, PCB_Z1 = 0.000, 1.510
PCB_PIN_ZMIN = -1.905

# 4x PCB M2 mounting holes (dia 2.2 mm)
PCB_HOLES = [
    (16.510, -16.764),  # FL
    (62.230, -16.764),  # FR
    (16.510, -74.422),  # RL
    (62.230, -74.422),  # RR
]

# 6x Omron D2F switch plunger tops (Z_top = 7.595 mm)
PLUNGER_Z = 7.595
SW_LMB  = (20.320, -23.530)
SW_RMB  = (58.420, -23.530)
SW_MMB  = (50.800, -27.975)
SW_DPI  = (40.040, -43.180)
SW_M5   = (20.990, -50.800)
SW_M4   = (20.990, -68.580)

# Alps EC10E encoder bore (dia 3.60 mm, axis +X)
ENC_Y = -27.900
ENC_Z = 8.595

# PMW3360 optical sensor center
SNS_X = 39.370
SNS_Y = -56.520

# =============================================================================
# DESIGN MASTER PARAMETERS (mm / deg)
# =============================================================================
WALL_T       = 1.8
Z_BOT        = -4.4
Z_PARTING    = 2.5
DRAFT_DEG    = 2.5
R_TOP_RIM    = 5.5
R_BOT_RIM    = 1.8
STRIKER_GAP  = 0.055          # Nominal CAD clearance above plunger top -> Z = 7.650
STRIKER_Z    = PLUNGER_Z + STRIKER_GAP

# 4x Shell-to-base M2 screws (2 front on fixed center nose bridge, 2 rear wide stance)
SHELL_SCREWS_FRONT = [(35.000, -11.500), (43.740, -11.500)]
SHELL_SCREWS_REAR  = [(25.000, -106.500), (53.740, -106.500)]

# Thumb bell-crank pivot axis (parallel to Y)
PIVOT_X = 14.800
PIVOT_Z = 11.800

# Canopy station table: (y, z_crest, z_drop_at_30mm)
CANOPY_STATIONS = [
    (   4.0,  5.5,  2.2),
    (  -4.0, 10.2,  3.2),
    ( -14.0, 14.8,  3.8),
    ( -27.9, 17.8,  4.2),
    ( -43.2, 25.5,  7.5),
    ( -58.0, 31.8, 10.5),
    ( -74.0, 35.0, 12.5),
    ( -96.0, 29.5, 11.0),
    (-114.0, 18.0,  7.0),
    (-128.0,  4.5,  2.0),
]

# Right-half plan silhouette control points (mirrored across XC for exact symmetry)
# Ordered front-center -> right side -> rear-center
PLAN_RIGHT_HALF = [
    (0.0,   -4.0),    # Nose tip
    (18.5,  -6.8),    # Nose right shoulder
    (29.2, -15.0),    # Front right corner (clears PCB X=64.26 by >2.5 mm inside)
    (30.6, -28.0),    # Front right cheek
    (29.4, -54.0),    # Ergonomic grip waist
    (31.8, -84.0),    # Rear palm swell
    (27.2, -105.0),   # Tail shoulder
    (15.5, -117.2),   # Tail curve
    (0.0,  -120.0),   # Rear tail center
]


def canopy_z_approx(x, y):
    """Analytic approximation of canopy outer Z at (x, y) for sizing internal boss top heights."""
    for i in range(len(CANOPY_STATIONS) - 1):
        y0, c0, d0 = CANOPY_STATIONS[i]
        y1, c1, d1 = CANOPY_STATIONS[i + 1]
        if y0 >= y >= y1:
            t = (y0 - y) / (y0 - y1)
            c = c0 + t * (c1 - c0)
            d = d0 + t * (d1 - d0)
            u = abs(x - XC) / 30.0
            return c - d * (0.75 * u * u + 0.25 * u ** 4)
    return 10.0


def plan_half_w(y, z=Z_BOT):
    """Analytic half-width at (y, z) accounting for DRAFT_DEG inward taper from Z_BOT."""
    hw0 = 29.5
    for i in range(len(PLAN_RIGHT_HALF) - 1):
        w0, y0 = PLAN_RIGHT_HALF[i]
        w1, y1 = PLAN_RIGHT_HALF[i + 1]
        if y0 >= y >= y1:
            t = (y0 - y) / (y0 - y1)
            hw0 = w0 + t * (w1 - w0)
            break
    dz = max(0.0, z - Z_BOT)
    return hw0 - dz * math.tan(math.radians(DRAFT_DEG))


# =============================================================================
# LOW-LEVEL GEOMETRY HELPERS (VERIFIED ON NX 2206)
# =============================================================================
def studio_spline(part, pts, periodic=False, degree=3):
    """Associative Studio Spline through 3D points."""
    SB = NXOpen.Features.StudioSplineBuilderEx
    b = part.Features.CreateStudioSplineBuilderEx(NXOpen.Features.StudioSpline.Null)
    try:
        b.Type = SB.Types.ThroughPoints
        b.Degree = degree
        b.IsAssociative = True
        b.IsPeriodic = periodic
        b.MatchKnotsType = SB.MatchKnotsTypes.NotSet
        b.OrientExpress.ReferenceOption = NXOpen.GeometricUtilities.OrientXpressBuilder.Reference.ProgramDefined
        b.DrawingPlaneOption = SB.DrawingPlaneOptions.General
        for p in pts:
            g = b.ConstraintManager.CreateGeometricConstraintData()
            g.Point = nxh.point(part, float(p[0]), float(p[1]), float(p[2]))
            b.ConstraintManager.Append(g)
        feat = b.Commit()
        curve = b.Curve
    finally:
        b.Destroy()
    return feat, curve


def rounded_rect_curves_xy(part, cx, cy, z, lx, ly, r):
    """Closed tangent rounded rectangle (or stadium when 2*r == min(lx,ly)) in XY plane at z."""
    hx, hy = lx / 2.0, ly / 2.0
    r = min(float(r), hx - 0.01, hy - 0.01)
    if r < 0.05:
        return nxh.rect(part, cx - hx, cy - hy, cx + hx, cy + hy, z)
    curves = []
    # Bottom line
    curves.append(nxh.line(part, (cx - hx + r, cy - hy, z), (cx + hx - r, cy - hy, z)))
    # BR arc
    curves.append(nxh.arc(part, (cx + hx - r, cy - hy + r, z), (1, 0, 0), (0, 1, 0), r, -math.pi / 2, 0.0))
    # Right line
    curves.append(nxh.line(part, (cx + hx, cy - hy + r, z), (cx + hx, cy + hy - r, z)))
    # TR arc
    curves.append(nxh.arc(part, (cx + hx - r, cy + hy - r, z), (1, 0, 0), (0, 1, 0), r, 0.0, math.pi / 2))
    # Top line
    curves.append(nxh.line(part, (cx + hx - r, cy + hy, z), (cx - hx + r, cy + hy, z)))
    # TL arc
    curves.append(nxh.arc(part, (cx - hx + r, cy + hy - r, z), (1, 0, 0), (0, 1, 0), r, math.pi / 2, math.pi))
    # Left line
    curves.append(nxh.line(part, (cx - hx, cy + hy - r, z), (cx - hx, cy - hy + r, z)))
    # BL arc
    curves.append(nxh.arc(part, (cx - hx + r, cy - hy + r, z), (1, 0, 0), (0, 1, 0), r, math.pi, 1.5 * math.pi))
    return curves


def rounded_rect_curves_yz(part, x, cy, cz, ly, lz, r):
    """Closed tangent rounded rectangle in YZ plane at x."""
    hy, hz = ly / 2.0, lz / 2.0
    r = min(float(r), hy - 0.01, hz - 0.01)
    if r < 0.05:
        return nxh.polyline(part, [
            (x, cy - hy, cz - hz), (x, cy + hy, cz - hz),
            (x, cy + hy, cz + hz), (x, cy - hy, cz + hz),
        ])
    curves = []
    # Bottom line (-Z)
    curves.append(nxh.line(part, (x, cy - hy + r, cz - hz), (x, cy + hy - r, cz - hz)))
    # Front-bottom arc (+Y, -Z)
    curves.append(nxh.arc(part, (x, cy + hy - r, cz - hz + r), (0, 1, 0), (0, 0, 1), r, -math.pi / 2, 0.0))
    # Front line (+Y)
    curves.append(nxh.line(part, (x, cy + hy, cz - hz + r), (x, cy + hy, cz + hz - r)))
    # Front-top arc (+Y, +Z)
    curves.append(nxh.arc(part, (x, cy + hy - r, cz + hz - r), (0, 1, 0), (0, 0, 1), r, 0.0, math.pi / 2))
    # Top line (+Z)
    curves.append(nxh.line(part, (x, cy + hy - r, cz + hz), (x, cy - hy + r, cz + hz)))
    # Rear-top arc (-Y, +Z)
    curves.append(nxh.arc(part, (x, cy - hy + r, cz + hz - r), (0, 1, 0), (0, 0, 1), r, math.pi / 2, math.pi))
    # Rear line (-Y)
    curves.append(nxh.line(part, (x, cy - hy, cz + hz - r), (x, cy - hy, cz - hz + r)))
    # Rear-bottom arc (-Y, -Z)
    curves.append(nxh.arc(part, (x, cy - hy + r, cz - hz + r), (0, 1, 0), (0, 0, 1), r, math.pi, 1.5 * math.pi))
    return curves


def extrude_rounded_xy(part, cx, cy, z0, z1, lx, ly, r, op=None, target=None):
    curves = rounded_rect_curves_xy(part, cx, cy, z0, lx, ly, r)
    sec = nxh.section(part, curves=curves, help_point=(cx, cy - ly / 2.0, z0))
    f = nxh.extrude(part, sec, (0, 0, 1), 0.0, z1 - z0, op=op, target=target)
    return f, (f.GetBodies()[0] if op is None else target)


def extrude_rounded_yz(part, x0, x1, cy, cz, ly, lz, r, op=None, target=None):
    curves = rounded_rect_curves_yz(part, x0, cy, cz, ly, lz, r)
    sec = nxh.section(part, curves=curves, help_point=(x0, cy, cz - lz / 2.0))
    f = nxh.extrude(part, sec, (1, 0, 0), 0.0, x1 - x0, op=op, target=target)
    return f, (f.GetBodies()[0] if op is None else target)


def extrude_polygon_xz(part, pts_xz, y0, y1, op=None, target=None):
    pts3 = [(float(x), float(y0), float(z)) for x, z in pts_xz]
    curves = nxh.polyline(part, pts3, closed=True)
    sec = nxh.section(part, curves=curves, help_point=pts3[0])
    f = nxh.extrude(part, sec, (0, 1, 0), 0.0, y1 - y0, op=op, target=target)
    return f, (f.GetBodies()[0] if op is None else target)


def blank_helpers(part, keep_bodies):
    """Blank all non-product bodies/curves AND exclude non-product bodies from MODEL reference set."""
    keep_tags = {b.Tag for b in keep_bodies}
    non_prod = [b for b in part.Bodies if b.Tag not in keep_tags]
    if non_prod:
        nxa.exclude_from_model(part, non_prod)
    to_blank = list(non_prod)
    for c in part.Curves:
        to_blank.append(c)
    for s in part.Splines:
        to_blank.append(s)
    if to_blank:
        nxh.S.DisplayManager.BlankObjects(to_blank)


def add_master_expressions(part):
    nxh.expr(part, "xc",        XC,        "mm", "PCB centerline X")
    nxh.expr(part, "wall_t",    WALL_T,    "mm", "Shell nominal wall thickness")
    nxh.expr(part, "z_bot",     Z_BOT,     "mm", "Outer base bottom Z")
    nxh.expr(part, "z_parting", Z_PARTING, "mm", "Base-to-top parting plane Z")
    nxh.expr(part, "r_top_rim", R_TOP_RIM, "mm", "Top canopy perimeter blend radius")
    nxh.expr(part, "r_bot_rim", R_BOT_RIM, "mm", "Bottom sole perimeter blend radius")
    nxh.expr(part, "draft_deg", DRAFT_DEG, "deg", "Ergonomic side wall inward draft")


# =============================================================================
# SHARED MASTER ERGONOMIC SHELL BUILDER (EXACT 0.000mm SEAM MATCH)
# =============================================================================
def build_master_shell(part, keep="base"):
    """Build the smooth compound-curved ergonomic mouse shell, shell inward by wall_t,
    and trim at Z_PARTING to produce either the 'base' or 'top' shell blank."""
    add_master_expressions(part)

    # 1. Plan silhouette: 16 symmetric points (closed periodic cubic spline in XY at Z_BOT)
    pts_plan = []
    for dx, y in PLAN_RIGHT_HALF:
        pts_plan.append((XC + dx, y, Z_BOT))
    for dx, y in reversed(PLAN_RIGHT_HALF[1:-1]):
        pts_plan.append((XC - dx, y, Z_BOT))

    _f_plan, plan_crv = studio_spline(part, pts_plan, periodic=True, degree=3)

    # Extrude plan solid upward with gentle inward ergonomic draft (2.5 deg)
    sec_plan = nxh.section(part, curves=[plan_crv], help_point=(XC, -4.0, Z_BOT))
    f_ext = nxf.extrude_ex(
        part, sec_plan, (0, 0, 1),
        start="0", end="46",
        draft="draft_deg",
    )
    body = f_ext.GetBodies()[0]

    # 2. Compound-curved 3D ergonomic top canopy (Through Curves sheet across 10 XZ splines)
    dx_samples = [-40.0, -30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0, 40.0]
    canopy_sections = []
    for y, crest, drop30 in CANOPY_STATIONS:
        spts = []
        for dx in dx_samples:
            u = abs(dx) / 30.0
            z = crest - drop30 * (0.75 * u * u + 0.25 * (u ** 4))
            spts.append((XC + dx, y, z))
        _fs, crv = studio_spline(part, spts, periodic=False, degree=3)
        sec = nxh.section(part, curves=[crv], help_point=(XC - 40.0, y, spts[0][2]))
        canopy_sections.append(sec)

    f_canopy = nxf.through_curves(part, canopy_sections, solid=False, preserve=False)
    canopy_sheet = f_canopy.GetBodies()[0]

    # 3. Trim extruded solid with 3D canopy sheet (keep lower ergonomic body)
    nxf.trim_body(part, body, keep_point=(XC, -60.0, Z_BOT + 1.0), sheet=canopy_sheet)

    # 4. Perimeter Edge Blends (top canopy rim R5.5, bottom sole rim R1.8)
    # Identify top rim edge(s) and bottom rim edge(s) cleanly by Z bbox
    top_edges = []
    bot_edges = []
    for e in body.GetEdges():
        bb = nxh.bbox(e)
        if bb[5] < Z_BOT + 0.5:
            bot_edges.append(e)
        elif bb[2] > Z_BOT + 3.0:
            top_edges.append(e)

    assert len(top_edges) >= 1 and len(bot_edges) >= 1, f"Edges not found: top={len(top_edges)} bot={len(bot_edges)}"
    nxf.edge_blend(part, [(top_edges, "r_top_rim")], overflow=True)
    # Re-query bottom edges after top blend
    bot_edges = [e for e in body.GetEdges() if nxh.bbox(e)[5] < Z_BOT + 0.5]
    nxf.edge_blend(part, [(bot_edges, "r_bot_rim")], overflow=True)

    # 5. Closed inward Shell -> uniform 1.800 mm wall thickness everywhere!
    v_solid = nxh.volume(part, body)
    nxf.shell(part, body, [], "wall_t", inward=True)
    v_hollow = nxh.volume(part, body)
    assert v_hollow < v_solid * 0.65, f"Shell did not hollow body: solid={v_solid:.1f}, hollow={v_hollow:.1f}"

    # 6. Trim Body at Z_PARTING datum plane -> Base (z <= 2.5) or Top Shell (z >= 2.5)
    _fdp, dp_parting = nxh.datum_plane(part, (XC, -60.0, Z_PARTING), (0, 0, 1))
    kp = (XC, -60.0, Z_BOT + 0.2) if keep == "base" else (XC, -60.0, 32.0)
    nxf.trim_body(part, body, keep_point=kp, datum_plane=dp_parting)

    return body, canopy_sheet


# =============================================================================
# PART 1: MOUSE BASE CHASSIS (mouse_base.prt)
# =============================================================================
def build_base(prt_path, stp_path):
    part = nxh.new_part(prt_path)
    body, _ = build_master_shell(part, keep="base")

    # 1. Scroll wheel bottom clearance trough (clears D23 wheel bottom Z=-2.905 by 0.495 mm; leaves 1.0 mm floor)
    extrude_rounded_xy(part, XC, -27.9, -3.40, -1.20, 9.8, 24.0, 2.5, op=nxf.BOOL.Subtract, target=body)

    # 2. 4x PCB Mounting Standoffs (OD 4.0 mm, top face EXACT Z = 0.000, M2 pilot hole D1.6)
    for hx, hy in PCB_HOLES:
        nxh.cylinder(part, (hx, hy, -2.85), (0, 0, 1), 4.0, 2.85, op=nxf.BOOL.Unite, target=body)
        nxh.cylinder(part, (hx, hy, -3.40), (0, 0, 1), 1.6, 3.80, op=nxf.BOOL.Subtract, target=body)

    # 2b. 2x Mid-PCB Support Pads flanking the PMW3360 DIP pin rows (clear of pins X=33.77..34.27 & 44.47..44.97)
    for sx in (31.4, 47.34):
        nxh.cylinder(part, (sx, -57.5, -2.85), (0, 0, 1), 3.0, 2.85, op=nxf.BOOL.Unite, target=body)

    # 3. PMW3360 Optical Sensor Through-Aperture (centered at SNS_X, SNS_Y; clears DIP pins cleanly)
    extrude_rounded_xy(part, SNS_X, -57.0, Z_BOT - 0.5, -1.2, 8.2, 15.2, 2.0, op=nxf.BOOL.Subtract, target=body)

    # 4. Scroll Wheel Right-Side Axle Guide Fork (inside PCB scroll slot X=44.0..45.2, clear of wheel 43.07 & PCB 45.72)
    # Build fork body rising from base floor Z=-3.55 to Z=10.6, then cut vertical U-slot centered at Y=-27.90
    fork_pts = [
        (44.00, -3.55), (45.20, -3.55), (45.20, 10.60), (44.00, 10.60)
    ]
    extrude_polygon_xz(part, fork_pts, ENC_Y - 3.0, ENC_Y + 3.0, op=nxf.BOOL.Unite, target=body)
    # Cut vertical U-slot for D1.90 right axle (width 2.15 mm -> Y in [-28.975, -26.825], floor at Z=6.80 for MMB click travel)
    extrude_rounded_yz(part, 43.5, 45.8, ENC_Y, 9.80, 2.15, 6.00, 1.05, op=nxf.BOOL.Subtract, target=body)

    # 5. 4x Shell-to-Base M2 Fastener Bosses (hidden under front & rear PTFE skates!)
    # Front 2 on fixed center bridge (decoupled from flexing LMB/RMB triggers!)
    for sx, sy in SHELL_SCREWS_FRONT:
        nxh.cylinder(part, (sx, sy, -2.85), (0, 0, 1), 4.2, 5.30, op=nxf.BOOL.Unite, target=body)     # top Z=2.45
        nxh.cylinder(part, (sx, sy, Z_BOT - 0.5), (0, 0, 1), 2.3, 8.0, op=nxf.BOOL.Subtract, target=body)  # M2 clearance
        nxh.cylinder(part, (sx, sy, Z_BOT - 0.5), (0, 0, 1), 3.7, 2.0, op=nxf.BOOL.Subtract, target=body)  # head recess
    # Rear 2 wide stance
    for sx, sy in SHELL_SCREWS_REAR:
        nxh.cylinder(part, (sx, sy, -2.85), (0, 0, 1), 5.0, 5.30, op=nxf.BOOL.Unite, target=body)     # top Z=2.45
        nxh.cylinder(part, (sx, sy, Z_BOT - 0.5), (0, 0, 1), 2.3, 8.0, op=nxf.BOOL.Subtract, target=body)
        nxh.cylinder(part, (sx, sy, Z_BOT - 0.5), (0, 0, 1), 4.2, 2.1, op=nxf.BOOL.Subtract, target=body)

    # 6. 3x Recessed PTFE Skate Pockets on bottom sole (Z = -4.4 .. -3.9, 0.5 mm deep)
    # Front skate pocket (covers front 2 shell screws)
    extrude_rounded_xy(part, XC, -10.5, Z_BOT - 0.2, Z_BOT + 0.50, 35.0, 6.8, 3.1, op=nxf.BOOL.Subtract, target=body)
    # Rear skate pocket (covers rear 2 shell screws)
    extrude_rounded_xy(part, XC, -107.5, Z_BOT - 0.2, Z_BOT + 0.50, 38.0, 11.8, 5.4, op=nxf.BOOL.Subtract, target=body)
    # Sensor ring skate pocket (annular recess around PMW3360 window)
    _f_ring_out, ring_tool = extrude_rounded_xy(part, SNS_X, -57.0, Z_BOT - 0.2, Z_BOT + 0.50, 14.6, 21.6, 4.0)
    extrude_rounded_xy(part, SNS_X, -57.0, Z_BOT - 0.4, Z_BOT + 0.70, 10.2, 17.2, 2.4, op=nxf.BOOL.Subtract, target=ring_tool)
    nxh.subtract(part, body, [ring_tool])

    # 7. 3x Perimeter Alignment Tabs rising from base floor to Z=4.0 (0.2 mm slip clearance inside top shell wall)
    for side in (-1, 1):
        # At Y=-88, inner wall of top shell at Z=2.5..4.0 is at dx ~ 29.2 -> tab dx in [27.6, 28.9]
        tx0 = (XC + 27.6) if side == 1 else (XC - 28.9)
        nxh.block(part, (tx0, -93.0, -2.75), (1.3, 10.0, 6.75), op=nxf.BOOL.Unite, target=body)
    # Rear center alignment tab (top shell inner wall at Y=-118.0 -> tab at Y=[-117.5, -116.2])
    nxh.block(part, (XC - 5.5, -117.5, -2.75), (11.0, 1.3, 6.75), op=nxf.BOOL.Unite, target=body)

    # 8. Front Nose USB Cable Exit Port (lower semicircle R=2.1 at Z=Z_PARTING)
    nxh.cylinder(part, (XC, -10.0, Z_PARTING), (0, 1, 0), 4.2, 10.0, op=nxf.BOOL.Subtract, target=body)

    blank_helpers(part, [body])
    assert len(nxh.solids(part)) == 1, f"Base solids={len(nxh.solids(part))}"
    errs = nxh.feature_errors(part)
    ex = nxh.examine_geometry(part, body)
    ok = nxh.body_ok(part, body)
    nxf.step_export(part, stp_path, ap242=False)
    return {
        "part": "mouse_base",
        "solids": len(nxh.solids(part)),
        "volume_mm3": round(nxh.volume(part, body), 2),
        "bbox": [round(v, 3) for v in nxh.bbox(body)],
        "body_ok": ok,
        "examine": ex,
        "feature_errors": errs,
    }


# =============================================================================
# PART 2: MOUSE TOP SHELL (mouse_top_shell.prt)
# =============================================================================
def build_top_shell(prt_path, stp_path):
    part = nxh.new_part(prt_path)
    body, _ = build_master_shell(part, keep="top")

    # 1. Scroll Wheel Opening (9.7 x 20.6 mm rounded window tightly framing D23 wheel with ~1.7 mm deck clearance)
    extrude_rounded_xy(part, XC, -27.8, 5.0, 35.0, 9.7, 20.6, 2.8, op=nxf.BOOL.Subtract, target=body)

    # 2. Split Cantilevered LMB & RMB Flex-Hinge Relief Slots (1.0 mm crisp slits flanking scroll bezel rails!)
    # Scroll bezel rails stay solid at X=[32.70..34.52] and X=[44.22..46.04], tying front nose bridge to palm!
    nxh.block(part, (31.65, -48.0, 2.0), (1.05, 47.0, 33.0), op=nxf.BOOL.Subtract, target=body)  # LMB split
    nxh.block(part, (46.04, -48.0, 2.0), (1.05, 47.0, 33.0), op=nxf.BOOL.Subtract, target=body)  # RMB split

    # Front trigger skirt hover relief (LMB & RMB front perimeter clears base rim by 1.8 mm for crisp clicks!)
    nxh.block(part, (2.0,   -47.0, 2.0), (30.2, 46.0, 2.3), op=nxf.BOOL.Subtract, target=body)   # LMB hover gap
    nxh.block(part, (46.54, -47.0, 2.0), (30.2, 46.0, 2.3), op=nxf.BOOL.Subtract, target=body)   # RMB hover gap

    # 3. LMB & RMB Plunger Striker Posts (united to underside of LMB & RMB paddles -> exact Z = 7.650 mm!)
    for sx, sy in (SW_LMB, SW_RMB):
        z_top_embed = canopy_z_approx(sx, sy) - 0.85   # Safely embedded ~0.95 mm into 1.8 mm wall, never pokes top!
        extrude_rounded_xy(part, sx, sy, STRIKER_Z, z_top_embed, 3.8, 3.0, 0.8, op=nxf.BOOL.Unite, target=body)

    # 4. Top Center DPI Button Opening (4.4 x 7.6 mm rounded stadium right behind scroll bezel, clean 1.3 mm bridge)
    extrude_rounded_xy(part, XC, SW_DPI[1], 16.0, 38.0, 4.4, 7.6, 2.1, op=nxf.BOOL.Subtract, target=body)

    # 5. Left Side Thumb Button Windows (M5 Forward & M4 Back, cleanly separated by 4.6 mm bridge!)
    extrude_rounded_yz(part, 0.0, 16.5, -50.80, 18.0, 12.4, 5.8, 2.4, op=nxf.BOOL.Subtract, target=body)  # M5
    extrude_rounded_yz(part, 0.0, 16.5, -67.80, 18.0, 12.4, 5.8, 2.4, op=nxf.BOOL.Subtract, target=body)  # M4

    # 6. Internal Bell-Crank Pivot Cradle Brackets (3x gussets on inner left wall, D2.2 pivot bore at PIVOT_X, PIVOT_Z)
    for y_gus in (-43.2, -59.3, -75.4):
        # Embed gusset root cleanly 0.9 mm inside the 1.8 mm left shell wall at (y_gus, Z=12)
        x_out = XC - plan_half_w(y_gus, 12.0)
        x_root = x_out + 0.90
        extrude_polygon_xz(
            part,
            [(x_root, 9.8), (16.8, 9.8), (16.8, 14.0), (x_root, 14.8)],
            y_gus - 0.9, y_gus + 0.9,
            op=nxf.BOOL.Unite, target=body
        )
        assert len(nxh.solids(part)) == 1, f"Gusset at y={y_gus} failed to unite (x_root={x_root:.2f})"
    # Drill coaxial D2.2 pivot bore through all 3 gussets
    nxh.cylinder(part, (PIVOT_X, -77.0, PIVOT_Z), (0, 1, 0), 2.2, 36.0, op=nxf.BOOL.Subtract, target=body)

    # 7. 4x Top-Shell M2 Screw Bosses (mating down to Z = 2.55 mm; 0.10 mm clearance above base bosses)
    for sx, sy in SHELL_SCREWS_FRONT:
        z_top_embed = canopy_z_approx(sx, sy) - 0.90
        nxh.cylinder(part, (sx, sy, 2.55), (0, 0, 1), 4.2, z_top_embed - 2.55, op=nxf.BOOL.Unite, target=body)
        assert len(nxh.solids(part)) == 1, f"Front screw boss {(sx, sy)} detached"
        nxh.cylinder(part, (sx, sy, 2.40), (0, 0, 1), 1.6, 7.0, op=nxf.BOOL.Subtract, target=body)
    for sx, sy in SHELL_SCREWS_REAR:
        z_top_embed = canopy_z_approx(sx, sy) - 1.00
        nxh.cylinder(part, (sx, sy, 2.55), (0, 0, 1), 5.0, z_top_embed - 2.55, op=nxf.BOOL.Unite, target=body)
        assert len(nxh.solids(part)) == 1, f"Rear screw boss {(sx, sy)} detached"
        nxh.cylinder(part, (sx, sy, 2.40), (0, 0, 1), 1.6, 8.0, op=nxf.BOOL.Subtract, target=body)

    # 8. Front Nose USB Cable Exit Port (upper semicircle R=2.1 at Z=Z_PARTING)
    nxh.cylinder(part, (XC, -10.0, Z_PARTING), (0, 1, 0), 4.2, 10.0, op=nxf.BOOL.Subtract, target=body)

    blank_helpers(part, [body])
    assert len(nxh.solids(part)) == 1, f"Top shell solids={len(nxh.solids(part))}"
    errs = nxh.feature_errors(part)
    ex = nxh.examine_geometry(part, body)
    ok = nxh.body_ok(part, body)
    nxf.step_export(part, stp_path, ap242=False)
    return {
        "part": "mouse_top_shell",
        "solids": len(nxh.solids(part)),
        "volume_mm3": round(nxh.volume(part, body), 2),
        "bbox": [round(v, 3) for v in nxh.bbox(body)],
        "body_ok": ok,
        "examine": ex,
        "feature_errors": errs,
    }


# =============================================================================
# PART 3: TACTILE SCROLL WHEEL + AXLE (mouse_scroll_wheel.prt)
# =============================================================================
def build_scroll_wheel(prt_path, stp_path):
    part = nxh.new_part(prt_path)
    nxh.expr(part, "wheel_od", 23.0, "mm", "Scroll wheel outer tire diameter")
    nxh.expr(part, "wheel_w",   7.4, "mm", "Scroll wheel tire width")
    nxh.expr(part, "enc_dia",   3.5, "mm", "Left encoder drive shaft diameter (fits 3.60 bore)")
    nxh.expr(part, "mmb_dia",   1.9, "mm", "Right MMB actuator axle diameter (bottom Z=7.645)")

    x_left = XC - 3.7
    x_right = XC + 3.7

    # 1. Outer wheel tire cylinder
    _f, body = nxh.cylinder(part, (x_left, ENC_Y, ENC_Z), (1, 0, 0), "wheel_od", "wheel_w")

    # Edge blend outer tire rims R0.9 mm for ergonomic finger roll
    rim_edges = [e for e in body.GetEdges() if abs(nxh.bbox(e)[5] - (ENC_Z + 11.5)) < 0.2]
    if rim_edges:
        nxf.edge_blend(part, [(rim_edges, "0.9")])

    # 2. Hollow out inner spoked recess (leaves outer rim OD23/ID17.2), then add 5 radial spokes + central hub
    nxh.cylinder(part, (x_left - 0.5, ENC_Y, ENC_Z), (1, 0, 0), 17.2, 8.4, op=nxf.BOOL.Subtract, target=body)
    for k in range(5):
        ang = k * (2.0 * math.pi / 5.0)
        ca, sa = math.cos(ang), math.sin(ang)
        # Spoke prism in YZ extruded along X (width 1.8 mm, spans from r=-1.5 through center out to r=9.5 inside rim!)
        ny, nz = -sa * 0.9, ca * 0.9
        p1 = (XC - 1.5, ENC_Y - ca * 1.5 + ny, ENC_Z - sa * 1.5 + nz)
        p2 = (XC - 1.5, ENC_Y + ca * 9.5 + ny, ENC_Z + sa * 9.5 + nz)
        p3 = (XC - 1.5, ENC_Y + ca * 9.5 - ny, ENC_Z + sa * 9.5 - nz)
        p4 = (XC - 1.5, ENC_Y - ca * 1.5 - ny, ENC_Z - sa * 1.5 - nz)
        sec = nxh.section(part, curves=nxh.polyline(part, [p1, p2, p3, p4], closed=True), help_point=p1)
        nxh.extrude(part, sec, (1, 0, 0), 0.0, 3.0, op=nxf.BOOL.Unite, target=body)
    # Central hub united onto the 5 spokes
    nxh.cylinder(part, (x_left + 0.5, ENC_Y, ENC_Z), (1, 0, 0), 8.4, 6.4, op=nxf.BOOL.Unite, target=body)

    # 3. 24 Tactile Grip Notches around outer tire circumference
    r_notch = 11.75
    for k in range(24):
        ang = k * (2.0 * math.pi / 24.0)
        cy = ENC_Y + r_notch * math.cos(ang)
        cz = ENC_Z + r_notch * math.sin(ang)
        nxh.cylinder(part, (x_left + 0.5, cy, cz), (1, 0, 0), 1.1, 6.4, op=nxf.BOOL.Subtract, target=body)

    # 4. Left Encoder Drive Shaft (X = 24.3 .. 36.2, D3.50 -> 0.05 mm slip clearance inside Alps EC10E D3.60 bore)
    nxh.cylinder(part, (24.3, ENC_Y, ENC_Z), (1, 0, 0), "enc_dia", x_left - 24.3 + 1.5, op=nxf.BOOL.Unite, target=body)

    # 5. Right MMB Switch Actuator Axle (X = 42.2 .. 52.0, D1.90 -> underside Z=7.645, 0.050 mm above SW_MMB!)
    nxh.cylinder(part, (x_right - 1.5, ENC_Y, ENC_Z), (1, 0, 0), "mmb_dia", 52.0 - (x_right - 1.5), op=nxf.BOOL.Unite, target=body)

    blank_helpers(part, [body])
    assert len(nxh.solids(part)) == 1, f"Scroll wheel solids={len(nxh.solids(part))}"
    errs = nxh.feature_errors(part)
    ex = nxh.examine_geometry(part, body)
    ok = nxh.body_ok(part, body)
    nxf.step_export(part, stp_path, ap242=False)
    return {
        "part": "mouse_scroll_wheel",
        "solids": len(nxh.solids(part)),
        "volume_mm3": round(nxh.volume(part, body), 2),
        "bbox": [round(v, 3) for v in nxh.bbox(body)],
        "body_ok": ok,
        "examine": ex,
        "feature_errors": errs,
    }


# =============================================================================
# PART 4: TOP CENTER DPI BUTTON (mouse_dpi_button.prt)
# =============================================================================
def build_dpi_button(prt_path, stp_path):
    part = nxh.new_part(prt_path)
    y_dpi = SW_DPI[1]   # -43.180

    # 1. Upper sculpted lozenge button cap (3.8 x 7.0 mm -> 0.3 mm uniform gap inside 4.4 x 7.6 mm top-shell slot)
    # Extrude generously up to Z=29.5 then trim top with sloped datum plane matching canopy rise (~24 deg)
    _f, body = extrude_rounded_xy(part, XC, y_dpi, 19.6, 29.5, 3.8, 7.0, 1.8)
    slope_rad = math.radians(24.0)
    # Normal points +Z and +Y (so plane rises as Y goes rear -Y, matching canopy slope!)
    _fdp, dp_cap = nxh.datum_plane(part, (XC, y_dpi, 26.6), (0.0, math.sin(slope_rad), math.cos(slope_rad)))
    nxf.trim_body(part, body, keep_point=(XC, y_dpi, 20.5), datum_plane=dp_cap)
    top_edges = [e for e in body.GetEdges() if nxh.bbox(e)[2] > 24.5]
    if top_edges:
        nxh.attempt("dpi_top_blend", lambda: nxf.edge_blend(part, [(top_edges, "0.55")]))

    # 2. Captive retention skirt flange safely below sloped inner top-shell ceiling (Z_in >= 21.5 -> skirt Z=18.8..20.0)
    extrude_rounded_xy(part, XC, y_dpi, 18.8, 20.0, 6.0, 9.0, 2.0, op=nxf.BOOL.Unite, target=body)

    # 3. Offset vertical striker stem hitting SW_DPI plunger at (40.040, -43.180, Z=7.650)
    extrude_rounded_xy(part, SW_DPI[0], SW_DPI[1], STRIKER_Z, 19.2, 3.0, 3.0, 0.6, op=nxf.BOOL.Unite, target=body)

    blank_helpers(part, [body])
    assert len(nxh.solids(part)) == 1, f"DPI button solids={len(nxh.solids(part))}"
    errs = nxh.feature_errors(part)
    ex = nxh.examine_geometry(part, body)
    ok = nxh.body_ok(part, body)
    nxf.step_export(part, stp_path, ap242=False)
    return {
        "part": "mouse_dpi_button",
        "solids": len(nxh.solids(part)),
        "volume_mm3": round(nxh.volume(part, body), 2),
        "bbox": [round(v, 3) for v in nxh.bbox(body)],
        "body_ok": ok,
        "examine": ex,
        "feature_errors": errs,
    }


# =============================================================================
# PART 5 & 6: 90-DEG BELL-CRANK THUMB BUTTONS (M5 FWD & M4 BACK)
# =============================================================================
def build_thumb_button(prt_path, stp_path, name, y_pad, y_plunger, x_pad_outer):
    """90-degree bell-crank thumb button:
    - Ergonomic thumb pad protrudes out left shell window at Z=[15.6..20.4]
    - Pivots around longitudinal Y-axis at (PIVOT_X=14.8, PIVOT_Z=11.8) via integral D1.95 trunnion pins
    - Horizontal inward arm drives 3.2x3.2 striker foot down to Z=7.650 directly over vertical Omron switch!
    """
    part = nxh.new_part(prt_path)

    # 1. Ergonomic thumb pad protruding out of left shell window (0.4 mm window clearance all around)
    _f, body = extrude_rounded_yz(part, x_pad_outer, 14.8, y_pad, 18.0, 11.4, 4.9, 2.0)
    outer_edges = [e for e in body.GetEdges() if nxh.bbox(e)[3] < x_pad_outer + 0.3]
    if outer_edges:
        nxf.edge_blend(part, [(outer_edges, "1.0")])

    # 2. Bell-crank L-arm (XZ polygon extruded 3.8 mm wide centered on y_plunger)
    # Connects thumb pad (X=13.5..15.2, Z=15.8) -> pivot hub (14.8, 11.8) -> actuator foot over (20.99, 7.65)
    arm_pts = [
        (13.6, 16.5),
        (15.6, 16.5),
        (16.0, 12.6),
        (22.4, 10.6),
        (22.4, STRIKER_Z),
        (19.4, STRIKER_Z),
        (19.4,  9.2),
        (13.6, 11.0),
    ]
    extrude_polygon_xz(part, arm_pts, y_plunger - 1.9, y_plunger + 1.9, op=nxf.BOOL.Unite, target=body)

    # 3. Pivot Hub Barrel + Integral D1.95 Trunnion Pins (engage shell cradle D2.2 bores at y_pad +/- 7.6!)
    # Hub spans y_pad - 5.2 .. y_pad + 5.2 (clears gussets at +/- 7.6 with 1.5 mm axial margin)
    nxh.cylinder(part, (PIVOT_X, y_pad - 5.2, PIVOT_Z), (0, 1, 0), 3.2, 10.4, op=nxf.BOOL.Unite, target=body)
    # Integral trunnion pin spans through both flanking cradle gussets (y_pad - 8.2 .. y_pad + 8.2)
    nxh.cylinder(part, (PIVOT_X, y_pad - 8.2, PIVOT_Z), (0, 1, 0), 1.95, 16.4, op=nxf.BOOL.Unite, target=body)

    blank_helpers(part, [body])
    assert len(nxh.solids(part)) == 1, f"{name} solids={len(nxh.solids(part))}"
    errs = nxh.feature_errors(part)
    ex = nxh.examine_geometry(part, body)
    ok = nxh.body_ok(part, body)
    nxf.step_export(part, stp_path, ap242=False)
    return {
        "part": name,
        "solids": len(nxh.solids(part)),
        "volume_mm3": round(nxh.volume(part, body), 2),
        "bbox": [round(v, 3) for v in nxh.bbox(body)],
        "body_ok": ok,
        "examine": ex,
        "feature_errors": errs,
    }


# =============================================================================
# PART 7: VIRGIN PTFE GLIDE SKATES (mouse_skates.prt)
# =============================================================================
def build_skates(prt_path, stp_path):
    part = nxh.new_part(prt_path)
    z0, z1 = Z_BOT - 0.30, Z_BOT + 0.45   # 0.75 mm thick PTFE, seated 0.45 mm in 0.50 mm pocket (0.05 gap), protrudes 0.30 mm

    # Front skate
    _f1, b_front = extrude_rounded_xy(part, XC, -10.5, z0, z1, 34.4, 6.2, 2.8)
    # Rear skate
    _f2, b_rear  = extrude_rounded_xy(part, XC, -107.5, z0, z1, 37.4, 11.2, 5.1)
    # Sensor ring skate
    _f3, b_ring  = extrude_rounded_xy(part, SNS_X, -57.0, z0, z1, 14.0, 21.0, 3.7)
    extrude_rounded_xy(part, SNS_X, -57.0, z0 - 0.2, z1 + 0.2, 10.8, 17.8, 2.7, op=nxf.BOOL.Subtract, target=b_ring)

    # Smooth 0.25 mm bottom chamfer on all 3 skates so edges glide effortlessly over cloth pads
    for idx, b in enumerate((b_front, b_rear, b_ring)):
        bot_e = [e for e in b.GetEdges() if nxh.bbox(e)[5] < z0 + 0.05]
        if bot_e:
            nxh.attempt(f"skate_chamfer_{idx}", lambda edges=bot_e: nxf.chamfer(part, edges, "0.25"))

    solids = [b_front, b_rear, b_ring]
    blank_helpers(part, solids)
    errs = nxh.feature_errors(part)
    ok_all = all(nxh.body_ok(part, b) for b in solids)
    nxf.step_export(part, stp_path, ap242=False)
    return {
        "part": "mouse_skates",
        "solids": len(nxh.solids(part)),
        "volume_mm3": round(sum(nxh.volume(part, b) for b in solids), 2),
        "body_ok": ok_all,
        "feature_errors": errs,
    }


# =============================================================================
# MAIN ORCHESTRATION: BUILD ALL PARTS + ASSEMBLY + STEP EXPORTS
# =============================================================================
def main():
    out_dir = sys.argv[1]
    pcb_step = sys.argv[2]
    prt_dir = os.path.join(out_dir, "prt")
    stp_dir = os.path.join(out_dir, "step")
    os.makedirs(prt_dir, exist_ok=True)
    os.makedirs(stp_dir, exist_ok=True)

    res = {"result": "FAIL", "parts": []}
    try:
        # Build all 7 mechanical parts
        parts_spec = [
            ("mouse_base",         lambda p, s: build_base(p, s)),
            ("mouse_top_shell",    lambda p, s: build_top_shell(p, s)),
            ("mouse_scroll_wheel", lambda p, s: build_scroll_wheel(p, s)),
            ("mouse_dpi_button",   lambda p, s: build_dpi_button(p, s)),
            ("mouse_thumb_fwd",    lambda p, s: build_thumb_button(p, s, "mouse_thumb_fwd",  -50.80, SW_M5[1], 9.0)),
            ("mouse_thumb_back",   lambda p, s: build_thumb_button(p, s, "mouse_thumb_back", -67.80, SW_M4[1], 8.3)),
            ("mouse_skates",       lambda p, s: build_skates(p, s)),
        ]

        part_paths = {}
        for name, fn in parts_spec:
            p = os.path.join(prt_dir, name + ".prt")
            s = os.path.join(stp_dir, name + ".step")
            info = fn(p, s)
            res["parts"].append(info)
            part_paths[name] = p

        # Build Mechanical-Only Assembly & export STEP
        asm_mech_path = os.path.join(prt_dir, "mouse_mech_asm.prt")
        asm_mech = nxa.new_assembly(asm_mech_path)
        for name, p in part_paths.items():
            nxa.add_component(asm_mech, p, name.upper())
        nxh.save(asm_mech)
        nxf.step_export(asm_mech, os.path.join(stp_dir, "mouse_mechanical_only.step"), ap242=False)

        # Import PCB STEP into mouse_pcb_ref.prt and build full 8-component assembly
        pcb_prt_path = os.path.join(prt_dir, "mouse_pcb_ref.prt")
        pcb_part = nxh.new_part(pcb_prt_path)
        scratch_prt = os.path.join(out_dir, "_pcb_import_scratch.prt")
        nxf.step_import(pcb_part, pcb_step, scratch_prt)
        nxh.save(pcb_part)

        asm_full_path = os.path.join(prt_dir, "mouse_asm.prt")
        asm_full = nxa.new_assembly(asm_full_path)
        nxa.add_component(asm_full, pcb_prt_path, "MOUSE_PCB")
        for name, p in part_paths.items():
            nxa.add_component(asm_full, p, name.upper())
        nxh.save(asm_full)

        # Native Parasolid Exact Clearance Analysis across ALL 8 components (including PCB!)
        cs = nxa.clearance_set(asm_full, "FULL_CHECK", zone=0.0)
        clearance_res = nxa.run_clearance(cs)
        res["clearance_exact"] = clearance_res
        res["hard_interferences_all"] = [c for c in clearance_res if c.get("type") == "Hard"]
        # Separate mechanical design interferences (involving any of our 7 MOUSE_* parts) from internal PCB STEP pairs
        res["hard_interferences_mech"] = [
            c for c in res["hard_interferences_all"]
            if any(p.startswith("MOUSE_") for p in c.get("pair", []))
        ]

        nxf.step_export(asm_full, os.path.join(stp_dir, "mouse_assembly_full.step"), ap242=False)

        all_ok = all(p["body_ok"] and not p["feature_errors"] for p in res["parts"])
        res["result"] = "PASS" if (all_ok and not res["hard_interferences_mech"]) else "CHECK_INTERFERENCE"
    except Exception:
        res["error"] = traceback.format_exc()

    nxh.write_json(os.path.join(out_dir, "result.json"), res)


if __name__ == "__main__":
    main()
