"""Sensor platform for Waste Collection Schedule integration."""
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_MUNICIPALITY_ID,
    CONF_MUNICIPALITY_NAME,
    CONF_STREET,
    ATTR_NEXT_COLLECTION,
    ATTR_WASTE_TYPE,
    ATTR_DAYS_UNTIL,
    ATTR_COLLECTIONS,
    ATTR_ALL_COLLECTIONS,
    ATTR_SCHEDULE,
    WASTE_TYPES,
)
from .coordinator import WasteCollectionCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the waste collection sensor."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Create entities
    entities = []

    # Create main sensor (next collection)
    entities.append(NextWasteCollectionSensor(coordinator, entry))

    # Create waste type specific sensors
    for waste_id, waste_info in WASTE_TYPES.items():
        if waste_id in coordinator.data["waste_types"]:
            entities.append(
                WasteTypeSensor(
                    coordinator,
                    entry,
                    waste_id,
                    waste_info["name"],
                    waste_info["icon"],
                    waste_info["color"]
                )
            )

    async_add_entities(entities)


class WasteCollectionSensorBase(CoordinatorEntity):
    """Base class for waste collection sensors."""

    def __init__(self, coordinator: WasteCollectionCoordinator, config_entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.municipality_id = config_entry.data[CONF_MUNICIPALITY_ID]
        self.municipality_name = config_entry.data[CONF_MUNICIPALITY_NAME]
        self.street = config_entry.data[CONF_STREET]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.municipality_id)},
            name=f"Waste Collection - {self.municipality_name}",
            manufacturer="kiedysmieci.info",
            model="Waste Collection Schedule",
            sw_version="0.1.0",
        )


class NextWasteCollectionSensor(WasteCollectionSensorBase, SensorEntity):
    """Sensor for the next waste collection."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: WasteCollectionCoordinator, config_entry: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_name = f"Next Waste Collection {self.street}"
        self._attr_unique_id = f"{self.municipality_id}_{self.street}_next_collection"
        self._attr_icon = "mdi:trash-can-outline"

    @property
    def native_value(self) -> Optional[str]:
        """Return the next collection date."""
        if self.coordinator.data and self.coordinator.data.get("next_collection"):
            return self.coordinator.data["next_collection"]["date"]
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        attrs = {}

        if self.coordinator.data and self.coordinator.data.get("next_collection"):
            next_collection = self.coordinator.data["next_collection"]
            attrs[ATTR_WASTE_TYPE] = next_collection["waste_type"]
            attrs[ATTR_DAYS_UNTIL] = next_collection["days_until"]
            attrs["weekday"] = next_collection["weekday"]
            attrs["waste_id"] = next_collection["waste_id"]
            attrs["icon"] = next_collection["icon"]
            attrs["color"] = next_collection["color"]

        # Add upcoming collections for each type
        if self.coordinator.data and self.coordinator.data.get("next_collections"):
            attrs[ATTR_COLLECTIONS] = [
                {
                    "date": c["date"],
                    "waste_type": c["waste_type"],
                    "waste_id": c["waste_id"],
                    "days_until": c["days_until"],
                    "weekday": c["weekday"]
                }
                for c in self.coordinator.data["next_collections"][:5]  # Show next 5 collections
            ]

        return attrs


class WasteTypeSensor(WasteCollectionSensorBase, SensorEntity):
    """Sensor for specific waste type collection."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self,
        coordinator: WasteCollectionCoordinator,
        config_entry: ConfigEntry,
        waste_id: str,
        waste_name: str,
        icon: str,
        color: str
    ):
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self.waste_id = waste_id
        self.waste_name = waste_name
        self._attr_name = f"{self.waste_name} Collection {self.street}"
        self._attr_unique_id = f"{self.municipality_id}_{self.street}_{self.waste_id}"
        self._attr_icon = icon
        self.color = color

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        return (
            self.coordinator.data is not None
            and self.waste_id in self.coordinator.data["waste_types"]
        )

    @property
    def native_value(self) -> Optional[str]:
        """Return the next collection date for this waste type."""
        if (
            self.coordinator.data
            and self.waste_id in self.coordinator.data["waste_types"]
            and self.coordinator.data["waste_types"][self.waste_id]["next_collection"]
        ):
            return self.coordinator.data["waste_types"][self.waste_id]["next_collection"]
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        attrs = {}

        if (
            self.coordinator.data
            and self.waste_id in self.coordinator.data["waste_types"]
        ):
            waste_data = self.coordinator.data["waste_types"][self.waste_id]

            if waste_data["next_collection"]:
                attrs[ATTR_DAYS_UNTIL] = waste_data["days_until"]
                attrs["weekday"] = waste_data["next_collection_weekday"]

            # Add all future collection dates for this type
            attrs[ATTR_ALL_COLLECTIONS] = waste_data["dates"]
            attrs["icon"] = self._attr_icon
            attrs["color"] = self.color

        return attrs