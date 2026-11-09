"""Sound detection tests; vendor UUIDs below are synthetic, not iSS50 captures."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.ihome_iss50.binary_sensor import ISS50BinarySensor
from custom_components.ihome_iss50.config_flow import SoundOptionsFlow
from custom_components.ihome_iss50.protocol import Reading, parse_readings

VENDOR_UUID = "12345678-1234-5678-ABCD-123456789001"


def database(*chars, service_name=None):
    if service_name:
        chars = ({"iid": 99, "type": "23", "perms": ["pr"], "value": service_name}, *chars)
    return [{"aid": 1, "services": [{"iid": 10, "characteristics": list(chars)}]}]


def sound_char(**overrides):
    return {
        "iid": 11,
        "type": VENDOR_UUID,
        "format": "bool",
        "perms": ["pr", "ev"],
        "description": "Sound Detected",
        "value": False,
        **overrides,
    }


@pytest.mark.parametrize("description", ["Sound Detected", "SoundDetection", "Noise Detected"])
def test_sound_description_creates_sound_reading(description):
    readings, values = parse_readings(database(sound_char(description=description)))
    assert [(r.kind, r.key, r.events) for r in readings] == [("sound", (1, 11), True)]
    assert values[(1, 11)]["value"] is False


def test_sound_service_name_identifies_one_unnamed_binary_characteristic():
    readings, _ = parse_readings(database(sound_char(description=""), service_name="Sound Sensor"))
    assert readings[0].kind == "sound"


@pytest.mark.parametrize(
    "description",
    ["Sound Sensitivity", "Sound Threshold", "Sound Enabled", "Sound Level", "Occupancy"],
)
def test_settings_and_occupancy_are_not_sound_detection(description):
    readings, _ = parse_readings(database(sound_char(description=description)))
    assert readings == []


def test_writable_sound_settings_are_not_detected():
    readings, _ = parse_readings(database(sound_char(perms=["pr", "pw", "ev"])))
    assert readings == []


def test_ambiguous_service_does_not_guess_a_sound_field():
    readings, _ = parse_readings(
        database(
            sound_char(description=""),
            sound_char(iid=12, description=""),
            service_name="Sound Sensor",
        )
    )
    assert readings == []


def test_manual_mapping_selects_only_chosen_field_and_preserves_standard_sensors():
    readings, _ = parse_readings(
        database(
            sound_char(description=""),
            {"iid": 2, "type": "11", "perms": ["pr"], "value": 20},
        ),
        sound_characteristic="1.11",
        sound_active_value=0,
    )
    assert [(r.kind, r.iid) for r in readings] == [("sound", 11), ("temperature", 2)]
    assert readings[0].active_value == 0


def test_disabled_sound_mapping_preserves_other_readings():
    readings, _ = parse_readings(database(sound_char()), sound_characteristic="disabled")
    assert readings == []


def test_vendor_uuid_prefix_does_not_impersonate_standard_temperature():
    readings, _ = parse_readings(database(sound_char(type="00000011-1234-5678-ABCD-123456789001")))
    assert [r.kind for r in readings] == ["sound"]


@pytest.mark.parametrize(
    ("value", "active", "expected"),
    [
        (0, 1, False),
        (1, 1, True),
        (False, 1, False),
        (True, 1, True),
        (0, 0, True),
        (2, 1, None),
        ("0", 1, None),
        (None, 1, None),
    ],
)
def test_sound_binary_sensor_values(value, active, expected):
    coordinator = SimpleNamespace(
        entry=SimpleNamespace(unique_id="test-device"),
        data={(1, 11): {"value": value}},
        last_update_success=True,
        async_add_listener=Mock(),
    )
    entity = ISS50BinarySensor(coordinator, Reading(1, 11, "sound", True, active_value=active))
    assert entity.device_class == BinarySensorDeviceClass.SOUND
    assert entity.name == "Sound detection"
    assert entity.is_on is expected
    assert entity.available is (expected is not None)


def options_flow():
    entry = SimpleNamespace(
        entry_id="test-entry",
        options={},
        data={"pairing": {"iOSDeviceLTSK": "private-test-key"}, "host": "192.0.2.1"},
    )
    coordinator = SimpleNamespace(accessories=database(sound_char(description="")))
    flow = SoundOptionsFlow()
    flow.handler = entry.entry_id
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_known_entry=Mock(return_value=entry)),
        data={"ihome_iss50": {entry.entry_id: coordinator}},
    )
    return flow, entry


@pytest.mark.asyncio
async def test_sound_options_preserve_existing_pairing_and_reload():
    flow, entry = options_flow()
    result = await flow.async_step_init({"sound_characteristic": "1.11", "sound_active_value": "0"})
    assert result["type"] == "create_entry"
    assert result["data"] == {"sound_characteristic": "1.11", "sound_active_value": 0}
    assert entry.data["pairing"]["iOSDeviceLTSK"] == "private-test-key"
    assert flow.automatic_reload is True


@pytest.mark.asyncio
async def test_sound_options_reject_nonexistent_field():
    flow, _ = options_flow()
    result = await flow.async_step_init(
        {"sound_characteristic": "1.999", "sound_active_value": "1"}
    )
    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_sound_mapping"}
