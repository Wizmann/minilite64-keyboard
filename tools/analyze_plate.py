"""Inspect the line-only R12 DXF supplied for the keyboard plate.

The script intentionally has no third-party dependencies.  It reports closed
connected contours and writes an SVG preview used to verify scale/orientation.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path


def read_lines(path: Path):
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
            result.append(
                (
                    (float(fields["10"]), float(fields["20"])),
                    (float(fields["11"]), float(fields["21"])),
                )
            )
            continue
        i += 1
    return result


def key(point, places=4):
    return round(point[0], places), round(point[1], places)


def connected_components(lines):
    incident = defaultdict(list)
    for index, (a, b) in enumerate(lines):
        incident[key(a)].append(index)
        incident[key(b)].append(index)

    unseen = set(range(len(lines)))
    components = []
    while unseen:
        seed = unseen.pop()
        queue = deque([seed])
        edges = [seed]
        while queue:
            edge = queue.popleft()
            for endpoint in lines[edge]:
                for neighbor in incident[key(endpoint)]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        queue.append(neighbor)
                        edges.append(neighbor)
        points = [p for edge in edges for p in lines[edge]]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        degree = defaultdict(int)
        for edge in edges:
            a, b = lines[edge]
            degree[key(a)] += 1
            degree[key(b)] += 1
        components.append(
            {
                "edges": edges,
                "edge_count": len(edges),
                "bbox": [min(xs), min(ys), max(xs), max(ys)],
                "width": max(xs) - min(xs),
                "height": max(ys) - min(ys),
                "closed": all(value == 2 for value in degree.values()),
            }
        )
    return sorted(components, key=lambda c: (-(c["width"] * c["height"]), c["bbox"]))


def write_svg(path: Path, lines, bounds):
    x0, y0, x1, y1 = bounds
    margin = 5
    width, height = x1 - x0 + margin * 2, y1 - y0 + margin * 2
    elements = []
    for (ax, ay), (bx, by) in lines:
        elements.append(
            f'<line x1="{ax-x0+margin:.4f}" y1="{y1-ay+margin:.4f}" '
            f'x2="{bx-x0+margin:.4f}" y2="{y1-by+margin:.4f}" />'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.2f}mm" '
        f'height="{height:.2f}mm" viewBox="0 0 {width:.4f} {height:.4f}">\n'
        '<g fill="none" stroke="black" stroke-width="0.2">\n'
        + "\n".join(elements)
        + "\n</g>\n</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dxf", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--svg", type=Path)
    args = parser.parse_args()

    lines = read_lines(args.dxf)
    components = connected_components(lines)
    all_points = [point for line in lines for point in line]
    bounds = [
        min(p[0] for p in all_points),
        min(p[1] for p in all_points),
        max(p[0] for p in all_points),
        max(p[1] for p in all_points),
    ]
    report = {
        "line_count": len(lines),
        "bounds": bounds,
        "size": [bounds[2] - bounds[0], bounds[3] - bounds[1]],
        "component_count": len(components),
        "closed_component_count": sum(c["closed"] for c in components),
        "components": [{k: v for k, v in c.items() if k != "edges"} for c in components],
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.svg:
        args.svg.parent.mkdir(parents=True, exist_ok=True)
        write_svg(args.svg, lines, bounds)
    print(json.dumps({k: report[k] for k in report if k != "components"}, indent=2))
    print("Largest components:")
    for component in components[:12]:
        print(component["edge_count"], component["closed"], component["bbox"], component["width"], component["height"])


if __name__ == "__main__":
    main()
