# PCB_DATA (WP-A) - mouse_pcb.step mechanical interface

Native STEP coordinates, mm. +X right, +Y FRONT, +Z up (component side). SHA-256 checked: da66ded6...f439.
Full numbers in `PCB_DATA.json` (it also holds a 1 mm keep-out grid). Re-run: `python pcb_intake.py`, then `python render_pcb.py`, then `<cadgenbench venv>\python render_pcb_iso.py`.
Mesh for renders: `pcb.stl` (board + all parts), `mesh/<group>.stl` (board, switch, encoder, sensor, usb_header, smd).

## 1. Board
- Bbox X 14.478..64.262, Y -76.454..-14.732 (49.784 x 61.722). **Thickness 1.51** (the brief says 1.6). Bottom Z 0, top Z 1.51; parts sit at Z 1.595 (copper and solder mask are not modelled).
- Outline: a rectangle with 0.508 x 45° corner chamfers, plus a **front notch for the scroll wheel**: X 33.02..45.72 (12.7 wide), open at the front edge, back edge at Y -39.37 (1.27 chamfers at the back corners, 0.508 at the mouth). The polygon is in the JSON (`board.outline_ccw`), area 2558 mm².
- **Sensor aperture** (closed cutout): X 35.07..43.67, Y -65.88..-48.62 (8.6 x 17.26).

## 2. Mounting holes: 4 x Ø2.2 (M2 clearance), screw axis along Z
| | X | Y |
|---|---|---|
| front-left | 16.510 | -16.764 |
| front-right | 62.230 | -16.764 |
| rear-left | 16.510 | -74.422 |
| rear-right | 62.230 | -74.422 |
Pitch 45.72 (X) x 57.658 (Y). No pad ring is modelled. Plan a boss face of Ø4.5 or less.
Other holes are THT only: switch leads Ø1.2, EC10E legs as Ø1.8 slots 2.05 long at (28.355, -32.4 / -23.4), EC10E pins as 0.7 x 1.0 slots, header Ø1.0, sensor Ø0.7, and one Ø1.0 at (51.31, -48.39).

## 3. D2F switches (placeholders)
Every switch is modelled the same way: a 12.8 x 5.8 body, Z 1.595..6.595 (5.0 tall), with a **plunger 2.9 x 1.2 x 1.0** on top (top Z **7.595**). The plunger is modelled as a fixed block, so there is no travel. The leads (0.5 x 0.8) go down to Z -1.905.
| role | origin | body box X / Y | body runs | actuator top XYZ |
|---|---|---|---|---|
| main LEFT | 20.32, -20.32 | 17.42..23.22 / -31.80..-19.00 | Y (rearward) | 20.32, -23.53, 7.595 |
| main RIGHT | 58.42, -20.32 | 55.52..61.32 / -31.80..-19.00 | Y (rearward) | 58.42, -23.53, 7.595 |
| MIDDLE (wheel press) | 50.80, -24.765 | 47.90..53.70 / -36.245..-23.445 | Y (rearward) | 50.80, -27.975, 7.595 |
| DPI | 36.83, -43.18 | 35.51..48.31 / -46.08..-40.28 | X (inboard) | 40.04, -43.18, 7.595 |
| SIDE forward | 17.78, -50.80 | 16.46..29.26 / -53.70..-47.90 | X (inboard) | 20.99, -50.80, 7.595 |
| SIDE back | 17.78, -68.58 | 16.46..29.26 / -71.48..-65.68 | X (inboard) | 20.99, -68.58, 7.595 |
- On the Y-running switches the plunger is 2.9 along X and 1.2 along Y. On the X-running switches it is 1.2 along X and 2.9 along Y.
- **The side switches push straight up (+Z)**, so a side button needs a rocker or lever that turns a sideways thumb press into a downward press at X 20.99. The board's left edge is X 14.478, so the plunger sits 6.5 mm inboard.
- The middle switch plunger is under the wheel axle line (Y -27.9; it is 0.075 off). Its top is 1.0 below the axle axis, so a wheel press can pivot about the encoder.

## 4. EC10E encoder (placeholder)
- Body box X 25.78..30.18, Y -32.70..-23.10, Z 1.595..12.595 (4.4 x 9.6 x 11.0). Its top Z 12.595 is the tallest point on the board.
- **Shaft axis: point (x, -27.9, 8.595), direction +X.** A Ø5.2 hub sticks out 1.8 on each side (X 23.98..25.78 and 30.18..31.98). A **round Ø3.6 through-bore** runs X 23.98..31.98. No flat or D-shape is modelled: the real part takes a keyed axle, so treat the bore as a placeholder.
- Leads go down to Z -1.905. The legs sit in Ø1.8 slots at X 28.355.
- **Wheel space:** X is free from 31.98 (hub end) to 47.90 (middle switch body), which is 15.9. The board notch X 33.02..45.72 lets the wheel drop below the board. Suggested wheel centre **(39.37, -27.9, 8.595)**. Up to Ø21.9 fits the notch length (axle to notch back is 11.47); wheel width ≤ about 10.5 (notch 12.7 less clearance). The DPI switch body starts at Y -40.28.
- Middle-click lever: from the encoder centre to the plunger is 22.8 along X.

## 5. PMW3360 (placeholder body, lens not modelled)
- Body box X 34.82..43.92, Y -64.62..-48.42, Z 1.595..4.895 (9.1 x 16.2 x 3.3). The body sits on top and over the PCB aperture.
- Pins: 2 rows x 8, Ø0.5 pins in Ø0.7 holes, pitch 1.78. The pin-1 row is at X 44.72, Y -63.10..-50.64; the other row is at X 34.02, Y -62.21..-49.75 (staggered 0.89). Rows are 10.7 apart. Leads go down to Z -1.405.
- **Optical centre (XY) = (39.37, -56.425)**, taken as the centroid of the 16 pads. Source: PMW3360 datasheet (aperture on the package centre) together with the symmetric KiCad footprint. Confidence is medium-high, ±0.3 in Y; X is certain. Cross-checks: the body centre is Y -56.52 and the aperture centre is Y -57.25.
- Lens: PixArt LM19-LSI, mounted from below through the aperture. The **lens reference plane is 2.4 above the tracking surface** (min 2.2, typ 2.4, max 2.6, PMW3360 datasheet). The lens height below the PCB is **not in this STEP**, so the floor Z must come from the LM19-LSI drawing.

## 6. USB 1x4 header (vertical, 2.54)
- Pins at Y -74.676, X **20.33 / 22.87 / 25.41 / 27.95** (pin 1 is at X 20.33). Pin 0.64 square, top Z **10.135**, bottom Z -1.405. Plastic housing X 19.06..29.22, Y -75.946..-73.406, Z 1.595..4.135.
- The header sits at the rear-left corner: 1.78 from the back edge and 5.85 from the left edge.
- A push-on Dupont housing reaches about Z 18 before the wire bend. To keep the top shell low, solder the cable to the pins instead.
- **Cable exit: rear wall, about X 24.1, just above the board.** Put strain relief in the bottom shell behind or beside the header, between the hole at (16.51, -74.42) and the SOT-223 at X ≥ 31.9.

## 7. Keep-out (top: max Z; bottom: min Z)
| zone | max top Z | tallest |
|---|---|---|
| front-left (X<33.02, Y>-39.37) | 12.595 | EC10E; D2F 7.595 |
| wheel notch | – (empty, the slot) | – |
| front-right (X>45.72, Y>-39.37) | 7.595 | D2F main R + middle |
| mid band (Y -39.37..-48) | 7.595 | DPI and side-forward D2F |
| thumb edge (X<30, Y<-48) | 10.135 | USB header; side D2F 7.595 |
| sensor zone (X 30..46, Y<-48) | 4.895 | PMW3360 (SOT-223 3.295) |
| rear-right MCU (X>46, Y<-48) | 3.755 | SOIC-8 (QFN 2.515, SOT-223 3.295) |
- **Bottom side:** no SMD parts. Only THT leads stick out below: D2F and EC10E to Z **-1.905**, sensor and header to Z **-1.405**. The bottom shell's inner floor should be at Z ≤ -2.4 under those leads (or clip the leads). Leave the lens window free.
- 1 mm grids: `keepout.top_max_z` / `keepout.bottom_min_z` (row j = Y0 + j, Y0 = -76.454; col i = X0 + i, X0 = 14.478).

## Renders
`work/renders/R00_pcb_top.png` (annotated top view), `R00_pcb_iso.png`, `R00_pcb_iso_front.png`, `R00_pcb_keepout.png`.
