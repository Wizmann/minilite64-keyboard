"""Small dependency-free STL preview renderer used for mechanical QA."""

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def read_stl(path: Path):
    data = path.read_bytes()
    if len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
        if 84 + count * 50 == len(data):
            values = np.empty((count, 3, 3), dtype=np.float64)
            offset = 84
            for i in range(count):
                values[i] = np.array(struct.unpack_from("<9f", data, offset + 12)).reshape(3, 3)
                offset += 50
            return values
    vertices = []
    triangle = []
    for line in data.decode("ascii", errors="ignore").splitlines():
        words = line.split()
        if len(words) == 4 and words[0] == "vertex":
            triangle.append(tuple(map(float, words[1:])))
            if len(triangle) == 3:
                vertices.append(triangle)
                triangle = []
    return np.asarray(vertices, dtype=np.float64)


def unit(vector):
    return vector / np.linalg.norm(vector)


def render(triangles, output: Path, width=1800, height=900, view="iso"):
    if view == "top":
        camera = unit(np.array([0.0, 0.0, 1.0]))
        right = np.array([1.0, 0.0, 0.0])
    elif view == "bottom":
        camera = unit(np.array([0.0, 0.0, -1.0]))
        right = np.array([-1.0, 0.0, 0.0])
    elif view == "side":
        # Right-side orthographic view: keyboard rear is at image right.
        camera = unit(np.array([1.0, 0.0, 0.0]))
        right = np.array([0.0, -1.0, 0.0])
    elif view == "front":
        camera = unit(np.array([0.0, 1.0, 0.0]))
        right = np.array([1.0, 0.0, 0.0])
    elif view == "rear":
        camera = unit(np.array([0.0, -1.0, 0.0]))
        right = np.array([-1.0, 0.0, 0.0])
    else:
        camera = unit(np.array([1.0, -1.15, 0.85]))
        right = unit(np.cross(camera, np.array([0.0, 0.0, 1.0])))
    up = unit(np.cross(right, camera))
    center = (triangles.min(axis=(0, 1)) + triangles.max(axis=(0, 1))) / 2
    points = triangles - center
    sx = np.tensordot(points, right, axes=([2], [0]))
    sy = np.tensordot(points, up, axes=([2], [0]))
    depth = np.tensordot(points.mean(axis=1), camera, axes=([1], [0]))
    span_x = max(1e-6, sx.max() - sx.min())
    span_y = max(1e-6, sy.max() - sy.min())
    scale = min((width - 80) / span_x, (height - 80) / span_y)
    px = (sx - (sx.min() + sx.max()) / 2) * scale + width / 2
    py = height / 2 - (sy - (sy.min() + sy.max()) / 2) * scale

    image = Image.new("RGB", (width, height), (238, 241, 246))
    draw = ImageDraw.Draw(image)
    light = unit(np.array([-0.2, -0.4, 1.0]))
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    normals[lengths > 0] /= lengths[lengths > 0, None]
    visible = np.dot(normals, camera) > -0.02
    order = np.argsort(depth)
    for index in order:
        if not visible[index]:
            continue
        shade = 0.45 + 0.5 * abs(float(np.dot(normals[index], light)))
        color = (int(74 * shade), int(139 * shade), int(188 * shade))
        polygon = [(float(px[index, i]), float(py[index, i])) for i in range(3)]
        draw.polygon(polygon, fill=color, outline=(48, 67, 82))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stl", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--view", choices=["iso", "top", "bottom", "side", "front", "rear"],
        default="iso",
    )
    parser.add_argument("--width", type=int, default=1800)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()
    render(read_stl(args.stl), args.output, args.width, args.height, args.view)


if __name__ == "__main__":
    main()
