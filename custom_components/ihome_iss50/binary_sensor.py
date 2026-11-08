from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .const import DOMAIN
from .entity import ISS50Entity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ISS50BinarySensor(coordinator, r)
            for r in coordinator.readings
            if r.kind in ("motion", "occupancy")
        ]
    )


class ISS50BinarySensor(ISS50Entity, BinarySensorEntity):
    def __init__(self, coordinator, reading):
        super().__init__(coordinator, reading)
        self._attr_device_class = (
            BinarySensorDeviceClass.MOTION
            if reading.kind == "motion"
            else BinarySensorDeviceClass.OCCUPANCY
        )

    @property
    def is_on(self):
        return None if self.value is None else bool(self.value)
