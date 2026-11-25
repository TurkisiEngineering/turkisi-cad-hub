# DIY gaming mouse shell for `mouse_pcb.step` (SolidCraft 0.49.1)

Input: `girdi/mouse_pcb.step`, SHA-256 `da66ded6…f974f439` (checked before starting).
Tool chain: SolidCraft 0.49.1 `solidcraft-cli` (headless, on the Contabo VPS), built from a
generated command script as the repo's `solidcraft-modeling` / `solidcraft-checking` skills describe
(numbers planned first, staged scripts, `run.py` report after every stage, `inspect.interference`,
every sketch at dof 0). Independent QA of the exported files with build123d + trimesh.

## Files

| File | What |
|---|---|
| `mouse_assembly.step` | STEP assembly, 9 named products (BottomShell, TopShell, ButtonL, ButtonR, DPIButton, SideBtnF, SideBtnR, Wheel, WheelPin), mouse frame |
| `mouse_assembly_with_pcb.step` | same + the input PCB placed where it sits in the mouse |
| `stl/01…08_*.stl` | one STL per printed part, **already in print orientation**, on z = 0 |
| `renders/` | iso, top, left (thumb side), front, back, exploded iso, centre section with PCB, x-ray top |
| `mouse_shell.sc` | the SolidCraft design (parametric timeline, PCB inserted) |
| `src/build_mouse.py` → `build_mouse.json` | generator and the 306-command SolidCraft script that rebuilds everything |
| `src/print_stl.json`, `export_step.json`, `exploded.json` | export scripts run on the design |
| `build_report.txt`, `qa_report.json` | SolidCraft build report, independent QA numbers |

## Frame and PCB placement
Table = z 0, +Y = front, origin = PCB centre in plan. PCB STEP → mouse: x = X − 39.37, y = Y + 45.59,
z = Z + 5.8. PCB underside at **5.8 mm**: PMW3360 lens reference plane 2.40 mm above the desk
(datasheet Z) + 3.40 mm lens stack to the PCB underside (my assumption, the lens is not in the STEP).
The floor has a lens seat pocket whose floor is exactly at z 2.40 and a 7 × 12 mm optical window
under the sensor centre (0, −10.93). If your lens differs, change `pcb_z` / `lens_ref` and rebuild.

Measured from the STEP (mouse frame): 6 × D2F plungers, tops z 13.39 — L (−19.05, 22.06),
R (19.05, 22.06), wheel click (11.43, 17.62), DPI behind the wheel (0.67, 2.41), thumb front
(−18.38, −5.21), thumb rear (−18.38, −22.99). EC10E rotor axis y 17.69, z 14.40, boss face x −7.39.
PCB wheel notch x ±6.35, y 6.22…30.86. M2 holes (±22.86, ±28.83). 4-pin USB header rear-left.

## Shape
120 × 64 × 37.6 mm, symmetric palm/claw shape, hump peak 37.6 mm at y ≈ −30 (≈ 62 % back from the
tip), low front (14 mm) so the wheel stands 3.5 mm proud of the buttons. Lofted through 12 superellipse
sections; wall 2.0 mm (cavity = matching loft, rear end pulled in so the taper keeps its thickness).

## Parts and mechanisms
- **Bottom shell** (floor 2.0, walls to the z 10 parting plane): 4 PCB standoffs with Ø1.6 pilots
  (M2 self-tapping from above), lens pocket + window, wheel pocket, wheel fork with snap neck,
  2 × 2 thumb-lever pivot posts, 2 alignment tabs rising 3 mm into the top shell (0.2 mm clear),
  3 top-shell screw columns (Ø2.4 clearance + Ø4.2 counterbore from below, under the skates),
  cable exit Ø3.8 at the front right (route the cable from the rear-left header behind the PCB and
  forward along the right wall, which is kept free for it).
- **Top shell**: rear 2/3 of the dome plus a spine behind the wheel; DPI window; 2 thumb-button
  windows open to the parting plane (so the shell drops straight on); 3 screw bosses (Ø1.6 pilot,
  M2 × 12 from below); 2 bosses carrying the main buttons' flex tongues.
- **Main buttons (L/R)**: separate caps split from the same skin, 0.5 mm gaps, Ø3 plunger posts
  0.15 mm above the D2F. Hinge = 0.9 × 7 × 5.6 mm flex tongue screwed (M2 × 5) under the top shell.
  The skirt's lower edge rises 1.9° toward the tip, so the gap to the bottom shell grows from 0.3 mm
  at the hinge to ~1.7 mm at the tip: it is also the **over-travel stop** (bottoms out after the
  click, protecting the D2F). Print in PETG for the flex.
- **DPI button**: cap in the spine window, retaining flange under the roof, post on the plunger.
- **Thumb buttons (2, left side)**: the switches lie flat on the PCB, so each button is a bell-crank:
  pad = the wall patch in the window, lever on a Ø1.75 mm filament pin (Ø1.85 holes) through two
  bottom-shell posts at (x −26.6, z 14.4); pushing the pad in turns the arm down onto the plunger
  (ratio ≈ 1.8). Rest stop = pad bottom edge 0.15 mm above the bottom-shell wall.
- **Wheel**: Ø23 × 7 mm, 30 grip grooves, Ø3 neck + 2.3 mm square key into the EC10E rotor on the
  left; Ø2 × 13.4 mm steel dowel pressed into the right face (Ø1.95 bore). The dowel runs through the
  fork slot (2.1 wide, snap neck 1.8) and rests on the wheel-click D2F, so pressing the wheel tilts it
  about the encoder and clicks the middle switch.

## Verification (final build)
- SolidCraft build: no failed step, no feature warning, every sketch dof 0 (`build_report.txt`).
- `inspect.interference` over all 78 bodies (9 parts + 69 PCB solids): only the intended Ø2 dowel
  press fit (0.6 mm³) and one overlap inside the input PCB file itself (encoder pins in the board).
- Independent QA on the exported files (`qa_report.json`, build123d + trimesh):
  - STEP: 9 named products (+ PCB in the context file); all 8 STLs watertight, on z 0.
  - Part-to-PCB gaps: L/R button posts 0.14, DPI post 0.04, thumb nubs 0.02, wheel pin on the click
    switch 0.01, wheel neck to encoder 0.17, standoffs seated on the board (0.0).
  - Part-to-part gaps: button ↔ wheel 1.79, wheel ↔ bottom shell 0.8, DPI cap ↔ window 0.25,
    thumb pads ↔ window 0.4, thumb pads ↔ bottom-shell stop 0.15, L ↔ R button 0.6
    (0.0 only where intended: tongue clamped to its boss, top shell resting on the bottom shell).
  - Wall thickness (ray sampling): median 1.8–2.0 mm; the steep rear taper of the top shell comes
    down to 1.15–1.25 mm measured normal to the wall (the lowest real values; sub-mm hits sit on cut
    edges and are ray artefacts). Button flex tongue 0.9 mm and wheel-pocket floor 1.2 mm by design.

## Bill of materials (besides the PCB)
M2 × 6 self-tapping × 4 (PCB), M2 × 12 × 3 (shells), M2 × 5 × 2 (button tongues), Ø2 × 13.4 mm steel
dowel × 1 (cut a Ø2 pin), Ø1.75 filament × 2 × 12 mm (thumb pivots), 0.8 mm PTFE skates (4 pads,
keep the screw heads under them), USB cable Ø ≤ 3.5 mm.

## Print settings (STLs are already oriented)
0.2 mm layers, 3 perimeters. Bottom shell: floor down, no support (small bridges at the counterbores
and pivot holes). Top shell and buttons: open side down, tree supports inside. Wheel: dowel face down,
key up, no support. Thumb buttons: as installed, support under the lever arm. DPI cap: face down
(turned 156.5° so its 23.5°-inclined face lies flat), brim recommended.
Buttons in PETG (flex hinge); shells PLA or PETG.

## Assumptions to check against the real parts
1. PMW3360 lens stack 3.40 mm (PCB underside 5.8 mm above the desk) and window size.
2. EC10E rotor key: 2.3 mm square assumed; match it to your encoder's shaft hole (`WheelKey`).
3. D2F and EC10E heights come from the placeholder bodies in the STEP (as GOREV says, estimates).
4. Thumb buttons are left-side (right-handed use), as the PCB places them.
