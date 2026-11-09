"""Allowlisted settings observed in a physical iSS50 accessory database."""

import math
from dataclasses import dataclass

from .protocol import standard_type

SOUND_THRESHOLD = "298A64ED-9BD6-4ADE-9697-F180CEACE5C4"
MOTION_SILENCE = "B0FABCF0-8911-41BC-9159-CB0323E3D49D"


@dataclass(frozen=True)
class Control:
    aid: int
    iid: int
    kind: str
    events: bool
    minimum: int
    maximum: int
    step: int = 1
    valid_values: tuple[int, ...] | None = None

    @property
    def key(self):
        return (self.aid, self.iid)

    def accepts(self, value):
        return (
            type(value) in (int, float)
            and math.isfinite(value)
            and value == int(value)
            and self.minimum <= value <= self.maximum
            and (value - self.minimum) % self.step == 0
            and (self.valid_values is None or value in self.valid_values)
        )


def parse_controls(accessories):
    """Never infer writable settings from similar names or arbitrary vendor fields."""
    controls, values = [], {}
    for accessory in accessories:
        for service in accessory.get("services", []):
            for char in service.get("characteristics", []):
                if not {"pr", "pw"}.issubset(char.get("perms", [])):
                    continue
                uuid = str(char.get("type", "")).upper()
                if standard_type(uuid) == "36" and char.get("format") == "uint8":
                    kind, lower, upper = "display_units", 0, 1
                elif uuid == SOUND_THRESHOLD and char.get("format") == "int":
                    kind, lower, upper = "sound_threshold", 3, 200
                elif uuid == MOTION_SILENCE and char.get("format") == "int":
                    kind, lower, upper = "motion_silence_duration", 1, 120
                else:
                    continue
                minimum = char.get("minValue", lower)
                maximum = char.get("maxValue", upper)
                step = char.get("minStep", 1)
                if (
                    any(type(v) is not int for v in (minimum, maximum, step))
                    or not lower <= minimum <= maximum <= upper
                    or step < 1
                ):
                    continue
                valid = char.get("valid-values")
                if valid is not None and (
                    not isinstance(valid, list)
                    or not valid
                    or any(type(v) is not int or not minimum <= v <= maximum for v in valid)
                ):
                    continue
                control = Control(
                    accessory["aid"],
                    char["iid"],
                    kind,
                    "ev" in char["perms"],
                    minimum,
                    maximum,
                    step,
                    tuple(valid) if valid is not None else None,
                )
                controls.append(control)
                if "value" in char:
                    values[control.key] = {"value": char["value"]}
    return controls, values
