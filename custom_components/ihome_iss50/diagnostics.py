"""Export characteristic metadata without config entries or pairing credentials."""

import asyncio

from .const import DOMAIN


def characteristic_summary(accessories):
    """Allowlist descriptors and numeric states; omit string/data/TLV values."""
    result = []
    for accessory in accessories:
        for service in accessory.get("services", []):
            for char in service.get("characteristics", []):
                item = {"aid": accessory["aid"], "service_type": service.get("type")}
                for key in (
                    "iid",
                    "type",
                    "format",
                    "perms",
                    "description",
                    "minValue",
                    "maxValue",
                    "minStep",
                    "unit",
                    "valid-values",
                ):
                    if key in char:
                        item[key] = char[key]
                value = char.get("value")
                if isinstance(value, (bool, int, float)):
                    item["value"] = value
                result.append(item)
    return result


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None:
        return {"loaded": False}
    accessories = coordinator.accessories
    fresh = False
    try:
        async with asyncio.timeout(15):
            accessories = await coordinator.pairing.list_accessories_and_characteristics()
            fresh = True
    except Exception:
        pass
    return {
        "loaded": True,
        "fresh_snapshot": fresh,
        "characteristics": characteristic_summary(accessories),
        "readings": [{"aid": r.aid, "iid": r.iid, "kind": r.kind} for r in coordinator.readings],
    }
