# WP_BRIEFS - parallel part work packages (WP-D .. WP-H)

Common rules for every package
- Read `DESIGN_SPEC.md` (this folder) first; the numbers there come from `master.py`.
- `import build123d` FIRST, then `import master as ML` (note: `from build123d import *` defines `M`, `MM`... so never alias master as `M`):
  ```python
  import sys; sys.path.insert(0, r"C:\Users\marya\Desktop\Mouse for PCB\work\02_master")
  from build123d import *
  import master as ML
  ```
- **Never edit master.py** and never redefine an interface number locally. If an interface is wrong or missing, write it in your result as an issue for the lead.
- Native PCB coordinates everywhere, no transforms. Floor Z = `ML.Z_FLOOR` (-5.85).
- Raw geometry comes from master (`ML.skin()`, `ML.inner()`, `ML.top_shell_raw()`, `ML.bottom_shell_raw()`, `ML.button_panel_raw(side)`; all cached, first call 10-70 s).
  OCC boolean trap: `ML.shell_wall() & X` can return None on this skin. Use `(ML.skin() & X) - ML.inner()` or subtract from the raw part. Always check `ML.check_part(...)` after each boolean (n_solids 1, valid, volume > 0).
- Fast probes: `ML.skin_z_at(x,y)`, `ML.inner_z_at(x,y)` (mesh rays, ±0.05), `ML.room_at(x,y,z)` (distance to the cavity wall), `ML.pcb_keepout(margin)`, `ML.pcb_clearances(shape)`, `ML.load_pcb()` (original STEP, for interference).
- Output: `ML.export_part(shape, "<part>")` -> `work/03_parts/<part>/<part>.step` + `.stl`. Write your builder as `work/03_parts/<part>/build_<part>.py` (re-runnable) and a `check_<part>.py` or a self-check block that prints the acceptance rows of DESIGN_SPEC §5 that concern your part.
- Progress render: one PNG per package into `work/renders/` with the prefix given in your task (pyvista: `C:\Users\marya\.venvs\cadgenbench\Scripts\python.exe`), part + PCB (`work/00_pcb/pcb.stl`). Send it to the user with SendUserFile (status proactive, one-line Turkish caption) if the tool is available.
- Clearance defaults: to PCB parts ≥ 1.0 for shells, ≥ 0.25 for moving parts; sliding 0.25; push fit 0.05-0.10; min wall 1.6 (ribs 0.8-1.2); overhang ≤ 45° in the stated print orientation; bridges ≤ 10.

---------------------------------------------------------------------------------------------------
## WP-D bottom_shell
Start: `B = ML.bottom_shell_raw()` (skin below Z 1.00, floor top Z -2.90, lip ring Z 1.0..2.5 with gaps at the side notches, wall tabs to Z 2.7 under the side faces).
Add (all from master constants):
1. **PCB bosses** at `PCB_HOLES`: Ø`PCB_BOSS_OD` 4.5, from the floor to `Z_BOSS_TOP` 0.0, pilot Ø`PCB_BOSS_PILOT` 1.6 down to Z -4.6 (blind). Note the front bosses sit 0.2 beyond the board front edge, fine.
2. **PCB support ribs** `PCB_RIBS` (top Z 0.0) under the main-button stop pads.
3. **TS screw columns** at `TS_SCREWS`: Ø`TS_BOTTOM_BOSS_OD` 6.0 from the floor to `Z_PART` 1.00; through hole Ø`TS_CLEAR_D` 2.4; counterbore Ø4.4 from the underside up to Z -3.25 (`TS_CBORE`). Front column (39.37,-10.8): keep the lip intact around it.
4. **Lens pocket** `LENS_POCKET` (19.6 x 22.2, R7, to Z -3.50) and **optical hole** `OPT_HOLE` (4.0 x 6.0 slot at Z -3.50, 45° flare down to the underside). No material may enter the 4.0 x 6.0 prism (A3).
5. **Wheel pocket** `WHEEL_POCKET` down to `Z_WHEEL_POCKET` -4.10.
6. **Yoke socket** `YOKE_SOCKET` 1.5 deep (`YOKE_SOCKET_DEPTH`), size = yoke + 0.05 per side (already in the numbers).
7. **Side-lever cradles**: per side button 2 C-cradles, length `SIDE_CRADLE_LEN` 3.0 centred at y0+1.8 and y1-1.8 (`SIDE_BTNS`), bore Ø`SIDE_CRADLE_ID` 2.30 on the axis (X 12.2, Z -1.6) along Y, wall 1.0, 270° wrap open to +Z (opening ±45° about +Z), merged into the floor/left wall. Cradle outer edge stays ≥ 0.6 from the board edge (A6 excludes nothing here).
8. **Cable channel** along `CABLE_PATH` (centre line), width `CABLE_W` 4.0, floor `Z_CABLE_FLOOR` -3.90 (trench into the floor plate; plate ≥ 1.15 under it with the skate recess). Exit hole Ø3.8 at `CABLE_EXIT` through the front wall along +Y, 0.8 chamfer outside. 3 strain-relief posts (Ø2.0, Z -3.9..-0.5) alternating ±1.2 in X from the channel centre at `CABLE_RELIEF_Y`. The channel passes 0.05-0.12 from the right PCB bosses: do not thin the bosses, trim the channel side instead.
9. **Skate recesses** `SKATES` (pocket outlines), 0.35 deep from the underside.
10. 0.3 x 45° chamfer on the underside outer edge (elephant foot) and on the optical-hole bed edge.
Print: underside on the bed, no supports. Dark opaque PLA/PETG.
Self-checks: one valid solid; A2-A5, A6 (≥ 1.0 to every component except the boss/rib contact faces and lead tips ≥ 0.99), A18-A21; no material above Z 2.7; lip outer face 0.15 inside the top-shell wall (`ML.inner_offset(ML.WALL+ML.LIP_GAP)`).
Outputs: `03_parts/bottom_shell/bottom_shell.step/.stl`, `build_bottom_shell.py`, render `R<nn>_bottom_shell.png`.

---------------------------------------------------------------------------------------------------
## WP-E top_shell
Start: `T = ML.top_shell_raw()` (wall above Z 1.00 minus both button regions (+0.25), wheel window `WHEEL_WIN`, DPI window `DPI_WIN`, side notches open to the rim).
Add:
1. **3 insert bosses** at `TS_SCREWS`: Ø`TS_BOSS_OD` 6.0 from Z 1.00 up into the ceiling, insert hole Ø3.2 x 4.0 from the bottom face (`TS_INSERT_HOLE`). Front boss: web it to the front band/tongue. Bottom faces exactly at Z 1.00.
2. **Leaf clamp pads** L/R: footprint X `LEAF_X_L` / `LEAF_X_R` (+1.0 each side) x Y `LEAF_CLAMP_Y`, from the ceiling down to `LEAF_Z_TOP` 20.0 (flat face). Pilot Ø1.6 ≥ 5 deep at `LEAF_SCREW_L/R`; 2 locating pins Ø`LEAF_PIN_D` 1.5 x 1.0 at screw X ± `LEAF_PIN_DX`. Gusset the pads to the ceiling at 45°.
3. **Rail webs** under the tongue along both long sides of the wheel window: X 33.87..35.32 and 43.42..44.87, Y = window Y range, from the tongue underside down to `RAIL_WEB_Z` 12.5.
4. **DPI guide sleeve** around `DPI_CAP` + `DPI_GUIDE_CLR` 0.15, wall 1.0, from the tongue underside down to `DPI_GUIDE_Z` 13.5. Keep ≥ 0.5 from the wheel (wheel rear at Y -38.5 at Z 13).
5. Optional light ribs (0.8-1.0) inside the hump; keep 1.0 from all PCB parts and 0.5 from every moving-part envelope (buttons rotate about `HINGE_PIVOT` by 0.02 rad, levers about `SIDE_PIVOT` by 0.093 rad, wheel drops 0.30).
6. 0.3 chamfer on the rim bed edge; 0.3 chamfer on the notch and window outer edges.
Nothing below Z 1.00 (prints rim-down). Supports: tree, inside only.
Self-checks: one valid solid; A11 (with WP-F parts if present, else vs `ML.button_panel_raw`), A15, A16, A18 (insert holes open from below), A23 (drop over the PCB + `ML.bottom_shell_raw()`), clearance ≥ 1.0 to PCB components.
Outputs: `03_parts/top_shell/top_shell.step/.stl`, builder, render.

---------------------------------------------------------------------------------------------------
## WP-F main buttons L + R (PETG)
Start: `P = ML.button_panel_raw("L")` / `("R")` (skin wall inside the button region, gaps 0.25 to the split centre lines, nose split at Z 6.70).
Add per button:
1. **Nub**: stem ≥ 2.5 x 2.5 from the panel underside, pad `NUB_PAD` 3.5 (X) x 2.5 (Y) centred on `SW_MAIN_L/R`, contact face at `NUB_Z` 7.695 (flat, edges R0.3). Gusset the stem to the panel.
2. **Stop post** footprint `STOP_PAD_L/R` (`STOP_POST_XY` 1.7 x 3.0), bottom at `STOP_POST_Z` 2.31 (lands on the board at rest + 0.80).
3. **Web + leaf**: web across `LEAF_X_L/R` at `LEAF_WEB_Y` (Y -59.4..-57.8) from the panel underside down to the leaf; leaf X `LEAF_X_*`, Z `LEAF_Z_TOP - LEAF_T` .. `LEAF_Z_TOP` (19.0..20.0), Y from -57.8 to `LEAF_CLAMP_Y[0]` -73.4; free part `LEAF_FREE_Y` must stay plain (no ribs). Clamp zone: hole Ø2.4 at `LEAF_SCREW_*`, holes Ø1.7 at ± `LEAF_PIN_DX`.
4. Optional: thin stiffening ribs (0.8) under the panel, ≥ 1.0 from the encoder top (Z 12.595) and every PCB part also after the 0.8 press.
Print: face up, tree supports under the panel, 0.16 layers; leaf flat in XY.
Self-checks: one valid solid each; A7, A9, A11, A12 (rotate about `HINGE_PIVOT` axis along X by atan(0.8/39.87) and check no contact except nub-plunger and stop-board), tip travel ≤ 1.3 < `BTN_FRONT_GAP`, leaf strain ≤ 1 %.
Outputs: `03_parts/button_L/...`, `03_parts/button_R/...`, builder, render.

---------------------------------------------------------------------------------------------------
## WP-G scroll wheel + axle + yoke (+ tyre)
Parts: `wheel` (one piece with the axle, PLA/PETG), `wheel_yoke` (PETG), optional `wheel_tyre` (TPU 95A).
1. **Wheel** Ø`WHEEL_D` 23.6 overall (incl. tyre `WHEEL_TYRE_T` 1.5 or an O-ring groove), width `WHEEL_W` 7.5 at `WHEEL_X` (35.62..43.12), axis `WHEEL_C`. Grip: tyre grooves/knurl on the TPU, or 24 shallow ribs if no tyre.
2. **Axle** Ø`AXLE_D` 2.0 along X over `AXLE_X` (30.10..52.30), hex `AXLE_HEX_AF` 1.70 A/F over `AXLE_HEX_X` (30.10..32.00) into the EC10E (hub face X 31.98); round Ø2.0 elsewhere; optional shoulder Ø3.0 x 0.5 at X 32.2 (axial stop on the hub face, 0.2 gap). The far end (X 49.35..52.30) rests on the middle plunger (axle bottom Z 7.595). Recommend a Ø2.0 steel pin pressed through the wheel as an alternative (state both in the README).
3. **Yoke**: plate X `YOKE_X`, Y `YOKE_Y`, from the socket bottom (Z -2.90 - 1.5) up to `YOKE_TOP_Z` 11.5; vertical axle slot width `YOKE_SLOT_W` 2.25 centred on Y -27.9, top `YOKE_SLOT_TOP` 9.695, bottom `YOKE_SLOT_BOTTOM` 7.111; closed slot, threaded onto the axle end before the yoke is pushed into `YOKE_SOCKET`. Push fit 0.05 in the socket.
4. Keep the wheel ≥ 0.3 from the board slot edges, the yoke, the tongue rails (X 35.32 / 43.42 at Z ≥ 12.5) and the wheel window; ≥ 0.5 from the DPI switch body (0.75 nominal) and the bottom-shell pocket (Z -4.10) also when dropped 0.30.
Print: wheel axis vertical, 0.12 layers, hex end up; yoke flat; tyre axis vertical, 20-30 mm/s.
Self-checks: one valid solid each; A10, A13, A14; hex A/F measured; middle-click travel at the plunger = 0.70 ± 0.1 from the yoke slot.
Outputs: `03_parts/wheel/`, `03_parts/wheel_yoke/` (+ `wheel_tyre/`), builder, render.

---------------------------------------------------------------------------------------------------
## WP-H small buttons: DPI + 2 side buttons
Parts: `dpi_button`, `side_btn_fwd`, `side_btn_back`.
1. **DPI cap**: plan `DPI_CAP` (6.0 x 5.0), top = skin surface (use `ML.skin() & prism(DPI_CAP)` for the top face, lowered 0.0), body straight down through the window and the sleeve (0.15 clearance) to a flange `DPI_FLANGE` (1.0 wider per side, 1.0 thick, top at `DPI_GUIDE_Z` - 0.15 = 13.35); nub stem ≥ 2.5 x 2.5 down to a pad `DPI_NUB_PAD` 2.5 (X) x 3.5 (Y) centred on `SW_DPI`, face at `PLUNGER_TOP_Z` + 0.0 (rests on the plunger). Insert from below before the top shell is closed.
2. **Side levers** (one per `SIDE_BTNS` entry, PETG):
   - face plate = left skin patch inside `ML.side_face_profile(name)` moved -X by `SIDE_PROUD` 1.0 (1.0 proud), 1.8 + 1.0 thick, 0.30 gap to the notch (`SIDE_GAP`), flange 0.8 wide x 0.8 behind the notch rim (inside the cavity, X ≥ cavity wall + 0.2) as the outward stop;
   - body plate inside the wall at X ≥ `SIDE_BODY_X0` 12.3, from the face down to the pivot;
   - pivot pin Ø`SIDE_PIN_D` 2.0 along Y at `SIDE_PIVOT` (12.2, -1.6), two pin stubs of `SIDE_CRADLE_LEN` + 0.3 at the cradle positions (y0+1.8, y1-1.8), snaps into the bottom-shell C-cradles;
   - arm over the board, underside ≥ `SIDE_ARM_Z_MIN` 8.4, width 4 centred on the plunger Y; nub pad `SIDE_NUB_PAD` 3.5 (X) x 2.5 (Y) centred at plunger X + `SIDE_NUB_DX` (-0.4), face at `NUB_Z` 7.695;
   - stop face on the body plate facing +X at Z 0.2..1.3, `SIDE_STOP_GAP` 0.22 from the board edge X 14.478 (Y range away from the rear-left boss Y -76.67..-72.17);
   - stay ≥ 0.6 from the lip (X ≤ 12.4 at Z 1.0..2.5 outside the notch Y range), ≥ 0.25 from the USB header (Y ≥ -73.4, pins to Z 10.135) and the side-switch bodies (top Z 6.595) over the full 5.2° rotation.
Print: DPI cap top face down on the bed; levers lying on the flat side of the face plate (pin axis parallel to the bed), 0.12 layers.
Self-checks: one valid solid each; A8, A22, lever rotated 5.2° about the pin axis: nub travel 0.8 ± 0.05 at the stop, no other contact; DPI cap free in the sleeve (0.15) and window (0.30).
Outputs: `03_parts/dpi_button/`, `03_parts/side_btn_fwd/`, `03_parts/side_btn_back/`, builder, render.
