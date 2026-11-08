import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiohomekit.exceptions import AuthenticationError, BusyError, UnavailableError

from custom_components.ihome_iss50 import config_flow as cf


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (AuthenticationError("test"), "authentication_failed"),
        (BusyError("test"), "pairing_busy"),
        (UnavailableError("test"), "already_paired"),
        (ConnectionError("test"), "cannot_connect"),
        (RuntimeError("test"), "cannot_pair"),
    ],
)
def test_errors_have_actionable_messages(error, expected):
    assert cf.error_key(error) == expected


def flow():
    obj = cf.ConfigFlow()
    obj.flow_id = "test"
    obj.handler = "ihome_iss50"
    obj.context = {}
    obj.hass = SimpleNamespace(
        async_create_task=asyncio.create_task,
        config_entries=SimpleNamespace(flow=SimpleNamespace(async_init=AsyncMock())),
    )
    obj.async_set_unique_id = AsyncMock()
    obj._abort_if_unique_id_configured = lambda: None
    return obj


@pytest.mark.asyncio
async def test_form_validates_input():
    f = flow()
    result = await f.async_step_user({"host": "bad-ip", "pin": "123"})
    assert result["errors"]["base"] == "invalid_input"


@pytest.mark.asyncio
async def test_background_pairing_saves_credentials_without_pin(monkeypatch):
    data = {
        "AccessoryPairingID": "AA:BB:CC:DD:EE:FF",
        "AccessoryIP": "10.0.0.2",
        "AccessoryPort": 51826,
    }
    monkeypatch.setattr(cf, "find_port", AsyncMock(return_value=51826))
    monkeypatch.setattr(cf, "pair_direct", AsyncMock(return_value=data))
    f = flow()
    result = await f.async_step_user({"host": "10.0.0.2", "pin": "32154987", "port": 0})
    assert result["type"] == "progress"
    await f._task
    assert (await f.async_step_connect())["type"] == "progress_done"
    result = await f.async_step_finish()
    assert result["type"] == "create_entry"
    assert result["data"]["pairing"] == data
    assert "pin" not in result["data"]
    assert "pin" not in f._input


@pytest.mark.asyncio
async def test_pair_failure_returns_retry_form(monkeypatch):
    monkeypatch.setattr(cf, "pair_direct", AsyncMock(side_effect=ConnectionError))
    f = flow()
    await f.async_step_user({"host": "10.0.0.2", "pin": "32154987", "port": 80})
    with pytest.raises(ConnectionError):
        await f._task
    result = await f.async_step_finish()
    assert result["step_id"] == "retry"
    assert result["errors"]["base"] == "cannot_connect"
    assert "pin" not in f._input


@pytest.mark.asyncio
async def test_cancelled_ui_retains_successful_pairing(monkeypatch):
    gate = asyncio.Event()
    data = {
        "AccessoryPairingID": "AA:BB:CC:DD:EE:FF",
        "AccessoryIP": "10.0.0.2",
        "AccessoryPort": 80,
    }

    async def pair(*args):
        await gate.wait()
        return data

    monkeypatch.setattr(cf, "pair_direct", pair)
    f = flow()
    await f.async_step_user({"host": "10.0.0.2", "pin": "32154987", "port": 80})
    await asyncio.sleep(0)
    f._task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await f._task
    f.async_remove()
    gate.set()
    for _ in range(5):
        await asyncio.sleep(0)
    imported = f.hass.config_entries.flow.async_init
    imported.assert_awaited_once()
    assert imported.call_args.kwargs["data"]["pairing"] == data
