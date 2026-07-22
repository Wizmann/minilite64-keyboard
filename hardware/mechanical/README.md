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

- `Minilite64_case_full.*` — one-piece case for a printer or machine with a
  build area larger than the Bambu A1.  Overall envelope is approximately
  293.75 x 109.25 x 27.5 mm.
- `Minilite64_case_A1_left.*` — left half of the Bambu A1 printable case.
- `Minilite64_case_A1_right.*` — right half of the Bambu A1 printable case.
- `Minilite64_case_joiner_print_2x.*` — bottom joining strap; print two copies
  to connect the A1 left/right case halves.

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
- `Minilite64_plate_spacer_print_5x.*` — 5 mm plate-to-PCB spacer; print five
  copies, one at each retained mounting location.

The original root-level `plate.dxf` is preserved for provenance.  Do not send
it to manufacturing: it contains an obsolete screw relief merged into the
bottom-row Menu switch opening.  The files in this directory remove that
collision while retaining the three round mounts and two side mounting slots.

