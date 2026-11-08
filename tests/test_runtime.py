"""Regression tests against Home Assistant's real coordinator scheduler."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import frame

from custom_components.ihome_iss50 import ISS50Coordinator, async_remove_entry
from custom_components.ihome_iss50 import config_flow as cf
from custom_components.ihome_iss50.protocol import Reading


@pytest.mark.asyncio
async def test_events_do_not_postpone_polling(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    frame.async_setup(hass)
    entry = SimpleNamespace(async_on_unload=Mock(), pref_disable_polling=False)
    pairing = SimpleNamespace(shutdown=AsyncMock())
    coordinator = ISS50Coordinator(hass, entry, pairing, [], {(1, 1): {"value": 20}})
    listener = Mock()
    remove_listener = coordinator.async_add_listener(listener)
    scheduled_poll = coordinator._unsub_refresh
    assert scheduled_poll is not None
    try:
        for value in range(21, 31):
            coordinator.on_event({(1, 1): {"value": value}})
            assert coordinator._unsub_refresh is scheduled_poll
        assert coordinator.data[(1, 1)]["value"] == 30
        assert listener.call_count == 10
    finally:
        remove_listener()
        await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_poll_keeps_event_for_another_characteristic(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    frame.async_setup(hass)
    entry = SimpleNamespace(async_on_unload=Mock(), pref_disable_polling=False)
    readings = [Reading(1, 1, "temperature", True), Reading(1, 2, "humidity", True)]
    pairing = SimpleNamespace(shutdown=AsyncMock(), subscribe=AsyncMock())
    coordinator = ISS50Coordinator(hass, entry, pairing, readings, {})

    async def get(keys):
        if keys == [(1, 1)]:
            return {(1, 1): {"value": 20}}
        coordinator.on_event({(1, 1): {"value": 25}})
        return {(1, 2): {"value": 40}}

    pairing.get_characteristics = get
    try:
        result = await coordinator._async_update_data()
        assert result[(1, 1)]["value"] == 25
        assert result[(1, 2)]["value"] == 40
    finally:
        await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_reconfigure_preserves_credentials(monkeypatch):
    pairing = {"AccessoryPairingID": "AA:BB:CC:DD:EE:FF", "iOSDeviceLTSK": "test-key"}
    entry = SimpleNamespace(data={"host": "192.0.2.1", "port": 80, "pairing": pairing})
    flow = cf.ConfigFlow()
    flow._get_reconfigure_entry = lambda: entry
    flow.async_update_reload_and_abort = Mock(return_value={"type": "abort"})
    validate = AsyncMock()
    monkeypatch.setattr(cf, "validate_connection", validate)
    result = await flow.async_step_reconfigure({"host": "192.0.2.2", "port": 1234})
    assert result["type"] == "abort"
    validate.assert_awaited_once_with("192.0.2.2", 1234, pairing)
    flow.async_update_reload_and_abort.assert_called_once_with(
        entry, data_updates={"host": "192.0.2.2", "port": 1234}
    )


@pytest.mark.asyncio
async def test_reconfigure_failure_keeps_original_endpoint(monkeypatch):
    entry = SimpleNamespace(data={"host": "192.0.2.1", "port": 80, "pairing": {}})
    flow = cf.ConfigFlow()
    flow._get_reconfigure_entry = lambda: entry
    flow.async_update_reload_and_abort = Mock()
    monkeypatch.setattr(cf, "validate_connection", AsyncMock(side_effect=ConnectionError))
    result = await flow.async_step_reconfigure({"host": "192.0.2.2", "port": 1234})
    assert result["errors"]["base"] == "cannot_connect"
    flow.async_update_reload_and_abort.assert_not_called()
    assert entry.data["host"] == "192.0.2.1"


@pytest.mark.asyncio
async def test_removal_unpairs_using_current_endpoint(monkeypatch):
    data = {"iOSPairingId": "test-controller"}
    entry = SimpleNamespace(data={"host": "192.0.2.2", "port": 1234, "pairing": data})
    unpair = AsyncMock()
    monkeypatch.setattr("custom_components.ihome_iss50.unpair_direct", unpair)
    await async_remove_entry(None, entry)
    unpair.assert_awaited_once_with("192.0.2.2", 1234, data)


@pytest.mark.asyncio
async def test_removal_failure_does_not_log_credentials(monkeypatch, caplog):
    entry = SimpleNamespace(data={"host": "192.0.2.2", "port": 80, "pairing": {}})
    monkeypatch.setattr(
        "custom_components.ihome_iss50.unpair_direct",
        AsyncMock(side_effect=ConnectionError("sensitive-protocol-response")),
    )
    await async_remove_entry(None, entry)
    assert "Could not unpair" in caplog.text
    assert "sensitive-protocol-response" not in caplog.text
