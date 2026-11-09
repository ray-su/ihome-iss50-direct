"""Diagnostics must not export config secrets or identity string values."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.ihome_iss50.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_diagnostics_omit_pairing_and_identity_values():
    accessories = [
        {
            "aid": 1,
            "services": [
                {
                    "type": "test",
                    "characteristics": [
                        {"iid": 1, "type": "30", "format": "string", "value": "private-serial"},
                        {"iid": 2, "type": "23", "format": "string", "value": "private-room-name"},
                        {
                            "iid": 3,
                            "type": "custom",
                            "format": "bool",
                            "value": True,
                            "description": "Sound Detected",
                        },
                    ],
                }
            ],
        }
    ]
    coordinator = SimpleNamespace(
        accessories=accessories,
        readings=[],
        pairing=SimpleNamespace(
            list_accessories_and_characteristics=AsyncMock(return_value=accessories)
        ),
    )
    hass = SimpleNamespace(data={"ihome_iss50": {"test": coordinator}})
    entry = SimpleNamespace(entry_id="test", data={"host": "private-ip", "pairing": "private-key"})
    result = await async_get_config_entry_diagnostics(hass, entry)
    encoded = json.dumps(result)
    assert "private-" not in encoded
    assert result["fresh_snapshot"] is True
    assert result["characteristics"][2]["value"] is True
