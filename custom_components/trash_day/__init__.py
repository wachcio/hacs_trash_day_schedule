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
        # Create a new YAML file that will be loaded by Home Assistant
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

        # Load templates file - używając async_add_executor_job, aby nie blokować pętli
        content = await hass.async_add_executor_job(
            lambda: open(template_file, "r", encoding="utf-8").read()
        )
        templates_config = yaml.safe_load(content)

        if not templates_config:
            _LOGGER.warning("No templates found in templates file")
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
        modified_templates = []
        for template_def in templates_config[0]['sensor']:
            template_copy = template_def.copy()
            original_name = template_copy['name']
            template_copy['name'] = f"trash_day_{street_name}_{original_name}"
            modified_templates.append(template_copy)

        # Create new YAML content
        new_config = [{'sensor': modified_templates}]
        new_yaml_content = yaml.dump(new_config, allow_unicode=True, default_flow_style=False)

        # Write the custom template file
        await hass.async_add_executor_job(
            lambda: open(templates_yaml_path, "w", encoding="utf-8").write(new_yaml_content)
        )

        # Create notification for user
        hass.components.persistent_notification.async_create(
            f"Template sensors for TrashDay have been created for street {street_name}. "
            f"To use them, add this line to your configuration.yaml:\n\n"
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

        # Get entity IDs for this street
        entities = {
            "bio": f"sensor.biodegradable_collection_{street_name}",
            "mixed": f"sensor.mixed_collection_{street_name}",
            "plastic": f"sensor.plastic_and_metal_collection_{street_name}",
            "paper": f"sensor.paper_collection_{street_name}",
            "glass": f"sensor.glass_collection_{street_name}",
            "ash": f"sensor.ash_collection_{street_name}",
            "next": f"sensor.next_waste_collection_{street_name}"
        }

        # Prepare template configuration for sensors
        template_sensors_config = []

        # Create template sensors
        for template_def in templates_config[0]['sensor']:
            # Get template name and configuration
            template_id = template_def['name']
            template_state = template_def['state']
            template_attributes = template_def.get('attributes', {})

            # Replace entity IDs in templates
            for placeholder, entity_id in [
                ("sensor.biodegradable_collection_cicha", entities["bio"]),
                ("sensor.mixed_collection_cicha", entities["mixed"]),
                ("sensor.plastic_and_metal_collection_cicha", entities["plastic"]),
                ("sensor.paper_collection_cicha", entities["paper"]),
                ("sensor.glass_collection_cicha", entities["glass"]),
                ("sensor.ash_collection_cicha", entities["ash"]),
                ("sensor.next_waste_collection_cicha", entities["next"])
            ]:
                template_state = template_state.replace(placeholder, entity_id)

                # Update attribute templates
                for attr_name, attr_value in template_attributes.items():
                    template_attributes[attr_name] = attr_value.replace(placeholder, entity_id)

            # Create the template sensor configuration
            sensor_id = f"trash_day_{street_name}_{template_id}"
            sensor_config = {
                "name": template_id.replace("_", " ").title(),
                "unique_id": f"{entry_id}_{sensor_id}",
                "state": template_state,
                "icon": "mdi:trash-can-outline"
            }

            # Add attributes
            if template_attributes:
                sensor_config["attributes"] = template_attributes

            template_sensors_config.append(sensor_config)

            _LOGGER.debug("Prepared template sensor: %s", sensor_id)

        # Create a config entry for the template sensors
        if template_sensors_config:
            # Import component directly
            from homeassistant.components.template import DOMAIN as TEMPLATE_DOMAIN
            from homeassistant.components.template.sensor import SensorTemplate

            # Create config data
            config = {
                TEMPLATE_DOMAIN: {
                    "sensor": template_sensors_config
                }
            }

            # Set up the template sensors
            await hass.config.components.async_forward_entry_setup(
                ConfigEntry(
                    entry_id=f"{entry_id}_templates",
                    domain=TEMPLATE_DOMAIN,
                    title=f"TrashDay Templates for {street_name}",
                    data={},
                    options=config
                ),
                "sensor"
            )

            _LOGGER.info("TrashDay template sensors installed successfully")
            return True
        else:
            _LOGGER.warning("No template sensors were created")
            return False

    except Exception as ex:
        _LOGGER.error("Error creating TrashDay template sensors: %s", ex, exc_info=True)
        return False
    """Create template sensors for trash day data."""

    try:
        # Create a new YAML file that will be loaded by Home Assistant
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
        templates_config = yaml.safe_load(content)

        if not templates_config:
            _LOGGER.warning("No templates found in templates file")
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

        # Write the custom template file
        await hass.async_add_executor_job(
            lambda: open(templates_yaml_path, "w", encoding="utf-8").write(processed_content)
        )

        # Ask the user to restart Home Assistant
        hass.components.persistent_notification.async_create(
            f"Template sensors for TrashDay have been created for street {street_name}. "
            "Please restart Home Assistant to activate these templates.",
            title="TrashDay Templates Created",
            notification_id=f"trash_day_templates_{entry_id}"
        )

        _LOGGER.info("TrashDay template file created: %s", templates_yaml_path)
        return True

    except Exception as ex:
        _LOGGER.error("Error creating TrashDay template file: %s", ex)
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