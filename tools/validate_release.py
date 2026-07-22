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
    require(set(review["artifacts"]) == {
        "plate_full", "plate_a1_fitcheck", "case_full", "case_a1_standing",
        "service_cover", "plate_spacer",
    }, "unexpected or missing mechanical release artifacts")
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
    require(abs(float(assembly["case_front_height_mm"]) - 20.0) < 1e-6,
            "spacebar-side case height changed")
    require(abs(float(assembly["case_rear_height_mm"]) - 29.318) < 1e-3,
            "number-row-side case height changed")
    require(float(assembly["main_component_to_controller_clearance_mm"]) >= 1.25,
            "main PCB stack is too close to the RP2040 carrier")
    require(float(assembly["main_component_to_floor_clearance_mm"]) >= 6.0,
            "hot-swap components are too close to the case floor")
    require(assembly["controller_bay_inside_gh60_footprint"],
            "controller bay escaped the GH60 outside footprint")
    require(not assembly["service_cover_external_button_access"],
            "service cover must not expose BOOT/RESET externally")
    require(len(assembly["foot_recess_centres_mm"]) == 4,
            "case must contain four foot recesses")
    require(assembly["foot_pad_nominal_diameter_mm"] == 10.0,
            "foot pad diameter changed")
    require(assembly["foot_recess_body_diameter_mm"] == 11.2,
            "foot recess placement allowance changed")
    require(assembly["foot_recess_minimum_floor_mm"] >= 1.7,
            "foot recess leaves too little case floor")
    require(abs(float(assembly["plate_a1_joint_total_gap_mm"]) - 0.4) < 1e-6,
            "A1 fit-check plate joint tolerance changed")
    require(assembly["ffc_type"] == "A / same-side",
            "FFC contact orientation changed")
    require(assembly["ffc_width_mm"] == 21.0 and assembly["ffc_length_mm"] == 100.0,
            "FFC dimensions changed")
    require(not assembly["ffc_axial_twist"], "FFC route must not require axial twist")
    require(float(assembly["ffc_installed_bend_radius_mm"]) >= 3.0,
            "installed FFC bend radius is too tight")
    require(float(assembly["ffc_verified_service_pose_travel_mm"]) >= 65.0,
            "100 mm FFC leaves too little modeled carrier-last assembly travel")
    require(float(assembly["ffc_verified_service_pose_centerline_length_mm"]) <= 96.0,
            "tangent-constrained FFC service pose is too close to taut")
    require(float(assembly["ffc_verified_service_pose_minimum_radius_mm"]) >= 3.5,
            "tangent-constrained FFC service pose bends too tightly")
    require(float(assembly["ffc_verified_service_pose_cubic_minimum_radius_mm"]) >= 4.0,
            "service-pose drop curve bends too tightly")
    require(assembly["ffc_both_ends_locked_cover_install_allowed"],
            "carrier-last assembly must remain supported")
    require(not assembly["ffc_service_requires_main_pcb_release_first"],
            "carrier service must not require releasing the main PCB")
    sequence = assembly["ffc_required_assembly_sequence"]
    require(len(sequence) == 4
            and "main end" in sequence[0]
            and "carrier end" in sequence[2],
            "main-first / carrier-last FFC assembly sequence is missing")
    require(float(assembly["ffc_rear_wall_skin_mm"]) >= 1.5,
            "rear cable pocket leaves too little printed case wall")
    require(4.0 <= float(assembly["ffc_installed_slack_mm"]) <= 12.0,
            "installed FFC has an implausible amount of stored slack")
    require(float(assembly["ffc_scroll_minimum_actual_layer_gap_mm"]) >= 0.1,
            "FFC scroll layers do not have enough actual body clearance")
    require(float(assembly["usb_to_ffc_pocket_web_mm"]) >= 1.2,
            "USB tunnel to FFC pocket printed web is too thin")
    require(assembly["physical_ffc_fit_check_required"]
            and assembly["release_status"].startswith("prototype-only"),
            "release must remain prototype-only until a real FFC is fitted")
    corridor = assembly["reserved_ffc_corridor_mm"]
    require(float(corridor[2]) - float(corridor[0]) >= 22.5,
            "FFC corridor is too narrow for the 21 mm cable")
    fitcheck_bounds = review["artifacts"]["plate_a1_fitcheck"]["bounds_mm"]
    require(all(float(value) <= 256.0 for value in fitcheck_bounds),
            f"A1 fit-check plate exceeds build volume: {fitcheck_bounds}")
    mechanical_dir = ROOT / "hardware" / "mechanical"
    forbidden_split_names = (
        "Minilite64_case_A1_left.*", "Minilite64_case_A1_right.*",
        "Minilite64_case_joiner_print_2x.*", "Minilite64_plate_print_left.*",
        "Minilite64_plate_print_right.*",
    )
    require(not any(next(mechanical_dir.glob(pattern), None) is not None
                    for pattern in forbidden_split_names),
            "obsolete split-print artifacts are still present")
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
    require('PLATE DXF • 1:1 CHECK' in main_board,
            "main PCB is missing the plate verification silkscreen label")
    require(main_board.count(
        '(stroke (width 0.12) (type default)) (layer "F.SilkS")'
    ) == 1626, "main PCB plate verification silkscreen is incomplete")
    require('(start 131.875 0) (end 153.875 0)' in main_board,
            "main ZIF mouth is not facing the rear C-bend pocket")
    require('(pad "1" smd roundrect (at 133.375 3.2)' in main_board
            and '(net 1 "COL0")' in main_board,
            "main ZIF left edge must be pin 1 / COL0")
    require('(pad "20" smd roundrect (at 152.375 3.2)' in main_board
            and '(net 20 "GND")' in main_board,
            "main ZIF right edge must be pin 20 / GND")
    require('(start 9 26.8)' in carrier and '(end 31 26.8)' in carrier,
            "carrier ZIF mouth is not facing the rear like the main ZIF")
    require('(at 10.5 30)' in carrier and '(net "COL0")' in carrier,
            "carrier ZIF pin 1 / COL0 placement changed")
    standing = review["artifacts"]["case_a1_standing"]["bounds_mm"]
    require(all(float(value) <= 256.0 for value in standing),
            f"standing one-piece case exceeds Bambu A1 build volume: {standing}")
    require("279.6 56.824" in main_board and "6.15 56.824" in main_board,
            "main PCB side mounting notches are missing")

    metadata = json.loads((ROOT / "build" / "hardware_metadata.json").read_text(encoding="utf-8"))
    require(metadata["main_board"]["mount_holes"][-2:] == expected_bottom_mounts,
            "hardware metadata is missing the bottom-row mounts")
    require(metadata["ffc"]["type"] == "A / same-side"
            and metadata["ffc"]["width"] == 21.0
            and metadata["ffc"]["length"] == 100
            and metadata["ffc"]["assembly_strategy"] == "main-first / carrier-last"
            and metadata["ffc"]["both_ends_locked_cover_install_allowed"]
            and not metadata["ffc"]["axial_twist"],
            "hardware metadata has the wrong FFC specification")
    drill_report = (ROOT / "manufacturing" / "keyboard" / "drill_report.rpt").read_text(encoding="utf-8")
    require('T2  2.400mm  0.0945"  (2 holes)' in drill_report,
            "manufacturing drill package is missing the two 2.4 mm NPTH mounts")
    pinout = (ROOT / "manufacturing" / "FFC_pinout.csv").read_text(encoding="utf-8-sig")
    require("1,1,COL0,GP13" in pinout and "20,20,GND,GND" in pinout,
            "FFC straight-through endpoint pinout is not documented")
    bom = (ROOT / "manufacturing" / "BOM.csv").read_text(encoding="utf-8-sig")
    require("Type-A FFC, 100mm x 21mm" in bom and "Same-side contacts" in bom,
            "BOM has the wrong FFC contact orientation")

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
