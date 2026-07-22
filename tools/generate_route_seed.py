"""Generate the compact-tongue Minilite64 routing seed.

The switch matrix is pre-routed; only the 20-way FFC breakout is left for
Freerouting.  This keeps the autorouter problem small and deterministic.
"""

from generate_hardware import (
    Board, FFC_NETS, FFC_X0, Key, add_openai_branding, diode_footprint,
    ffc_footprint, mounting_hole, parse_kle, switch_footprint, ROOT,
)


def build(keys: list[Key], out):
    board = Board("Minilite64-tongue-seed")
    for name in [*(f"COL{i}" for i in range(14)), *(f"ROW{i}" for i in range(5)), "GND"]:
        board.net(name)
    for key in keys:
        board.net(f"KEY{key.index + 1}_D")

    outline = [
        (0.15, 0.15), (120.0, 0.15), (120.0, -13.7),
        (165.0, -13.7), (165.0, 0.15), (285.6, 0.15),
        (285.6, 95.1), (0.15, 95.1), (0.15, 0.15),
    ]
    for a, b in zip(outline, outline[1:]):
        board.edge(a, b)
    ffc_footprint(board, "J1", FFC_X0, -9.5, FFC_NETS, "seed-ffc")

    by_row = {row: [] for row in range(5)}
    for key in keys:
        by_row[key.row].append(key)
        switch_footprint(board, key)
        diode_footprint(board, key)
        socket2 = (key.x - 5.842, key.y - 5.08)
        anode = (key.x - 7.65, key.y + 2.7)
        board.polyline(f"KEY{key.index + 1}_D", [socket2, (key.x - 7.65, key.y - 5.08), anode], "B.Cu", 0.28)
        board.segment(f"ROW{key.row}", (key.x - 7.65, key.y + 6.5), (key.x - 7.65, key.y + 8.0), "B.Cu", 0.3)

    col_vias = {}
    for row, row_keys in by_row.items():
        for key in row_keys:
            pad1 = (key.x + 7.085, key.y - 2.54)
            if row == 2 and key.col == 5:
                # Keep the centre DXF mounting hole and its 5 mm head envelope clear.
                via = (124.0, key.y - 2.54)
                board.segment(f"COL{key.col}", pad1, via, "B.Cu", 0.28)
            elif key.x + 8.8 > 281.4:
                via = (key.x + 7.1, key.y - 4.45)
                board.polyline(f"COL{key.col}", [pad1, (key.x + 7.1, key.y - 2.54), via], "B.Cu", 0.28)
            else:
                via = (key.x + 8.8, key.y - 2.54)
                board.segment(f"COL{key.col}", pad1, via, "B.Cu", 0.28)
            board.via(f"COL{key.col}", via)
            col_vias[(row, key.col)] = via

    for col in range(14):
        existing_rows = [row for row in range(5) if (row, col) in col_vias]
        for row_a, row_b in zip(existing_rows, existing_rows[1:]):
            a = col_vias[(row_a, col)]
            b = col_vias[(row_b, col)]
            center_a = by_row[row_a][0].y
            center_b = by_row[row_b][0].y
            board.polyline(
                f"COL{col}",
                [a, (a[0], center_a + 3.0), (b[0], center_b - 7.0), b],
                "F.Cu", 0.2,
            )

    row_ends = [280.6, 281.5, 282.4, 283.3, 284.2]
    for row, row_keys in by_row.items():
        bus_y = row_keys[0].y + 8.0
        diode_xs = [key.x - 7.65 for key in row_keys]
        board.segment(f"ROW{row}", (min(diode_xs), bus_y), (row_ends[row], bus_y), "B.Cu", 0.3)

    # First three centres are the exact 5x5 mm openings measured from plate.dxf.
    holes = [(25.4820, 67.0920), (128.4830, 47.6912), (260.3315, 67.0920),
             (25.35, 28.05), (260.20, 28.05), (140.25, 85.35)]
    for index, point in enumerate(holes, 1):
        mounting_hole(board, f"H{index}", point)

    board.text("MINILITE64 • REV B • 2 LAYER", (142.875, 92.2), "F.SilkS", 1.0)
    board.text("20P FFC • 1.0 mm • TYPE A", (142.5, -12.6), "B.SilkS", 0.72, "mirror")
    add_openai_branding(board)
    board.write(out)


if __name__ == "__main__":
    build(parse_kle(ROOT / "KLE.txt"), ROOT / "build" / "Minilite64_tongue_seed.kicad_pcb")
