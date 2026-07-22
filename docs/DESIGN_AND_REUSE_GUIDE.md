# Minilite64 Design, Assembly, and Reuse Guide

This document records how Minilite64 was designed, what was verified, what
failed during the process, and which practices should be reused on the next
keyboard project.  It is intentionally more explicit than a normal build
guide because the difficult parts were mechanical coordination and source-of-
truth management rather than the keyboard matrix itself.

## 1. Product definition

Minilite64 is based on the supplied 64-key KLE and plate DXF.  The confirmed
requirements are:

- 64 MX-compatible switches in a 5 x 14 sparse matrix.
- Kailh CPG151101S11-style hot-swap sockets on the PCB bottom.
- One hand-solderable SOD-123 1N4148W diode per key.
- No keyboard lighting.  The RP2040-Zero's onboard indicators are unaffected.
- A two-copper-layer main PCB with a rectangular GH60-style envelope and no PCB tongue.
- A separate Waveshare RP2040-Zero carrier.
- A 20-position, 1.0 mm Type-A/same-side FFC, nominally 80 mm long.
- Vial/VIA remapping, four dynamic layers, Bootmagic, and a firmware boot key.
- A PC or FR4 plate, 1.5 mm thick, plus printable verification plates.
- A Case.step-inspired wedge case, a bottom service cover, and a one-piece
  Bambu A1 standing print.

## 2. Electrical architecture

### Main PCB

The main PCB is 285.45 x 94.95 mm in its final edge-cut bounding box.  It uses
two copper layers, 0.20 mm minimum routed track width, 0.20 mm minimum routed
clearance, 0.30 mm vias, and a nominal 1.60 mm board thickness.

The switch matrix has five rows and fourteen columns.  Diode direction is
`COL2ROW`.  The FFC pinout is:

| FFC pin | Net | RP2040-Zero pad |
|---:|---|---|
| 1 | GND | GND |
| 2-6 | ROW0-ROW4 | GP29, GP28, GP27, GP26, GP15 |
| 7-20 | COL0-COL13 | GP13 through GP0 in the order recorded in `manufacturing/FFC_pinout.csv` |

The final main board includes seven usable mounting locations:

- Original round mounts: `(25.57496, 28.22478)`, `(128.57596, 47.62558)`, and
  `(260.42446, 28.22478)` mm.
- Balanced bottom-row M2 mounts: `(47.625, 85.20)` and `(238.125, 85.20)` mm.
- Side-slot screw axes: `(3.65, 56.824)` and `(282.10, 56.824)` mm.

The bottom-row screw relief near the Menu key is deliberately absent.  It
overlapped the switch opening and would have collided with the switch/hot-swap
assembly.  The two replacement mounts are symmetric about the keyboard center,
sit in full material between adjacent 1.25U switches, and avoid the spacebar
stabilizer.  The PCB uses 2.4 mm NPTH holes at these new locations; the plate
uses 3.2 mm clearance holes.

### RP2040-Zero carrier

The carrier is 40 x 36 mm with four 2.2 mm holes at `(3,3)`, `(37,3)`,
`(3,33)`, and `(37,33)` mm.  The RP2040-Zero is mounted on F.Cu and the FFC
connector is on B.Cu.  In the case, the module side faces the bottom service
cover.  The cover intentionally has no external BOOT/RESET opening.  Normal
remapping uses Vial and the keymap provides `QK_BOOT`; if damaged firmware
cannot enter its bootloader, remove the service cover to press the physical
buttons.  Removing the cover also brings the carrier out far enough to reach
the FFC latch without sharply folding the cable.

Do not regenerate the routed carrier from the old seed.  The generator now
writes an optional unrouted carrier seed only to `build/` when invoked with
`--write-carrier-seed`; it never overwrites the routed board in `hardware/`.

## 3. Coordinate systems and the plate correction

The most important geometry lesson was that the DXF Y axis and the KLE/KiCad Y
axis point in opposite directions.  Treating them as identical incorrectly
made a valid mounting hole appear to collide with Shift.

The conversion used here mirrors the DXF about its own center and maps that
center to the PCB center:

```text
pcb_x = dxf_x + pcb_center_x - dxf_center_x
pcb_y = pcb_center_y - (dxf_y - dxf_center_y)
```

The original DXF contains 68 closed connected contours, but one switch contour
has 33 segments because an obsolete circular screw relief was merged into the
bottom-row Menu opening.  The corrected file replaces that merged contour with
a normal MX opening and adds the two bottom-row clearance holes.  The corrected
DXF has 70 closed contours and no 33-segment internal contour.

Always order the plate from:

`hardware/mechanical/Minilite64_plate_fixed.dxf`

Keep the original `plate.dxf` only as provenance.

## 4. Routing lessons

1. Reserve the FFC escape before routing the matrix.  A 20-pin connector at
   1.0 mm pitch is easy to place and surprisingly hard to escape after the
   row/column buses occupy both layers.
2. Rotating the top-row hot-swap sockets opened the shallow rear corridor used
   by the main FFC connector.
3. Move diodes when they block a route, but check the full physical envelope:
   socket body, stabilizer wire, screw head, case post, and soldering-iron
   access.
4. Do not extend row buses decoratively to the board edge.  The first revision
   left five harmless dangling ends.  Terminating each row bus on its first and
   last diode stub removed all five warnings and cleared the right mounting
   notch.
5. Right-angle traces are not an electrical concern for a keyboard matrix, but
   clean 45-degree routing remains useful because it is easier to inspect and
   leaves predictable mechanical corridors.
6. A rectangular PCB can still contain edge mounting notches.  "No tongue"
   should not be interpreted as "discard all edge mounting geometry."

## 5. Mechanical architecture

GH60 defines a PCB and mounting ecosystem, not one official case shell.  The
case exterior therefore combines the supplied references with the GH60 PCB
datum:

- The original [GH60 project](https://github.com/komar007/gh60) supplies the
  PCB and mounting datum.
- The supplied Linhai GH60 3MF supplies the 307 x 106.5 mm outside plan and its
  proven 45 degree standing-print strategy.
- The supplied `Case.step` measures approximately 303.64 x 115.22 x 33.47 mm.
  Its main profile is about 22.91 mm at the front and 32.06 mm at the rear,
  with a 5 degree typing plane, tapered walls, rounded hand-contact edges, and
  triangulated internal ribs.

The resulting Minilite64 case uses a nominal 307 x 106.5 mm GH60-style plan,
R5 plan corners, a 22.9 mm front, a 32.218 mm rear, and a 5 degree wedge.  It
adds a 2.5 mm wall taper, an R2 upper edge, and a C1.2 lower edge break so the
printed shell does not leave a sharp hand-contact edge.  The previous flat tray
and its rear controller projection were removed.  The carrier was moved
forward so the service cover, USB-C tunnel, and R6 FFC corridor all fit inside
the rectangular exterior.

The main PCB, plate, spacers, screw axes, and upper post sections share the
5 degree plane.  Approximate assembled heights are:

| Item | Rear datum | Front datum |
|---|---:|---:|
| Case floor | 0-2.4 mm | 0-2.4 mm |
| Carrier PCB | 8.0-9.6 mm | horizontal |
| Main PCB bottom | 22.0 mm | 13.68 mm |
| Plate bottom | 28.6 mm | 20.28 mm |
| Case rim | 32.218 mm exterior | 22.9 mm exterior |

The height values at the PCB edges differ slightly from the case exterior-edge
values because the PCB is inset from the front and rear walls.

The 80 mm FFC must be stored as a broad S-shaped loop in the reserved center
bay.  Keep every bend at or above R6, keep the cable inside the documented
20.55 mm-wide corridor, and never crease it at either ZIF mouth.  Insert and
lock the FFC before tightening the main PCB.

The assembled-orientation case is 307 mm long, but the one-piece
`Minilite64_case_A1_standing.stl` is stored front-wall-down and rotated 45
degrees.  Its approximate slicer bounds are 236.3 x 236.3 x 106.3 mm, leaving
room for an approximately 8 mm brim on the Bambu A1.  Use the standing file as
the one-piece print.  The printable full plate is primarily a fit-check model;
order the final plate in 1.5 mm PC or FR4 from the corrected DXF.

For the standing case, keep the stored orientation, add an 8-10 mm brim, and
inspect the slicer's support preview around the horizontal insert bosses,
service opening, and internal ribs.  Do not scale the model to make it fit.
Print a small insert-pilot test coupon to tune screw clearances for the chosen
filament before committing to the full case.

## 6. Mechanical checks performed

`build/mechanical_review.json` is generated from actual FreeCAD solids plus
conservative component envelopes.  The following intersections must remain
zero:

- Main components versus main mounting bosses.
- Main components versus the controller assembly.
- Controller assembly versus the case.
- Service cover versus the case.
- Main PCB and plate versus case walls.
- Plate-mount stabilizer envelopes versus the seven plate spacers.
- FFC corridor versus the case and mounting bosses.

The hot-swap keep-outs initially collided with three full-diameter posts.  The
final main posts use a wide lower body below component height and normally a
6 mm upper boss.  The legacy center location retains a 4.8 mm neck because a
6 mm neck intersects its socket envelope.  Each main boss has a 2.8 mm pilot
for a short M2 heat-set insert with nominal 3.2 mm OD and 3 mm length.  Their
axes follow the 5 degree PCB normal.  The service-cover screw towers were also
moved outside the 40 mm carrier outline after the first solid-intersection pass
found an overlap.

These checks are envelope checks, not a substitute for a physical prototype.
Print the fit-check plate, install representative switches, sockets,
stabilizers, screws, and an actual FFC, then print the case.

## 7. Assembly order

1. Inspect both PCBs under magnification and check for solder bridges.
2. Solder the 64 diodes with the cathode stripe toward the row bus.
3. Solder the 64 Kailh hot-swap sockets on the main PCB bottom.
4. Solder both 20P ZIF connectors.  Confirm pin 1 before installing the FFC.
5. Solder the RP2040-Zero castellations to the carrier with USB-C toward the
   rear opening.
6. Mount the carrier to the service cover, module side toward the closed cover
   surface; the modeled standoffs provide component clearance.
7. Insert and lock the FFC at the carrier, route a broad R6-or-larger S loop,
   and lock the main-board end.
8. Heat-set the seven main M2 inserts with a temperature-controlled tip.  Keep
   each insert square to the tilted boss and stop flush; do not force it deeper
   than the 3 mm insert length.
9. Install seven 5 mm plate spacers, the main PCB, plate, plate stabilizers, and
   switches.  Use the two new symmetric bottom-row supports, not the deleted
   Menu-key screw location.
10. Check the FFC through the open service bay, then install the cover.
11. Flash the UF2 and perform a full matrix test before fitting keycaps.

For normal remapping, use Vial.  The physical BOOT/RESET buttons should rarely
be needed after the first flash.  The default Fn1 layer provides `QK_BOOT` on
the top-left key, and Bootmagic is enabled.

## 8. Firmware build

The source lives at `firmware/vial-qmk/keyboards/minilite64`.  Copy that folder
into a Vial-QMK checkout and build:

```bash
make minilite64:vial
```

The confirmed toolchain is Vial-QMK plus `arm-none-eabi-gcc` 13.2.1.  On WSL,
build from the Linux filesystem rather than `/mnt/c` or `/mnt/e`; QMK scans
tens of thousands of small files and is dramatically slower on a mounted
Windows filesystem.

## 9. Reproducing generated artifacts

Main PCB and metadata, without touching the routed carrier:

```powershell
python tools/generate_hardware.py
```

Optional unrouted carrier seed:

```powershell
python tools/generate_hardware.py --write-carrier-seed
```

Mechanical outputs with FreeCAD:

```powershell
freecadcmd.exe -c "exec(compile(open(r'E:\Code\Minilite\tools\generate_mechanical.py', encoding='utf-8').read(), r'E:\Code\Minilite\tools\generate_mechanical.py', 'exec'), {'__file__': r'E:\Code\Minilite\tools\generate_mechanical.py', '__name__': '__main__'})"
```

Firmware source:

```powershell
python tools/generate_firmware.py
```

Release validation:

```powershell
python tools/validate_release.py
```

## 10. Manufacturing and release checklist

- Confirm two-copper-layer, 1.6 mm FR4 for both PCBs.
- Confirm all seven Gerber layers exist: F/B copper, F/B mask, F/B silkscreen,
  and Edge.Cuts.
- Include both PTH and NPTH drill files.
- Confirm main PCB DRC and carrier DRC each show zero violations and zero
  unconnected items.
- Confirm the plate vendor receives the fixed DXF and 1.5 mm thickness.
- Verify the exact purchased ZIF footprint against the board before ordering a
  production batch; generic 20P 1.0 mm connectors are not mechanically
  interchangeable.
- Buy a same-side/Type-A 20P 1.0 mm FFC and enforce R6 during installation.
- Confirm M2 heat-set inserts are 3.2 mm nominal OD and 3 mm long before
  heating them into the 2.8 mm case pilots; tune the pilot on a test coupon if
  the actual insert knurl differs.
- For the A1 one-piece case, use the stored standing orientation and an
  8-10 mm brim; review supports before slicing.
- Print one plate half and a service-cover/carrier test before the full case.
- Test all 64 switch positions, USB enumeration, Vial unlock, and the boot key.
- Only after the prototype passes should the case tolerances be tuned for the
  chosen printer, filament, heat-set inserts, and screw supplier.

## 11. General lessons for the next project

- Use one coordinate-system conversion function and test it with asymmetric
  mounting features before placing hardware.
- Model screw heads, insert bosses, connector latch access, cable bends, and
  soldering access—not only nominal PCB outlines.
- Keep generated seeds and routed production boards in different paths.
- Make the release validator assert expected manufacturing layers; a board can
  pass copper DRC while still lacking declared mask layers.
- Stop and review from the assembler's point of view after every major layout
  change: what is installed first, what tool reaches the latch, what must be
  removed for service, and where slack cable goes.
- Preserve the original customer geometry, but publish a clearly named fixed
  derivative when a source drawing contains a known collision.
