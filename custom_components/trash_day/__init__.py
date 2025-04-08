"""The TrashDay integration."""
import asyncio
import logging
import os
import yaml
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import Platform
from homeassistant.helpers import template

from .const import (
    DOMAIN,
    CONF_MUNICIPALITY_ID,
    CONF_MUNICIPALITY_NAME,
    CONF_STREET,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import WasteCollectionCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the TrashDay component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TrashDay from a config entry."""
    municipality_id = entry.data[CONF_MUNICIPALITY_ID]
    street = entry.data[CONF_STREET]
    municipality_name = entry.data.get(CONF_MUNICIPALITY_NAME, "Unknown Municipality")
    update_interval = timedelta(minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds() / 60))

    coordinator = WasteCollectionCoordinator(
        hass,
        municipality_id=municipality_id,
        street=street,
        update_interval=update_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.data:
        raise ConfigEntryNotReady("Failed to fetch initial data")

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Install template sensors
    safe_street = street.lower().replace(' ', '_').replace('-', '_')
    await create_template_sensors(hass, safe_street, entry.entry_id)

    # Register service to install templates
    @callback
    def install_template_sensors(call):
        """Install template sensors for TrashDay."""
        force = call.data.get("force", False)
        _LOGGER.info("Installing TrashDay template sensors (force=%s)", force)
        return asyncio.run_coroutine_threadsafe(
            create_template_sensors(hass, safe_street, entry.entry_id, force),
            hass.loop
        ).result()

    hass.services.async_register(
        DOMAIN, 'install_template_sensors', install_template_sensors
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Setup options update listener
    entry.async_on_unload(entry.add_update_listener(update_options))

    return True


async def create_template_sensors(hass, street_name, entry_id, force=False):
    """Create template sensors for trash day data."""

    # Check if templates already exist
    existing = [
        entity_id for entity_id in hass.states.async_entity_ids("sensor")
        if entity_id.startswith(f"sensor.trash_day_{street_name}_")
    ]

    if existing and not force:
        _LOGGER.info("TrashDay template sensors already exist. Skipping creation.")
        return False

    try:
        # Path to templates file
        template_file = os.path.join(os.path.dirname(__file__), "templates.yaml")

        if not os.path.exists(template_file):
            _LOGGER.warning("Templates file not found: %s", template_file)
            return False

        # Load templates file - używając async_add_executor_job, aby nie blokować pętli
        content = await hass.async_add_executor_job(
            lambda: open(template_file, "r", encoding="utf-8").read()
        )
        templates_config = yaml.safe_load(content)

        if not templates_config:
            _LOGGER.warning("No templates found in templates file")
            return False

        # Process and create templates
        coordinator = hass.data[DOMAIN][entry_id]

        # Get entity IDs for this street
        entities = {
            "bio": f"sensor.biodegradable_collection_{street_name}",
            "mixed": f"sensor.mixed_collection_{street_name}",
            "plastic": f"sensor.plastic_and_metal_collection_{street_name}",
            "paper": f"sensor.paper_collection_{street_name}",
            "glass": f"sensor.glass_collection_{street_name}",
            "ash": f"sensor.ash_collection_{street_name}"
        }

        # Create template sensors
        for template_def in templates_config[0]['sensor']:
            # Get template name and configuration
            template_id = template_def['name']
            template_state = template_def['state']
            template_attributes = template_def.get('attributes', {})

            # Replace entity IDs in templates
            for key, entity_id in entities.items():
                placeholder = f"sensor.{key}_collection_cicha"
                template_state = template_state.replace(placeholder, entity_id)

                # Update attribute templates
                for attr_name, attr_value in template_attributes.items():
                    template_attributes[attr_name] = attr_value.replace(placeholder, entity_id)

            # Create the template sensor
            template_sensor_id = f"trash_day_{street_name}_{template_id}"

            # Remove special characters from ID
            safe_id = "".join(c if c.isalnum() or c == '_' else '_' for c in template_id)

            # Register the template sensor
            await hass.helpers.template.async_register_template_entity(
                entry_id,
                "sensor",
                safe_id,
                template_state,
                template_id.replace("_", " ").title(),
                "mdi:trash-can-outline",
                template_attributes,
                None
            )

            _LOGGER.debug("Created template sensor: %s", template_sensor_id)

        _LOGGER.info("TrashDay template sensors installed successfully")
        return True

    except Exception as ex:
        _LOGGER.error("Error creating TrashDay template sensors: %s", ex)
        return False

async def update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options for existing entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok