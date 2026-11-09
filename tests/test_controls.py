"""Settings observed on an iSS50, with writes confined to mocks/simulator."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.ihome_iss50 import ISS50Coordinator
from custom_components.ihome_iss50.controls import MOTION_SILENCE, SOUND_THRESHOLD, parse_controls
from custom_components.ihome_iss50.number import ISS50Number
from custom_components.ihome_iss50.protocol import Reading, parse_readings
from custom_components.ihome_iss50.select import ISS50DisplayUnits


def database():
    # Curated protocol metadata only; no device identity, keys, or sensor states.
    return [
        {
            "aid": 1,
            "services": [
                {
                    "characteristics": [
                        {
                            "iid": 27,
                            "type": SOUND_THRESHOLD,
                            "format": "int",
                            "perms": ["pr", "pw"],
                            "minValue": 3,
                            "maxValue": 200,
                            "value": 3,
                        },
                        {
                            "iid": 28,
                            "type": "00000036-0000-1000-8000-0026BB765291",
                            "format": "uint8",
                            "perms": ["pr", "pw", "ev"],
                            "minValue": 0,
                            "maxValue": 1,
                            "value": 1,
                        },
                        {
                            "iid": 30,
                            "type": MOTION_SILENCE,
                            "format": "int",
                            "perms": ["pr", "pw"],
                            "minValue": 1,
                            "maxValue": 120,
                            "value": 30,
                        },
                    ]
                }
            ],
        }
    ]


def test_hardware_settings_are_separate_from_sensor_readings():
    controls, values = parse_controls(database())
    assert [c.kind for c in controls] == [
        "sound_threshold",
        "display_units",
        "motion_silence_duration",
    ]
    assert values[(1, 28)] == {"value": 1}
    assert parse_readings(database())[0] == []


@pytest.mark.parametrize(
    "change",
    [
        {"perms": ["pr"]},
        {"perms": ["pw"]},
        {"type": "UNKNOWN"},
        {"format": "string"},
        {"minValue": -1},
        {"maxValue": 999},
        {"minStep": 0},
        {"minStep": True},
        {"valid-values": []},
        {"valid-values": ["3"]},
    ],
)
def test_no_control_for_unsafe_or_unrecognized_metadata(change):
    data = database()
    chars = data[0]["services"][0]["characteristics"]
    chars[0].update(change)
    assert all(c.kind != "sound_threshold" for c in parse_controls(data)[0])


def test_entity_state_ranges_and_units():
    controls, values = parse_controls(database())
    coordinator = SimpleNamespace(
        entry=SimpleNamespace(unique_id="test-device"),
        data=values,
        last_update_success=True,
        async_add_listener=Mock(),
    )
    sound = ISS50Number(coordinator, controls[0])
    display = ISS50DisplayUnits(coordinator, controls[1])
    motion = ISS50Number(coordinator, controls[2])
    assert sound.native_min_value == 3 and sound.native_max_value == 200
    assert motion.native_min_value == 1 and motion.native_max_value == 120
    assert motion.native_unit_of_measurement is None  # Firmware unit not yet verified.
    assert display.options == ["celsius", "fahrenheit"]
    assert display.current_option == "fahrenheit"
    assert display.unique_id == "test-device_1_28"
    values[(1, 28)] = {"value": 0}
    assert display.current_option == "celsius"
    values[(1, 27)] = {"value": "3"}
    assert not sound.available and sound.native_value is None
    values[(1, 28)] = {"value": True}
    assert not display.available and display.current_option is None


@pytest.fixture
async def coordinator(tmp_path):
    controls, values = parse_controls(database())
    pairing = SimpleNamespace(
        put_characteristics=AsyncMock(return_value={}),
        get_characteristics=AsyncMock(return_value={(1, 27): {"value": 20}}),
        subscribe=AsyncMock(),
        shutdown=AsyncMock(),
    )
    entry = SimpleNamespace(
        unique_id="test-device",
        async_on_unload=Mock(),
        pref_disable_polling=False,
    )
    coord = ISS50Coordinator(HomeAssistant(str(tmp_path)), entry, pairing, [], values, controls)
    yield coord
    await coord.async_shutdown()


@pytest.mark.asyncio
async def test_write_reads_back_and_suppresses_optimistic_callback(coordinator):
    observed = []
    coordinator.async_update_listeners = lambda: observed.append(dict(coordinator.data))

    async def write(values):
        coordinator.on_event({(1, 27): {"value": 20}})
        assert coordinator.data[(1, 27)]["value"] == 3
        return {}

    coordinator.pairing.put_characteristics.side_effect = write
    await ISS50Number(coordinator, coordinator.controls[0]).async_set_native_value(20.0)
    coordinator.pairing.put_characteristics.assert_awaited_once_with([(1, 27, 20)])
    assert type(coordinator.pairing.put_characteristics.call_args.args[0][0][2]) is int
    assert observed[-1][(1, 27)]["value"] == 20


@pytest.mark.asyncio
async def test_display_writes_zero_for_celsius(coordinator):
    coordinator.pairing.get_characteristics.return_value = {(1, 28): {"value": 0}}
    entity = ISS50DisplayUnits(coordinator, coordinator.controls[1])
    await entity.async_select_option("celsius")
    coordinator.pairing.put_characteristics.assert_awaited_once_with([(1, 28, 0)])
    assert entity.current_option == "celsius"
    with pytest.raises(HomeAssistantError):
        await entity.async_select_option("kelvin")


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [2, 201, 3.5, float("nan"), float("inf"), True, "20"])
async def test_invalid_values_never_reach_device(coordinator, value):
    with pytest.raises(HomeAssistantError):
        await coordinator.async_write_control(coordinator.controls[0], value)
    coordinator.pairing.put_characteristics.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["rejected", "disconnect", "readback", "different"])
async def test_write_failures_do_not_claim_success(coordinator, failure):
    if failure == "rejected":
        coordinator.pairing.put_characteristics.return_value = {(1, 27): {"status": -70404}}
    elif failure == "disconnect":
        coordinator.pairing.put_characteristics.side_effect = ConnectionError("private payload")
    elif failure == "readback":
        coordinator.pairing.get_characteristics.return_value = {(1, 27): {"status": -70402}}
    else:
        coordinator.pairing.get_characteristics.return_value = {(1, 27): {"value": 10}}
    with pytest.raises(HomeAssistantError) as error:
        await coordinator.async_write_control(coordinator.controls[0], 20)
    assert "private payload" not in str(error.value)
    if failure == "different":
        assert coordinator.data[(1, 27)]["value"] == 10
    else:
        assert coordinator.data[(1, 27)]["status"] != 0
    assert coordinator._writing_key is None


@pytest.mark.asyncio
async def test_control_read_failure_keeps_standard_sensors_available(coordinator):
    coordinator.readings = [Reading(1, 20, "temperature", False)]

    async def read(keys):
        if keys == [(1, 20)]:
            return {(1, 20): {"value": 22}}
        raise ConnectionError

    coordinator.pairing.get_characteristics.side_effect = read
    result = await coordinator._async_update_data()
    assert result[(1, 20)]["value"] == 22
    assert result[(1, 27)]["status"] != 0
    coordinator.pairing.put_characteristics.assert_not_awaited()
    coordinator.pairing.subscribe.assert_awaited_once_with([(1, 28)])


@pytest.mark.asyncio
async def test_poll_and_write_are_serialized(coordinator):
    started, resume = asyncio.Event(), asyncio.Event()

    async def read(keys):
        if not started.is_set():
            started.set()
            await resume.wait()
        return {key: {"value": 20} for key in keys}

    coordinator.pairing.get_characteristics.side_effect = read
    poll = asyncio.create_task(coordinator._async_update_data())
    await started.wait()
    write = asyncio.create_task(coordinator.async_write_control(coordinator.controls[0], 20))
    await asyncio.sleep(0)
    coordinator.pairing.put_characteristics.assert_not_awaited()
    resume.set()
    await poll
    await write
    assert coordinator.data[(1, 27)]["value"] == 20
