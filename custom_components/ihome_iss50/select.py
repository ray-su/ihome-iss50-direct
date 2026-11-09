"""Physical LCD temperature units, independent of HA's temperature display."""

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .entity import ISS50Entity

OPTIONS = {"celsius": 0, "fahrenheit": 1}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ISS50DisplayUnits(coordinator, control)
        for control in coordinator.controls
        if control.kind == "display_units"
    )


class ISS50DisplayUnits(ISS50Entity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "display_units"

    def __init__(self, coordinator, control):
        super().__init__(coordinator, control)
        self._attr_name = None
        self._attr_options = [name for name, value in OPTIONS.items() if control.accepts(value)]

    @property
    def current_option(self):
        if not self.reading.accepts(self.value):
            return None
        return next((name for name, value in OPTIONS.items() if value == self.value), None)

    @property
    def available(self):
        return super().available and self.current_option is not None

    async def async_select_option(self, option):
        if option not in self.options:
            raise HomeAssistantError("Unsupported display unit")
        await self.coordinator.async_write_control(self.reading, OPTIONS[option])
