# REVIEW_RV01: DIY gaming mouse shell, all 9 parts (WP-D..WP-H), lead engineer review

**VERDICT: REVISE**: 9 BLOCKER, 2 MAJOR, 9 MINOR. Most of the geometry is sound. 17 of the 25 §5 rows pass on my own measurements. The failures are:
- the wheel jams on the right rail web during the middle click,
- the side-nub pad is shorter than the plunger, and the side-lever stop over-travels,
- printability misses on 4 parts,
- knife edges on the top shell,
- a counterbore/tool-path conflict in the spec.

Date 2026-11-26. Reviewer: lead engineer, working independently. Nothing below is copied from the builders' REPORT numbers.

## 0. Method (re-runnable, all in `work/05_review/`)
| script | what |
|---|---|
| `rv01_step.py <part>` | imports the delivered STEP: n_solids, is_valid, volume; **exact BRep boolean** against every bbox-overlapping solid of the original `mouse_pcb.step` (A5); top-shell downward planar faces (A16); fine re-tessellation (0.01) to `mesh/` |
| `rv01_checks.py <group>` | mesh measurements of every §5 row (vectorised vertical/normal ray casts, KD prefilter + exact point-triangle distance, parity containment), poses (button press, wheel drop/up/tilt, lever 5.2°/stop, DPI press/lift), assembly drop sweep, print-orientation overhang regions, thin features. JSON per group: `rv01_<group>.json`, logs `rv01_<group>.log` |
| `rv01_levers.py` | side-lever travel measured on the rotated mesh in fixed coordinates; button nose split |
| `rv01_extra.py` | **exact BRep** lip gap at the 12 tightest mesh points; skate edge distance and underside chamfer in world XY |

Meshes: the finest tessellation of each delivered STEP (mine at 0.01, or WP-E's and WP-F's 0.005/0.01 STLs where those are finer). My bottom-shell mesh is within 0.045 of its BRep. Every gap within 0.05 of a limit was confirmed exactly (LIP).
§6 assumptions ledger: DESIGN_SPEC has no §6, and there is no GATE_LIBRARY or VERDICT_TEMPLATE in this project. No gate rests on a ledger assumption. Assumptions I made are marked `(assumed)` below.

## 1. §5 acceptance table: measured vs limit
| # | measured (RV01, independent) | limit | result | sev |
|---|---|---|---|---|
| A1 | all 10 STEPs (9 parts + wheel_body): 1 solid, valid. Volumes: bottom 20493.5, top 19615.1, btn_L 2674.8, btn_R 2655.8, wheel 3202.1 (body 3151.2), yoke 145.2, dpi 379.6, side_fwd 618.5, side_back 573.7 mm³. All meshes watertight | n=1 valid | PASS | - |
| A2 | underside Z -5.400, so floor -5.850 | -5.85 ±0.05 | PASS | - |
| A3 | 0.0000 mm³ of material in 4.0x6.0 prism Z -5.5..0 (0.1 grid) | 0 | PASS | - |
| A4 | 0.0000 mm³ in 19.6x22.2 R7 Z -3.50..0; pocket floor -3.500 | 0 | PASS | - |
| A5 | exact boolean, all parts x PCB solids: max 0.00000 mm³ (69/69 solids tested for each shell) | 0 | PASS | - |
| A6 | shells: top shell ≥2.33 (encoder) / board 3.09; bottom shell to components 0.995 (lead tips, design 0.99), header 1.25, sensor 2.10. Moving parts (designed contacts excluded): btn L/R 0.52, wheel 0.376 (middle D2F, rest), DPI 0.319, levers 0.206 at rest (pad bevel corner next to its own plunger) | ≥1.0 / ≥0.25 | PASS | MINOR note F-17 |
| A7 | nub face gap 0.100 over the whole plunger box, L and R | 0.05..0.30 | PASS | - |
| A8 | DPI 0.000 over the whole box. **Side fwd/back: 0.100 under the pad, but the pad is 2.5 long in Y against a 2.9 plunger. The 0.2 at each plunger end is uncovered (arm at Z 8.4, so 0.805)** | 0..0.30 over the box | **FAIL** | BLOCKER F-2 |
| A9 | stop post bottom - 1.51 = 0.800 (L, R) | 0.75..0.90 | PASS | - |
| A10 | axle bottom 0.0005 over the plunger; slot top - axle top 0.100; slot-bottom stop 1.94° gives 0.670 at the plunger | 0..0.10 / 0.05..0.15 / 0.6..0.8 | PASS | - |
| A11 | btn L/R to top shell 0.500 (0 inside), clamp zone excluded; nose split 1.400 (vertical, Y -4.5..-5); L to R > 5 | 0.40..0.60, nose ≥1.30 | PASS | - |
| A12 | rotated -0.02006 rad about HINGE_PIVOT: top shell 0.212 / 0 inside; tip drops 1.188. PCB, excluding designed contacts: switch ≥0.40, board 0.028 = stop post landing (designed). Others: bottom 1.48, wheel 2.25, yoke 2.49, dpi 2.33 | volume 0 | PASS | - |
| A13 | rest: top 0.300 (rail), bottom 0.784, board 1.68. Dropped 0.30: top 0.300, bottom 0.502, board 1.53. Up 0.10: 0.300. **Tilted to the middle-click stop (1.94° about X 31.0): 175 wheel samples inside the right rail web X 43.42, gap 0.000**; bottom 0.449 | 0 vol, ≥0.3 | **FAIL** | BLOCKER F-1 |
| A14 | wheel top 20.395 - skin 17.254 = 3.141 | 2.5..4.0 | PASS | - |
| A15 | bottom shell walls: median 1.799, p1 1.673 (19 edge/chamfer samples). Buttons: median 1.80; the outliers are ≥57° corners at the split lines. **Top shell: 920 of 42.7k skin samples (2.2 %) under 1.6, min 0.001, p1 0.86. These are feather edges (~40° wedge) along both outer button splits (X 12.3-13.8 and 64.8-66.3, Y -60..-7) plus the moved wheel-window front edge** | ≥1.6 | **FAIL (top shell)** | BLOCKER F-8 |
| A16 | top shell min Z 1.0000; lowest downward planes are all at Z 1.000 (5 faces, 512 mm²) | exact | PASS | - |
| A17 | bottom: **rear skate ceiling bridge 36.0x11.0 (span 11.0)**; ring 4.0, front 6.4, cbores 4.4, exit hole 2.8; lip staircase 45°. Top: **2 notch tops, flat downward faces 13.0 long x 2.3 at Z 10.3 on the outside**; inside: ceiling, pads, rails, sleeve. Buttons: under the panel (declared). Wheel: 2.0 bridge. Yoke: 0. **dpi: 26 mm² flange ledge (supports "none")**. **Levers: bed contact 0.0 mm², 97 mm² overhang under the visible thumb face** | per §4.8 | **FAIL** | BLOCKER F-4, F-5, F-6, F-7 |
| A18 | from below: **material in the Ø4.5 path = 1.052 mm³ per TS screw (cbore Ø4.399)**; Ø4.4 path 0. PCB screws from above: 0 mm³ from the bottom shell, wheel, yoke, levers; nearest PCB part 2.41 from the axis (head Ø3.5 OK) | 0 in Ø4.5 | **FAIL (spec conflict)** | BLOCKER F-9 |
| A19 | PCB pilots Ø1.6 x 4.6, boss tops 0.000; TS through Ø2.4, cbore Ø4.4 to Z -3.25; inserts Ø3.2 x 4.0 (x3); leaf pilots Ø1.6 x 6.0; pin tips Z 19.0 | ≥4.5 / 3.2x4.0 / ≥5 | PASS | - |
| A20 | width 4.0 (p5 4.0); narrowings to 2.23 only at the 3 relief posts (designed); floor -3.90 except the exit dip -4.05 (Y -9..-4); exit Ø3.799 (mesh chord) at X 46.5, rays clear along +Y; front face Y -4.000 | ≥4.0 / -3.90 / ≥3.8 | PASS | MINOR F-18 |
| A21 | recess ceiling -5.05, so depth 0.350; outlines 31x6.4, 36x11, ring 22/14; edge distance front 3.30, ring 20.3, rear 11.7; all 3 cbore rings lie inside recesses | 0.35, ≥1.5, covered | PASS | - |
| A22 | levers at rest, 5.2° and the stop (5.48°): 0 interference with top shell, bottom shell, button_L, wheel; face to notch 0.174 (5.2°) / 0.170 (stop); pins in cradles 0.150 radial | 0 vol, ≥0.15 | PASS | (travel: F-3) |
| A23 | top shell + pre-mounted buttons + DPI cap dropped from +15 over the PCB, bottom shell, wheel, yoke and both levers: 0 collisions (both sweep directions) | none | PASS | - |
| A24 | 120.00 x 63.50 x 39.93 | 118-126 x 62-68 x 38-42 | PASS | - |
| A25 | bottom underside outline inset 0.344 (Z -5.39 vs -4.9); top rim inset 0.146 net of wall lean (WP-E 0.28 to skin): present on both | present | PASS | - |
| LIP | exact BRep 0.147..0.153 at the 12 tightest points (mesh said 0.099, a tessellation artifact) | 0.15 | PASS | - |
| ZMAX | bottom shell max Z 2.700 | ≤2.7 | PASS | - |

## 2. Findings and designer instructions
| ID | owner | sev | finding (measured) | fix |
|---|---|---|---|---|
| F-1 | WP-E (+MASTER WHEEL_WIN) | BLOCKER | A13: on a middle click the wheel tilts 1.94° about X 31.0. The wheel top sways +0.31 in X into the right rail web at X 43.42 (175 samples inside, gap 0). The middle click rubs or jams. | Move the right rail web inner face and the wheel-window right edge to X ≥ 43.75 (= 43.12 + 0.31 sway + 0.30). Set WHEEL_WIN x1 = 43.75 in master and rebuild the rail web X 43.75..45.20. Re-measure A13 at rest, dropped 0.30 and tilted to the slot stop. |
| F-2 | MASTER (+WP-H rebuild) | BLOCKER | A8: SIDE_NUB_PAD = 3.5 X x 2.5 Y was not rotated for the X-running side D2F (plunger 1.2 X x 2.9 Y). The pad covers Y ±1.25 of a ±1.45 plunger, so no Y position tolerance is left (rule: cover the plunger ±0.5). | Set SIDE_NUB_PAD = (3.5 X, 3.5 Y) in master (as was done for DPI_NUB_PAD). WP-H rebuilds both levers and re-checks the pad-to-switch-body clearance over the full swing (≥0.25). |
| F-3 | WP-H | BLOCKER | Lever stop travel, measured as the deepest pad point over the plunger box on the rotated mesh: 0.816 at 5.2°, **0.858 at the board-edge stop (5.48°)**, i.e. plunger depression 0.758, which exceeds PT 0.5 + OT-min 0.25. The limit is 0.80 ±0.05. WP-H's issue note ("5.2° gives only 0.762") is wrong. | Put the stop face so it lands at ~5.2°: rest stop gap 0.22 → ~0.205 at Z 0.75. Target total nub drop 0.80-0.82 at the stop, measured in fixed coordinates over the plunger box. |
| F-4 | MASTER | BLOCKER | A17 bottom shell: the rear skate recess ceiling is an 11.0 mm bridge, against a 10 mm limit. | Change SKATES rear to 36.0 x 10.0 R4. It still covers both Ø4.4 counterbores at Y -98 with ≥2.8 margin. Skate = pocket - 0.2. WP-D re-exports. |
| F-5 | MASTER + WP-E (+WP-H face top) | BLOCKER | A17 top shell: each side-notch top is a downward face 13.0 long (9 flat + R2.8 arcs) x 2.3 deep at Z 10.3. It is on the outside, where no support zone is allowed, and it is a bridge longer than 10. There is also a 0.46 mm² overhang at 53° on a notch chamfer. | Make the notch tops self-supporting: a 45° gable or 45° corner chamfers so the flat span is ≤ 8. Change the face-plate top in `side_face_profile` to match. Alternatively, record a lead waiver for a 13 mm PLA bridge. RV01 does not grant one. |
| F-6 | WP-H | BLOCKER | A17 dpi_button: the flange ledge is 26 mm² of downward overhang in the declared print orientation (cap down, tilted 153.5°), and §4.8 allows no supports. | Turn the flange's up-stop face into a 45° cone, with a matching 45° chamfer at the sleeve bottom (WP-E). The up-stop stays 0.15. Or change the print orientation and update §4.8. |
| F-7 | WP-H | BLOCKER | A17 / printability, side levers: the print STL stands on the concave thumb face. Bed contact is 0.0 mm² (edges only). There is 97 mm² of overhang under the visible face plus 27 mm² under the flange, and the parts print as an unsupported rocking shape. | Re-orient: stand the lever on its flat Y-end face (all features are prismatic along Y). Then either print the pin stubs and accept them axis-vertical, or use a pressed Ø2 steel pin through a Ø2.0 bore, as for the wheel. Or add a flat print land of ≥30 mm² opposite the face. Re-run the overhang and bed-contact checks. |
| F-8 | MASTER (+WP-E apply) | BLOCKER | A15 top shell: the vertical button-split prisms cut the inward-leaning side wall at ~40°. This leaves a feather edge along both outer splits (wall < 1.6 over a 0.6-1.3 mm band, min 0.001, 2.2 % of skin samples). The same happens at the moved wheel-window front edge. These are visible, fragile slivers. | Cut the split faces normal to the skin, or give the strip top a ≥1.0 flat land or an R0.5 round so the wedge is ≥ 70°. Re-run A15 with the edge band included. |
| F-9 | MASTER | BLOCKER | A18: TS_CBORE Ø4.4 against an A18 tool path of Ø4.5. Measured 1.052 mm³ in the Ø4.5 path and 0 in Ø4.4. The spec contradicts itself. | Lead decision: set TS_CBORE = (4.6, -3.25). The head seat still sits under the skate recesses and the rear skate covers 4.6 with F-4. WP-D re-exports. (Alternative: amend A18 to Ø4.2 = head 3.8 + 0.2.) |
| F-10 | MASTER (+WP-D) | MAJOR | YOKE_SOCKET is 0.15 per side in X (socket 43.95..45.45 against yoke 44.10..45.30). Y is 0.05 (socket -32.05..-23.75 against -32.00..-23.80). The spec asks for a 0.05 push fit, so the yoke can rock. | YOKE_SOCKET = (44.05, -32.05, 45.35, -23.75). WP-D re-cuts. |
| F-11 | WP-E | MAJOR | Rail webs (bottom Z 12.5, 1.45 x 20.3) and the DPI sleeve start mid-air at Z 12.5/13.5 inside the shell. They need tree supports in zones that §4.8 does not list (it lists ceiling, pads, sleeve). | Taper the rail-web undersides at 45° toward the tongue, or have the lead add "rail webs" to the §4.8 support zones (MASTER doc). |
| F-12 | MASTER | MINOR | Local floor plate under 1.2 (6 layers): PCB pilot bottoms 0.8, yoke socket floor 1.0, cable trench over the front skate 1.15, wheel pocket 1.3 (CONSTRAINTS says 1.5). Lens pocket over the ring skate 1.55. | Accept, or deepen the bosses from below (pilot blind 0.8 → 1.2). Raise Z_WHEEL_POCKET to -3.9 if A13 still keeps 0.3 after the WP-D reliefs. |
| F-13 | WP-F | MINOR | Button print STL: bed contact is only the stop post (5.1 mm²). The rest hangs on tree supports, the post bottom is a precision stop face (A9) printed against the bed, and elephant-foot lands there. | Add a sacrificial brim/raft note to the print card, or chamfer the post foot 0.2 and add 0.05 in Z. Keep the orientation. |
| F-14 | WP-H | MINOR | Lever outward-stop flange is exactly 0.8 thick (thin-feature limit). Its rest gap to the final top shell is 0.128 (fwd) / 0.164 (back), against the 0.15 design value. The thumb-face bottom edge (Z 3.0-3.3) is feathered under 0.8. | Make the flange 1.0 thick; add a 0.3 flat on the face-plate bottom edge. |
| F-15 | WP-D | MINOR | The right lip inner face leans about 56° from vertical over its top 0.5 (25 mm², X 67.7-68.4, Y -89..-16). This is a small bottom-shell overhang. | Add a 45° chamfer on the lip's top inner edge. |
| F-16 | MASTER | MINOR | `export_part` writes STLs at 0.02 / 0.15 rad, which on the skin B-splines gives 0.05-0.2 facet error. bottom_shell.stl and bottom_shell_print.stl are at that tolerance, and `out/bottom_shell_raw.stl` is stale (no right lip). | Use 0.005-0.01 / 0.05 rad in export_part and refresh `out/*.stl`. |
| F-17 | WP-D | MINOR | Cable relief-post tops (Z -0.5) are 0.53 below the board's right edge. That is consistent with §4.6 (cable top Z -0.4 under the board corner), but under the 1.0 shell rule if the board counts. | Accept, (assumed) board ≠ component. Optionally lower the post tops to -0.9. |
| F-18 | WP-D | MINOR | The exit hole bottom dips to -4.05 for Y -9..-4 (channel floor -3.90). A horizontal Ø3.8 hole is used where CONSTRAINTS asks for a teardrop/flat top. | Accept the dip; give the exit hole a teardrop top for print. |
| F-19 | WP-H / WP-F | MINOR | Report hygiene: WP-H volumes 622.9/577.9 do not match the STEPs (618.5/573.7). WP-H checked against stale master envelopes; RV01 re-ran A22/A23 on the final WP-D/WP-E parts and they pass. | Report volumes from the delivered STEP. |
| F-20 | MASTER | MINOR | Main buttons are 19.6 wide each (X 13.76..33.37), against the CONSTRAINTS ergonomic 25-28. This is because of the side strips and the 11.0 tongue. | Note for the client brief. No change unless the client asks. |

Verified and closed (no action): WP-E's WHEEL_WIN y1 = -16.5 leaves the band at ≥0.30 from the wheel. WP-D's wheel-pocket reliefs give 0.502 dropped. The DPI cap is flush (-0.009..-0.002), sleeve 0.150, window 0.300, pressed 0.75 still 0.359 to the wheel, and the up-stop contacts after a 0.14-0.15 lift. The hex section is 1.700 A/F (corners 1.963). The leaf is 1.0 thick over 8.0 free length with nothing in the free zone. Strain is 0.13 % (PETG limit 1 %).

## 3. Printability summary (from each `*_print.stl`)
| part | bed contact mm² | overhang >45° outside declared zones | bridges >10 | thin <0.8 | verdict |
|---|---|---|---|---|---|
| bottom_shell | 6249 | lip top inner 25 mm² (F-15) | **rear skate 11.0 (F-4)** | none (edges only) | FAIL |
| top_shell | 512 | **notch tops (F-5)**, 0.46 chamfer | **notch tops 13.0** | feather edges (F-8) | FAIL |
| button_L / R | 5.1 | none (panel, leaf on declared tree supports) | - | corners only | PASS, MINOR F-13 |
| wheel_body | 356 | 0 (2.0 pin-bore bridge) | - | groove lips only | PASS |
| wheel_yoke | 119 | 0 | - | min 1.2 | PASS |
| dpi_button | 33.5 | **26 mm² flange (F-6)** | - | cap edge only | FAIL |
| side_btn_fwd / back | **0.0** | **97 + 27 mm² (F-7)** | - | flange 0.8, face edge (F-14) | FAIL |
Flexure leaf: PETG, 16 x 1.0, prints flat with layers along the leaf; strain 0.13 %. OK.

## 4. Function sanity
- Click feel: main nubs rest at 0.100 and stop at 0.800. Middle click: 0 gap and 0.670 travel. **Middle click is blocked by the rail web (F-1).** DPI rests on the plunger at 0.000. Side levers: 0.100 at rest, **0.858 at the stop (F-3)**, pad shorter than the plunger (F-2).
- Wheel: 3.14 proud of the button surface (typical 3-5).
- Sensor aperture: 0 material in the optical prism (A3) and the lens pocket (A4). No other part comes below the board at the sensor.
- Cable: channel 4.0 wide on floor -3.90, exit Ø3.8 at X 46.5 through the front face, ray-clear.
- Screws: 4 PCB screws reachable from above (0 material, PCB parts ≥2.41 from the axis). 3 TS screws reachable from below with a Ø4.4 tool (A18 conflict F-9). All TS heads sit under skates.
- Ergonomics: 120.0 x 63.5 x 39.9, thumb groove left 2.6 deep, button length 56 from the tip, side buttons 14 long at 47/65 from the tip. Buttons are narrow (F-20).

## 5. GATE_LIBRARY §P plausibility checklist (written answers)
1. Gravity: YES. The DPI cap rests on its plunger and hangs on its flange when lifted. The wheel axle is held from above by the yoke slot top (0.10). The levers sit in 270° cradles. Nothing relies on glue or friction to stay in place.
2. Function-chain adjacency: YES, except F-1. finger → panel → nub → plunger → stop post on the board; thumb → face → lever → nub → plunger, with the stop on the board edge; wheel → hex → EC10E, and axle end → middle D2F → yoke stop. The middle-click chain is interrupted by the rail web (BLOCKER).
3. Orientation: YES. +Y front, thumb groove and side buttons on the left (right-handed), sensor on the centreline, cable out of the front face.
4. Human factors: YES. Forces about 1.15 N (main) and 1.6 N (side), travel within D2F PT/OT except F-3, 1.40 nose gap, 0.5 split gaps. Narrow buttons are noted (F-20).
5. Consumer reference: YES. 120 x 63.5 x 40 matches the Zowie EC2 (120 x 64 x 40) and the G Pro (125 x 63.5 x 40).
No §P answer is NO. The REVISE comes from the numerical and printability BLOCKERs.

## 6. Re-review scope (RV02)
After the MASTER constant changes (F-1 WHEEL_WIN/rails, F-2 SIDE_NUB_PAD, F-4 SKATES rear, F-5 notch top profile, F-8 split cut, F-9 TS_CBORE, F-10 YOKE_SOCKET), WP-D, WP-E and WP-H rebuild. WP-F and WP-G need no geometry change. Re-run `rv01_step.py` for every part, then `rv01_checks.py` (all groups), `rv01_levers.py` and `rv01_extra.py`. All §5 rows are gated again.

Note: SendUserFile is not available in this reviewer session, so no PNG was sent. The renders I viewed (R02_*) are correctly framed. None is clipped.
