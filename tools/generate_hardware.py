"""Generate the Minilite64 KiCad boards, source schematics and manufacturing data.

The project is intentionally generated from a compact, reviewable Python source:
the 64-key physical layout, matrix assignment, routes, footprints, BOM and pin map
all live here.  No third-party Python modules are required.
"""

from __future__ import annotations

import csv
import json
import math
import re
import uuid
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PITCH = 19.05
BOARD_W = 285.75
BOARD_H = 95.25
FFC_PITCH = 1.0
# A small central rear tongue carries the hand-solderable 20P connector.
# Columns fan left and right in a 2.5 mm edge corridor; no full-width wing.
FFC_X0 = BOARD_W / 2 - 9.5
FFC_Y = -0.4
ROW_TRACK_X = [280.6, 281.5, 282.4, 283.3, 284.2]
# Pin 8..14 run in reverse physical order so the right-hand fan cannot cross.
FFC_NETS = [*(f"COL{i}" for i in range(14)), *(f"ROW{i}" for i in range(5)), "GND"]

# Official OpenAI monoblossom path from:
# https://developers.openai.com/assets/OpenAI-black-monoblossom.svg
OPENAI_BLOSSOM_PATH = """M304.246 294.611V249.028C304.246 245.189 305.687 242.309 309.044 240.392L400.692 187.612C413.167 180.415 428.042 177.058 443.394 177.058C500.971 177.058 537.44 221.682 537.44 269.182C537.44 272.54 537.44 276.379 536.959 280.218L441.954 224.558C436.197 221.201 430.437 221.201 424.68 224.558L304.246 294.611ZM518.245 472.145V363.224C518.245 356.505 515.364 351.707 509.608 348.349L389.174 278.296L428.519 255.743C431.877 253.826 434.757 253.826 438.115 255.743L529.762 308.523C556.154 323.879 573.905 356.505 573.905 388.171C573.905 424.636 552.315 458.225 518.245 472.141V472.145ZM275.937 376.182L236.592 353.152C233.235 351.235 231.794 348.354 231.794 344.515V238.956C231.794 187.617 271.139 148.749 324.4 148.749C344.555 148.749 363.264 155.468 379.102 167.463L284.578 222.164C278.822 225.521 275.942 230.319 275.942 237.039V376.186L275.937 376.182ZM360.626 425.122L304.246 393.455V326.283L360.626 294.616L417.002 326.283V393.455L360.626 425.122ZM396.852 570.989C376.698 570.989 357.989 564.27 342.151 552.276L436.674 497.574C442.431 494.217 445.311 489.419 445.311 482.699V343.552L485.138 366.582C488.495 368.499 489.936 371.379 489.936 375.219V480.778C489.936 532.117 450.109 570.985 396.852 570.985V570.989ZM283.134 463.99L191.486 411.211C165.094 395.854 147.343 363.229 147.343 331.562C147.343 294.616 169.415 261.509 203.48 247.593V356.991C203.48 363.71 206.361 368.508 212.117 371.866L332.074 441.437L292.729 463.99C289.372 465.907 286.491 465.907 283.134 463.99ZM277.859 542.68C223.639 542.68 183.813 501.895 183.813 451.514C183.813 447.675 184.294 443.836 184.771 439.997L279.295 494.698C285.051 498.056 290.812 498.056 296.568 494.698L417.002 425.127V470.71C417.002 474.549 415.562 477.429 412.204 479.346L320.557 532.126C308.081 539.323 293.206 542.68 277.854 542.68H277.859ZM396.852 599.776C454.911 599.776 503.37 558.513 514.41 503.812C568.149 489.896 602.696 439.515 602.696 388.176C602.696 354.587 588.303 321.962 562.392 298.45C564.791 288.373 566.231 278.296 566.231 268.224C566.231 199.611 510.571 148.267 446.274 148.267C433.322 148.267 420.846 150.184 408.37 154.505C386.775 133.392 357.026 119.958 324.4 119.958C266.342 119.958 217.883 161.22 206.843 215.921C153.104 229.837 118.557 280.218 118.557 331.557C118.557 365.146 132.95 397.771 158.861 421.283C156.462 431.36 155.022 441.437 155.022 451.51C155.022 520.123 210.682 571.466 274.978 571.466C287.931 571.466 300.407 569.549 312.883 565.228C334.473 586.341 364.222 599.776 396.852 599.776Z"""


def uid(name: str) -> str:
    return str(uuid.uuid5(uuid.UUID("71c1f736-55ce-4dc8-950f-7212df82e306"), name))


def fmt(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text if text not in {"", "-0"} else "0"


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " / ")


@dataclass
class Key:
    index: int
    row: int
    col: int
    label: str
    x: float
    y: float
    w: float
    h: float = 1.0

    @property
    def ref(self) -> str:
        return f"SW{self.index + 1}"

    @property
    def diode(self) -> str:
        return f"D{self.index + 1}"


def parse_kle(path: Path) -> list[Key]:
    # KLE raw data is a sequence of JSON arrays separated by commas.
    raw = path.read_text(encoding="utf-8").strip()
    # KLE's "raw data" format is JavaScript-like and leaves metadata keys
    # unquoted (for example {w:2}); quote them before feeding json.loads.
    raw = re.sub(r"([{,])\s*([A-Za-z][A-Za-z0-9_]*)\s*:", r'\1"\2":', raw)
    rows = json.loads("[" + raw + "]")
    keys: list[Key] = []
    index = 0
    y = 0.0
    for matrix_row, items in enumerate(rows):
        x = 0.0
        width = height = 1.0
        physical_col = 0
        for item in items:
            if isinstance(item, dict):
                x += float(item.get("x", 0))
                y += float(item.get("y", 0))
                width = float(item.get("w", 1))
                height = float(item.get("h", 1))
                continue
            keys.append(
                Key(
                    index=index,
                    row=matrix_row,
                    col=physical_col,
                    label=str(item),
                    x=(x + width / 2) * PITCH,
                    y=(y + height / 2) * PITCH,
                    w=width,
                    h=height,
                )
            )
            index += 1
            physical_col += 1
            x += width
            width = height = 1.0
        y += 1.0
    counts = [sum(k.row == row for k in keys) for row in range(5)]
    if len(keys) != 64 or counts != [14, 14, 13, 12, 11]:
        raise ValueError(f"Unexpected KLE: {len(keys)} keys, row counts {counts}")
    return keys


class Board:
    def __init__(self, title: str):
        self.title = title
        self.nets = {"": 0}
        self.items: list[str] = []
        self.counter = 0

    def net(self, name: str) -> int:
        if name not in self.nets:
            self.nets[name] = len(self.nets)
        return self.nets[name]

    def uuid(self, kind: str) -> str:
        self.counter += 1
        return uid(f"{self.title}-{kind}-{self.counter}")

    def add(self, text: str):
        self.items.append(text)

    def segment(self, net: str, a, b, layer: str, width: float = 0.25):
        if math.dist(a, b) < 1e-7:
            return
        self.add(
            f'  (segment (start {fmt(a[0])} {fmt(a[1])}) (end {fmt(b[0])} {fmt(b[1])}) '
            f'(width {fmt(width)}) (layer "{layer}") (net {self.net(net)}) (uuid {self.uuid("seg")}))'
        )

    def polyline(self, net: str, points, layer: str, width: float = 0.25):
        for a, b in zip(points, points[1:]):
            self.segment(net, a, b, layer, width)

    def mitered_polyline(self, net: str, points, layer: str, width: float = 0.25, chamfer: float = 0.7):
        """Route a polyline with short diagonal cuts instead of sharp corners."""
        if len(points) < 3:
            self.polyline(net, points, layer, width)
            return
        routed = [points[0]]
        for previous, corner, following in zip(points, points[1:], points[2:]):
            vin = (corner[0] - previous[0], corner[1] - previous[1])
            vout = (following[0] - corner[0], following[1] - corner[1])
            lin, lout = math.hypot(*vin), math.hypot(*vout)
            if lin < 1e-6 or lout < 1e-6:
                continue
            uin, uout = (vin[0] / lin, vin[1] / lin), (vout[0] / lout, vout[1] / lout)
            if abs(uin[0] * uout[1] - uin[1] * uout[0]) < 1e-5:
                routed.append(corner)
                continue
            distance = min(chamfer, lin * 0.25, lout * 0.25)
            routed.append((corner[0] - uin[0] * distance, corner[1] - uin[1] * distance))
            routed.append((corner[0] + uout[0] * distance, corner[1] + uout[1] * distance))
        routed.append(points[-1])
        self.polyline(net, routed, layer, width)

    def via(self, net: str, point, size=0.7, drill=0.3):
        self.add(
            f'  (via (at {fmt(point[0])} {fmt(point[1])}) (size {fmt(size)}) (drill {fmt(drill)}) '
            f'(layers "F.Cu" "B.Cu") (net {self.net(net)}) (uuid {self.uuid("via")}))'
        )

    def edge(self, a, b, width=0.05):
        self.add(
            f'  (gr_line (start {fmt(a[0])} {fmt(a[1])}) (end {fmt(b[0])} {fmt(b[1])}) '
            f'(stroke (width {fmt(width)}) (type default)) (layer "Edge.Cuts") (uuid {self.uuid("edge")}))'
        )

    def text(self, value, point, layer="F.SilkS", size=1.2, justify=""):
        justify_expr = f" (justify {justify})" if justify else ""
        self.add(
            f'  (gr_text "{esc(value)}" (at {fmt(point[0])} {fmt(point[1])}) (layer "{layer}") '
            f'(uuid {self.uuid("text")}) (effects (font (size {fmt(size)} {fmt(size)}) (thickness 0.18)){justify_expr}))'
        )

    def polygon(self, points, layer="F.SilkS"):
        pts = " ".join(f"(xy {fmt(x)} {fmt(y)})" for x, y in points)
        self.add(
            f'  (gr_poly (pts {pts}) (stroke (width 0) (type default)) (fill solid) '
            f'(layer "{layer}") (uuid {self.uuid("poly")}))'
        )

    def graphic_line(self, a, b, layer="F.SilkS", width=0.18):
        self.add(
            f'  (gr_line (start {fmt(a[0])} {fmt(a[1])}) '
            f'(end {fmt(b[0])} {fmt(b[1])}) '
            f'(stroke (width {fmt(width)}) (type default)) '
            f'(layer "{layer}") (uuid {self.uuid("graphic-line")}))'
        )

    def write(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        layers = '''  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (34 "B.Paste" user "b.paste")
    (35 "F.Paste" user "f.paste")
    (36 "B.SilkS" user "b.silkscreen")
    (37 "F.SilkS" user "f.silkscreen")
    (38 "B.Mask" user "b.mask")
    (39 "F.Mask" user "f.mask")
    (44 "Edge.Cuts" user)
    (46 "B.CrtYd" user "b.courtyard")
    (47 "F.CrtYd" user "f.courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )'''
        net_lines = [f'  (net {number} "{esc(name)}")' for name, number in self.nets.items()]
        content = [
            '(kicad_pcb (version 20240108) (generator "minilite-generator")',
            '  (general (thickness 1.6))',
            '  (paper "A3")',
            layers,
            '  (setup (pad_to_mask_clearance 0) (allow_soldermask_bridges_in_footprints no))',
            *net_lines,
            *self.items,
            ')',
            '',
        ]
        path.write_text("\n".join(content), encoding="utf-8")


def svg_path_polygons(path_data: str, curve_steps: int = 7):
    """Convert the official absolute M/L/H/V/C/Z path into sampled polygons."""
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", path_data)
    command = None
    index = 0
    current = (0.0, 0.0)
    start = None
    polygon = []
    polygons = []
    counts = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6}
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
            if command == "Z":
                if polygon:
                    polygons.append(polygon)
                polygon = []
                current = start or current
                start = None
                command = None
                continue
        if command not in counts:
            raise ValueError(f"Unsupported SVG command {command}")
        count = counts[command]
        values = list(map(float, tokens[index:index + count]))
        index += count
        if command == "M":
            current = (values[0], values[1])
            if polygon:
                polygons.append(polygon)
            polygon = [current]
            start = current
            command = "L"  # Additional coordinate pairs after M are lines.
        elif command == "L":
            current = (values[0], values[1])
            polygon.append(current)
        elif command == "H":
            current = (values[0], current[1])
            polygon.append(current)
        elif command == "V":
            current = (current[0], values[0])
            polygon.append(current)
        elif command == "C":
            p0 = current
            p1, p2, p3 = (values[0], values[1]), (values[2], values[3]), (values[4], values[5])
            for step in range(1, curve_steps + 1):
                t = step / curve_steps
                u = 1 - t
                polygon.append((
                    u**3 * p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
                    u**3 * p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1],
                ))
            current = p3
    if polygon:
        polygons.append(polygon)
    return polygons


def add_openai_branding(board: Board, left=140.125, top=82.975, layer="F.SilkS"):
    # Use the official monoblossom contours as strokes.  Filling each SVG
    # sub-path independently closes its negative spaces and turns a small
    # silkscreen logo into a dark blob; the outline remains crisp at PCB size.
    polygons = svg_path_polygons(OPENAI_BLOSSOM_PATH, curve_steps=4)
    all_points = [point for polygon in polygons for point in polygon]
    x0, x1 = min(p[0] for p in all_points), max(p[0] for p in all_points)
    y0, y1 = min(p[1] for p in all_points), max(p[1] for p in all_points)
    scale = 5.5 / max(x1 - x0, y1 - y0)
    for polygon in polygons:
        points = [(left + (x-x0)*scale, top + (y-y0)*scale) for x, y in polygon]
        for a, b in zip(points, points[1:] + points[:1]):
            board.graphic_line(a, b, layer, 0.18)
    board.text(
        "MINILITE • DESIGNED WITH CODEX", (139.0, 78.5), layer, 0.9,
        "mirror" if layer.startswith("B.") else "",
    )


def property_text(name, value, at, layer, ident, hide=False):
    hidden = " hide" if hide else ""
    justify = " (justify mirror)" if layer.startswith("B.") else ""
    return (
        f'    (property "{name}" "{esc(value)}" (at {fmt(at[0])} {fmt(at[1])} 0) '
        f'(layer "{layer}"){hidden} (uuid {ident}) '
        f'(effects (font (size 0.8 0.8) (thickness 0.12)){justify}))'
    )


def pad(board: Board, number: str, kind: str, shape: str, at, size, layers, net="", drill=None, rr=None):
    if isinstance(drill, tuple):
        drill_expr = f' (drill oval {fmt(drill[0])} {fmt(drill[1])})'
    else:
        drill_expr = f' (drill {fmt(drill)})' if drill else ""
    rr_expr = f' (roundrect_rratio {fmt(rr)})' if rr is not None else ""
    net_expr = f' (net {board.net(net)} "{esc(net)}")' if number and net else ""
    return (
        f'    (pad "{number}" {kind} {shape} (at {fmt(at[0])} {fmt(at[1])}) '
        f'(size {fmt(size[0])} {fmt(size[1])}){drill_expr} (layers {" ".join(fchr(x) for x in layers)})'
        f'{rr_expr}{net_expr} (uuid {board.uuid("pad")}))'
    )


def fchr(value: str) -> str:
    return f'"{value}"'


def switch_footprint(board: Board, key: Key, rotated=False):
    x, y = key.x, key.y
    col = f"COL{key.col}"
    intermediate = f"KEY{key.index + 1}_D"
    lines = [
        f'  (footprint "Kailh_MX_Hotswap" (layer "F.Cu") (at {fmt(x)} {fmt(y)}{ " 180" if rotated else ""})',
        f'    (uuid {uid(f"sw-fp-{key.index}")})',
        '    (attr smd)',
        property_text("Reference", key.ref, (0, -8.0), "B.Fab", uid(f"sw-ref-{key.index}")),
        property_text("Value", f"Kailh MX hotswap / {key.label}", (0, 8.0), "B.Fab", uid(f"sw-val-{key.index}"), True),
        '    (fp_rect (start -7 -7) (end 7 7) (stroke (width 0.2) (type default)) (fill none) (layer "F.Fab") (uuid ' + uid(f"sw-body-{key.index}") + '))',
        pad(board, "", "np_thru_hole", "circle", (0, 0), (4.1, 4.1), ["*.Cu", "*.Mask"], drill=4.1),
        pad(board, "", "np_thru_hole", "circle", (-5.08, 0), (1.9, 1.9), ["*.Cu", "*.Mask"], drill=1.9),
        pad(board, "", "np_thru_hole", "circle", (5.08, 0), (1.9, 1.9), ["*.Cu", "*.Mask"], drill=1.9),
        pad(board, "", "np_thru_hole", "circle", (-2.54, -5.08), (3, 3), ["*.Cu", "*.Mask"], drill=3),
        pad(board, "", "np_thru_hole", "circle", (3.81, -2.54), (3, 3), ["*.Cu", "*.Mask"], drill=3),
        pad(board, "1", "smd", "roundrect", (7.085, -2.54), (2.55, 2.5), ["B.Cu", "B.Paste", "B.Mask"], col, rr=0.12),
        pad(board, "2", "smd", "roundrect", (-5.842, -5.08), (2.55, 2.5), ["B.Cu", "B.Paste", "B.Mask"], intermediate, rr=0.12),
        '  )',
    ]
    board.add("\n".join(lines))


def diode_footprint(board: Board, key: Key, right_side=False):
    # Vertical SOD-123, placed on the back left edge of the switch envelope.
    x, y = key.x + (7.65 if right_side else -7.65), key.y
    intermediate = f"KEY{key.index + 1}_D"
    row = f"ROW{key.row}"
    lines = [
        f'  (footprint "SOD-123_HandSolder" (layer "F.Cu") (at {fmt(x)} {fmt(y)})',
        f'    (uuid {uid(f"d-fp-{key.index}")})',
        '    (attr smd)',
        property_text("Reference", key.diode, (0, 0), "B.Fab", uid(f"d-ref-{key.index}")),
        property_text("Value", "1N4148W SOD-123", (0, 0), "B.Fab", uid(f"d-val-{key.index}"), True),
        '    (fp_rect (start -1.25 3.65) (end 1.25 5.55) (stroke (width 0.16) (type default)) (fill none) (layer "B.Fab") (uuid ' + uid(f"d-body-{key.index}") + '))',
        '    (fp_line (start -1.4 5.75) (end 1.4 5.75) (stroke (width 0.3) (type default)) (layer "B.Fab") (uuid ' + uid(f"d-k-{key.index}") + '))',
        pad(board, "1", "smd", "roundrect", (0, 2.7), (2.2, 2.4), ["B.Cu", "B.Paste", "B.Mask"], intermediate, rr=0.18),
        pad(board, "2", "smd", "roundrect", (0, 6.5), (2.2, 2.4), ["B.Cu", "B.Paste", "B.Mask"], row, rr=0.18),
        '  )',
    ]
    board.add("\n".join(lines))


def top_row_diode_footprint(board: Board, key: Key):
    """Horizontal SOD-123 below a 180-degree top-row hot-swap socket.

    This keeps both diode pads out of the rear FFC corridor and avoids the
    rotated socket pads.  Pad 1 is directly below socket contact 2; pad 2
    drops to the row bus in the inter-row corridor.
    """
    anode = (key.x + 5.842, key.y + 8.0)
    cathode = (key.x + 9.642, key.y + 8.0)
    body_x = (anode[0] + cathode[0]) / 2
    intermediate = f"KEY{key.index + 1}_D"
    row = f"ROW{key.row}"
    lines = [
        f'  (footprint "SOD-123_HandSolder_Horizontal" (layer "F.Cu") (at 0 0)',
        f'    (uuid {uid(f"d-fp-{key.index}")})',
        '    (attr smd)',
        property_text("Reference", key.diode, (body_x, key.y + 8.0), "B.Fab", uid(f"d-ref-{key.index}")),
        property_text("Value", "1N4148W SOD-123", (body_x, key.y + 8.0), "B.Fab", uid(f"d-val-{key.index}"), True),
        f'    (fp_rect (start {fmt(body_x - 1.25)} {fmt(key.y + 7.05)}) (end {fmt(body_x + 1.25)} {fmt(key.y + 8.95)}) (stroke (width 0.16) (type default)) (fill none) (layer "B.Fab") (uuid {uid(f"d-body-{key.index}")}))',
        f'    (fp_line (start {fmt(cathode[0] + 1.35)} {fmt(key.y + 6.9)}) (end {fmt(cathode[0] + 1.35)} {fmt(key.y + 9.1)}) (stroke (width 0.3) (type default)) (layer "B.Fab") (uuid {uid(f"d-k-{key.index}")}))',
        pad(board, "1", "smd", "roundrect", anode, (2.4, 2.2), ["B.Cu", "B.Paste", "B.Mask"], intermediate, rr=0.18),
        pad(board, "2", "smd", "roundrect", cathode, (2.4, 2.2), ["B.Cu", "B.Paste", "B.Mask"], row, rr=0.18),
        '  )',
    ]
    board.add("\n".join(lines))
    return anode, cathode


def ffc_footprint(board: Board, ref: str, x0: float, y: float, nets: list[str], ident: str):
    lines = [
        f'  (footprint "FFC_20P_1.0mm_BottomContact" (layer "F.Cu") (at 0 0)',
        f'    (uuid {uid(ident + "-fp")})',
        '    (attr smd)',
        property_text("Reference", ref, (x0 + 9.5, y - 4.8), "F.Fab", uid(ident + "-ref")),
        property_text("Value", "20P 1.0mm FFC ZIF bottom-contact", (x0 + 9.5, y), "F.Fab", uid(ident + "-val"), True),
        f'    (fp_rect (start {fmt(x0 - 2.1)} {fmt(y - 4.0)}) (end {fmt(x0 + 21.1)} {fmt(y + 3.0)}) (stroke (width 0.25) (type default)) (fill none) (layer "F.Fab") (uuid {uid(ident + "-body")}))',
        f'    (fp_line (start {fmt(x0 - 1.5)} {fmt(y - 3.2)}) (end {fmt(x0 + 20.5)} {fmt(y - 3.2)}) (stroke (width 0.5) (type default)) (layer "F.Fab") (uuid {uid(ident + "-mouth")}))',
    ]
    for index, net in enumerate(nets):
        lines.append(pad(board, str(index + 1), "smd", "roundrect", (x0 + index, y), (0.6, 2.6), ["F.Cu", "F.Paste", "F.Mask"], net, rr=0.15))
    # Large mechanical hold-down tabs, hand-solder friendly.
    lines.append(pad(board, "", "smd", "rect", (x0 - 1.8, y - 0.7), (2.4, 3.2), ["F.Cu", "F.Paste", "F.Mask"]))
    lines.append(pad(board, "", "smd", "rect", (x0 + 20.8, y - 0.7), (2.4, 3.2), ["F.Cu", "F.Paste", "F.Mask"]))
    lines.append('  )')
    board.add("\n".join(lines))


def back_ffc_footprint(board: Board, ref: str, x0: float, y: float, nets: list[str], ident: str):
    """Horizontal 20P ZIF on B.Cu, with the cable mouth at the rear edge."""
    lines = [
        f'  (footprint "FFC_20P_1.0mm_BottomContact_Back" (layer "B.Cu") (at 0 0)',
        f'    (uuid {uid(ident + "-fp")})',
        '    (attr smd)',
        property_text("Reference", ref, (x0 + 9.5, y + 4.8), "B.Fab", uid(ident + "-ref")),
        property_text("Value", "20P 1.0mm FFC ZIF bottom-contact", (x0 + 9.5, y), "B.Fab", uid(ident + "-val"), True),
        f'    (fp_rect (start {fmt(x0 - 2.1)} {fmt(y - 4.0)}) (end {fmt(x0 + 21.1)} {fmt(y + 3.0)}) (stroke (width 0.25) (type default)) (fill none) (layer "B.Fab") (uuid {uid(ident + "-body")}))',
        f'    (fp_line (start {fmt(x0 - 1.5)} {fmt(y - 3.2)}) (end {fmt(x0 + 20.5)} {fmt(y - 3.2)}) (stroke (width 0.5) (type default)) (layer "B.Fab") (uuid {uid(ident + "-mouth")}))',
    ]
    for index, net in enumerate(nets):
        lines.append(pad(board, str(index + 1), "smd", "roundrect", (x0 + index, y), (0.6, 2.6), ["B.Cu", "B.Paste", "B.Mask"], net, rr=0.15))
    lines.append(pad(board, "", "smd", "rect", (x0 - 1.8, y + 0.7), (2.4, 3.2), ["B.Cu", "B.Paste", "B.Mask"]))
    lines.append(pad(board, "", "smd", "rect", (x0 + 20.8, y + 0.7), (2.4, 3.2), ["B.Cu", "B.Paste", "B.Mask"]))
    lines.append('  )')
    board.add("\n".join(lines))


def vertical_back_ffc_footprint(board: Board, ref: str, x: float, y0: float, nets: list[str], ident: str):
    """20P 1.0 mm bottom-contact ZIF, rotated 90 degrees on B.Cu."""
    lines = [
        f'  (footprint "FFC_20P_1.0mm_BottomContact_Vertical" (layer "B.Cu") (at 0 0)',
        f'    (uuid {uid(ident + "-fp")})',
        '    (attr smd)',
        property_text("Reference", ref, (x, y0 - 4.8), "B.Fab", uid(ident + "-ref")),
        property_text("Value", "20P 1.0mm FFC ZIF bottom-contact", (x, y0 + 9.5), "B.Fab", uid(ident + "-val"), True),
        f'    (fp_rect (start {fmt(x - 3.0)} {fmt(y0 - 2.1)}) (end {fmt(x + 4.0)} {fmt(y0 + 21.1)}) (stroke (width 0.25) (type default)) (fill none) (layer "B.Fab") (uuid {uid(ident + "-body")}))',
        f'    (fp_line (start {fmt(x + 3.2)} {fmt(y0 - 1.5)}) (end {fmt(x + 3.2)} {fmt(y0 + 20.5)}) (stroke (width 0.5) (type default)) (layer "B.Fab") (uuid {uid(ident + "-mouth")}))',
    ]
    for index, net in enumerate(nets):
        lines.append(pad(board, str(index + 1), "smd", "roundrect", (x, y0 + index), (2.6, 0.6), ["B.Cu", "B.Paste", "B.Mask"], net, rr=0.15))
    lines.append(pad(board, "", "smd", "rect", (x + 0.7, y0 - 1.8), (3.2, 2.4), ["B.Cu", "B.Paste", "B.Mask"]))
    lines.append(pad(board, "", "smd", "rect", (x + 0.7, y0 + 20.8), (3.2, 2.4), ["B.Cu", "B.Paste", "B.Mask"]))
    lines.append('  )')
    board.add("\n".join(lines))


def mounting_hole(board: Board, ref: str, point, diameter=2.7):
    lines = [
        f'  (footprint "MountingHole_{fmt(diameter)}mm" (layer "F.Cu") (at {fmt(point[0])} {fmt(point[1])})',
        f'    (uuid {uid(ref + "-fp")})',
        property_text("Reference", ref, (0, 3.3), "F.Fab", uid(ref + "-ref")),
        property_text("Value", "M2 clearance", (0, 0), "F.Fab", uid(ref + "-val"), True),
        pad(board, "", "np_thru_hole", "circle", (0, 0), (diameter, diameter), ["*.Cu", "*.Mask"], drill=diameter),
        '  )',
    ]
    board.add("\n".join(lines))


def mounting_slot(board: Board, ref: str, point):
    lines = [
        f'  (footprint "GH60_Case_Mount_Slot" (layer "F.Cu") (at {fmt(point[0])} {fmt(point[1])})',
        f'    (uuid {uid(ref + "-fp")})',
        property_text("Reference", ref, (0, 4.0), "F.Fab", uid(ref + "-ref")),
        property_text("Value", "GH60 edge slot 7.0x2.5", (0, 0), "F.Fab", uid(ref + "-val"), True),
        pad(board, "", "np_thru_hole", "oval", (0, 0), (10.0, 5.0), ["*.Cu", "*.Mask"], drill=(7.0, 2.5)),
        '  )',
    ]
    board.add("\n".join(lines))


def main_board(keys: list[Key], out: Path):
    board = Board("Minilite64-main")
    for name in [*(f"COL{i}" for i in range(14)), *(f"ROW{i}" for i in range(5)), "GND"]:
        board.net(name)
    for key in keys:
        board.net(f"KEY{key.index + 1}_D")

    # GH60 envelope with only a 25 mm-wide, 4.5 mm-deep FFC tongue.
    outline = [
        (0.15, 0.15), (130.0, 0.15), (130.0, -4.45),
        (155.0, -4.45), (155.0, 0.15), (285.6, 0.15), (285.6, 95.1),
        (0.15, 95.1), (0.15, 0.15),
    ]
    for a, b in zip(outline, outline[1:]):
        board.edge(a, b)

    ffc_footprint(board, "J1", FFC_X0, FFC_Y, FFC_NETS, "main-ffc")

    by_row: dict[int, list[Key]] = {row: [] for row in range(5)}
    for key in keys:
        by_row[key.row].append(key)
        switch_footprint(board, key)
        diode_footprint(board, key)

        # Socket contact 2 to diode anode, safely around the centre/locating holes.
        socket2 = (key.x - 5.842, key.y - 5.08)
        anode = (key.x - 7.65, key.y + 2.7)
        board.polyline(f"KEY{key.index + 1}_D", [socket2, (key.x - 7.65, key.y - 5.08), anode], "B.Cu", 0.28)
        # Diode cathode to horizontal row bus.
        board.segment(f"ROW{key.row}", (key.x - 7.65, key.y + 6.5), (key.x - 7.65, key.y + 8.0), "B.Cu", 0.3)

    col_vias: dict[tuple[int, int], tuple[float, float]] = {}
    for row, row_keys in by_row.items():
        for key in row_keys:
            pad1 = (key.x + 7.085, key.y - 2.54)
            if key.x + 8.8 > 281.4:
                via = (key.x + 7.1, key.y - 4.45)
                board.polyline(f"COL{key.col}", [pad1, (key.x + 7.1, key.y - 2.54), via], "B.Cu", 0.28)
            else:
                via = (key.x + 8.8, key.y - 2.54)
                board.segment(f"COL{key.col}", pad1, via, "B.Cu", 0.28)
            board.via(f"COL{key.col}", via)
            col_vias[(row, key.col)] = via

    # Four inter-row corridors carry the column breakout on B.Cu.  A short,
    # ordered F.Cu fan connects the vertical ZIF without crossings.
    column_lanes = [18.6, 19.4, 20.2, 21.0, 37.65, 38.45, 39.25, 40.05,
                    56.7, 57.5, 58.3, 75.75, 76.55, 77.35]
    for col in range(14):
        first = col_vias[(0, col)]
        lane_y = column_lanes[col]
        pad_point = (MAIN_FFC_X, MAIN_FFC_Y0 + col)
        source = (241.7, MAIN_FFC_Y0 + col)
        anchor = (238.5, lane_y)
        target = (first[0], lane_y)
        board.segment(f"COL{col}", pad_point, source, "B.Cu", 0.2)
        board.via(f"COL{col}", source)
        board.segment(f"COL{col}", source, anchor, "F.Cu", 0.2)
        board.via(f"COL{col}", anchor)
        board.segment(f"COL{col}", anchor, target, "B.Cu", 0.2)
        board.via(f"COL{col}", target)
        board.segment(f"COL{col}", target, first, "F.Cu", 0.2)
        existing_rows = [row for row in range(5) if (row, col) in col_vias]
        for row_a, row_b in zip(existing_rows, existing_rows[1:]):
            a = col_vias[(row_a, col)]
            b = col_vias[(row_b, col)]
            center_a = by_row[row_a][0].y
            center_b = by_row[row_b][0].y
            board.polyline(
                f"COL{col}",
                [a, (a[0], center_a + 3.0), (b[0], center_b - 7.0), b],
                "F.Cu",
                0.2,
            )

    # Row buses stay on B.Cu.  Only ROW4 needs a short F.Cu jump over the two
    # column lanes that continue into the far-right key positions.
    row_tracks = [252.0, 252.8, 253.6, 254.4, 255.2]
    for row, row_keys in by_row.items():
        bus_y = row_keys[0].y + 8.0
        diode_xs = [key.x - 7.65 for key in row_keys]
        track_x = row_tracks[row]
        pin_y = MAIN_FFC_Y0 + 14 + row
        board.segment(f"ROW{row}", (min(diode_xs), bus_y), (track_x, bus_y), "B.Cu", 0.3)
        if row != 4:
            board.mitered_polyline(f"ROW{row}", [(MAIN_FFC_X, pin_y), (track_x, pin_y), (track_x, bus_y)], "B.Cu", 0.22, 0.4)
        else:
            # Jump over the COL12/COL13 B.Cu lanes on F.Cu.
            jump_a, jump_b = (track_x, 75.35), (track_x, 77.75)
            board.mitered_polyline(f"ROW{row}", [(MAIN_FFC_X, pin_y), (track_x, pin_y), jump_a], "B.Cu", 0.22, 0.4)
            board.via(f"ROW{row}", jump_a)
            board.via(f"ROW{row}", jump_b)
            board.segment(f"ROW{row}", jump_a, jump_b, "F.Cu", 0.22)
            board.segment(f"ROW{row}", jump_b, (track_x, bus_y), "B.Cu", 0.22)

    # Ground is a reference/service contact on the passive key matrix board.
    tp = (252.0, MAIN_FFC_Y0 + 19)
    board.segment("GND", (MAIN_FFC_X, MAIN_FFC_Y0 + 19), tp, "B.Cu", 0.3)
    board.add(
        '\n'.join([
            f'  (footprint "TestPoint_Pad_D2.0mm" (layer "B.Cu") (at {fmt(tp[0])} {fmt(tp[1])})',
            f'    (uuid {uid("main-tp-fp")})',
            property_text("Reference", "TP1", (0, -2), "F.Fab", uid("main-tp-ref")),
            property_text("Value", "GND", (0, 0), "F.Fab", uid("main-tp-val"), True),
            pad(board, "1", "smd", "circle", (0, 0), (2.0, 2.0), ["B.Cu", "B.Mask"], "GND"),
            '  )',
        ])
    )

    # Canonical GH60 tray-mount coordinates, translated to this board origin.
    holes = [(25.35, 28.05), (128.35, 47.15), (190.65, 85.35), (260.20, 28.05)]
    slots = [(1.61, 56.65), (283.69, 56.65)]
    for index, point in enumerate(holes, 1):
        mounting_hole(board, f"H{index}", point)
    for index, point in enumerate(slots, len(holes) + 1):
        mounting_slot(board, f"H{index}", point)

    board.text("MINILITE64  •  64 KEY  •  REV B", (142.875, 92.2), "F.SilkS", 1.05)
    board.text("20P FFC • 1.0 mm • TYPE A", (218.0, 71.8), "B.SilkS", 0.8, "mirror")
    add_openai_branding(board)
    board.write(out)
    return holes + slots


def main_board_v2(keys: list[Key], out: Path):
    """Compact two-layer board with a local FFC tongue and no rear shelf."""
    board = Board("Minilite64-main-revB")
    for name in [*(f"COL{i}" for i in range(14)), *(f"ROW{i}" for i in range(5)), "GND"]:
        board.net(name)
    for key in keys:
        board.net(f"KEY{key.index + 1}_D")

    outline = [
        (0.15, 0.15), (285.6, 0.15),
        (285.6, 95.1), (0.15, 95.1), (0.15, 0.15),
    ]
    for a, b in zip(outline, outline[1:]):
        board.edge(a, b)
    back_ffc_footprint(board, "J1", FFC_X0, 3.2, FFC_NETS, "main-revb-ffc")

    by_row: dict[int, list[Key]] = {row: [] for row in range(5)}
    for key in keys:
        by_row[key.row].append(key)
        rotate = key.row == 0
        switch_footprint(board, key, rotate)
        if rotate:
            anode, cathode = top_row_diode_footprint(board, key)
            diode_x = cathode[0]
        else:
            diode_footprint(board, key)
            diode_x = key.x - 7.65
        if rotate:
            socket2 = (key.x + 5.842, key.y + 5.08)
            board.segment(f"KEY{key.index + 1}_D", socket2, anode, "B.Cu", 0.28)
            board.segment(f"ROW{key.row}", cathode, (cathode[0], key.y + 9.5), "B.Cu", 0.3)
        else:
            socket2 = (key.x - 5.842, key.y - 5.08)
            anode = (diode_x, key.y + 2.7)
            board.polyline(f"KEY{key.index + 1}_D", [socket2, (diode_x, key.y - 5.08), anode], "B.Cu", 0.28)
            board.segment(f"ROW{key.row}", (diode_x, key.y + 6.5), (diode_x, key.y + 8.0), "B.Cu", 0.3)

    col_vias: dict[tuple[int, int], tuple[float, float]] = {}
    for row, row_keys in by_row.items():
        for key in row_keys:
            if row == 0:
                pad1 = (key.x - 7.085, key.y + 2.54)
                via = (key.x - 8.8, key.y + 2.54)
                board.segment(f"COL{key.col}", pad1, via, "B.Cu", 0.28)
            elif key.x + 8.8 > 281.4:
                pad1 = (key.x + 7.085, key.y - 2.54)
                via = (key.x + 7.1, key.y - 4.45)
                board.polyline(f"COL{key.col}", [pad1, (key.x + 7.1, key.y - 2.54), via], "B.Cu", 0.28)
            else:
                pad1 = (key.x + 7.085, key.y - 2.54)
                via = (key.x + 8.8, key.y - 2.54)
                board.segment(f"COL{key.col}", pad1, via, "B.Cu", 0.28)
            board.via(f"COL{key.col}", via)
            col_vias[(row, key.col)] = via

    # The rotated top row opens a 7 mm rear corridor.  Left columns use F.Cu;
    # right columns use B.Cu, leaving an independent B.Cu band for the rows.
    for col in range(14):
        first = col_vias[(0, col)]
        lane_y = (0.7 + (7 - col) * 0.5) if col <= 7 else (0.7 + (col - 8) * 0.5)
        connector_x = FFC_X0 + col
        source = (connector_x, 6.65)
        hub = (129.0 if col <= 7 else 156.0, lane_y)
        target = (first[0], lane_y)
        board.segment(f"COL{col}", (connector_x, 4.2), source, "B.Cu", 0.2)
        board.via(f"COL{col}", source, 0.6, 0.3)
        board.segment(f"COL{col}", source, hub, "F.Cu", 0.2)
        board.segment(f"COL{col}", hub, target, "F.Cu", 0.2)
        board.via(f"COL{col}", target, 0.6, 0.3)
        board.segment(f"COL{col}", target, first, "B.Cu", 0.2)
        existing_rows = [row for row in range(5) if (row, col) in col_vias]
        for row_a, row_b in zip(existing_rows, existing_rows[1:]):
            a = col_vias[(row_a, col)]
            b = col_vias[(row_b, col)]
            center_a = by_row[row_a][0].y
            center_b = by_row[row_b][0].y
            if row_a == 0:
                board.polyline(f"COL{col}", [a, (a[0], 18.8), (b[0], 21.0), b], "F.Cu", 0.2)
            else:
                board.polyline(f"COL{col}", [a, (a[0], center_a + 3.0), (b[0], center_b - 7.0), b], "F.Cu", 0.2)

    for row, row_keys in by_row.items():
        bus_y = row_keys[0].y + (9.5 if row == 0 else 8.0)
        diode_xs = [key.x + 9.642 if row == 0 else key.x - 7.65 for key in row_keys]
        board.segment(f"ROW{row}", (min(diode_xs), bus_y), (ROW_TRACK_X[row], bus_y), "B.Cu", 0.3)
        connector_x = FFC_X0 + 14 + row
        lane_y = 4.6 + row * 0.4
        source = (connector_x, 6.65)
        destination = (ROW_TRACK_X[row], lane_y)
        board.segment(f"ROW{row}", (connector_x, 4.2), source, "B.Cu", 0.2)
        board.via(f"ROW{row}", source, 0.6, 0.3)
        board.polyline(f"ROW{row}", [source, (connector_x, lane_y), destination], "F.Cu", 0.2)
        board.via(f"ROW{row}", destination, 0.6, 0.3)
        board.segment(f"ROW{row}", destination, (ROW_TRACK_X[row], bus_y), "B.Cu", 0.22)

    gnd_x = FFC_X0 + 19
    gnd_via = (gnd_x, 6.65)
    tp = gnd_via
    board.segment("GND", (gnd_x, 4.2), gnd_via, "B.Cu", 0.2)
    board.via("GND", gnd_via, 0.6, 0.3)
    board.add('\n'.join([
        f'  (footprint "TestPoint_Pad_D2.0mm" (layer "B.Cu") (at {fmt(tp[0])} {fmt(tp[1])})',
        f'    (uuid {uid("main-revb-tp-fp")})',
        property_text("Reference", "TP1", (0, -2), "B.Fab", uid("main-revb-tp-ref")),
        property_text("Value", "GND", (0, 0), "B.Fab", uid("main-revb-tp-val"), True),
        pad(board, "1", "smd", "circle", (0, 0), (2.0, 2.0), ["B.Cu", "B.Mask"], "GND"),
        '  )',
    ]))

    # The DXF uses a bottom-left Y axis while the KLE/PCB uses a top-left Y
    # axis.  Mirror the three 5 x 5 mm plate openings about the common board
    # centre; do not copy their DXF Y coordinates verbatim.  The small X
    # translation aligns the DXF and PCB outline centres.
    dxf_center_x = (0.0950846 + 285.469) / 2
    pcb_center_x = (0.15 + 285.6) / 2
    dxf_center_y = (0.228755 + 95.1548) / 2
    pcb_center_y = (0.15 + 95.1) / 2
    dxf_holes = [(25.4820, 67.0920), (128.4830, 47.6912), (260.3315, 67.0920)]
    holes = [
        (x + pcb_center_x - dxf_center_x,
         pcb_center_y - (y - dxf_center_y))
        for x, y in dxf_holes
    ]
    for index, point in enumerate(holes, 1):
        mounting_hole(board, f"H{index}", point)

    board.text("MINILITE64 • REV B • 2 LAYER", (142.875, 92.2), "F.SilkS", 1.0)
    board.text("20P FFC • 1.0 mm • TYPE A", (142.5, -3.5), "B.SilkS", 0.72, "mirror")
    add_openai_branding(board)
    board.write(out)
    return holes


RP_SIDE_Y = [1.59 + 2.54 * i for i in range(9)]
RP_BOTTOM_X = [3.92 + 2.54 * i for i in range(5)]


def rp2040_footprint(board: Board, origin=(13.5, 3.0)):
    ox, oy = origin
    # Physical order from the official Waveshare drawing.
    left = ["5V", "GND", "3V3", "GP29", "GP28", "GP27", "GP26", "GP15", "GP14"]
    right = ["GP0", "GP1", "GP2", "GP3", "GP4", "GP5", "GP6", "GP7", "GP8"]
    bottom = ["GP13", "GP12", "GP11", "GP10", "GP9"]
    signal_net = {
        "GND": "GND",
        "GP29": "ROW0", "GP28": "ROW1", "GP27": "ROW2", "GP26": "ROW3", "GP15": "ROW4",
        "GP13": "COL0", "GP12": "COL1", "GP11": "COL2", "GP10": "COL3", "GP9": "COL4",
        "GP8": "COL5", "GP7": "COL6", "GP6": "COL7", "GP5": "COL8", "GP4": "COL9",
        "GP3": "COL10", "GP2": "COL11", "GP1": "COL12", "GP0": "COL13",
    }
    lines = [
        f'  (footprint "Waveshare_RP2040_Zero_Castellated" (layer "F.Cu") (at 0 0)',
        f'    (uuid {uid("rp-fp")})',
        '    (attr smd)',
        property_text("Reference", "U1", (ox + 9, oy + 12), "F.Fab", uid("rp-ref")),
        property_text("Value", "Waveshare RP2040-Zero", (ox + 9, oy + 12), "F.Fab", uid("rp-val"), True),
        f'    (fp_rect (start {fmt(ox)} {fmt(oy)}) (end {fmt(ox+18)} {fmt(oy+23.5)}) (stroke (width 0.25) (type default)) (fill none) (layer "F.Fab") (uuid {uid("rp-body")}))',
        f'    (fp_rect (start {fmt(ox+4.67)} {fmt(oy-1.2)}) (end {fmt(ox+16.62)} {fmt(oy+4.6)}) (stroke (width 0.3) (type default)) (fill none) (layer "F.Fab") (uuid {uid("rp-usb")}))',
    ]
    for i, name in enumerate(left):
        lines.append(pad(board, name, "smd", "roundrect", (ox, oy + RP_SIDE_Y[i]), (2.4, 1.7), ["F.Cu", "F.Mask"], signal_net.get(name, ""), rr=0.25))
    for i, name in enumerate(right):
        lines.append(pad(board, name, "smd", "roundrect", (ox + 18, oy + RP_SIDE_Y[i]), (2.4, 1.7), ["F.Cu", "F.Mask"], signal_net.get(name, ""), rr=0.25))
    for i, name in enumerate(bottom):
        lines.append(pad(board, name, "smd", "roundrect", (ox + RP_BOTTOM_X[i], oy + 23.5), (1.7, 2.4), ["F.Cu", "F.Mask"], signal_net.get(name, ""), rr=0.25))
    lines.append('  )')
    board.add("\n".join(lines))
    return ox, oy, signal_net


def controller_board(out: Path):
    board = Board("Minilite64-controller")
    for name in [*(f"COL{i}" for i in range(14)), *(f"ROW{i}" for i in range(5)), "GND"]:
        board.net(name)
    width, height = 45.0, 47.0
    outline = [(0, 0), (45, 0), (45, 47), (0, 47), (0, 0)]
    for a, b in zip(outline, outline[1:]):
        board.edge(a, b)
    ffc_x0, ffc_y = 13.0, 41.0
    ffc_footprint(board, "J1", ffc_x0, ffc_y, FFC_NETS, "ctrl-ffc")
    ox, oy, _ = rp2040_footprint(board, (13.5, 2.0))

    # Pin order follows the RP2040-Zero perimeter: ground + five rows on the
    # module's left, five columns on its bottom, then nine columns on its right.
    # This removes crossings and keeps every 1 mm pitch escape hand-fabricable.

    # COL0..4: ordered fan from FFC pins 7..11 to bottom castellations.
    bottom_targets = [(ox + RP_BOTTOM_X[i], oy + 23.5) for i in range(5)]
    for col, target in enumerate(bottom_targets):
        start = (ffc_x0 + 6 + col, ffc_y)
        board.polyline(f"COL{col}", [start, (start[0], 29.0), (target[0], 27.2), target], "F.Cu", 0.2)

    # COL5..13: ordered fan and branch bundle around the right of the module.
    for offset in range(9):
        col = 5 + offset
        start = (ffc_x0 + 11 + offset, ffc_y)
        lane_y = 36.0 - offset * 0.7
        lane_x = 33.0 + offset * 0.8
        target = (ox + 18, oy + RP_SIDE_Y[8 - offset])  # GP8 down to GP0
        source_via = (start[0], lane_y)
        target_via = (lane_x, lane_y)
        board.segment(f"COL{col}", start, source_via, "F.Cu", 0.2)
        board.via(f"COL{col}", source_via)
        board.segment(f"COL{col}", source_via, target_via, "B.Cu", 0.2)
        board.via(f"COL{col}", target_via)
        board.polyline(f"COL{col}", [target_via, (lane_x, target[1]), target], "F.Cu", 0.2)

    # GND and rows use ordered B.Cu lanes around the left, then return to F.Cu.
    row_target_indices = [3, 4, 5, 6, 7]  # GP29, GP28, GP27, GP26, GP15
    left_nets = [("GND", 1)] + [(f"ROW{row}", side_index) for row, side_index in enumerate(row_target_indices)]
    for index, (net, side_index) in enumerate(left_nets):
        start = (ffc_x0 + index, ffc_y)
        lane_y = 36.0 - index * 0.7
        source_via = (start[0], lane_y)
        lane_x = 6.0 + index * 0.8
        target_y = oy + RP_SIDE_Y[side_index]
        target_via = (lane_x, lane_y)
        board.segment(net, start, source_via, "F.Cu", 0.2 if net != "GND" else 0.25)
        board.via(net, source_via)
        board.segment(net, source_via, target_via, "B.Cu", 0.2 if net != "GND" else 0.25)
        board.via(net, target_via)
        board.polyline(net, [target_via, (lane_x, target_y), (ox, target_y)], "F.Cu", 0.2 if net != "GND" else 0.25)

    holes = [(4.0, 4.0), (41.0, 4.0), (4.0, 43.0), (41.0, 43.0)]
    for index, point in enumerate(holes, 1):
        mounting_hole(board, f"H{index}", point, 2.2)
    board.text("RP2040-ZERO CARRIER  REV A", (22.5, 45.2), "B.SilkS", 0.9, "mirror")
    board.text("USB-C → REAR", (22.5, 1.0), "F.SilkS", 0.9)
    board.write(out)
    return holes


def controller_board_v2(out: Path):
    """Compact carrier seed for the RP2040-Zero and rear-accessible FFC."""
    board = Board("Minilite64-controller-revB")
    for name in [*(f"COL{i}" for i in range(14)), *(f"ROW{i}" for i in range(5)), "GND"]:
        board.net(name)

    width, height = 40.0, 36.0
    outline = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]
    for a, b in zip(outline, outline[1:]):
        board.edge(a, b)

    # RP2040-Zero component side faces the service cover.  USB-C exits the
    # rear edge; the onboard BOOT/RESET buttons remain directly accessible.
    rp2040_footprint(board, (11.0, 1.5))

    # Both mouths face rear.  The carrier connector is pulled toward the main
    # board so the installed Type-A C-loop can unfold for bottom-cover service.
    back_ffc_footprint(board, "J1", 10.5, 30.0, FFC_NETS, "ctrl-revb-ffc")

    holes = [(3.0, 3.0), (37.0, 3.0), (3.0, 33.0), (37.0, 33.0)]
    for index, point in enumerate(holes, 1):
        mounting_hole(board, f"H{index}", point, 2.2)

    board.text("RP2040-ZERO • REV B", (20.0, 27.2), "F.SilkS", 0.85)
    board.write(out)
    return holes


def legacy_component(lib, ref, value, x, y, unit=1, orientation="1 0 0 -1"):
    return f'''$Comp
L {lib} {ref}
U {unit} 1 {uid(ref).replace('-', '')[:8]}
P {x} {y}
F 0 "{ref}" H {x+180} {y+100} 50  0000 C CNN
F 1 "{esc(value)}" H {x+250} {y-100} 50  0000 C CNN
\t1    {x} {y}
\t{orientation}
$EndComp
'''


def write_keyboard_legacy_schematic(keys: list[Key], path: Path):
    parts = [
        "EESchema Schematic File Version 4\n",
        "LIBS:power\nLIBS:device\nLIBS:switch\nLIBS:Connector_Generic\n",
        "EELAYER 29 0\nEELAYER END\n",
        "$Descr A3 16535 11693\nSheet 1 1\nTitle \"Minilite64 key matrix\"\nComment1 \"64 Kailh hotswap switches, SOD-123 diodes, hand solder\"\n$EndDescr\n",
    ]
    for key in keys:
        x = 900 + key.col * 1000
        y = 1200 + key.row * 1900
        parts.append(legacy_component("Switch:SW_Push", key.ref, key.label, x, y))
        parts.append(legacy_component("Device:D_Small", key.diode, "1N4148W", x + 420, y, orientation="-1 0 0 1"))
        parts.append(f"Wire Wire Line\n\t{x-250} {y} {x-100} {y}\n")
        parts.append(f"Text Label {x-250} {y} 2    40   ~ 0\nCOL{key.col}\n")
        parts.append(f"Wire Wire Line\n\t{x+100} {y} {x+320} {y}\n")
        parts.append(f"Wire Wire Line\n\t{x+520} {y} {x+700} {y}\n")
        parts.append(f"Text Label {x+700} {y} 0    40   ~ 0\nROW{key.row}\n")
    parts.append(legacy_component("Connector_Generic:Conn_01x20", "J1", "Type-A FFC / pins straight", 14800, 9300, orientation="1 0 0 -1"))
    for index, name in enumerate(FFC_NETS):
        y = 8350 + index * 100
        parts.append(f"Wire Wire Line\n\t14550 {y} 14350 {y}\nText Label 14350 {y} 2    40   ~ 0\n{name}\n")
    parts.append("Text Notes 900 10700 0    80   ~ 12\nDiode direction: COL2ROW (cathode toward ROW)\n")
    parts.append("$EndSCHEMATC\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts), encoding="utf-8")


def write_controller_legacy_schematic(path: Path):
    parts = [
        "EESchema Schematic File Version 4\n",
        "LIBS:power\nLIBS:device\nLIBS:Connector_Generic\n",
        "EELAYER 29 0\nEELAYER END\n",
        "$Descr A4 11693 8268\nSheet 1 1\nTitle \"Minilite64 RP2040-Zero carrier\"\nComment1 \"Castellated module carrier and 20P FFC\"\n$EndDescr\n",
        legacy_component("Connector_Generic:Conn_01x20", "J1", "Type-A FFC / pins straight", 2900, 3700),
        legacy_component("Connector_Generic:Conn_01x23", "U1", "Waveshare RP2040-Zero castellated", 7200, 3700),
    ]
    ffc_nets = FFC_NETS
    rp_order = ["5V_NC", "GND", "3V3_NC", "ROW0", "ROW1", "ROW2", "ROW3", "ROW4", "GP14_NC",
                "COL13", "COL12", "COL11", "COL10", "COL9", "COL8", "COL7", "COL6", "COL5",
                "COL0", "COL1", "COL2", "COL3", "COL4"]
    for index, name in enumerate(ffc_nets):
        y = 2750 + index * 100
        parts.append(f"Wire Wire Line\n\t2650 {y} 2450 {y}\nText Label 2450 {y} 2    40   ~ 0\n{name}\n")
    for index, name in enumerate(rp_order):
        y = 2600 + index * 100
        parts.append(f"Wire Wire Line\n\t6950 {y} 6700 {y}\nText Label 6700 {y} 2    40   ~ 0\n{name}\n")
    parts.append("Text Notes 1800 6500 0    80   ~ 12\nGP16 is reserved for the onboard WS2812 and is not used. GP14 remains spare.\n")
    parts.append("$EndSCHEMATC\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts), encoding="utf-8")


def write_project(path: Path):
    # KiCad expands this seed with board rules and editor settings.  Preserve
    # that real project configuration on subsequent hardware regenerations.
    if not path.exists():
        path.write_text(
            json.dumps({"meta": {"filename": path.name, "version": 1}}, indent=2),
            encoding="utf-8",
        )


def write_bom(keys: list[Key], root: Path):
    root.mkdir(parents=True, exist_ok=True)
    rows = [
        ["Reference(s)", "Qty", "Value", "Package", "Assembly", "Notes"],
        ["SW1-SW64", 64, "Kailh MX hot-swap socket CPG151101S11", "Kailh hotswap SMD", "Hand solder", "Socket on PCB bottom"],
        ["D1-D64", 64, "1N4148W", "SOD-123", "Hand solder", "Large hand-solder pads; cathode stripe to ROW"],
        ["J1 (main), J1 (carrier)", 2, "20P 1.0mm bottom-contact flip-lock FFC/FPC connector", "20P 1.0mm SMT", "Hand solder", "Generic or equivalent; verify same footprint"],
        ["FFC1", 1, "20P 1.0mm Type-A FFC, 100mm x 21mm", "Same-side contacts", "Purchased cable", "No axial twist; flexible body <=0.20mm; prototype-fit the smooth service scroll"],
        ["U1", 1, "Waveshare RP2040-Zero 23.5x18mm USB-C", "Castellated module", "Hand solder", "Mount component-side up; USB toward rear"],
        ["H1-H5 main", 5, "M2 screw + 3.2x3mm heat-set insert", "Mechanical", "Assembly", "Three original mounts plus two balanced bottom-row supports"],
        ["S1-S2 main sides", 2, "M2 screw + 3.2x3mm heat-set insert", "Mechanical", "Assembly", "Left/right DXF edge slots; screw heads retain PCB and plate"],
        ["H1-H4 carrier", 4, "M2 screw + heat-set insert", "Mechanical", "Assembly", "Four-corner mounting"],
    ]
    with (root / "BOM.csv").open("w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(rows)

    pin_rows = [["Main J1 pin", "Carrier J1 pin", "Net", "RP2040-Zero pad"]]
    rp_pad = {"GND": "GND"}
    row_gpio = [29, 28, 27, 26, 15]
    for row, gpio in enumerate(row_gpio):
        rp_pad[f"ROW{row}"] = f"GP{gpio}"
    col_gpio = [13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    for col, gpio in enumerate(col_gpio):
        rp_pad[f"COL{col}"] = f"GP{gpio}"
    for carrier_pin, net in enumerate(FFC_NETS, 1):
        pin_rows.append([carrier_pin, carrier_pin, net, rp_pad[net]])
    with (root / "FFC_pinout.csv").open("w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(pin_rows)

    with (root / "key_matrix.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Reference", "Label", "Matrix row", "Matrix column", "X mm", "Y mm", "Width U"])
        for key in keys:
            writer.writerow([key.ref, key.label.replace("\n", "/"), key.row, key.col, f"{key.x:.3f}", f"{key.y:.3f}", key.w])


def main(write_carrier_seed: bool = False):
    keys = parse_kle(ROOT / "KLE.txt")
    keyboard_dir = ROOT / "hardware" / "keyboard"
    controller_dir = ROOT / "hardware" / "controller"
    # The final rectangular router lives in a separate, focused source file so
    # its manually verified 20P escape is not mixed with legacy experiments.
    from generate_rect_seed import build as build_rectangular_main, edge_mount_slots
    main_holes = build_rectangular_main(keys, keyboard_dir / "Minilite64.kicad_pcb")
    # The routed carrier is a checked-in design artifact.  Never overwrite it
    # from this generator: controller_board_v2() only emits an unrouted seed.
    controller_holes = [(3.0, 3.0), (37.0, 3.0), (3.0, 33.0), (37.0, 33.0)]
    if write_carrier_seed:
        controller_board_v2(ROOT / "build" / "RP2040_Zero_Carrier_seed.kicad_pcb")
    write_keyboard_legacy_schematic(keys, keyboard_dir / "Minilite64.sch")
    write_controller_legacy_schematic(controller_dir / "RP2040_Zero_Carrier.sch")
    write_project(keyboard_dir / "Minilite64.kicad_pro")
    write_project(controller_dir / "RP2040_Zero_Carrier.kicad_pro")
    write_bom(keys, ROOT / "manufacturing")
    metadata = {
        "key_count": len(keys),
        "row_counts": [sum(k.row == row for k in keys) for row in range(5)],
        "plate": {"width": 285.3739, "height": 94.9260, "thickness": 1.5, "material": "PC or FR4"},
        "main_board": {
            "width": BOARD_W,
            "height": BOARD_H,
            "rear_tongue_depth": 0.0,
            "mount_holes": main_holes,
            "edge_mount_slots": edge_mount_slots(),
            "bottom_row_conflicting_mount_removed": True,
        },
        "controller_board": {"width": 40.0, "height": 36.0, "mount_holes": controller_holes},
        "ffc": {"positions": 20, "pitch": 1.0, "width": 21.0, "length": 100,
                "type": "A / same-side", "minimum_bend_radius": 3.0,
                "target_bend_radius": 4.0,
                "maximum_flexible_body_thickness": 0.20,
                "assembly_strategy": "main-first / carrier-last",
                "both_ends_locked_cover_install_allowed": True,
                "release_status": "prototype-only until real FFC fit check",
                "axial_twist": False},
    }
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    (build / "hardware_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-carrier-seed",
        action="store_true",
        help="write an unrouted carrier seed under build/ without touching the routed board",
    )
    main(parser.parse_args().write_carrier_seed)
