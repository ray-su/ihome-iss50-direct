"""Device configuration numbers using the existing authenticated connection."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory

from .const import DOMAIN
from .entity import ISS50Entity

NAMES = {
    "sound_threshold": "Sound detection threshold",
    "motion_silence_duration": "Motion silence duration",
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ISS50Number(coordinator, control)
        for control in coordinator.controls
        if control.kind in NAMES
    )


class ISS50Number(ISS50Entity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, control):
        super().__init__(coordinator, control)
        self._attr_name = NAMES[control.kind]
        self._attr_native_min_value = control.minimum
        self._attr_native_max_value = control.maximum
        self._attr_native_step = control.step

    @property
    def available(self):
        return super().available and self.reading.accepts(self.value)

    @property
    def native_value(self):
        return self.value if self.reading.accepts(self.value) else None

    async def async_set_native_value(self, value):
        await self.coordinator.async_write_control(self.reading, value)
