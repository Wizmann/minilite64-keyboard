# Minilite64 Keyboard

Minilite64 is a 64-key hot-swap keyboard built around a Waveshare
RP2040-Zero.  Its main PCB uses two copper layers; the Vial firmware exposes
four dynamic keymap layers.  The main keyboard PCB and controller carrier are
connected by a 20-position, 1.0 mm Type-A FFC.  The design has no per-key
lighting.

## Release contents

- `hardware/keyboard/Minilite64.kicad_pcb` — routed GH60-size main PCB
- `hardware/controller/RP2040_Zero_Carrier.kicad_pcb` — routed 40 x 36 mm carrier
- `hardware/mechanical/Minilite64_plate_fixed.dxf` — corrected plate for PC/FR4 ordering
- `hardware/mechanical/*.stl` and `*.step` — full-size and A1 standing mechanical parts
- `manufacturing/*_gerber.zip` — order-ready PCB packages
- `firmware/vial-qmk/keyboards/minilite64` — Vial-QMK keyboard source
- `firmware/releases/Minilite64_vial.uf2` — locally verified RP2040 firmware
- `docs/DESIGN_AND_REUSE_GUIDE.md` — design history, assembly notes, checks, and reusable lessons

Both PCBs currently report zero DRC violations and zero unconnected items.
The mechanical review reports zero intersections for the checked component,
mounting, controller, stabilizer, cover, and cable envelopes.
The main PCB front silkscreen also carries the complete corrected plate DXF at
1:1 scale for visual Gerber and bare-board inspection.

The checked-in UF2 was built with `arm-none-eabi-gcc 13.2.1`; its SHA-256 is
recorded in `firmware/releases/SHA256SUMS.txt`.

## Important fabrication note

Use `hardware/mechanical/Minilite64_plate_fixed.dxf`, not the original
`plate.dxf`.  The original drawing contains an obsolete screw relief merged
into the bottom-row Menu switch opening.  The fixed file removes that conflict
and adds two balanced bottom-row supports, for five round mounts plus two side
mounting slots in total.

See the [design and reuse guide](docs/DESIGN_AND_REUSE_GUIDE.md) before ordering
or assembling the first prototype.
