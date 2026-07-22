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
  a 5 degree wedge, a 20.0 mm spacebar side, and a 29.318 mm number-row side.
  The tapered wall,
  R2 hand-contact rim, C1.2 lower edge break, and internal ribs follow the
  supplied references.  There is no controller tongue or rear projection.
- `Minilite64_case_A1_standing.*` — the same one-piece case rotated onto its
  front wall and 45 degrees across the bed.  Its stored bounds are about
  236.3 x 236.3 x 106.3 mm, so it fits the Bambu A1 with room for an
  approximately 8 mm brim.  Use this file for the preferred one-piece print.

The RP2040 carrier, service cover, USB-C tunnel, and rear-wall FFC service-loop
pocket are custom internal features.  They do not change the selected
rectangular outside envelope.

The PCB/plate stack and its seven mounting axes follow the 5 degree typing
plane; the carrier remains horizontal at the bottom for service access.

The 100 mm FFC is a service tether.  Connect and fasten the main PCB first,
connect the carrier/cover outside the case, then guide the smooth scroll into
its rounded rear pocket and install the cover screws.  The controller can be
removed later without disturbing the main PCB.

`Minilite64_assembly_review.*` also contains a named 65 mm controller service
pose with tangent cable exits.  The modeled service path is 94.762 mm long,
keeps 5.238 mm slack, reaches R3.6 at the fixed rear hairpin, and keeps the
cubic drop above R4.82.  The 81.625 mm straight-line value is only a theoretical
upper bound.  Use an FFC flexible body no thicker than 0.20 mm; the reinforced
ends may be 0.30 mm.

This package is prototype-only until a real cable has been fitted.  A solid
model cannot prove that the flexible strip will settle into the ideal scroll
instead of buckling during cover insertion.

The bottom has four circular pockets for nominal Ø10 x 1.5-2.0 mm adhesive
silicone feet.  Each pocket has an Ø11.2 mm body, 0.65 mm depth, and an Ø12 mm
tapered opening.  The extra diameter tolerates placement error; the shallow
lead-in avoids a sharp unsupported lip when the case is printed standing.

## Controller service part

- `Minilite64_service_cover.*` — removable bottom cover carrying the 40 x
  36 mm RP2040-Zero carrier.  It includes four carrier posts, cover screw
  holes, and a closed outside surface.  Remove the cover if physical
  BOOT/RESET recovery is ever required.

## Plate

- `Minilite64_plate_fixed.dxf` — corrected 1.5 mm plate drawing for PC/FR4
  fabrication.  This is the DXF to send to the plate vendor.
- `Minilite64_plate_print_fixed.*` — one-piece, 1.5 mm printable plate for a
  large printer.  It is primarily a fit-check model.
- `Minilite64_plate_A1_fitcheck.stl` — one A1-ready STL containing two flat
  printable halves.  The loose stepped joint avoids complete switch openings,
  uses a 0.4 mm total seam gap, and relies on switches and PCB screws for final
  alignment.  No glue is required for fit checking.
- `Minilite64_plate_spacer_print_7x.*` — 5 mm plate-to-PCB spacer; print seven
  copies, one at each retained mounting location.

The original root-level `plate.dxf` is preserved for provenance.  Do not send
it to manufacturing: it contains an obsolete screw relief merged into the
bottom-row Menu switch opening.  The files in this directory remove that
collision and add two symmetric bottom-row supports.  The finished plate has
five round mounts and two side mounting slots.
