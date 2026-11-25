# DESIGN_SPEC - DIY gaming mouse shell around mouse_pcb.step (WP-C master layout)

All numbers are native STEP coordinates in mm: +X right, +Y FRONT, +Z up. The PCB is never moved (board Z 0..1.51, parts seated at Z 1.595).
The single source of every number below is `master.py` (same folder). Names in `code` are its constants/functions.
Numbers verified by `layout_check.py` (log: `out/layout_check.log`, json: `out/layout_check.json`). Rules: `../01_research/CONSTRAINTS.md`.

## 1. Concept

Right-handed, palm/claw, wired gaming mouse in 9 printed parts + 1 optional tyre:

| part | material | job |
|---|---|---|
| `bottom_shell` | PLA/PETG, **opaque dark** | tub + floor plate (sets the sensor height), 4 PCB bosses, lens pocket + optical hole, skate recesses, cable channel + exit, side-lever cradles, wheel pocket, yoke socket, joint lip |
| `top_shell` | PLA | palm hump, side walls, front band, centre tongue (wheel + DPI windows), 3 insert bosses, 2 leaf clamp pads |
| `button_L`, `button_R` | **PETG** | separate main buttons, each on a rear clamped flexure leaf, nub on the D2F, own hard stop |
| `wheel` (+ optional `wheel_tyre` TPU 95A) | PLA/PETG | Ø23.6 x 7.5 wheel with axle, hex end in the EC10E, far end rests on the middle-click D2F |
| `wheel_yoke` | PETG | small plate plugged into the bottom shell: Y-location, up-stop and down-stop of the axle far end (reprintable if the EC10E is the H = 9 variant) |
| `dpi_button` | PLA/PETG | sliding cap in the tongue behind the wheel, guided by a sleeve |
| `side_btn_fwd`, `side_btn_back` | PETG | bell-crank levers: thumb push +X turns into -Z on the top-actuated side D2F switches |

Shape: loft of 23 superellipse sections (`section_points`), flat underside, nose/tail cap fillets R6, thumb groove on the LEFT (depth 2.6, Z 6.5, Y -40..-88), ridge 1.8 mm to the thumb side over the palm. Skin builds in ~8 s, cached (`cache/*.brep`).

## 2. Overall dimensions and Z stack

| item | value |
|---|---|
| length x width x height above the floor | **120.0 x 63.5 x 39.9** (Y -4..-124, X 7.87..71.37, top Z 34.09) |
| centreline | X 39.37 (= PCB centre = sensor X) |
| hump | Z 34.08 at Y -74 (40 above floor); button surface at the wheel Z 17.25 (23.1 above floor); nose top ~Z 9 |
| floor / tracking surface `Z_FLOOR` | **-5.85** (PCB top 1.51 -> 7.36 above floor; real 1.6 board -> 7.45; datasheet 7.40) |
| lens reference plane `Z_LENS_PLANE` | -3.45 = **2.40 above the floor** (datasheet 2.2-2.6) |
| shell underside `Z_UNDER` | -5.40 (PTFE skate 0.8 in a 0.35 recess -> 0.45 proud) |
| bottom-shell inner floor `Z_INNER_FLOOR` | -2.90 (lead tips -1.905 -> 0.995 clear); plate 2.5 |
| lens pocket floor `Z_LENS_POCKET` | -3.50 |
| PCB seat (boss tops) `Z_BOSS_TOP` | 0.00 |
| parting plane `Z_PART` | **+1.00** (flat): bottom shell below, top shell above |
| wall `WALL` | 1.80 everywhere on the skin (true normal offset, `inner()`) |

## 3. PCB position, parting, joint, screws

- PCB stays at its STEP position; it sits on 4 bottom-shell bosses (`PCB_HOLES`, OD 4.5, top Z 0, pilot Ø1.6 PLA / 1.7 PETG, ≥ 4.5 deep) and is held by **4 x M2x6 self-tapping screws from above**, head ≤ Ø3.5. Two support ribs `PCB_RIBS` (top Z 0) carry the main-button stop loads.
- Parting: flat plane Z 1.00. The top shell has nothing below Z 1.00 (it prints rim-down). The bottom shell carries a **lip** (`LIP_*`: 1.0 thick, 1.5 high, 0.15 inside the top-shell wall, offsets 1.95..2.95 from the skin), interrupted at the side-button notches.
- **Top shell to bottom shell: 3 x M2x8 from below** into M2x3 heat-set inserts (hole Ø3.2 x 4.0) in top-shell bosses OD 6.0: `TS_SCREWS` = (39.37,-10.8) front, (27.37,-98.0), (51.37,-98.0) rear. Bottom shell: Ø2.4 through + Ø4.4 counterbore up to Z -3.25 (head top ≥ 0.2 under the skate recess floor), all three heads hidden under skates. Assembly is a straight vertical drop of the top shell (no hooks).
- Assembly order: lens on sensor -> PCB onto the bottom shell (4 screws) -> side levers clicked into their cradles -> wheel+axle into the encoder, yoke over the axle end and into its socket -> cable soldered + laid in the channel -> top shell with buttons (leaf screws) and DPI cap pre-mounted, dropped on -> 3 screws from below -> skates.

## 4. Mechanisms

### 4.1 Main buttons L / R (WP-F)
- Split lines on the skin, gap `BTN_GAP` 0.50: inner edges X 33.62 / 45.12 (centre tongue `TONGUE_HW` 5.5 between them), rear edge Y -60.0, outer edge = plan line `BTN_SIDE_L` (X 14.3 at Y -60 -> 13.7 at Y -30, mirrored for R; meets the skin at Z 24.7 / 18.4 / 13.0 / 10.3 at Y -60/-45/-30/-15), nose split = plane Z 6.0 with **1.40 gap** (button tip moves 1.19 at full stop).
- Hinge: PETG **flexure leaf** 16 x 1.0, free length 8.0 (Y -59.4..-67.4), top face Z 20.0, clamped under a top-shell pad (Y -67.4..-73.4) by one M2 self-tap screw from below + 2 Ø1.5 locating pins. Pivot line (Y -63.4, Z 19.5). Nub arm 39.9 / finger arm 51.4 (Y -12) -> ratio 0.78; finger force ≈ 1.15 N + 0.13 N leaf. Leaf strain 0.13 %.
- Nub: pad 3.5 (X) x 2.5 (Y) centred on the plunger, contact face Z **7.695** (rest gap 0.10); nub length 5.5 (panel underside Z 13.2). Hard stop: post 1.7 x 3.0 at `STOP_PAD_L/R` on the free board strip, bottom Z 2.31 = board top + 0.80 (0.10 + 0.70 travel; on the real 1.6 board 0.71).

### 4.2 Scroll wheel + middle click (WP-G)
- Wheel Ø23.6 (incl. tyre) x 7.5 at X 35.62..43.12, axis (Y -27.9, Z 8.595) = EC10E axis. Top Z 20.40 -> **3.15 proud** of the button surface. Bottom Z -3.205 in a bottom-shell pocket to Z -4.10.
- Axle Ø2.0 along X from 30.10 to 52.30: hex 1.70 A/F x 1.9 into the EC10E rotor (hub face X 31.98), far end rests on the middle D2F plunger (50.80, -27.975, top 7.595 = axle bottom). Middle click = wheel+axle tilts about the hex (`ENC_PIVOT_X` 31.0, 3° flare); travel 0.70 at the plunger = 0.30 at the wheel.
- `wheel_yoke` plate X 44.10..45.30, Y -31.90..-23.90, plugged 1.5 deep into `YOKE_SOCKET` (push fit 0.05), top Z 11.5: vertical slot 2.25 wide, top Z 9.695 (up-stop, 0.10), bottom Z 7.111 (down-stop at 0.70 plunger travel).
- Gaps: wheel to slot edges 2.6 / 2.6, wheel to encoder hub 3.64, wheel to yoke 0.98, yoke to slot edge 0.42, wheel to DPI switch body 0.75, wheel in board slot reaches Y -37.34 (slot back -39.37).
- Force at the wheel ≈ 3.5 N with a standard D2F (lever 8.4/19.8). **Recommend D2F-01F (0.74 N) for the middle switch -> 1.7 N.**

### 4.3 DPI button (WP-H)
- Cap 6.0 x 5.0 centred on the DPI plunger (40.04, -43.18) in the tongue window (+0.30 gap), top flush with the skin (Z ≈ 22.9). Sliding cap guided by a sleeve hanging from the tongue down to Z 13.5 (0.15 clearance). Flange below the sleeve = up-stop. Nub pad 2.5 (X) x 3.5 (Y), length ≈ 13 (tongue underside Z 21.06). At rest the cap rests on the plunger (gravity), flange 0.15 under the sleeve. Down travel limited by the D2F (OT).

### 4.4 Side buttons (WP-H)
- Faces on the thumb groove: fwd Y -57.8..-43.8, back Y -75.6..-61.6, Z 3.0..10.0, top corners R2.5, **1.0 proud**, 0.30 gap. The top shell has **notches open at the rim** (Z 1.0..10.3), so it drops on over the faces; the bottom shell fills each notch with a wall tab up to Z 2.7.
- Bell-crank lever per button: pin Ø2.0 along Y at `SIDE_PIVOT` (X 12.2, Z -1.6) in two bottom-shell C-cradles (ID 2.30, 270° wrap, open to +Z), body plate inside the wall (X ≥ 12.3), arm over the board at Z ≥ 8.4, nub down to Z 7.695 at X 20.99. Rotation 5.2° for 0.8 at the nub, thumb travel 0.74, thumb force 1.6 N, nub slides 0.85 in +X (pad 3.5 in X, start 0.4 to -X of the plunger). Hard stop: a face on the lever body hits the board left edge (X 14.478, Z 0..1.51) after 0.8 nub travel (gap 0.22 at Z 0.75). Outward stop: the face-plate flange behind the notch rim.

### 4.5 Sensor
- Optical centre `OPT_C` (39.37, -57.44). Lens pocket 19.6 (X) x 22.2 (Y) R7 down to Z -3.50; optical slot 4.0 x 6.0 at Z -3.50 flaring 45° to the underside; no supports in it; elephant-foot chamfer 0.3. Sensor-ring skate OD 22 / ID 14 around it.

### 4.6 USB cable
- Ø3.5 max cable **soldered** to the header pins (no Dupont housing; pins top Z 10.135). Channel 4.0 wide, floor Z -3.90 (1.5 plate under it), centre line `CABLE_PATH`: header (24.1,-76.8) -> behind the board Y -80 -> right side X 66.6 -> passes outboard of the front-right PCB boss and under the board corner (board is Z 0..1.51, cable top Z -0.4) -> Y -9.8 -> **exit through the front face at X 46.5, Z -2.15** (hole Ø3.8, 0.8 chamfer outside). Room to the cavity wall ≥ 2.2 along the path (layout_check). Strain relief: 3 zig-zag posts in the right channel at Y -50/-40/-30, plus the 90° turn at the exit.

### 4.7 Skates (PTFE 0.8, recess 0.35)
Pocket outlines in `SKATES`: front rrect 31.0 x 6.4 R3 at (39.37,-10.6) (covers the front screw), rear rrect 36.0 x 11.0 R4 at (39.37,-98.0) (covers both rear screws), sensor ring OD 22 / ID 14. Skates = pocket - 0.2.

### 4.8 Print orientation (0.4 nozzle)

| part | orientation | supports | layer |
|---|---|---|---|
| bottom_shell | underside on the bed | none (lip, bosses, cradles all grow up; tab undersides ≥ 45°; optical hole flares 45° to the bed) | 0.2 |
| top_shell | rim (Z 1.00 plane) on the bed, dome up | tree supports **inside only** (hump ceiling, pads, sleeve); never on the skin | 0.2 |
| button_L / R | finger face up | tree supports under the panel; leaf lies flat (layers along the leaf) | 0.16 |
| wheel | axis vertical | none | 0.12 |
| wheel_yoke | flat side (YZ face) on the bed | none | 0.12 |
| dpi_button | upside down: cap top face on the bed, nub up | none | 0.12 |
| side levers | lying on the face-plate's flat side / pin axis parallel to the bed | minimal | 0.12 |

### 4.9 Clearances (design values)
Shell to any PCB component ≥ 1.0 (worst: encoder top 1.02 under button L) | moving part to fixed part ≥ 0.25 (sliding) | visible split gaps 0.50 (front 1.40, side faces 0.30) | push fits 0.05-0.10 | lip 0.15 | nub rest gap 0.10 | THT tips to floor ≥ 0.99.

## 5. ACCEPTANCE (lead engineer measures these on the delivered STEP files, PCB from the original STEP)

| # | what | how measured | limit |
|---|---|---|---|
| A1 | every part is one valid solid | `master.check_part`: n_solids == 1, is_valid | all 9 parts (+ tyre) |
| A2 | sensor height | Z_FLOOR = skate underside: Z_UNDER - 0.45 | -5.85 ± 0.05 (lens plane 2.40 above floor) |
| A3 | optical path clear | bottom shell ∩ vertical prism 4.0 x 6.0 at OPT_C, Z -5.5..0 | volume 0 |
| A4 | lens pocket | bottom shell ∩ rrect 19.6 x 22.2 R7 at OPT_C, Z -3.50..0 | volume 0 |
| A5 | no interference with the PCB | every part ∩ PCB STEP solids | volume 0 |
| A6 | PCB clearance | min distance part -> PCB component (not the designed contacts: bosses/ribs/stop posts on the board, nubs/axle on plungers) | ≥ 1.0 shells, ≥ 0.25 moving parts |
| A7 | main nub rest gap | nub face Z - 7.595 over the plunger box | 0.05 .. 0.30 |
| A8 | DPI / side nub rest gap | same | 0.0 .. 0.30 |
| A9 | main hard stop | stop post bottom Z - 1.51 | 0.75 .. 0.90 |
| A10 | axle on middle plunger | axle bottom Z over (50.8,-27.975) - 7.595 | 0.0 .. 0.10; yoke slot top - axle top 0.05..0.15; slot bottom gives 0.6..0.8 plunger travel |
| A11 | button-to-shell gaps | min distance button_L/R to top_shell (and to each other) at rest | 0.40 .. 0.60 (nose split ≥ 1.30) |
| A12 | buttons move freely | button rotated by the full stop (0.8 at the nub about HINGE_PIVOT) ∩ top_shell, PCB, other parts | volume 0 |
| A13 | wheel clearances | wheel ∩ top_shell, bottom_shell, PCB, yoke (rest and 0.30 dropped) | volume 0; min gap ≥ 0.3 to shells/board slot |
| A14 | wheel proud | wheel top Z - skin Z at (39.37,-27.9) | 2.5 .. 4.0 |
| A15 | wall thickness | sampled thickness of top/bottom shell walls and button panels | ≥ 1.6 (≥ 0.8 on ribs/webs) |
| A16 | top shell printable | top shell min Z = Z_PART (1.00) and its bottom face is one planar face set at Z 1.00 | exact |
| A17 | overhangs | faces with downward normal steeper than 45° from vertical in the stated print orientation, area outside supported zones | bottom shell: 0 except bridges ≤ 10 mm; others: only inside declared support zones |
| A18 | screws reachable | straight vertical tool path (Ø4.5) from below to each of the 3 TS screws; from above to each PCB screw (Ø4.5 cylinder up to Z 40, top shell removed) | no material in the path |
| A19 | screw engagement | insert hole Ø3.2 depth ≥ 4.0; PCB pilot depth ≥ 4.5; leaf screw pilot depth ≥ 5 | as listed |
| A20 | cable | channel width ≥ 4.0, floor Z -3.90; exit hole Ø ≥ 3.8 on the front face at X 46.5 | as listed |
| A21 | skates | recesses 0.35 deep, ≥ 1.5 from the underside edge, covering the 3 TS screw heads | as listed |
| A22 | side levers | lever rotated 5.2° about SIDE_PIVOT ∩ everything | volume 0; face stays inside the notch with ≥ 0.15 |
| A23 | assembly drop | top shell translated +Z 15 -> 0 sweeps no fixed part (levers, wheel, yoke, PCB) | no collision |
| A24 | ergonomics envelope | L x W x H above floor | 118-126 x 62-68 x 38-42 |
| A25 | bed-edge chamfer | 0.3 chamfer on bed edges that mate (bottom shell underside, top shell rim) | present |
