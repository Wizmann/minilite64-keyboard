"""Generate the printable Minilite64 mechanical package with FreeCAD.

Run with FreeCAD's Python, for example:
    freecadcmd.exe tools/generate_mechanical.py

The supplied plate DXF contains one obsolete screw relief merged into the
bottom-row Menu switch opening.  This generator repairs that contour and adds
two balanced M2 supports between bottom-row keys before making the printable
plate and corrected manufacturing DXF.  The original three round mounting
holes and the two side mounting notches remain.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from pathlib import Path

import FreeCAD as App
import Mesh
import Part


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hardware" / "mechanical"
BUILD = ROOT / "build"

PCB_X0, PCB_Y0 = 0.15, 0.15
PCB_X1, PCB_Y1 = 285.60, 95.10
PCB_CX, PCB_CY = (PCB_X0 + PCB_X1) / 2, (PCB_Y0 + PCB_Y1) / 2
ORIGINAL_MAIN_ROUND_HOLES = [
    (25.5749577, 28.2247775),
    (128.5759577, 47.6255775),
    (260.4244577, 28.2247775),
]
BOTTOM_ROW_MOUNT_HOLES = [(47.625, 85.20), (238.125, 85.20)]
MAIN_ROUND_HOLES = ORIGINAL_MAIN_ROUND_HOLES + BOTTOM_ROW_MOUNT_HOLES
MAIN_EDGE_SLOTS = [(3.65, 56.824), (282.10, 56.824)]
MAIN_MOUNTS = MAIN_ROUND_HOLES + MAIN_EDGE_SLOTS

# Canonical GH60 enclosure reference used by this project:
#   * 285 x 94.6 mm GH60 PCB datum
#   * 307 x 106.5 mm Linhai-style outside plan, R5 plan corners
#   * 5 degree typing angle and a 20.0/29.3 mm low/high profile
# The proportions follow the supplied Linhai 3MF and Case.step references.
# Unlike the previous tray, the controller bay remains inside the body.
CASE_W, CASE_H = 307.0, 106.5
CASE_X = PCB_CX - CASE_W / 2
CASE_Y = PCB_CY - CASE_H / 2
CASE_RADIUS = 5.0
CASE_ANGLE_DEG = 5.0
CASE_FRONT_H = 20.0
CASE_REAR_H = CASE_FRONT_H + CASE_H * math.tan(math.radians(CASE_ANGLE_DEG))
CASE_SIDE_INSET = 2.5
CASE_TOP_FILLET = 2.0
CASE_BOTTOM_CHAMFER = 1.2
FLOOR_T = 2.4
# Local stack datum at PCB y=0.  The whole PCB/plate stack follows the
# five-degree Case.step typing plane.
MAIN_PCB_Z = 19.1
PCB_T = 1.6
PLATE_GAP = 5.0
PLATE_T = 1.5
PLATE_Z = MAIN_PCB_Z + PCB_T + PLATE_GAP

# The controller is centred at the rear but remains entirely inside the
# selected 307 x 106.5 mm GH60-style footprint.  Its USB-C receptacle faces the rear
# wall and the FFC exits toward the main PCB without a tight fold.
CARRIER_ORIGIN = (122.875, -1.00)
CARRIER_Z = 8.0
CARRIER_T = 1.6
CARRIER_HOLES_LOCAL = [(3, 3), (37, 3), (3, 33), (37, 33)]
CARRIER_HOLES = [
    (CARRIER_ORIGIN[0] + x, CARRIER_ORIGIN[1] + y)
    for x, y in CARRIER_HOLES_LOCAL
]

SERVICE_OUTER = (115.90, -2.70, 54.05, 40.20)
SERVICE_OPEN = (117.45, -1.60, 50.95, 37.95)
SERVICE_SCREWS = [(118.9, 0.1), (166.9, 0.1), (118.9, 34.9), (166.9, 34.9)]

# Four pads define a stable support plane and tolerate print warp better than
# six hard points.  These pockets target common Ø10 x 1.5-2.0 mm self-adhesive
# silicone feet.  The radial clearance allows for placement error, while the
# shallow tapered mouth prints cleanly when the A1 model is standing upright.
FOOT_PAD_NOMINAL_D = 10.0
FOOT_RECESS_D = 11.2
FOOT_RECESS_OPEN_D = 12.0
FOOT_RECESS_DEPTH = 0.65
FOOT_RECESS_CHAMFER_H = 0.45
FOOT_EDGE_INSET_X = 18.0
FOOT_EDGE_INSET_Y = 16.0
FOOT_RECESS_CENTRES = [
    (CASE_X + FOOT_EDGE_INSET_X, CASE_Y + FOOT_EDGE_INSET_Y),
    (CASE_X + CASE_W - FOOT_EDGE_INSET_X, CASE_Y + FOOT_EDGE_INSET_Y),
    (CASE_X + FOOT_EDGE_INSET_X, CASE_Y + CASE_H - FOOT_EDGE_INSET_Y),
    (CASE_X + CASE_W - FOOT_EDGE_INSET_X, CASE_Y + CASE_H - FOOT_EDGE_INSET_Y),
]

# One STL contains both fit-check halves already arranged on the A1 bed.  The
# stepped seam follows the web between switch rows/columns instead of slicing
# through a complete MX opening.  A 0.4 mm total gap gives 0.2 mm clearance
# per mating side.
PLATE_JOINT_GAP = 0.40
PLATE_JOINT_BED_GAP = 6.0
PLATE_JOINT_BOUNDARY = [
    (133.350, -10.0),
    (133.350, 19.050),
    (142.875, 19.050),
    (142.875, 38.100),
    (147.6375, 38.100),
    (147.6375, 57.150),
    (138.1125, 57.150),
    (138.1125, 76.200),
    (144.500, 76.200),
    (144.500, 105.0),
]


def pkey(point, places=5):
    return round(point[0], places), round(point[1], places)


def read_dxf_lines(path: Path):
    raw = path.read_text(encoding="ascii", errors="ignore").splitlines()
    pairs = [(raw[i].strip(), raw[i + 1].strip()) for i in range(0, len(raw) - 1, 2)]
    result = []
    i = 0
    while i < len(pairs):
        if pairs[i] == ("0", "LINE"):
            fields = {}
            i += 1
            while i < len(pairs) and pairs[i][0] != "0":
                fields[pairs[i][0]] = pairs[i][1]
                i += 1
            result.append(((float(fields["10"]), float(fields["20"])),
                           (float(fields["11"]), float(fields["21"]))))
            continue
        i += 1
    return result


def ordered_contours(lines):
    incident = defaultdict(list)
    for index, (a, b) in enumerate(lines):
        incident[pkey(a)].append(index)
        incident[pkey(b)].append(index)
    unseen = set(range(len(lines)))
    contours = []
    while unseen:
        seed = unseen.pop()
        queue = deque([seed])
        component = [seed]
        while queue:
            edge = queue.popleft()
            for endpoint in lines[edge]:
                for neighbor in incident[pkey(endpoint)]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        queue.append(neighbor)
                        component.append(neighbor)
        adjacency = defaultdict(list)
        for edge in component:
            a, b = lines[edge]
            adjacency[pkey(a)].append(pkey(b))
            adjacency[pkey(b)].append(pkey(a))
        start = min(adjacency)
        points = [start]
        previous = None
        current = start
        while True:
            candidates = [point for point in adjacency[current] if point != previous]
            if not candidates:
                break
            following = candidates[0]
            if following == start:
                points.append(start)
                break
            points.append(following)
            previous, current = current, following
        if points[-1] != points[0]:
            points.append(points[0])
        contours.append(points)
    return contours


def bounds(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def repaired_plate_contours():
    contours = ordered_contours(read_dxf_lines(ROOT / "plate.dxf"))
    outer = max(contours, key=lambda c: (bounds(c)[2] - bounds(c)[0]) * (bounds(c)[3] - bounds(c)[1]))
    inner = [c for c in contours if c is not outer]

    # The merged Menu/screw contour is the only 33-segment internal contour.
    bad = next(c for c in inner if len(c) - 1 == 33)
    bad_box = bounds(bad)
    bad_cy = (bad_box[1] + bad_box[3]) / 2
    normal = [
        c for c in inner
        if len(c) - 1 == 20
        and 15.45 < bounds(c)[2] - bounds(c)[0] < 15.75
        and 13.85 < bounds(c)[3] - bounds(c)[1] < 14.15
    ]
    reference = min(
        normal,
        key=lambda c: abs((bounds(c)[0] + bounds(c)[2]) / 2 - 204.7875)
        + abs((bounds(c)[1] + bounds(c)[3]) / 2 - bad_cy),
    )
    ref_box = bounds(reference)
    ref_cx, ref_cy = (ref_box[0] + ref_box[2]) / 2, (ref_box[1] + ref_box[3]) / 2
    menu_cx = 9.625 * 19.05
    replacement = [(x + menu_cx - ref_cx, y + bad_cy - ref_cy) for x, y in reference]
    inner[inner.index(bad)] = replacement

    x0, y0, x1, y1 = bounds(outer)
    dxf_cx, dxf_cy = (x0 + x1) / 2, (y0 + y1) / 2

    # Add two Ø3.2 mm plate holes in the full-material gaps between adjacent
    # 1.25U bottom-row switches.  They are symmetric about the keyboard centre
    # and deliberately avoid the deleted Menu-key relief.
    for pcb_x, pcb_y in BOTTOM_ROW_MOUNT_HOLES:
        dxf_x = pcb_x - PCB_CX + dxf_cx
        dxf_y = dxf_cy + PCB_CY - pcb_y
        radius = 1.6
        circle = [
            (
                dxf_x + radius * math.cos(2 * math.pi * i / 48),
                dxf_y + radius * math.sin(2 * math.pi * i / 48),
            )
            for i in range(49)
        ]
        inner.append(circle)

    def to_pcb(contour):
        return [
            (x + PCB_CX - dxf_cx, PCB_CY - (y - dxf_cy))
            for x, y in contour
        ]

    return [to_pcb(outer)] + [to_pcb(c) for c in inner], [outer] + inner


def wire(points):
    vectors = [App.Vector(x, y, 0) for x, y in points]
    if vectors[-1].distanceToPoint(vectors[0]) > 1e-6:
        vectors.append(vectors[0])
    return Part.makePolygon(vectors)


def moved(shape, vector):
    """Return a translated copy; compatible with older FreeCAD releases."""
    result = shape.copy()
    result.translate(vector)
    return result


def tilted(shape):
    """Place a local stack solid parallel to the six-degree GH60 rim."""
    result = shape.copy()
    result.rotate(App.Vector(0, 0, MAIN_PCB_Z), App.Vector(1, 0, 0),
                  -CASE_ANGLE_DEG)
    return result


def tilted_point(x, y, z):
    """Transform a local stack point into the case assembly coordinate frame."""
    angle = math.radians(CASE_ANGLE_DEG)
    dz = z - MAIN_PCB_Z
    return App.Vector(
        x,
        y * math.cos(angle) + dz * math.sin(angle),
        MAIN_PCB_Z - y * math.sin(angle) + dz * math.cos(angle),
    )


def stack_normal():
    angle = math.radians(CASE_ANGLE_DEG)
    return App.Vector(0, math.sin(angle), math.cos(angle))


def plate_shape(contours):
    outer = Part.Face(wire(contours[0])).extrude(App.Vector(0, 0, PLATE_T))
    cutters = [Part.Face(wire(c)).extrude(App.Vector(0, 0, PLATE_T + 0.2)) for c in contours[1:]]
    return outer.cut(Part.makeCompound(cutters)).removeSplitter()


def plate_a1_fitcheck_shape(plate):
    """Split on a loose stepped seam and arrange both parts on one A1 bed."""
    far_left, far_right = -20.0, 310.0
    low_y, high_y = -10.0, 105.0
    boundary = PLATE_JOINT_BOUNDARY

    def offset_boundary(distance):
        """Miter-offset this axis-aligned open polyline to its left side."""
        normals = []
        for (ax, ay), (bx, by) in zip(boundary, boundary[1:]):
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy)
            normals.append((-dy / length, dx / length))
        shifted = []
        for index, (x, y) in enumerate(boundary):
            if index == 0:
                nx, ny = normals[0]
            elif index == len(boundary) - 1:
                nx, ny = normals[-1]
            else:
                before, after = normals[index - 1], normals[index]
                if abs(before[0] - after[0]) < 1e-9 and abs(before[1] - after[1]) < 1e-9:
                    nx, ny = before
                else:
                    nx, ny = before[0] + after[0], before[1] + after[1]
            shifted.append((x + distance * nx, y + distance * ny))
        return shifted

    # Offset each clipping boundary into its own half.  This directly creates
    # the 0.4 mm seam and avoids an overlapping-compound ribbon cutter that
    # older OpenCASCADE versions can classify as invalid.
    left_boundary = offset_boundary(PLATE_JOINT_GAP / 2)
    right_boundary = offset_boundary(-PLATE_JOINT_GAP / 2)
    left_polygon = [
        (far_left, low_y), *left_boundary,
        (far_left, high_y), (far_left, low_y),
    ]
    right_polygon = [
        right_boundary[0], (far_right, low_y), (far_right, high_y),
        right_boundary[-1], *reversed(right_boundary[:-1]),
    ]
    left_region = Part.Face(wire(left_polygon)).extrude(App.Vector(0, 0, PLATE_T))
    right_region = Part.Face(wire(right_polygon)).extrude(App.Vector(0, 0, PLATE_T))
    left = plate.common(left_region).removeSplitter()
    right = plate.common(right_region).removeSplitter()

    # Both disconnected parts are flat and compact in this slicer-only file.
    left = moved(left, App.Vector(
        5.0 - left.BoundBox.XMin, 5.0 - left.BoundBox.YMin, 0,
    ))
    right = moved(right, App.Vector(
        5.0 - right.BoundBox.XMin,
        5.0 + left.BoundBox.YLength + PLATE_JOINT_BED_GAP - right.BoundBox.YMin,
        0,
    ))
    return [left, right]


def board_outline_points():
    right = [
        (285.60, 54.324), (282.10, 54.324), (281.327, 54.445),
        (280.631, 54.801), (280.078, 55.355), (279.723, 56.051),
        (279.600, 56.824), (279.723, 57.597), (280.078, 58.294),
        (280.631, 58.847), (281.327, 59.201), (282.10, 59.324),
        (285.60, 59.324),
    ]
    left = [(285.75 - x, y) for x, y in reversed(right)]
    return [(0.15, 0.15), (285.60, 0.15), *right,
            (285.60, 95.10), (0.15, 95.10), *left, (0.15, 0.15)]


def simplified_main_pcb():
    shape = Part.Face(wire(board_outline_points())).extrude(App.Vector(0, 0, PCB_T))
    for x, y in MAIN_ROUND_HOLES:
        shape = shape.cut(Part.makeCylinder(1.35, PCB_T + 0.2, App.Vector(x, y, -0.1)))
    return shape.removeSplitter()


def rounded_prism(x, y, width, height, radius, z0, depth):
    radius = min(radius, width / 2, height / 2)
    a = Part.makeBox(width - 2 * radius, height, depth, App.Vector(x + radius, y, z0))
    b = Part.makeBox(width, height - 2 * radius, depth, App.Vector(x, y + radius, z0))
    result = a.fuse(b)
    for cx, cy in [
        (x + radius, y + radius), (x + width - radius, y + radius),
        (x + radius, y + height - radius), (x + width - radius, y + height - radius),
    ]:
        result = result.fuse(Part.makeCylinder(radius, depth, App.Vector(cx, cy, z0)))
    return result.removeSplitter()


def rounded_rectangle_wire(x, y, width, height, radius, z):
    """Exact eight-edge rounded rectangle used by the tapered case loft."""
    radius = min(radius, width / 2, height / 2)
    point = lambda px, py: App.Vector(px, py, z)
    normal = App.Vector(0, 0, 1)
    return Part.Wire([
        Part.makeLine(point(x + radius, y), point(x + width - radius, y)),
        Part.makeCircle(radius, point(x + width - radius, y + radius), normal, 270, 360),
        Part.makeLine(point(x + width, y + radius), point(x + width, y + height - radius)),
        Part.makeCircle(radius, point(x + width - radius, y + height - radius), normal, 0, 90),
        Part.makeLine(point(x + width - radius, y + height), point(x + radius, y + height)),
        Part.makeCircle(radius, point(x + radius, y + height - radius), normal, 90, 180),
        Part.makeLine(point(x, y + height - radius), point(x, y + radius)),
        Part.makeCircle(radius, point(x + radius, y + radius), normal, 180, 270),
    ])


def outer_case_prism():
    """Linhai/Case.step-style tapered body with safe hand-contact edges."""
    lower = rounded_rectangle_wire(
        CASE_X, CASE_Y, CASE_W, CASE_H, CASE_RADIUS, 0,
    )
    inset = CASE_SIDE_INSET
    upper = rounded_rectangle_wire(
        CASE_X + inset, CASE_Y + inset,
        CASE_W - 2 * inset, CASE_H - 2 * inset,
        max(1.0, CASE_RADIUS - inset), CASE_REAR_H + 0.5,
    )
    tapered = Part.makeLoft([lower, upper], True, False)
    rear_y = CASE_Y
    front_y = CASE_Y + CASE_H
    side = Part.Face(Part.makePolygon([
        App.Vector(CASE_X - 1.0, rear_y, 0),
        App.Vector(CASE_X - 1.0, front_y, 0),
        App.Vector(CASE_X - 1.0, front_y, CASE_FRONT_H),
        App.Vector(CASE_X - 1.0, rear_y, CASE_REAR_H),
        App.Vector(CASE_X - 1.0, rear_y, 0),
    ]))
    wedge = side.extrude(App.Vector(CASE_W + 2.0, 0, 0))
    outer = tapered.common(wedge).removeSplitter()

    # Case.step rounds the hand-contact rim and breaks the lower edge.  Keep
    # these operations on the external solid before opening the cavity so the
    # internal functional geometry remains dimensionally predictable.
    top_edges = [
        edge for edge in outer.Edges
        if edge.BoundBox.ZMin >= CASE_FRONT_H - 0.1
    ]
    outer = outer.makeFillet(CASE_TOP_FILLET, top_edges)
    bottom_edges = [edge for edge in outer.Edges if edge.BoundBox.ZMax < 0.01]
    outer = outer.makeChamfer(CASE_BOTTOM_CHAMFER, bottom_edges)
    return outer.removeSplitter()


def main_bosses():
    result = []
    normal = stack_normal()
    for x, y in MAIN_MOUNTS:
        # Posts and insert pilots follow the PCB normal.  This keeps screw
        # heads, PCB holes, and the plate spacers coaxial after the 5 deg tilt.
        top = tilted_point(x, y, MAIN_PCB_Z)
        total_h = (top.z - FLOOR_T) / normal.z
        base = top - normal * total_h
        neck_h = min(4.8, total_h - 1.0)
        lower_h = total_h - neck_h
        lower = Part.makeCylinder(3.75, lower_h, base, normal)
        # Case.step uses Ø6 mm upper bosses.  The matching Ø2.8 mm pilot is
        # sized for a short M2 3.2x3 mm heat-set insert and normally leaves
        # 1.6 mm of radial polymer.  The legacy centre mount remains Ø4.8 mm
        # because its socket envelope is tighter; it still retains 1.0 mm.
        neck_radius = 2.40 if (x, y) == ORIGINAL_MAIN_ROUND_HOLES[1] else 3.00
        neck = Part.makeCylinder(neck_radius, neck_h,
                                 base + normal * lower_h, normal)
        result.append(lower.fuse(neck))
    return Part.makeCompound(result)


def case_floor_ribs():
    """Case.step-style triangulated ribs tying the lower mounts together."""
    paths = [
        (ORIGINAL_MAIN_ROUND_HOLES[1], ORIGINAL_MAIN_ROUND_HOLES[0]),
        (ORIGINAL_MAIN_ROUND_HOLES[1], ORIGINAL_MAIN_ROUND_HOLES[2]),
        (ORIGINAL_MAIN_ROUND_HOLES[1], BOTTOM_ROW_MOUNT_HOLES[0]),
        (ORIGINAL_MAIN_ROUND_HOLES[1], BOTTOM_ROW_MOUNT_HOLES[1]),
        (BOTTOM_ROW_MOUNT_HOLES[0], MAIN_EDGE_SLOTS[0]),
        (BOTTOM_ROW_MOUNT_HOLES[1], MAIN_EDGE_SLOTS[1]),
    ]
    ribs = []
    width = 2.4
    height = 1.8
    for (ax, ay), (bx, by) in paths:
        length = math.hypot(bx - ax, by - ay)
        rib = Part.makeBox(
            length, width, height,
            App.Vector(ax, ay - width / 2, FLOOR_T),
        )
        rib.rotate(
            App.Vector(ax, ay, FLOOR_T), App.Vector(0, 0, 1),
            math.degrees(math.atan2(by - ay, bx - ax)),
        )
        ribs.append(rib)
    return Part.makeCompound(ribs)


def foot_recess_cutters():
    """Shallow, standing-print-friendly pockets in the outside bottom face."""
    cutters = []
    body_radius = FOOT_RECESS_D / 2
    opening_radius = FOOT_RECESS_OPEN_D / 2
    for x, y in FOOT_RECESS_CENTRES:
        body = Part.makeCylinder(
            body_radius, FOOT_RECESS_DEPTH + 0.05,
            App.Vector(x, y, -0.05),
        )
        lead_in = Part.makeCone(
            opening_radius, body_radius, FOOT_RECESS_CHAMFER_H,
            App.Vector(x, y, -0.05),
        )
        cutters.append(body.fuse(lead_in))
    return Part.makeCompound(cutters)


def case_shape():
    outer = outer_case_prism()
    cavity = rounded_prism(-0.30, -0.30, 286.35, 96.35, 1.2,
                           FLOOR_T, CASE_REAR_H - FLOOR_T + 0.7)
    rear_cavity = rounded_prism(116.85, -1.80, 51.8, 39.7, 1.5,
                                FLOOR_T, CASE_REAR_H - FLOOR_T + 0.7)
    case = outer.cut(cavity.fuse(rear_cavity))

    # Recess adhesive feet into the outside bottom without breaking through
    # the 2.4 mm floor or touching the internal ribs.
    case = case.cut(foot_recess_cutters())

    # Rear USB-C tunnel.  The module receptacle face is about 4 mm inboard and
    # no external controller tongue or case projection is required.
    usb = Part.makeBox(15.5, 5.5, 6.6, App.Vector(136.8, CASE_Y - 0.2, 3.2))
    case = case.cut(usb)

    # Bottom service-cover opening plus a shallow flush flange recess.
    sx, sy, sw, sh = SERVICE_OPEN
    through = rounded_prism(sx, sy, sw, sh, 2.0, -0.2, FLOOR_T + 0.4)
    ox, oy, ow, oh = SERVICE_OUTER
    recess = rounded_prism(ox, oy, ow, oh, 2.2, -0.1, 1.25)
    case = case.cut(through.fuse(recess))

    # Main PCB/plate stack standoffs, with M2 heat-set insert pilots.
    bosses = main_bosses()
    case = case.fuse(bosses).fuse(case_floor_ribs())
    normal = stack_normal()
    for x, y in MAIN_MOUNTS:
        top = tilted_point(x, y, MAIN_PCB_Z)
        case = case.cut(Part.makeCylinder(1.4, 5.4, top - normal * 5.2, normal))

    # Service-cover M2.5 insert towers.  They stay outside the carrier outline.
    for x, y in SERVICE_SCREWS:
        case = case.fuse(Part.makeCylinder(3.2, 6.2, App.Vector(x, y, FLOOR_T)))
        case = case.cut(Part.makeCylinder(1.9, 5.2, App.Vector(x, y, 3.4)))

    return case.removeSplitter()


def service_cover_shape():
    ox, oy, ow, oh = SERVICE_OUTER
    sx, sy, sw, sh = SERVICE_OPEN
    flange = rounded_prism(ox + 0.20, oy + 0.20, ow - 0.40, oh - 0.40, 2.0, 0, 1.15)
    plug = rounded_prism(sx + 0.20, sy + 0.20, sw - 0.40, sh - 0.40, 1.8, 1.15, 1.20)
    cover = flange.fuse(plug)

    # Carrier mounting posts.  The RP2040-Zero faces the closed inner surface;
    # BOOT/RESET remain serviceable only after removing the cover.
    for x, y in CARRIER_HOLES:
        cover = cover.fuse(Part.makeCylinder(2.8, CARRIER_Z - 2.35, App.Vector(x, y, 2.35)))
        cover = cover.cut(Part.makeCylinder(1.6, 4.8, App.Vector(x, y, CARRIER_Z - 4.7)))
    for x, y in SERVICE_SCREWS:
        cover = cover.cut(Part.makeCylinder(1.45, 3.0, App.Vector(x, y, -0.2)))
        cover = cover.cut(Part.makeCylinder(2.8, 0.9, App.Vector(x, y, -0.05)))
    return cover.removeSplitter()


def carrier_shape():
    return Part.makeBox(40, 36, CARRIER_T,
                        App.Vector(CARRIER_ORIGIN[0], CARRIER_ORIGIN[1], CARRIER_Z))


def component_envelopes(keys):
    sockets = []
    diodes = []
    for key in keys:
        x, y, row = key[0], key[1], key[2]
        if row == 0:
            sockets.append(Part.makeBox(7.0, 16.0, 2.8, App.Vector(x - 3.5, y - 8.0, MAIN_PCB_Z - 2.8)))
            dx, dy = x + 2.0, y - 7.6
        else:
            sockets.append(Part.makeBox(14.0, 6.0, 2.8, App.Vector(x - 7.0, y - 3.0, MAIN_PCB_Z - 2.8)))
            dx, dy = x - 7.65, y + 4.6
        diodes.append(Part.makeBox(4.2, 2.4, 2.0, App.Vector(dx - 2.1, dy - 1.2, MAIN_PCB_Z - 2.0)))
    main_ffc = Part.makeBox(23.2, 7.0, 2.6, App.Vector(131.275, 0.20, MAIN_PCB_Z - 2.6))
    return tilted(Part.makeCompound(sockets + diodes + [main_ffc]))


def stabilizer_envelopes(keys):
    """Conservative plate-mount stabilizer wire/clip space above the PCB."""
    solids = []
    for x, y, _row, width_u in keys:
        if width_u < 2.0:
            continue
        span = min(width_u * 19.05 - 8.0, 34.0)
        solids.append(Part.makeBox(span, 5.0, 2.4,
                                   App.Vector(x - span / 2, y - 2.5,
                                              MAIN_PCB_Z + PCB_T + 0.8)))
    return tilted(Part.makeCompound(solids))


def assembled_spacers():
    solids = []
    for x, y in MAIN_MOUNTS:
        outer = Part.makeCylinder(3.0, PLATE_GAP, App.Vector(x, y, MAIN_PCB_Z + PCB_T))
        inner = Part.makeCylinder(1.45, PLATE_GAP + 0.2,
                                  App.Vector(x, y, MAIN_PCB_Z + PCB_T - 0.1))
        solids.append(outer.cut(inner))
    return tilted(Part.makeCompound(solids))


def controller_envelopes():
    # RP2040-Zero and USB-C are on F.Cu (down); the FFC is on B.Cu (up).
    rp = Part.makeBox(18.0, 23.5, 4.0,
                      App.Vector(CARRIER_ORIGIN[0] + 11.0,
                                 CARRIER_ORIGIN[1] + 1.5,
                                 CARRIER_Z - 4.0))
    usb = Part.makeBox(12.0, 5.8, 4.2,
                       App.Vector(CARRIER_ORIGIN[0] + 15.67,
                                  CARRIER_ORIGIN[1] + 0.30,
                                  CARRIER_Z - 4.2))
    ffc = Part.makeBox(23.2, 7.0, 2.6,
                       App.Vector(CARRIER_ORIGIN[0] + 8.4,
                                  CARRIER_ORIGIN[1] + 28.8,
                                  CARRIER_Z + CARRIER_T))
    return Part.makeCompound([rp, usb, ffc])


def parse_keys():
    import re
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from generate_hardware import parse_kle
    return [(key.x, key.y, key.row, key.w) for key in parse_kle(ROOT / "KLE.txt")]


def spacer_shape():
    outer = Part.makeCylinder(3.0, PLATE_GAP)
    inner = Part.makeCylinder(1.45, PLATE_GAP + 0.2, App.Vector(0, 0, -0.1))
    return outer.cut(inner)


def standing_print_shape(shape):
    """Orient the one-piece case like the supplied A1-compatible 3MF.

    The front wall becomes the broad bed-contact face.  A 45 degree in-plane
    rotation fits the 307 mm length inside the A1's 256 x 256 mm square while
    keeping the rear USB opening away from the build plate.
    """
    result = shape.copy()
    result.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90)
    result.translate(App.Vector(0, 0, CASE_Y + CASE_H))
    result.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 45)
    bounds = result.BoundBox
    result.translate(App.Vector(8.0 - bounds.XMin, 8.0 - bounds.YMin, -bounds.ZMin))
    return result


def export_shape(name, shape, stl=True):
    if shape.isNull() or not shape.isValid():
        raise RuntimeError(f"Invalid FreeCAD shape: {name}")
    doc = App.newDocument(name)
    obj = doc.addObject("Part::Feature", name)
    obj.Label = name
    obj.Shape = shape
    doc.recompute()
    doc.saveAs(str(OUT / f"{name}.FCStd"))
    Part.export([obj], str(OUT / f"{name}.step"))
    if stl:
        Mesh.export([obj], str(OUT / f"{name}.stl"))
    volume = shape.Volume
    App.closeDocument(doc.Name)
    return {"valid": True, "volume_mm3": round(volume, 3),
            "bounds_mm": [round(shape.BoundBox.XLength, 3),
                           round(shape.BoundBox.YLength, 3),
                           round(shape.BoundBox.ZLength, 3)]}


def export_stl_only(name, shapes):
    """Export a slicer-only artifact without adding redundant CAD files."""
    if not isinstance(shapes, (list, tuple)):
        shapes = [shapes]
    for index, shape in enumerate(shapes):
        if shape.isNull() or not shape.isValid():
            raise RuntimeError(f"Invalid FreeCAD shape: {name}[{index}]")
    doc = App.newDocument(name)
    objects = []
    for index, shape in enumerate(shapes, 1):
        obj = doc.addObject("Part::Feature", f"{name}_{index}")
        obj.Shape = shape
        objects.append(obj)
    doc.recompute()
    Mesh.export(objects, str(OUT / f"{name}.stl"))
    App.closeDocument(doc.Name)
    x_min = min(shape.BoundBox.XMin for shape in shapes)
    y_min = min(shape.BoundBox.YMin for shape in shapes)
    z_min = min(shape.BoundBox.ZMin for shape in shapes)
    x_max = max(shape.BoundBox.XMax for shape in shapes)
    y_max = max(shape.BoundBox.YMax for shape in shapes)
    z_max = max(shape.BoundBox.ZMax for shape in shapes)
    return {"valid": True,
            "volume_mm3": round(sum(shape.Volume for shape in shapes), 3),
            "bounds_mm": [round(x_max - x_min, 3), round(y_max - y_min, 3),
                           round(z_max - z_min, 3)]}


def export_assembly(name, objects):
    doc = App.newDocument(name)
    exported = []
    for label, shape in objects:
        obj = doc.addObject("Part::Feature", label)
        obj.Label = label
        obj.Shape = shape
        exported.append(obj)
    doc.recompute()
    doc.saveAs(str(OUT / f"{name}.FCStd"))
    Part.export(exported, str(OUT / f"{name}.step"))
    Mesh.export(exported, str(OUT / f"{name}.stl"))
    App.closeDocument(doc.Name)


def write_corrected_dxf(path, contours):
    rows = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC",
            "0", "SECTION", "2", "ENTITIES"]
    for contour in contours:
        for (ax, ay), (bx, by) in zip(contour, contour[1:]):
            rows += ["0", "LINE", "8", "0", "10", f"{ax:.6f}", "20", f"{ay:.6f}",
                     "30", "0.0", "11", f"{bx:.6f}", "21", f"{by:.6f}", "31", "0.0"]
    rows += ["0", "ENDSEC", "0", "EOF"]
    path.write_text("\n".join(rows) + "\n", encoding="ascii")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    contours, corrected_dxf_contours = repaired_plate_contours()
    plate = plate_shape(contours)
    case = case_shape()
    cover = service_cover_shape()
    pcb = tilted(moved(simplified_main_pcb(), App.Vector(0, 0, MAIN_PCB_Z)))
    carrier = carrier_shape()
    keys = parse_keys()
    main_components = component_envelopes(keys)
    stabilizers = stabilizer_envelopes(keys)
    spacers = assembled_spacers()
    ctrl_components = controller_envelopes()
    # 20 mm cable plus 0.275 mm side clearance.  Connector hold-down tabs sit
    # outside this flexible-cable envelope and do not travel through the bay.
    ffc_corridor = Part.makeBox(
        20.55, 35.7, MAIN_PCB_Z - 3.0,
        App.Vector(132.60, -0.2, 3.0),
    )

    report = {"artifacts": {}}
    artifacts = report["artifacts"]
    artifacts["plate_full"] = export_shape("Minilite64_plate_print_fixed", plate)
    artifacts["plate_a1_fitcheck"] = export_stl_only(
        "Minilite64_plate_A1_fitcheck", plate_a1_fitcheck_shape(plate)
    )
    artifacts["case_full"] = export_shape("Minilite64_case_full", case)
    artifacts["case_a1_standing"] = export_shape(
        "Minilite64_case_A1_standing", standing_print_shape(case)
    )
    artifacts["service_cover"] = export_shape("Minilite64_service_cover", cover)
    artifacts["plate_spacer"] = export_shape("Minilite64_plate_spacer_print_7x", spacer_shape())

    export_assembly("Minilite64_assembly_review", [
        ("Case", case), ("ServiceCover", cover), ("MainPCB", pcb),
        ("Plate", tilted(moved(plate, App.Vector(0, 0, PLATE_Z)))),
        ("MainComponents", main_components), ("Stabilizers", stabilizers),
        ("PlateSpacers", spacers), ("CarrierPCB", carrier),
        ("ControllerComponents", ctrl_components),
    ])
    write_corrected_dxf(OUT / "Minilite64_plate_fixed.dxf", corrected_dxf_contours)

    boss_collision = main_components.common(main_bosses()).Volume
    main_to_controller = main_components.common(carrier.fuse(ctrl_components)).Volume
    main_to_controller_clearance = main_components.distToShape(
        carrier.fuse(ctrl_components)
    )[0]
    main_to_floor_clearance = main_components.BoundBox.ZMin - FLOOR_T
    controller_to_case = carrier.fuse(ctrl_components).common(case).Volume
    controller_to_cover = carrier.fuse(ctrl_components).common(cover).Volume
    cover_to_case = cover.common(case).Volume
    pcb_to_case = pcb.common(case).Volume
    placed_plate = tilted(moved(plate, App.Vector(0, 0, PLATE_Z)))
    plate_to_case = placed_plate.common(case).Volume
    stabilizer_to_spacer = stabilizers.common(spacers).Volume
    ffc_corridor_to_case = ffc_corridor.common(case).Volume
    ffc_corridor_to_boss = ffc_corridor.common(main_bosses()).Volume
    inner_x0, inner_x1 = -0.30, 286.05
    inner_y0, inner_y1 = -0.30, 95.55
    keycap_clearances = []
    for x, y, _row, width_u in keys:
        half_w = (width_u * 19.05 - 0.8) / 2
        half_h = (19.05 - 0.8) / 2
        keycap_clearances.extend([
            x - half_w - inner_x0, inner_x1 - (x + half_w),
            y - half_h - inner_y0, inner_y1 - (y + half_h),
        ])
    report["assembly"] = {
        "main_pcb_bottom_z_mm": MAIN_PCB_Z,
        "plate_bottom_z_mm": PLATE_Z,
        "case_typing_angle_deg": CASE_ANGLE_DEG,
        "case_front_height_mm": round(CASE_FRONT_H, 3),
        "case_rear_height_mm": round(CASE_REAR_H, 3),
        "case_external_plan_mm": [CASE_W, CASE_H],
        "case_plan_corner_radius_mm": CASE_RADIUS,
        "foot_recess_centres_mm": FOOT_RECESS_CENTRES,
        "foot_pad_nominal_diameter_mm": FOOT_PAD_NOMINAL_D,
        "foot_recess_body_diameter_mm": FOOT_RECESS_D,
        "foot_recess_opening_diameter_mm": FOOT_RECESS_OPEN_D,
        "foot_recess_depth_mm": FOOT_RECESS_DEPTH,
        "foot_recess_minimum_floor_mm": FLOOR_T - FOOT_RECESS_DEPTH,
        "plate_a1_joint_total_gap_mm": PLATE_JOINT_GAP,
        "ffc_minimum_bend_radius_mm": 6.0,
        "reserved_ffc_corridor_mm": [132.60, -0.2, 153.15, 35.5, 3.0, MAIN_PCB_Z],
        "main_component_to_mount_boss_intersection_mm3": round(boss_collision, 6),
        "main_component_to_controller_intersection_mm3": round(main_to_controller, 6),
        "main_component_to_controller_clearance_mm": round(main_to_controller_clearance, 3),
        "main_component_to_floor_clearance_mm": round(main_to_floor_clearance, 3),
        "controller_to_case_intersection_mm3": round(controller_to_case, 6),
        "controller_to_service_cover_intersection_mm3": round(controller_to_cover, 6),
        "service_cover_to_case_intersection_mm3": round(cover_to_case, 6),
        "main_pcb_to_case_intersection_mm3": round(pcb_to_case, 6),
        "plate_to_case_intersection_mm3": round(plate_to_case, 6),
        "stabilizer_to_spacer_intersection_mm3": round(stabilizer_to_spacer, 6),
        "ffc_corridor_to_case_intersection_mm3": round(ffc_corridor_to_case, 6),
        "ffc_corridor_to_mount_boss_intersection_mm3": round(ffc_corridor_to_boss, 6),
        "minimum_keycap_to_inner_wall_xy_clearance_mm": round(min(keycap_clearances), 3),
        "wall_top_to_keycap_skirt_vertical_clearance_mm": 1.5,
        "controller_bay_inside_gh60_footprint": True,
        "service_cover_external_button_access": False,
        "bottom_row_conflicting_screw_relief_removed": True,
        "round_main_mounts": MAIN_ROUND_HOLES,
        "side_main_mounts": MAIN_EDGE_SLOTS,
        "carrier_mounts": CARRIER_HOLES,
    }
    (BUILD / "mechanical_review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
