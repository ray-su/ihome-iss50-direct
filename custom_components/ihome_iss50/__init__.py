"""Local iHome iSS50 integration using direct-IP HomeKit pairing."""

import logging
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS
from .protocol import load_pairing, parse_readings, unpair_direct

_LOGGER = logging.getLogger(__name__)


class ISS50Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, pairing, readings, initial):
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name="iHome iSS50",
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry
        self.pairing = pairing
        self.readings = readings
        self.data = initial
        self.cancel_events = None
        self.subscribed = False
        self._poll_events = None

    async def _async_update_data(self):
        values = dict(self.data or {})
        self._poll_events = {}
        try:
            # Read one at a time: older iHome firmware can fail large batches.
            for item in self.readings:
                try:
                    response = await self.pairing.get_characteristics([item.key])
                    values[item.key] = response.get(item.key, {"status": -70402})
                except Exception:
                    if item.kind != "sound":
                        raise
                    # Optional custom firmware fields must not disable the
                    # established standard sensors when a read is rejected.
                    values[item.key] = {"status": -70402}
            if not self.subscribed:
                await self._subscribe()
            # Events received during an awaited read are newer than the snapshot
            # collected at the beginning of this poll.
            return {**values, **self._poll_events}
        except Exception as err:
            raise UpdateFailed("Cannot read iHome sensor") from err
        finally:
            self._poll_events = None

    async def _subscribe(self):
        events = [r.key for r in self.readings if r.events]
        if not events:
            self.subscribed = True
            return
        self.subscribed = True
        for key in events:
            try:
                await self.pairing.subscribe([key])
            except Exception:
                # Continue subscribing to the other fields. Polling remains
                # active when this firmware rejects some notifications.
                self.subscribed = False

    def on_event(self, changes):
        if changes:
            self.data = {**(self.data or {}), **changes}
            if self._poll_events is not None:
                self._poll_events.update(changes)
            # async_set_updated_data resets the poll timer. A busy event source
            # must not starve reads for characteristics with missing events.
            self.async_update_listeners()

    async def close(self):
        await self.async_shutdown()
        if self.cancel_events:
            self.cancel_events()
        await self.pairing.shutdown()


async def async_setup_entry(hass, entry):
    pairing = load_pairing(entry.data["host"], entry.data["port"], entry.data["pairing"])
    try:
        accessories = await pairing.list_accessories_and_characteristics()
        readings, values = parse_readings(
            accessories,
            sound_characteristic=entry.options.get("sound_characteristic", "auto"),
            sound_active_value=entry.options.get("sound_active_value", 1),
        )
        if not readings:
            raise ValueError("No supported sensor characteristics")
    except Exception as err:
        await pairing.shutdown()
        raise ConfigEntryNotReady("Cannot read iHome accessory database") from err
    coordinator = ISS50Coordinator(hass, entry, pairing, readings, values)
    coordinator.accessories = accessories
    coordinator.cancel_events = pairing.dispatcher_connect(coordinator.on_event)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    try:
        await coordinator.async_config_entry_first_refresh()
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.close()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise
    return True


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.close()
        return True
    return False


async def async_remove_entry(hass, entry):
    """Remove this controller's pairing when the user deletes the integration."""
    try:
        await unpair_direct(entry.data["host"], entry.data["port"], entry.data["pairing"])
    except Exception as err:
        # HA continues deleting the entry even if this hook raises. Do not log
        # exception messages: a protocol error could contain sensitive data.
        _LOGGER.warning(
            "Could not unpair iHome during removal (%s). Restore a backup of "
            "the entry or reset the accessory before pairing again",
            type(err).__name__,
        )
