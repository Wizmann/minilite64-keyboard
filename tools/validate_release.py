"""Validate checked-in Minilite64 release artifacts without external modules."""

from __future__ import annotations

import json
import hashlib
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_drc(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    require("Found 0 DRC violations" in text, f"DRC violations in {path}")
    require("Found 0 unconnected pads" in text, f"unconnected pads in {path}")


def check_gerber_zip(path, prefix):
    expected = {
        f"{prefix}-F_Cu.gtl", f"{prefix}-B_Cu.gbl",
        f"{prefix}-f_mask.gts", f"{prefix}-b_mask.gbs",
        f"{prefix}-f_silkscreen.gto", f"{prefix}-b_silkscreen.gbo",
        f"{prefix}-Edge_Cuts.gm1", f"{prefix}-PTH.drl", f"{prefix}-NPTH.drl",
    }
    with zipfile.ZipFile(path) as archive:
        names = {Path(name).name for name in archive.namelist()}
    require(expected <= names, f"missing manufacturing layers in {path}: {expected - names}")


def main():
    check_drc(ROOT / "build" / "main_final_drc.rpt")
    check_drc(ROOT / "build" / "controller_final_drc.rpt")

    review = json.loads((ROOT / "build" / "mechanical_review.json").read_text(encoding="utf-8"))
    assembly = review["assembly"]
    intersection_keys = [key for key in assembly if key.endswith("intersection_mm3")]
    require(intersection_keys, "mechanical report contains no intersection checks")
    for key in intersection_keys:
        require(abs(float(assembly[key])) < 1e-6, f"mechanical collision: {key}={assembly[key]}")
    require(assembly["bottom_row_conflicting_screw_relief_removed"], "bad plate mount was not removed")
    require(assembly["case_external_plan_mm"] == [307.0, 106.5],
            "case no longer matches the selected Linhai outside plan")
    require(abs(float(assembly["case_typing_angle_deg"]) - 5.0) < 1e-6,
            "case typing angle changed")
    require(assembly["controller_bay_inside_gh60_footprint"],
            "controller bay escaped the GH60 outside footprint")
    expected_bottom_mounts = [[47.625, 85.2], [238.125, 85.2]]
    require(assembly["round_main_mounts"][-2:] == expected_bottom_mounts,
            "balanced bottom-row mount axes changed")

    plate_report = json.loads((ROOT / "build" / "plate_fixed_analysis.json").read_text(encoding="utf-8"))
    require(plate_report["component_count"] == 70, "unexpected fixed plate contour count")
    require(plate_report["closed_component_count"] == 70, "fixed plate has open contours")
    require(all(item["edge_count"] != 33 for item in plate_report["components"]),
            "obsolete merged Menu/screw contour still exists")

    main_board = (ROOT / "hardware" / "keyboard" / "Minilite64.kicad_pcb").read_text(encoding="utf-8")
    carrier = (ROOT / "hardware" / "controller" / "RP2040_Zero_Carrier.kicad_pcb").read_text(encoding="utf-8")
    for layer in ("F.Cu", "B.Cu", "F.Mask", "B.Mask", "F.SilkS", "B.SilkS", "Edge.Cuts"):
        require(f'"{layer}"' in main_board, f"main PCB missing layer declaration {layer}")
        require(f'"{layer}"' in carrier, f"carrier missing layer declaration {layer}")
    require(main_board.count('MountingHole_2.7mm') == 3, "main PCB must retain three original round mounts")
    require(main_board.count('MountingHole_2.4mm') == 2, "main PCB must contain two bottom-row M2 mounts")
    standing = review["artifacts"]["case_a1_standing"]["bounds_mm"]
    require(all(float(value) <= 256.0 for value in standing),
            f"standing one-piece case exceeds Bambu A1 build volume: {standing}")
    require("279.6 56.824" in main_board and "6.15 56.824" in main_board,
            "main PCB side mounting notches are missing")

    metadata = json.loads((ROOT / "build" / "hardware_metadata.json").read_text(encoding="utf-8"))
    require(metadata["main_board"]["mount_holes"][-2:] == expected_bottom_mounts,
            "hardware metadata is missing the bottom-row mounts")
    drill_report = (ROOT / "manufacturing" / "keyboard" / "drill_report.rpt").read_text(encoding="utf-8")
    require('T2  2.400mm  0.0945"  (2 holes)' in drill_report,
            "manufacturing drill package is missing the two 2.4 mm NPTH mounts")

    keyboard = json.loads((ROOT / "firmware" / "vial-qmk" / "keyboards" / "minilite64" / "keyboard.json").read_text(encoding="utf-8"))
    require(keyboard["matrix_pins"]["rows"] == ["GP29", "GP28", "GP27", "GP26", "GP15"],
            "firmware row pins changed")
    require(keyboard["matrix_pins"]["cols"] == [f"GP{i}" for i in range(13, -1, -1)],
            "firmware column pins changed")
    require(keyboard["diode_direction"] == "COL2ROW", "wrong diode direction")

    uf2 = ROOT / "firmware" / "releases" / "Minilite64_vial.uf2"
    require(uf2.stat().st_size > 32_000, "compiled UF2 is missing or unexpectedly small")
    expected_hash = (ROOT / "firmware" / "releases" / "SHA256SUMS.txt").read_text().split()[0]
    require(hashlib.sha256(uf2.read_bytes()).hexdigest() == expected_hash, "UF2 checksum mismatch")

    check_gerber_zip(ROOT / "manufacturing" / "Minilite64_keyboard_gerber.zip", "Minilite64")
    check_gerber_zip(ROOT / "manufacturing" / "RP2040_Zero_Carrier_gerber.zip", "RP2040_Zero_Carrier")
    print("Minilite64 release validation passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
