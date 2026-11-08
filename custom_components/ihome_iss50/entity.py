from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class ISS50Entity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, reading):
        super().__init__(coordinator)
        self.reading = reading
        device_id = coordinator.entry.unique_id
        self._attr_unique_id = f"{device_id}_{reading.aid}_{reading.iid}"
        self._attr_name = reading.kind.capitalize()
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": "iHome iSS50",
            "manufacturer": "SDI Technologies",
            "model": "iSS50",
        }

    @property
    def available(self):
        data = (self.coordinator.data or {}).get(self.reading.key, {})
        return super().available and data.get("status", 0) == 0 and "value" in data

    @property
    def value(self):
        return (self.coordinator.data or {}).get(self.reading.key, {}).get("value")
