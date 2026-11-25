# WP-G scroll wheel + axle + yoke

Re-run: `python build_wheel.py` (about 2 min; it also writes `../wheel_yoke/`). Iso render: `<cadgenbench venv>\python.exe render_wheel.py`.
Measured self-check: `selfcheck.log` / `selfcheck.json`. Section PNGs: `work/renders/R02_wheel_section_*.png`, iso: `R02_wheel_iso*.png`.

## Files (native PCB coords, assembly position)
| file | what |
|---|---|
| `wheel.step/.stl` | wheel + axle as ONE solid: the interface envelope that the lead checks (A10/A13/A14). It is also the one-piece printed variant, but that variant needs support (see below) |
| `wheel_body.step/.stl`, `wheel_print.stl` | **the part you print**: wheel with grooves, printed hex stub (left), blind Ø2.0 pin bore (right). Print: axis vertical, right face (X 43.12) on the bed, hex up, 0.12 layers, no support |
| `axle_pin.step/.stl` | **bought** steel pin ISO 2338 / ISO 8734 Ø2 m6 x 16, pressed into the bore from the right until flush with X 52.30 (sticks out 9.18) |
| `../wheel_yoke/wheel_yoke.step/.stl`, `wheel_yoke_print.stl` | PETG yoke. Print: flat on its YZ face, 0.12 layers |
| `wheel_keepout_envelope.step` | NOT a part: wheel at rest + tilted to the slot stop, +0.30. WP-E / WP-D can subtract it |

## Axle decision
- **Default = printed wheel + steel pin.** A printed Ø2 far end (plunger load 1.5 N at 7.7 mm from the wheel face) sees about 15 MPa bending. With the axis vertical that load pulls the layers apart, so it will break in fatigue. Also, the wheel face over a Ø2 axle cannot print without support (356 mm² of overhang).
- **The hex stays printed** on the short left stub: hex 1.70 A/F x 1.9 + Ø2.0 neck + Ø3.0 shoulder (0.22 from the hub face = axial stop). Loads there are low: neck about 3 MPa, detent torque about 8 MPa shear. A hex **sleeve on a steel pin is impossible**, because 1.70 A/F is smaller than the Ø2.0 pin. Print the hex at 0.12 layers and test-fit it in the EC10E (hole 1.73 +0.05). Sand the flats if it is tight. If it is loose, scale the hex in the slicer by +1-2 %.
- Alternative B: a Ø2 steel pin through the whole wheel (X 30.10..52.30, 22.2 long) with a hex 1.70 A/F x 1.9 ground or filed on its end. This is the most robust option, but it needs workshop work. The wheel bore then goes all the way through.
- Middle click: wheel + axle tilt about the hex (X 31.0) onto the middle D2F. The yoke slot gives the up-stop (0.10 above the axle) and the down-stop at 0.67 plunger travel.

## Yoke
Plate X 44.10..45.30 (YOKE_X), Y -31.90..-23.90. The plug below the floor is Y -32.00..-23.80, which gives a 0.05 push fit in YOKE_SOCKET in Y. In X the socket is 1.50 wide against a 1.20 plate (0.15 per side). Either WP-D narrows the socket to X 44.05..45.35, or a drop of glue fixes it. The slot is closed: thread the yoke onto the pin end, then push it into the socket.

## Grip
24 axial grooves 0.8 x 0.4 deep (one per detent) with a rib on top, and rim chamfers 1.2 x 1.1. No tyre was made. If you want a TPU or O-ring tyre, the core has to shrink by 1.5 in radius (WHEEL_TYRE_T).
