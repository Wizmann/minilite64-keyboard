# Mechanical File Manifest

Files with the same base name describe the same geometry in different formats:

- `.FCStd` — editable FreeCAD document.
- `.step` — neutral CAD exchange file for inspection, modification, or machining.
- `.stl` — triangulated mesh for slicers and 3D printing.

## Assembly review

- `Minilite64_assembly_review.FCStd`
- `Minilite64_assembly_review.step`
- `Minilite64_assembly_review.stl`

Combined case, cover, main PCB, plate, carrier, component keep-outs,
stabilizers, and spacers.  Use it to inspect placement and interference.  It is
not a single printable part.

## Case

- `Minilite64_case_full.*` — one-piece case in assembled orientation.  It uses
  a 307 x 106.5 mm Linhai/Case.step-inspired GH60-style plan, R5 plan corners,
  a 5 degree wedge, a 22.9 mm front, and a 32.218 mm rear.  The tapered wall,
  R2 hand-contact rim, C1.2 lower edge break, and internal ribs follow the
  supplied references.  There is no controller tongue or rear projection.
- `Minilite64_case_A1_standing.*` — the same one-piece case rotated onto its
  front wall and 45 degrees across the bed.  Its stored bounds are about
  236.3 x 236.3 x 106.3 mm, so it fits the Bambu A1 with room for an
  approximately 8 mm brim.  Use this file for the preferred one-piece print.
- `Minilite64_case_A1_left.*` — left half of the Bambu A1 printable case.
- `Minilite64_case_A1_right.*` — right half of the Bambu A1 printable case.
- `Minilite64_case_joiner_print_2x.*` — bottom joining strap; print two copies
  to connect the A1 left/right case halves.

The RP2040 carrier, service cover, USB-C tunnel, and R6 FFC corridor are custom
internal features.  They do not change the selected rectangular outside
envelope.
The PCB/plate stack and its seven mounting axes follow the 5 degree typing
plane; the carrier remains horizontal at the bottom for service access.

## Controller service part

- `Minilite64_service_cover.*` — removable bottom cover carrying the 40 x
  36 mm RP2040-Zero carrier.  It includes four carrier posts, cover screw
  holes, and a BOOT/RESET access opening.

## Plate

- `Minilite64_plate_fixed.dxf` — corrected 1.5 mm plate drawing for PC/FR4
  fabrication.  This is the DXF to send to the plate vendor.
- `Minilite64_plate_print_fixed.*` — one-piece, 1.5 mm printable plate for a
  large printer.  It is primarily a fit-check model.
- `Minilite64_plate_print_left.*` — left Bambu A1-sized plate test half.
- `Minilite64_plate_print_right.*` — right Bambu A1-sized plate test half.
- `Minilite64_plate_spacer_print_7x.*` — 5 mm plate-to-PCB spacer; print seven
  copies, one at each retained mounting location.

The original root-level `plate.dxf` is preserved for provenance.  Do not send
it to manufacturing: it contains an obsolete screw relief merged into the
bottom-row Menu switch opening.  The files in this directory remove that
collision and add two symmetric bottom-row supports.  The finished plate has
five round mounts and two side mounting slots.
