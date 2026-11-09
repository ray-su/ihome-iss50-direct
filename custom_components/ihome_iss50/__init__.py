"""Local iHome iSS50 integration using direct-IP HomeKit pairing."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS
from .controls import parse_controls
from .protocol import load_pairing, parse_readings, unpair_direct

_LOGGER = logging.getLogger(__name__)


class ISS50Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, pairing, readings, initial, controls=()):
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
        self.controls = controls
        self._io_lock = asyncio.Lock()
        self._writing_key = None
        self.data = initial
        self.cancel_events = None
        self.subscribed = False
        self._poll_events = None

    async def _async_update_data(self):
        async with self._io_lock:
            return await self._async_read_data()

    async def _async_read_data(self):
        values = dict(self.data or {})
        self._poll_events = {}
        try:
            # Read one at a time: older iHome firmware can fail large batches.
            for item in [*self.readings, *self.controls]:
                try:
                    response = await self.pairing.get_characteristics([item.key])
                    values[item.key] = response.get(item.key, {"status": -70402})
                except Exception:
                    if item.kind != "sound" and item not in self.controls:
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
        events = [r.key for r in [*self.readings, *self.controls] if r.events]
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
        # aiohomekit emits an optimistic callback for writes. Only publish a
        # setting after reading it back from the accessory.
        changes = {key: value for key, value in changes.items() if key != self._writing_key}
        if changes:
            self.data = {**(self.data or {}), **changes}
            if self._poll_events is not None:
                self._poll_events.update(changes)
            # async_set_updated_data resets the poll timer. A busy event source
            # must not starve reads for characteristics with missing events.
            self.async_update_listeners()

    async def async_write_control(self, control, value):
        if control not in self.controls or not control.accepts(value):
            raise HomeAssistantError("Invalid value for this iHome setting")
        async with self._io_lock:
            self._writing_key = control.key
            try:
                async with asyncio.timeout(20):
                    response = await self.pairing.put_characteristics(
                        [(control.aid, control.iid, int(value))]
                    )
                    if response.get(control.key, {}).get("status", 0) != 0:
                        raise HomeAssistantError("The iHome sensor rejected the setting")
                    result = await self.pairing.get_characteristics([control.key])
                    state = result.get(control.key, {})
                    if state.get("status", 0) != 0 or not control.accepts(state.get("value")):
                        raise HomeAssistantError("Could not verify the iHome setting")
            except Exception:
                self._writing_key = None
                self.on_event({control.key: {"status": -70402}})
                raise HomeAssistantError(
                    "Could not confirm the iHome setting. It may have changed; "
                    "wait for the next device read before trying again."
                ) from None
            finally:
                self._writing_key = None
            self.on_event({control.key: state})
            if state["value"] != value:
                raise HomeAssistantError("The iHome sensor did not retain the requested value")

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
        controls, control_values = parse_controls(accessories)
        values.update(control_values)
    except Exception as err:
        await pairing.shutdown()
        raise ConfigEntryNotReady("Cannot read iHome accessory database") from err
    coordinator = ISS50Coordinator(hass, entry, pairing, readings, values, controls)
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
