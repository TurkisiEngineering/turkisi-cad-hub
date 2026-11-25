# CONSTRAINTS.md - WP-B design rule sheet (shell designers follow this)

Frame: native STEP coords, +X right, +Y FRONT, +Z up, mm. PCB never moves (bottom Z 0, top Z 1.51 in STEP; brief says 1.6).
Board facts below come from `work/00_pcb/PCB_DATA.json`. Datasheet page images are next to this file (`ds_*.png`).
Figure: `work/renders/B01_stackup.png` (script `stackup_fig.py`).

Sources:
[S1] PixArt PMW3360DM-T2QU datasheet v1.30 (Fig.3 cut-outs, Fig.4 stack-up, Fig.6 LM19-LSI lens, Fig.8 base plate, Z table), copy at https://www.epsglobal.com/Media-Library/EPSGlobal/Products/files/pixart/PMW3360DM-T2QU.pdf
[S2] PixArt PMW3330 datasheet (same LM19-LSI lens, Z 2.2/2.4/2.6), https://www.epsglobal.com/Media-Library/EPSGlobal/Products/files/pixart/PMW3330DM-TZQU.pdf
[S3] Omron D2F datasheet p.4, https://omronfs.omron.com/en_US/ecb/products/pdf/en-d2f.pdf
[S4] Alps Alpine EC10E catalog (hollow shaft, Drawing No.2-4), https://www.alpsalpine.com/cms.media/product_catalog_ec_03_ec10e_en_a9ede251c7.pdf ; product page https://tech.alpsalpine.com/e/products/detail/EC10E1220501/
[S5] Practice values (FDM, ergonomics, skates) = common maker practice and published mouse specs, marked "practice". Not from one datasheet.

---------------------------------------------------------------------------------------------------
## 1. Sensor PMW3360 + LM19-LSI lens: sets the floor height

Datasheet stack-up [S1 Fig.4] (PCB 1.60 reference):
| item | value |
|---|---|
| lens flange bottom (lens reference plane) to tracking surface, Z | **2.40** nominal, **2.2-2.6** allowed [S1 table, S2] |
| top of PCB (sensor seating plane) to tracking surface | **7.40** |
| PCB bottom to base plate top (gap) | **2.90** |
| top of sensor to surface | 9.81 ; sensor die to surface 8.84 |
| lift-off distance | firmware setting (~1-2 mm), not geometry |

The sensor sits on the PCB top and the lens clips to the sensor through the PCB cut-out, so the rule is
**floor Z = PCB top - 7.40**. STEP PCB top 1.51 -> -5.89; real 1.6 board -> -5.80.
**RECOMMEND: Z_FLOOR = -5.85** (lens Z = 2.40 +/-0.05 for either board thickness; leaves +/-0.15 for print and skate error inside the 2.2-2.6 window).

Derived Z levels (use these numbers):
- Z_FLOOR (skate bottom / mousepad) = **-5.85**
- lens reference plane (lens flange bottom) = **-3.45**
- bottom-shell underside (skate pads stand 0.45 proud) = **-5.40**
- bottom-shell inner floor top near the sensor and under the PCB = **-2.90** (datasheet gap 2.90). THT pin tips: D2F -1.905, PDIP/header -1.405 -> 1.0 / 1.5 mm clear. Never raise the inner floor above -2.90 under the board.
- plate thickness under the board = 2.50.

Sensor XY (datasheet Fig.3 checked against the board): PCB cut-out X 35.07..43.67, Y -65.88..-48.62 is exactly the datasheet cut-out
(pin1 + [-14.48, +2.78] along the row, [1.05, 9.65] across), so front of the mouse is +Y as PixArt draws it.
**Optical centre = (39.37, -57.44)** = pin1 (44.72,-63.1) + (-5.35, +5.66) [S1 Fig.3].
Note: PCB_DATA.json `optical_centre_xy` -56.425 is the pin-field centre and is 1.0 mm off. Use **-57.44**.

LM19-LSI lens [S1 Fig.6]: flange outline **21.15 (along Y) x 18.85 (along X)**, rounded corners, flange about 0.53 thick, optical centre 10.87 from one Y end.
Two clip arms 8.47 apart go up through the PCB cut-out and snap onto the sensor; two Ø0.90 guide posts 16.5 apart. **The lens is self-retained.** The shell only gives it a pocket and must not press on it.

Bottom-shell features at the sensor [S1 Fig.8, adapted for FDM]:
- lens pocket from the inner floor (-2.90) down to **Z -3.50** (0.05 below the lens plane, so no preload): **22.2 (Y) x 19.6 (X), corner R7.0, centred on (39.37,-57.44)**.
  The datasheet base plate pocket is 21.35 x 19.00 R7.05; the extra allows +/-0.3 for print error and lens orientation.
- optical through-hole under the lens: at Z -3.50 at least **4.0 (X) x 6.0 (Y)** slot (datasheet min width 4.0, end radius R2 max), centred on the optical centre,
  then flaring **45 deg** down to the underside (about 7.9 x 9.9 at Z -5.40). The datasheet flare is 69.5 deg; 45 deg prints without support.
- skate near the opening: datasheet note says "mouse feet should be placed close to the opening". Put a **ring skate or two pads within 3-6 mm of the hole** (Fig.8: ring edge at least 1.5 from the opening).
- LED: it is inside the PMW3360 package, and the lens carries the light pipe/prism. No external LED and no light pipe in the shell.
  Print the bottom shell in an **opaque, dark** filament; avoid translucent/white PLA near the lens. Keep the hole free of burrs and elephant foot (chamfer the bed edge 0.3).

## 2. Omron D2F micro switches (6x) [S3]

| D2F (pin plunger) | D2F std | D2F-F (low force) |
|---|---|---|
| operating force OF max | **1.47 N (150 gf)** | 0.74 N (75 gf) |
| release force RF min | 0.20 N | 0.05 N |
| pretravel PT max | **0.5** | 0.5 |
| overtravel OT min | **0.25** | 0.25 |
| movement differential | 0.12 | 0.12 |
| operating position OP (from seating plane) | **5.5 +/-0.3** | same |
| body | 12.7-12.8 L x 5.8 W x 5 H, plunger about 2.9 x 1.2 | |

The STEP placeholder has the body top at Z 6.595 and the plunger top at **Z 7.595** (6.0 above the seat, consistent with OP 5.5 + PT 0.5).
Plunger XY per switch: `PCB_DATA.json switches[].plunger_box`. Main L (20.32,-23.53), main R (58.42,-23.53), middle (50.80,-27.975),
DPI (40.04,-43.18), side fwd (20.99,-50.80), side back (20.99,-68.58). All plungers push in **-Z**.
Rules:
- **Rest gap nub to plunger = 0.10** (nub contact face at Z **7.70**). Gaming practice is about zero pre-travel; 0.1 absorbs print error. Allow a 0.1-0.2 shim/sand adjustment.
- **Travel stop: hard stop 0.8 mm after nub contact** (PT 0.5 max + OT >= 0.25). The stop lands on the shell or a rib, not on the switch body.
- **Nub contact pad >= 3.5 x 2.5** (covers the 2.9 x 1.2 plunger +/-0.5 position error), flat, edge R0.3. Nub stem >= 2.0 x 2.0 (PETG) or Ø2.5.
  Long nubs (DPI about 10 mm) run in a guide sleeve with 0.25 radial clearance.
- Force at the finger is about 1.5 N x (plunger arm / finger arm). Keep the main-button plunger at >= 60 % of the finger-arm length from the pivot.

## 3. Alps EC10E encoder (scroll) [S4] + middle click

- **Hollow shaft, not a D-cut or knurled shaft.** The rotor has a **hex hole 1.73 (+0.05/0) across flats**, 1.7 +/-0.1 deep with a **3 deg flare** (so the axle can tilt),
  then a Ø2.2 +/-0.1 round bore; rotor Ø2.98; hub Ø3.6. Body 9.8 wide, 4.4 thick along the axis (3.2 + 2 x 0.6), mount height **H = 7, 9 or 11** (variant).
  Detents: **24 detents, 12 pulses/rev** (EC10E1220501); detent torque 5 +/- 3 mN·m; life 100k rev; must be mounted horizontally [S4 product page].
- STEP placeholder: axis along **X**, through **(Y -27.9, Z 8.595)**, so H = 7.0 above the seat. Hub faces at X 23.98 / 31.98.
  **RISK:** the Alps page lists EC10E1220501 with H = 9.0 (axis Z 10.595). Follow the STEP (8.595), but put the far-end axle support in a separate small printed part so a +2 mm change means reprinting one part.
- The PCB has a **wheel slot X 33.02..45.72, Y -39.37..-14.73** (front notch). The middle-click D2F plunger sits **directly under the axle line** (Y -27.975, top Z 7.595)
  = axle Z 8.595 - Ø2 axle radius 1.0. The board was laid out for the standard mouse design:
  **Wheel on a separate axle: hex end (1.70-1.73 A/F, 2.0 long) in the encoder; the axle crosses the slot; its far end (Ø2.0, X about 49.5-52) rests on the middle-click plunger.**
  Middle click = the wheel+axle tilts about the encoder hex (lever about 19 mm; 0.8 mm travel = 2.4 deg, inside the 3 deg flare). The D2F spring returns it.
  A printed **cage/yoke** over the far end (from the bottom shell, U-slot 2.0 + 0.25 wide) sets the up-stop (axle top Z 9.60 at rest) and a down-stop at 0.8 travel. Keep the axle free in Y +/-0.1.
- Wheel: **Ø22-24, width 7-8, centred at X 39.37** (mouse centreline; slot allows width <= 12). Wheel side to slot edge >= 0.3; wheel to encoder hub >= 0.5.
  A Ø24 wheel reaches Z -3.4 through the slot, so the bottom shell needs a **local pocket to Z -3.9** under the wheel (plate still 1.5 thick there).
  Wheel opening in the top shell: wheel width + 0.6 (0.3/side), chord length + 1.0.
- Tyre: **O-ring in a groove** (e.g. NBR 2.0 cord, ID about 19-20 for a Ø24 wheel; groove depth 1.4-1.5) or a TPU 95A tyre 1.5-2 thick, printed separately, pressed or glued on.
- Axle: a printed 1.73 hex is weak and inexact. Prefer a **steel Ø2.0 rod with a filed/ground hex end, or an OEM mouse wheel axle**.
  If printed, print wheel+axle in one piece with the **axis vertical, 0.12 layers, hex at 1.70 A/F**, and test-fit first.

## 4. Ergonomics, right-handed palm/claw (practice [S5]; reference mice: Logitech G Pro 125x63.5x40, Zowie EC2 120x64x40, Razer Viper 126.7x66.2x37.8)

| item | rule |
|---|---|
| overall L x W x H | **120 (118-126) x 64 (62-68) x 40 (38-42)** above the floor |
| mouse centreline | **X = 39.37** (= PCB centre = sensor X) -> outer width X 7.4..71.4 for W 64 |
| front tip | **Y about -4 (+/-2)** -> wheel centre (Y -27.9) about 24 from the tip (typical 20-30); rear Y about -124 |
| hump (max height) | **Z 34.15 (40 above floor) at Y -70..-78** (55-62 % of L from the front; claw: further back) |
| button surface at the wheel | about **23 above floor (Z 17.2)**; wheel top Z 20.6 -> wheel stands about 3.4 proud (typical 3-5) |
| front tip height | 12-15 above floor; front edge rounded R >= 3 |
| main buttons | finger part **55-65 long** from the tip; L/R split gap about 0.5; button width about 25-28 each; wheel gap between buttons 10-12 |
| thumb side (LEFT, -X) | concave groove **depth 2-3, Z 3..18 above floor**, along Y about -45..-80; side buttons there |
| side buttons | already fixed by the switches: plungers at Y -50.8 / -68.58 (about 47 / 65 from the tip, typical 45-75), button faces 14-18 long, about 6-8 high, centred about 12-15 above floor; proud 1.0-1.5 |
| right side | slight outward flare at the bottom for the ring/pinky; wall slopes 5-10 deg |
| PTFE skates | **0.6-0.8 thick** (incl. adhesive); **recess 0.30-0.35**, standing **0.40-0.50 proud**; pocket = skate + 0.2; edge R0.5; >= 2 from the shell edge; 2 big (front + rear) + sensor ring, or 4 corners + ring |

Clearances to the PCB: top-shell inside surface >= 1.0 above the tallest part under it (USB header pins Z 10.135; with a Dupont housing plan Z >= 20 there, or solder the cable);
side walls >= 1.0 from the PCB edge (more where side-button levers sit).
Cable: the header is at the rear-left (24.14,-74.68). Route behind the PCB to a **front-centre exit** (typical) through a channel in the bottom shell beside the board (X 64.3..69, gap >= Ø cable + 0.5), with a zig-zag strain relief.

## 5. FDM printability: PLA / PETG, 0.4 nozzle (practice [S5])

| rule | value |
|---|---|
| min wall (structural) | **0.8** (2 lines); **shell walls 1.6-2.0** (4-5 lines); floor/roof >= 1.2 (6 x 0.2 layers) |
| ribs | 0.8-1.2 thick (0.5-0.6 x wall), height <= 5 x thickness |
| overhang without support | **<= 45 deg** from vertical (PLA up to 55, do not design to it) |
| bridges | **<= 10** design limit (PLA OK to 15-20 if cooling is good) |
| min hole / pin | vertical hole >= Ø1.5 (prints 0.1-0.2 undersize; model +0.15); horizontal holes as a teardrop / flat top; printed pins >= Ø2.5, axis parallel to the bed for strength |
| clearances | **sliding/rotating 0.25-0.30** per side; push fit 0.10; press/interference 0.0 to -0.05; part-to-part visible gap 0.4-0.5 |
| layer height | 0.2 shells; **0.12-0.16 for the wheel, nubs, hinges, hex** |
| M2 self-tap into a printed boss | pilot **Ø1.6 (PLA) / Ø1.7 (PETG)**, **boss OD 4.5-5.0**, engagement >= 4 (2 x d), 6 better; through hole Ø2.4; pan head Ø3.8 x 1.3-1.6 -> counterbore Ø4.4; button head ISO 7380 dk 3.5 |
| M2 heat-set insert | M2 x 3, OD about 3.6 -> **hole Ø3.2, depth 3.5-4.0**, boss OD >= 6.0. Use where a joint is opened repeatedly (top-to-bottom shell) |
| snap hooks | cantilever strain e = 1.5·t·y/L^2 <= **1.5 % PLA, 2.5 % PETG**. Example: t 1.2, overhang y 0.6, L >= 8. 30 deg lead-in, 90 deg retain face (or 45 deg if removable). Print with the hook length in the XY plane, never along Z |
| flexure / living hinge | PLA cracks under fatigue; use **PETG for flexures**. Hinge strain e = t·θ/(2·Lf). A button hinge: θ about 0.8/36 rad, t 1.0, Lf 8 -> e about 0.14 %, fine even in PLA. Keep e <= 0.3 % PLA, <= 1 % PETG. Leaf t 0.8-1.2, Lf >= 8, layers along the leaf length |
| TPU | 95A tyre 1.5-2.0 thick, printed slowly (20-30 mm/s), axis vertical |
| elephant foot | 0.3 x 45 deg chamfer on every bed edge that mates with something |

Print orientation:
- **Bottom shell:** underside on the bed. The skate recesses are blind pockets from below; the lens pocket and bosses go upward; everything is self-supporting. The optical hole flares 45 deg toward the bed. Do not use supports in the optical hole.
- **Top shell:** rim on the bed, dome up. Outer surface quality wins. Internal tree supports only for flat ceilings; design the inner ceiling >= 35 deg where possible, with bosses and hooks gusseted at 45 deg.
- **Main/side/DPI buttons:** outer (finger) face up, flexure leaf flat in XY. Nubs/stops are gusseted (self-supporting) or use tree supports from the bed only.
- **Wheel:** axis vertical (round, true). Tyre separate. Wheel cage/yoke: flat side down.

## 6. Assembly scheme (recommended)

1. **PCB to bottom shell:** 4 x M2 x 6 self-tapping (or M2 + insert) from above through the PCB holes Ø2.2 at
   (16.51,-74.422) (62.23,-74.422) (16.51,-16.764) (62.23,-16.764) into bottom-shell bosses, **OD 4.5, top face Z 0.0**, pilot Ø1.6, from the inner floor -2.90.
   The front-left/right heads are 0.34 from the D2F bodies (body Y ends at -19.0): use heads <= Ø3.5.
   Add 2-3 extra 1.0-wide support ribs under the board (top Z 0.0) away from THT pins, in the main-click areas (Y -20..-32, beside the switches) so clicks do not flex the board.
2. **Top shell to bottom shell:** **2 x M2 from below at the rear** (about X 39.37 +/- 14, Y -95..-105, under the rear skate) into top-shell bosses with heat-set inserts (or self-tap Ø1.6), boss OD 5-6.
   **Front: 2 hooks** on the top-shell front strip/side walls (beside the wheel) engage slots in the bottom-shell front lip. Locate with 2 pins/ribs, 0.15 gap.
   The skates cover the screw heads (counterbore so the head sits >= 0.2 below the skate recess floor).
   Lip/tongue joint around the parting line: tongue 1.0 x 1.5, 0.2 gap, so the seam is light-tight and straight.
3. **Main buttons:** separate PETG parts. **Rear flexure leaf** (t 1.0, Lf 8-10, width 15-20) clamped between top shell and a clamp bar (or slid into a slot and pinned) at about Y -62..-70,
   so the button pivots about 36-45 behind the plunger. The leaf gives the return force and zero rattle.
   Side guide ribs with a 0.2 gap stop sideways wobble. Rest gap 0.10 at the nub (Z 7.70) and a hard stop at 0.8 travel.
   Alternative: a hinge pin (Ø2 steel) in C-clips (270 deg wrap, 0.15 gap); pins rattle more.
4. **Middle click:** wheel + axle tilting about the encoder hex onto the D2F at (50.8,-27.975). The cage gives the up-stop and the 0.8 down-stop (section 3). The axle end bears on the plunger with a 0-0.1 gap.
5. **DPI button** (plunger 40.04,-43.18, behind the wheel): a small top button with a long nub in a guide sleeve (0.25 clearance), the same flexure idea or a sliding plunger with an integral PETG leaf.
6. **Side buttons:** the plungers are vertical (push -Z) about 13 mm inboard from the left wall. Use **bell-crank levers**: a pivot along Y near the wall top (or a PETG flexure),
   thumb pushes +X, the inner arm presses down -Z on the plunger. Lever ratio about 1:1, rest gap 0.1, stop at 0.8.
7. Assembly order: lens on sensor -> PCB onto the bottom shell (4 screws) -> wheel+axle into the encoder + cage -> side levers -> top shell with the buttons hooked at the front, 2 rear screws -> skates.

## Key numbers (summary)
Z_FLOOR -5.85 | lens plane -3.45 (Z 2.40, 2.2-2.6) | PCB top to floor 7.40 | inner floor -2.90 | shell underside -5.40 | optical centre (39.37,-57.44) |
lens pocket 22.2 x 19.6 R7 to Z -3.50 | optical hole >= 4.0 x 6.0 + 45 deg flare | D2F OF 1.47 N, PT 0.5, OT 0.25, OP 5.5 +/-0.3, plunger top 7.595 | nub rest Z 7.70, stop 0.8 |
EC10E hex 1.73 A/F, 24 detents, axle Z 8.595 (H=7, risk H=9) | wheel Ø22-24 x 7-8 at X 39.37 | mouse 120 x 64 x 40, tip Y about -4, hump Z 34.15 at Y about -74 |
skate 0.8 in 0.35 recess | wall 1.6-2.0 | overhang 45 | bridge 10 | clearance 0.25-0.30 slide / 0.10 push | M2 pilot 1.6, boss 4.5-5, insert hole 3.2 | snap e <= 1.5 % PLA / 2.5 % PETG.
