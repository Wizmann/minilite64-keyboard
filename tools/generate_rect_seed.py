"""Generate the rectangular two-layer Minilite64 routing seed.

The switch matrix is pre-routed.  Only the nineteen matrix signals at the
20-way rear FFC connector are left for Freerouting; pin 20 is the cable ground
reference and intentionally has no second connection on this passive board.
"""

from generate_hardware import (
    Board, FFC_NETS, FFC_X0, Key, ROOT, add_openai_branding,
    back_ffc_footprint, diode_footprint, mounting_hole, parse_kle,
    switch_footprint, top_row_diode_footprint,
)

ROUTE_FFC = False


def plate_mount_holes():
    """Return the three supplied DXF holes in KLE/PCB coordinates."""
    dxf_center_x = (0.0950846 + 285.469) / 2
    pcb_center_x = (0.15 + 285.6) / 2
    dxf_center_y = (0.228755 + 95.1548) / 2
    pcb_center_y = (0.15 + 95.1) / 2
    dxf_holes = [(25.4820, 67.0920), (128.4830, 47.6912), (260.3315, 67.0920)]
    return [
        (
            x + pcb_center_x - dxf_center_x,
            pcb_center_y - (y - dxf_center_y),
        )
        for x, y in dxf_holes
    ]


def edge_mount_slots():
    """Return the screw axes of the two valid DXF edge mounting notches."""
    return [(3.65, 56.824), (282.10, 56.824)]


def board_outline():
    """GH60 rectangle with the two valid side mounting notches.

    The supplied DXF also contains a screw relief merged into the bottom-row
    Menu switch opening.  That location is intentionally not reproduced: it
    clashes with the switch/hot-swap assembly.  The short segmented arcs here
    are the left and right R2.5 mm DXF notches, mapped into PCB coordinates.
    """
    right = [
        (285.60, 54.324), (282.10, 54.324), (281.327, 54.445),
        (280.631, 54.801), (280.078, 55.355), (279.723, 56.051),
        (279.600, 56.824), (279.723, 57.597), (280.078, 58.294),
        (280.631, 58.847), (281.327, 59.201), (282.10, 59.324),
        (285.60, 59.324),
    ]
    left = [(285.75 - x, y) for x, y in reversed(right)]
    return [
        (0.15, 0.15), (285.60, 0.15),
        *right,
        (285.60, 95.10), (0.15, 95.10),
        *left,
        (0.15, 0.15),
    ]


def build(keys: list[Key], out):
    board = Board("Minilite64-rectangular-seed")
    for name in [*(f"COL{i}" for i in range(14)), *(f"ROW{i}" for i in range(5)), "GND"]:
        board.net(name)
    for key in keys:
        board.net(f"KEY{key.index + 1}_D")

    outline = board_outline()
    for a, b in zip(outline, outline[1:]):
        board.edge(a, b)

    # Bottom-side ZIF mouth faces the rear edge.  Rotating only the top-row
    # hot-swap sockets opens the shallow rear component corridor it needs.
    back_ffc_footprint(board, "J1", FFC_X0, 4.2, FFC_NETS, "rect-seed-ffc")

    by_row = {row: [] for row in range(5)}
    diode_x_by_key = {}
    for key in keys:
        by_row[key.row].append(key)
        rotated = key.row == 0
        switch_footprint(board, key, rotated)
        if rotated:
            anode, cathode = top_row_diode_footprint(board, key)
            diode_x_by_key[key.index] = cathode[0]
            socket2 = (key.x + 5.842, key.y + 5.08)
            board.segment(f"KEY{key.index + 1}_D", socket2, anode, "B.Cu", 0.28)
            board.segment(
                f"ROW{key.row}", cathode, (cathode[0], key.y + 9.5),
                "B.Cu", 0.3,
            )
        else:
            diode_footprint(board, key)
            diode_x = key.x - 7.65
            diode_x_by_key[key.index] = diode_x
            socket2 = (key.x - 5.842, key.y - 5.08)
            anode = (diode_x, key.y + 2.7)
            board.polyline(
                f"KEY{key.index + 1}_D",
                [socket2, (diode_x, key.y - 5.08), anode],
                "B.Cu", 0.28,
            )
            board.segment(
                f"ROW{key.row}",
                (diode_x, key.y + 6.5), (diode_x, key.y + 8.0),
                "B.Cu", 0.3,
            )

    col_vias = {}
    for row, row_keys in by_row.items():
        for key in row_keys:
            if row == 0:
                pad1 = (key.x - 7.085, key.y + 2.54)
                via_x = 1.05 if key.col == 0 else key.x - 8.8
                via = (via_x, key.y + 2.54)
                board.segment(f"COL{key.col}", pad1, via, "B.Cu", 0.28)
            else:
                pad1 = (key.x + 7.085, key.y - 2.54)
                if key.x + 8.8 > 281.4:
                    via = (key.x + 7.1, key.y - 4.45)
                else:
                    via = (key.x + 8.8, key.y - 2.54)
                board.segment(f"COL{key.col}", pad1, via, "B.Cu", 0.28)
            board.via(f"COL{key.col}", via)
            col_vias[(row, key.col)] = via

    # Columns use the front layer between row corridors.  The only special
    # lane is COL5 around the exact centre DXF mounting hole.
    for col in range(14):
        existing_rows = [row for row in range(5) if (row, col) in col_vias]
        for row_a, row_b in zip(existing_rows, existing_rows[1:]):
            a = col_vias[(row_a, col)]
            b = col_vias[(row_b, col)]
            center_a = by_row[row_a][0].y
            center_b = by_row[row_b][0].y
            if row_a == 0:
                points = [a, (a[0], 18.8), (b[0], 21.0), b]
            elif row_a == 2 and col == 5:
                # Detour left of the centre DXF mounting hole and its head.
                points = [
                    a, (126.2, a[1]), (126.2, center_a + 3.0),
                    (b[0], center_b - 7.0), b,
                ]
            else:
                points = [a, (a[0], center_a + 3.0), (b[0], center_b - 7.0), b]
            board.polyline(f"COL{col}", points, "F.Cu", 0.2)

    # Terminate each bus on the first/last diode stub.  Besides removing the
    # old decorative dangling ends, this keeps copper clear of the right-hand
    # DXF mounting notch.
    row_ends = []
    for row, row_keys in by_row.items():
        bus_y = row_keys[0].y + (9.5 if row == 0 else 8.0)
        diode_xs = [diode_x_by_key[key.index] for key in row_keys]
        row_ends.append(max(diode_xs))
        board.segment(
            f"ROW{row}", (min(diode_xs), bus_y), (max(diode_xs), bus_y),
            "B.Cu", 0.3,
        )

    # Route the FFC escape in 0.8 mm lanes.  All fourteen columns travel in
    # F.Cu above the connector; their remote vertical drops use B.Cu.  The
    # wider pitch keeps every through-via clear of adjacent parallel tracks.
    fan_width = 0.2
    launch_y = 6.6

    for col in range(14):
        pad_point = (FFC_X0 + col, 4.2)
        launch = (pad_point[0], launch_y)
        if col < 7:
            lane_y = 5.75 - col * 0.8
        elif col == 7:
            lane_y = 6.4
        else:
            lane_y = 0.95 + (col - 8) * 0.8
        target = col_vias[(0, col)]
        lane_target = (target[0], lane_y)
        board.segment(f"COL{col}", pad_point, launch, "B.Cu", fan_width)
        board.via(f"COL{col}", launch, 0.6, 0.3)
        if col == 7:
            board.polyline(
                f"COL{col}",
                [launch, (launch[0], 7.4), (134.8, 7.4),
                 (134.8, target[1]), target],
                "F.Cu", fan_width,
            )
            continue
        board.segment(f"COL{col}", launch, (launch[0], lane_y), "F.Cu", fan_width)
        if col == 8:
            lane_target = (156.0, lane_y)
        board.segment(f"COL{col}", (launch[0], lane_y), lane_target, "F.Cu", fan_width)
        board.via(f"COL{col}", lane_target, 0.6, 0.3)
        if col == 8:
            detour = (156.0, 6.9)
            approach = (target[0], 6.9)
            board.segment(f"COL{col}", lane_target, detour, "B.Cu", fan_width)
            board.segment(f"COL{col}", detour, approach, "B.Cu", fan_width)
            board.segment(f"COL{col}", approach, target, "B.Cu", fan_width)
        else:
            board.segment(f"COL{col}", lane_target, target, "B.Cu", fan_width)

    # Three rows pass below the connector hold-down tab on B.Cu; one passes
    # above it.  ROW4 uses the free F.Cu lane.  At the far right each route
    # changes layer twice so the existing B.Cu row bus remains untouched.
    row_lanes = [
        ("B.Cu", 0.8), ("B.Cu", 1.6), ("B.Cu", 2.4),
        ("B.Cu", 6.8), ("F.Cu", 6.8),
    ]
    for row, (layer, lane_y) in enumerate(row_lanes if ROUTE_FFC else []):
        pad_point = (FFC_X0 + 14 + row, 4.2)
        bus_y = by_row[row][0].y + (9.5 if row == 0 else 8.0)
        target = (row_ends[row], bus_y)
        lane_target = (target[0], lane_y)
        if layer == "B.Cu":
            board.segment(f"ROW{row}", pad_point, (pad_point[0], lane_y), "B.Cu", fan_width)
            board.segment(f"ROW{row}", (pad_point[0], lane_y), lane_target, "B.Cu", fan_width)
            board.via(f"ROW{row}", lane_target, 0.6, 0.3)
            board.via(f"ROW{row}", target, 0.6, 0.3)
            board.segment(f"ROW{row}", lane_target, target, "F.Cu", fan_width)
        else:
            launch = (pad_point[0], 7.4)
            board.segment(f"ROW{row}", pad_point, launch, "B.Cu", fan_width)
            board.via(f"ROW{row}", launch, 0.6, 0.3)
            board.segment(f"ROW{row}", launch, (launch[0], lane_y), "F.Cu", fan_width)
            board.segment(f"ROW{row}", (launch[0], lane_y), lane_target, "F.Cu", fan_width)
            board.via(f"ROW{row}", lane_target, 0.6, 0.3)
            board.segment(f"ROW{row}", lane_target, target, "B.Cu", fan_width)

    # ROW0 uses the clear corridor between the two centre top-row switches.
    row0_pad = (FFC_X0 + 14, 4.2)
    row0_launch = (row0_pad[0], 7.4)
    row0_target = (154.5, 18.0)
    row0_bus = (154.5, by_row[0][0].y + 9.5)
    board.segment("ROW0", row0_pad, row0_launch, "B.Cu", fan_width)
    board.via("ROW0", row0_launch, 0.6, 0.3)
    board.polyline(
        "ROW0", [row0_launch, (154.5, 7.4), row0_target],
        "F.Cu", fan_width,
    )
    board.via("ROW0", row0_target, 0.6, 0.3)
    board.segment("ROW0", row0_target, row0_bus, "B.Cu", fan_width)

    # ROW1 steps through successive switch gaps as the rows stagger.
    row1_pad = (FFC_X0 + 15, 4.2)
    row1_launch = (row1_pad[0], 6.8)
    row1_approach = (190.5, 19.0)
    row1_drop = (191.0, 19.7)
    row1_target = (161.925, 34.0)
    row1_bus = (161.925, by_row[1][0].y + 8.0)
    board.segment("ROW1", row1_pad, row1_launch, "B.Cu", fan_width)
    board.via("ROW1", row1_launch, 0.6, 0.3)
    board.polyline(
        "ROW1",
        [row1_launch, (190.5, 6.8), row1_approach, row1_drop],
        "F.Cu", fan_width,
    )
    board.via("ROW1", row1_drop, 0.6, 0.3)
    board.polyline(
        "ROW1",
        [row1_drop, (191.0, 21.0), (161.925, 21.0),
         row1_target, row1_bus],
        "B.Cu", fan_width,
    )

    # ROW2 crosses ROW1's bus at an F.Cu gap between two column lanes.
    row2_pad = (FFC_X0 + 16, 4.2)
    row2_launch = (row2_pad[0], 6.2)
    row2_approach = (209.55, 19.0)
    row2_drop = (210.0, 19.7)
    board.segment("ROW2", row2_pad, row2_launch, "B.Cu", fan_width)
    board.via("ROW2", row2_launch, 0.6, 0.3)
    board.polyline(
        "ROW2",
        [row2_launch, (209.55, 6.2), row2_approach, row2_drop],
        "F.Cu", fan_width,
    )
    board.via("ROW2", row2_drop, 0.6, 0.3)
    row2_pre_cross = (176.0, 35.6)
    board.polyline(
        "ROW2",
        [row2_drop, (210.0, 21.5), (180.975, 21.5),
         (180.975, 35.6), row2_pre_cross],
        "B.Cu", fan_width,
    )
    row2_post_cross = (176.0, 37.4)
    board.via("ROW2", row2_pre_cross, 0.6, 0.3)
    board.segment("ROW2", row2_pre_cross, row2_post_cross, "F.Cu", fan_width)
    board.via("ROW2", row2_post_cross, 0.6, 0.3)
    row2_gap = (185.7375, 37.4)
    row2_bus = (185.7375, by_row[2][0].y + 8.0)
    board.polyline(
        "ROW2", [row2_post_cross, row2_gap, row2_bus],
        "B.Cu", fan_width,
    )

    # ROW3 uses the next set of staggered gaps and two short F.Cu bus jumps.
    row3_pad = (FFC_X0 + 17, 4.2)
    row3_launch = (row3_pad[0], 5.575)
    row3_approach = (228.6, 19.0)
    row3_drop = (229.0, 19.7)
    board.segment("ROW3", row3_pad, row3_launch, "B.Cu", fan_width)
    board.via("ROW3", row3_launch, 0.6, 0.3)
    board.polyline(
        "ROW3",
        [row3_launch, (228.6, 5.575), row3_approach, row3_drop],
        "F.Cu", fan_width,
    )
    board.via("ROW3", row3_drop, 0.6, 0.3)

    row3_pre_row1 = (211.0, 35.6)
    board.polyline(
        "ROW3",
        [row3_drop, (229.0, 20.4), (219.075, 20.4),
         (219.075, 35.6),
         row3_pre_row1],
        "B.Cu", fan_width,
    )
    row3_post_row1 = (211.0, 37.4)
    board.via("ROW3", row3_pre_row1, 0.6, 0.3)
    board.segment("ROW3", row3_pre_row1, row3_post_row1, "F.Cu", fan_width)
    board.via("ROW3", row3_post_row1, 0.6, 0.3)

    row3_pre_row2 = (223.8375, 54.8)
    board.polyline(
        "ROW3",
        [row3_post_row1, (223.8375, 37.4), row3_pre_row2],
        "B.Cu", fan_width,
    )
    row3_post_row2 = (223.8375, 56.45)
    board.via("ROW3", row3_pre_row2, 0.6, 0.3)
    board.segment("ROW3", row3_pre_row2, row3_post_row2, "F.Cu", fan_width)
    board.via("ROW3", row3_post_row2, 0.6, 0.3)
    row3_gap = (241.6969, 56.45)
    row3_bus = (241.6969, by_row[3][0].y + 8.0)
    board.polyline(
        "ROW3", [row3_post_row2, row3_gap, row3_bus],
        "B.Cu", fan_width,
    )

    # ROW4 leaves the connector directly through the centre switch gap.  This
    # avoids adding a fifth trace to the already full rear-edge F.Cu fan.
    row4_pad = (FFC_X0 + 18, 4.2)
    row4_entry = (row4_pad[0], 15.8)
    board.segment("ROW4", row4_pad, row4_entry, "B.Cu", fan_width)
    board.via("ROW4", row4_entry, 0.6, 0.3)
    row4_drop = (152.5, 19.69)
    board.polyline(
        "ROW4", [row4_entry, (152.5, 15.8), row4_drop],
        "F.Cu", fan_width,
    )
    board.via("ROW4", row4_drop, 0.6, 0.3)

    row4_pre_row1 = (142.875, 35.6)
    board.polyline(
        "ROW4",
        [row4_drop, (142.875, 20.0), row4_pre_row1],
        "B.Cu", fan_width,
    )
    row4_post_row1 = (142.875, 37.4)
    board.via("ROW4", row4_pre_row1, 0.6, 0.3)
    board.segment("ROW4", row4_pre_row1, row4_post_row1, "F.Cu", fan_width)
    board.via("ROW4", row4_post_row1, 0.6, 0.3)

    row4_pre_row2 = (147.6375, 54.8)
    board.polyline(
        "ROW4",
        [row4_post_row1, (147.6375, 37.4), row4_pre_row2],
        "B.Cu", fan_width,
    )
    row4_post_row2 = (147.6375, 56.45)
    board.via("ROW4", row4_pre_row2, 0.6, 0.3)
    board.segment("ROW4", row4_pre_row2, row4_post_row2, "F.Cu", fan_width)
    board.via("ROW4", row4_post_row2, 0.6, 0.3)

    row4_pre_row3 = (165.0, 73.8)
    board.polyline(
        "ROW4",
        [row4_post_row2, (157.1625, 56.45), (157.1625, 71.25),
         (165.0, 71.25), row4_pre_row3],
        "B.Cu", fan_width,
    )
    row4_post_row3 = (165.0, 75.5)
    board.via("ROW4", row4_pre_row3, 0.6, 0.3)
    board.segment("ROW4", row4_pre_row3, row4_post_row3, "F.Cu", fan_width)
    board.via("ROW4", row4_post_row3, 0.6, 0.3)
    row4_gap = (171.45, 75.5)
    row4_bus = (171.45, by_row[4][0].y + 8.0)
    board.polyline(
        "ROW4", [row4_post_row3, row4_gap, row4_bus],
        "B.Cu", fan_width,
    )

    for index, point in enumerate(plate_mount_holes(), 1):
        mounting_hole(board, f"H{index}", point)

    board.text("MINILITE64 • REV B • 2 LAYER", (142.875, 92.2), "F.SilkS", 1.0)
    add_openai_branding(board)
    board.write(out)
    return plate_mount_holes()


if __name__ == "__main__":
    build(
        parse_kle(ROOT / "KLE.txt"),
        ROOT / "build" / "Minilite64_rect_seed.kicad_pcb",
    )
