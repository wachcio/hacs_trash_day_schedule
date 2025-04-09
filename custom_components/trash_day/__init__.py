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
    try:
        # Create a new YAML file in the config directory
        templates_yaml_path = hass.config.path(f"trash_day_{street_name}_templates.yaml")

        # Check if file already exists and we're not forcing recreation
        if os.path.exists(templates_yaml_path) and not force:
            _LOGGER.info("Template YAML file already exists. Skipping creation.")
            return False

        # Path to templates file
        template_file = os.path.join(os.path.dirname(__file__), "templates.yaml")

        if not os.path.exists(template_file):
            _LOGGER.warning("Templates file not found: %s", template_file)
            return False

        # Load templates file
        content = await hass.async_add_executor_job(
            lambda: open(template_file, "r", encoding="utf-8").read()
        )

        # Try to load YAML content to validate it
        try:
            templates_config = yaml.safe_load(content)
            if not templates_config:
                _LOGGER.warning("No templates found in templates file")
                return False
        except yaml.YAMLError as exc:
            _LOGGER.error(f"Error parsing templates.yaml: {exc}")
            return False

        # Get entity IDs for this street
        replacements = {
            "sensor.biodegradable_collection_cicha": f"sensor.biodegradable_collection_{street_name}",
            "sensor.mixed_collection_cicha": f"sensor.mixed_collection_{street_name}",
            "sensor.plastic_and_metal_collection_cicha": f"sensor.plastic_and_metal_collection_{street_name}",
            "sensor.paper_collection_cicha": f"sensor.paper_collection_{street_name}",
            "sensor.glass_collection_cicha": f"sensor.glass_collection_{street_name}",
            "sensor.ash_collection_cicha": f"sensor.ash_collection_{street_name}",
            "sensor.next_waste_collection_cicha": f"sensor.next_waste_collection_{street_name}"
        }

        # Process templates content
        processed_content = content
        for placeholder, replacement in replacements.items():
            processed_content = processed_content.replace(placeholder, replacement)

        # Replace template names to include street name
        for template_def in templates_config[0]['sensor']:
            original_name = template_def['name']
            new_name = f"trash_day_{street_name}_{original_name}"
            processed_content = processed_content.replace(f"name: \"{original_name}\"", f"name: \"{new_name}\"")
            processed_content = processed_content.replace(f"name: '{original_name}'", f"name: '{new_name}'")

        # Write the custom template file
        await hass.async_add_executor_job(
            lambda: open(templates_yaml_path, "w", encoding="utf-8").write(processed_content)
        )

        # Create notification for user
        hass.components.persistent_notification.async_create(
            f"Template sensors for TrashDay have been created for street {street_name}. "
            f"To activate them, add this line to your configuration.yaml file:\n\n"
            f"template: !include {os.path.basename(templates_yaml_path)}\n\n"
            f"Then restart Home Assistant.",
            title="TrashDay Templates Created",
            notification_id=f"trash_day_templates_{entry_id}"
        )

        _LOGGER.info("TrashDay template file created: %s", templates_yaml_path)
        return True

    except Exception as ex:
        _LOGGER.error("Error creating TrashDay template file: %s", ex, exc_info=True)
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