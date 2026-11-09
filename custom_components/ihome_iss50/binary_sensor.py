from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .const import DOMAIN
from .entity import ISS50Entity

DEVICE_CLASSES = {
    "motion": BinarySensorDeviceClass.MOTION,
    "occupancy": BinarySensorDeviceClass.OCCUPANCY,
    "sound": BinarySensorDeviceClass.SOUND,
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ISS50BinarySensor(coordinator, r)
            for r in coordinator.readings
            if r.kind in DEVICE_CLASSES
        ]
    )


class ISS50BinarySensor(ISS50Entity, BinarySensorEntity):
    def __init__(self, coordinator, reading):
        super().__init__(coordinator, reading)
        self._attr_device_class = DEVICE_CLASSES[reading.kind]
        if reading.kind == "sound":
            self._attr_name = "Sound detection"

    @property
    def available(self):
        if self.reading.kind == "sound" and self.is_on is None:
            return False
        return super().available

    @property
    def is_on(self):
        if self.reading.kind == "sound":
            value = self.value
            if not isinstance(value, (bool, int)) or value not in (0, 1):
                return None
            return value == self.reading.active_value
        return None if self.value is None else bool(self.value)
