"""Generate QMK/Vial source files from the confirmed KLE matrix."""

from __future__ import annotations

import json
from pathlib import Path

from generate_hardware import parse_kle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "firmware" / "vial-qmk" / "keyboards" / "minilite64"


BASE_CODES = [
    ["KC_GRV", "KC_1", "KC_2", "KC_3", "KC_4", "KC_5", "KC_6", "KC_7", "KC_8", "KC_9", "KC_0", "KC_MINS", "KC_EQL", "KC_BSPC"],
    ["KC_TAB", "KC_Q", "KC_W", "KC_E", "KC_R", "KC_T", "KC_Y", "KC_U", "KC_I", "KC_O", "KC_P", "KC_LBRC", "KC_RBRC", "KC_BSLS"],
    ["KC_CAPS", "KC_A", "KC_S", "KC_D", "KC_F", "KC_G", "KC_H", "KC_J", "KC_K", "KC_L", "KC_SCLN", "KC_QUOT", "KC_ENT"],
    ["KC_LSFT", "KC_Z", "KC_X", "KC_C", "KC_V", "KC_B", "KC_N", "KC_M", "KC_COMM", "KC_DOT", "KC_SLSH", "KC_RSFT"],
    ["KC_LCTL", "KC_LGUI", "KC_LALT", "MO(1)", "KC_SPC", "MO(2)", "KC_APP", "MO(3)", "KC_RALT", "KC_RGUI", "KC_RCTL"],
]


def layer(fill="KC_TRNS"):
    return [[fill for _ in row] for row in BASE_CODES]


def flatten(rows):
    return [value for row in rows for value in row]


def generate():
    keys = parse_kle(ROOT / "KLE.txt")
    OUT.mkdir(parents=True, exist_ok=True)
    vial_dir = OUT / "keymaps" / "vial"
    vial_dir.mkdir(parents=True, exist_ok=True)

    layout = []
    for key in keys:
        layout.append({
            "label": key.label.replace("\n", "/"),
            "matrix": [key.row, key.col],
            "x": round(key.x / 19.05 - key.w / 2, 4),
            "y": key.row,
            **({"w": key.w} if key.w != 1 else {}),
        })
    keyboard = {
        "manufacturer": "Minilite",
        "keyboard_name": "Minilite64",
        "maintainer": "minilite",
        "bootloader": "rp2040",
        "processor": "RP2040",
        "diode_direction": "COL2ROW",
        "features": {"bootmagic": True, "command": False, "console": False, "extrakey": True, "mousekey": True, "nkro": True},
        "matrix_pins": {
            "rows": ["GP29", "GP28", "GP27", "GP26", "GP15"],
            "cols": ["GP13", "GP12", "GP11", "GP10", "GP9", "GP8", "GP7", "GP6", "GP5", "GP4", "GP3", "GP2", "GP1", "GP0"],
        },
        "usb": {"device_version": "1.0.0", "pid": "0x6464", "vid": "0xFEED"},
        "layouts": {"LAYOUT": {"layout": layout}},
    }
    (OUT / "keyboard.json").write_text(json.dumps(keyboard, indent=2), encoding="utf-8")

    layers = [BASE_CODES, layer(), layer(), layer()]
    # Recovery and useful defaults; Vial can remap all four layers later.
    layers[1][0][0] = "QK_BOOT"
    layers[1][1][8] = "KC_UP"
    layers[1][2][7:10] = ["KC_LEFT", "KC_DOWN", "KC_RGHT"]
    layers[1][0][13] = "KC_DEL"
    layers[1][1][11:14] = ["KC_HOME", "KC_END", "KC_INS"]
    layers[2][0][1:13] = ["KC_F1", "KC_F2", "KC_F3", "KC_F4", "KC_F5", "KC_F6", "KC_F7", "KC_F8", "KC_F9", "KC_F10", "KC_F11", "KC_F12"]
    layers[2][1][7:10] = ["KC_MPRV", "KC_MPLY", "KC_MNXT"]
    layers[2][2][7:10] = ["KC_VOLD", "KC_MUTE", "KC_VOLU"]

    blocks = []
    for index, values in enumerate(layers):
        args = flatten(values)
        lines = []
        cursor = 0
        for row in BASE_CODES:
            row_args = args[cursor:cursor + len(row)]
            cursor += len(row)
            lines.append("        " + ", ".join(row_args))
        blocks.append(f"    [{index}] = LAYOUT(\n" + ",\n".join(lines) + "\n    )")
    keymap_c = """// Generated from KLE.txt.  Requires the Vial QMK fork.
#include QMK_KEYBOARD_H

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
""" + ",\n".join(blocks) + "\n};\n"
    (vial_dir / "keymap.c").write_text(keymap_c, encoding="utf-8")
    (vial_dir / "config.h").write_text(
        """#pragma once

#define VIAL_KEYBOARD_UID {0x4D, 0x69, 0x6E, 0x69, 0x6C, 0x69, 0x74, 0x65}
#define VIAL_UNLOCK_COMBO_ROWS {4, 4}
#define VIAL_UNLOCK_COMBO_COLS {3, 7}
#define DYNAMIC_KEYMAP_LAYER_COUNT 4
""",
        encoding="utf-8",
    )
    (vial_dir / "rules.mk").write_text("VIA_ENABLE = yes\nVIAL_ENABLE = yes\nLTO_ENABLE = yes\n", encoding="utf-8")

    via_rows = []
    for row_index in range(5):
        row_items = []
        for key in [item for item in keys if item.row == row_index]:
            if key.w != 1:
                row_items.append({"w": key.w})
            row_items.append(f"{key.row},{key.col}")
        via_rows.append(row_items)
    vial_json = {
        "name": "Minilite64",
        "vendorId": "0xFEED",
        "productId": "0x6464",
        "matrix": {"rows": 5, "cols": 14},
        "layouts": {"keymap": via_rows},
    }
    (vial_dir / "vial.json").write_text(json.dumps(vial_json, indent=2), encoding="utf-8")
    (OUT / "readme.md").write_text(
        """# Minilite64 Vial firmware

Copy this directory to `vial-qmk/keyboards/minilite64`, then build with:

```sh
make minilite64:vial
```

Hold the top-left key while plugging in for Bootmagic reset. The default Fn1
layer also places `QK_BOOT` on the top-left key. Normal Vial remapping never
requires the physical BOOT/RESET buttons.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    generate()
    print(f"Generated firmware in {OUT}")
