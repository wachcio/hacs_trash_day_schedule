"""Config flow for TrashDay integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_NAME

from .const import (
    DOMAIN,
    CONF_MUNICIPALITY_ID,
    CONF_MUNICIPALITY_NAME,
    CONF_STREET,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_NAME,
    SELECTOR_MUNICIPALITY,
    SELECTOR_STREET,
    OPTION_SCAN_INTERVAL,
)
from .coordinator import WasteCollectionCoordinator

_LOGGER = logging.getLogger(__name__)


async def _get_municipalities(hass: HomeAssistant):
    """Get list of municipalities."""
    try:
        return await WasteCollectionCoordinator.get_municipalities(hass)
    except Exception as e:
        _LOGGER.error("Error getting municipalities: %s", e)
        return []


async def _get_streets(hass: HomeAssistant, municipality_id: str):
    """Get list of streets for municipality."""
    try:
        return await WasteCollectionCoordinator.get_streets(hass, municipality_id)
    except Exception as e:
        _LOGGER.error("Error getting streets: %s", e)
        return {"streets": [], "municipality_name": "Unknown"}


class WasteCollectionFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TrashDay."""

    VERSION = 1

    def __init__(self):
        """Initialize flow."""
        self._municipalities = []
        self._streets_data = {"streets": [], "municipality_name": ""}
        self._municipality_id = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is None:
            # Fetch municipalities
            self._municipalities = await _get_municipalities(self.hass)

            if not self._municipalities:
                return self.async_abort(reason="no_municipalities")

            return await self.async_step_municipality()

        return await self.async_step_municipality(user_input)

    async def async_step_municipality(self, user_input=None):
        """Handle municipality selection step."""
        errors = {}

        if user_input is not None:
            self._municipality_id = user_input[CONF_MUNICIPALITY_ID]

            # Fetch streets for selected municipality
            self._streets_data = await _get_streets(self.hass, self._municipality_id)

            if not self._streets_data["streets"]:
                errors["base"] = "no_streets"
            else:
                return await self.async_step_street()

        # Prepare municipality dropdown options
        municipality_options = {}
        for m in self._municipalities:
            try:
                key = m["id"]
                value = f"{m['municipality']} ({m['district']}, {m['province']})"
                municipality_options[key] = value
            except (KeyError, TypeError):
                _LOGGER.error("Invalid municipality data: %s", m)

        if not municipality_options:
            return self.async_abort(reason="no_municipalities")

        schema = vol.Schema(
            {
                vol.Required(CONF_MUNICIPALITY_ID): vol.In(municipality_options),
            }
        )

        return self.async_show_form(
            step_id="municipality",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "municipality_count": str(len(self._municipalities))
            }
        )

    async def async_step_street(self, user_input=None):
        """Handle street selection step."""
        errors = {}

        municipality_name = self._streets_data.get("municipality_name", "Unknown")

        if user_input is not None:
            selected_street = user_input[CONF_STREET]

            # Create the entry
            return self.async_create_entry(
                title=f"{municipality_name} - {selected_street}",
                data={
                    CONF_MUNICIPALITY_ID: self._municipality_id,
                    CONF_MUNICIPALITY_NAME: municipality_name,
                    CONF_STREET: selected_street,
                },
            )

        # Prepare street dropdown options
        street_options = {}
        for s in self._streets_data.get("streets", []):
            street_options[s] = s

        if not street_options:
            return self.async_abort(reason="no_streets")

        schema = vol.Schema(
            {
                vol.Required(CONF_STREET): vol.In(street_options),
            }
        )

        return self.async_show_form(
            step_id="street",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "municipality_name": municipality_name,
                "street_count": str(len(self._streets_data.get("streets", [])))
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for the integration."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get default scan interval
        default_scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds() / 60
        )

        # Ensure it's a valid positive integer
        try:
            default_scan_interval = int(default_scan_interval)
            if default_scan_interval <= 0:
                default_scan_interval = int(DEFAULT_SCAN_INTERVAL.total_seconds() / 60)
        except (ValueError, TypeError):
            default_scan_interval = int(DEFAULT_SCAN_INTERVAL.total_seconds() / 60)

        options = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=default_scan_interval,
            ): cv.positive_int,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))