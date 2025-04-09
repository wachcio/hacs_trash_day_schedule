"""The TrashDay integration."""
import asyncio
import logging
import os
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
    try:
        municipality_id = entry.data[CONF_MUNICIPALITY_ID]
        street = entry.data[CONF_STREET]
        municipality_name = entry.data.get(CONF_MUNICIPALITY_NAME, "Unknown Municipality")

        # Oblicz interwał aktualizacji
        scan_interval_minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds() / 60)
        update_interval = timedelta(minutes=scan_interval_minutes)

        # Utwórz koordynatora
        coordinator = WasteCollectionCoordinator(
            hass,
            municipality_id=municipality_id,
            street=street,
            update_interval=update_interval,
        )

        # Fetch initial data
        await coordinator.async_config_entry_first_refresh()

        # Sprawdź dane, nawet puste dane są OK, ale błąd nie
        if coordinator.last_update_success is False:
            raise ConfigEntryNotReady("Failed to fetch initial data")

        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Setup platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Setup options update listener
        entry.async_on_unload(entry.add_update_listener(update_options))

        # Utwórz funkcję serwisową do tworzenia szablonów
        @callback
        def install_template_sensors(call):
            """Install template sensors for TrashDay."""
            try:
                force = call.data.get("force", False)
                _LOGGER.info("Installing TrashDay template sensors (force=%s)", force)

                # Przygotuj nazwę ulicy bezpieczną dla nazwy pliku
                safe_street = street.lower().replace(' ', '_').replace('-', '_')

                # Utwórz plik szablonu
                template_path = hass.config.path(f"trash_day_{safe_street}_templates.yaml")

                # Zawartość szablonu
                template_content = """
- sensor:
    - name: "trash_day_{street}_next_days_text"
      state: >
        {{% set days = state_attr('sensor.next_waste_collection_{street}', 'days_until') %}}
        {{% if days == 0 %}}
          Dzisiaj!
        {{% elif days == 1 %}}
          Jutro!
        {{% elif days != None %}}
          Za {{{{ days }}}} dni
        {{% else %}}
          Brak danych
        {{% endif %}}

    - name: "trash_day_{street}_bio_days_text"
      state: >
        {{% set days = state_attr('sensor.biodegradable_collection_{street}', 'days_until') %}}
        {{% if days == 0 %}}
          Dzisiaj!
        {{% elif days == 1 %}}
          Jutro!
        {{% elif days != None %}}
          Za {{{{ days }}}} dni
        {{% else %}}
          Brak danych
        {{% endif %}}

    - name: "trash_day_{street}_mixed_days_text"
      state: >
        {{% set days = state_attr('sensor.mixed_collection_{street}', 'days_until') %}}
        {{% if days == 0 %}}
          Dzisiaj!
        {{% elif days == 1 %}}
          Jutro!
        {{% elif days != None %}}
          Za {{{{ days }}}} dni
        {{% else %}}
          Brak danych
        {{% endif %}}

    - name: "trash_day_{street}_plastic_days_text"
      state: >
        {{% set days = state_attr('sensor.plastic_and_metal_collection_{street}', 'days_until') %}}
        {{% if days == 0 %}}
          Dzisiaj!
        {{% elif days == 1 %}}
          Jutro!
        {{% elif days != None %}}
          Za {{{{ days }}}} dni
        {{% else %}}
          Brak danych
        {{% endif %}}

    - name: "trash_day_{street}_paper_days_text"
      state: >
        {{% set days = state_attr('sensor.paper_collection_{street}', 'days_until') %}}
        {{% if days == 0 %}}
          Dzisiaj!
        {{% elif days == 1 %}}
          Jutro!
        {{% elif days != None %}}
          Za {{{{ days }}}} dni
        {{% else %}}
          Brak danych
        {{% endif %}}

    - name: "trash_day_{street}_glass_days_text"
      state: >
        {{% set days = state_attr('sensor.glass_collection_{street}', 'days_until') %}}
        {{% if days == 0 %}}
          Dzisiaj!
        {{% elif days == 1 %}}
          Jutro!
        {{% elif days != None %}}
          Za {{{{ days }}}} dni
        {{% else %}}
          Brak danych
        {{% endif %}}

    - name: "trash_day_{street}_ash_days_text"
      state: >
        {{% set days = state_attr('sensor.ash_collection_{street}', 'days_until') %}}
        {{% if days == 0 %}}
          Dzisiaj!
        {{% elif days == 1 %}}
          Jutro!
        {{% elif days != None %}}
          Za {{{{ days }}}} dni
        {{% else %}}
          Brak danych
        {{% endif %}}
""".format(street=safe_street)

                # Check if file exists and we don't want to force overwrite
                if os.path.exists(template_path) and not force:
                    _LOGGER.info("Template file already exists: %s", template_path)
                    return

                # Write the file
                with open(template_path, "w", encoding="utf-8") as f:
                    f.write(template_content)

                # Create notification for user
                hass.components.persistent_notification.async_create(
                    f"Template sensors for TrashDay have been created for street {street}. "
                    f"To activate them, add this line to your configuration.yaml file:\n\n"
                    f"template: !include {os.path.basename(template_path)}\n\n"
                    f"Then restart Home Assistant.",
                    title="TrashDay Templates Created",
                    notification_id=f"trash_day_templates_{entry.entry_id}"
                )

                _LOGGER.info("TrashDay template file created: %s", template_path)
            except Exception as e:
                _LOGGER.error("Error creating templates: %s", e, exc_info=True)

        # Rejestracja serwisu
        hass.services.async_register(
            DOMAIN, 'install_template_sensors', install_template_sensors
        )

        return True
    except Exception as e:
        _LOGGER.error("Error setting up TrashDay: %s", e, exc_info=True)
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