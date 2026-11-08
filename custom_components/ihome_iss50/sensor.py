from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import LIGHT_LUX, PERCENTAGE, UnitOfTemperature

from .const import DOMAIN
from .entity import ISS50Entity

METADATA = {
    "temperature": (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    "humidity": (SensorDeviceClass.HUMIDITY, PERCENTAGE),
    "illuminance": (SensorDeviceClass.ILLUMINANCE, LIGHT_LUX),
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [ISS50Sensor(coordinator, r) for r in coordinator.readings if r.kind in METADATA]
    )


class ISS50Sensor(ISS50Entity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, reading):
        super().__init__(coordinator, reading)
        self._attr_device_class, self._attr_native_unit_of_measurement = METADATA[reading.kind]

    @property
    def native_value(self):
        return self.value
