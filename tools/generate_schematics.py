"""Generate editable KiCad 10 schematics for the two Minilite64 boards.

Requires `kicad-sch-api==0.5.6`.  The generated files are committed, so this
dependency is needed only when regenerating the schematics.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def configure_kicad_symbols():
    if os.environ.get("KICAD_SYMBOL_DIR"):
        return
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "KiCad" / "10.0" / "share" / "kicad" / "symbols",
        Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols"),
    ]
    for candidate in candidates:
        if candidate.is_dir():
            os.environ["KICAD_SYMBOL_DIR"] = str(candidate)
            return
    raise RuntimeError("KiCad 10 symbol directory was not found")


configure_kicad_symbols()
import kicad_sch_api as ksa  # noqa: E402
from generate_hardware import FFC_NETS, parse_kle  # noqa: E402


def generate_keyboard():
    schematic = ksa.Schematic.create("Minilite64 key matrix", paper="A3")
    keys = parse_kle(ROOT / "KLE.txt")
    for key in keys:
        x = 18.0 + key.col * 27.0
        y = 28.0 + key.row * 48.0
        schematic.components.add(
            "Switch:SW_Push",
            reference=key.ref,
            value=key.label.replace("\n", "/"),
            position=(x, y),
            footprint="Minilite:Kailh_MX_Hotswap",
            grid_units=False,
        )
        schematic.components.add(
            "Device:D_Small",
            reference=key.diode,
            value="1N4148W",
            position=(x + 12.7, y),
            footprint="Minilite:SOD-123_HandSolder",
            grid_units=False,
        )
        schematic.add_wire_between_pins(key.ref, "2", key.diode, "1")
        schematic.add_label(f"COL{key.col}", pin=(key.ref, "1"), size=1.0)
        schematic.add_label(f"ROW{key.row}", pin=(key.diode, "2"), size=1.0)

    schematic.components.add(
        "Connector_Generic:Conn_01x20",
        reference="J1",
        value="20P 1.0mm FFC Type A",
        position=(400.0, 130.0),
        footprint="Minilite:FFC_20P_1.0mm_BottomContact",
        grid_units=False,
    )
    for pin, net in enumerate(FFC_NETS, 1):
        schematic.add_label(net, pin=("J1", str(pin)), size=1.0)

    schematic.save_as(ROOT / "hardware" / "keyboard" / "Minilite64.kicad_sch")


def generate_controller():
    schematic = ksa.Schematic.create("Minilite64 RP2040-Zero carrier", paper="A4")
    schematic.components.add(
        "Connector_Generic:Conn_01x20",
        reference="J1",
        value="20P 1.0mm FFC Type A",
        position=(45.0, 100.0),
        footprint="Minilite:FFC_20P_1.0mm_BottomContact",
        grid_units=False,
    )
    for pin, net in enumerate(FFC_NETS, 1):
        schematic.add_label(net, pin=("J1", str(pin)), size=1.0)

    schematic.components.add(
        "Connector_Generic:Conn_01x23",
        reference="U1",
        value="Waveshare RP2040-Zero 23.5x18mm",
        position=(140.0, 100.0),
        footprint="Minilite:Waveshare_RP2040_Zero_Castellated",
        grid_units=False,
    )
    # Generic connector pins follow the carrier footprint's documented order:
    # left edge top-to-bottom, right edge top-to-bottom, then bottom left-to-right.
    rp_pin_labels = [
        "5V_NC", "GND", "3V3_NC", "ROW0", "ROW1", "ROW2", "ROW3", "ROW4", "GP14_SPARE",
        "COL13", "COL12", "COL11", "COL10", "COL9", "COL8", "COL7", "COL6", "COL5",
        "COL0", "COL1", "COL2", "COL3", "COL4",
    ]
    for pin, net in enumerate(rp_pin_labels, 1):
        schematic.add_label(net, pin=("U1", str(pin)), size=1.0)

    schematic.save_as(ROOT / "hardware" / "controller" / "RP2040_Zero_Carrier.kicad_sch")


if __name__ == "__main__":
    generate_keyboard()
    generate_controller()
    print("Generated native KiCad schematics")
