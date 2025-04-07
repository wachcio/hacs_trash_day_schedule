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
    return await WasteCollectionCoordinator.get_municipalities(hass)


async def _get_streets(hass: HomeAssistant, municipality_id: str):
    """Get list of streets for municipality."""
    return await WasteCollectionCoordinator.get_streets(hass, municipality_id)


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
        municipality_options = {m["id"]: f"{m['municipality']} ({m['district']}, {m['province']})"
                               for m in self._municipalities}

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

        municipality_name = self._streets_data["municipality_name"]

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
        street_options = {s: s for s in self._streets_data["streets"]}

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
                "street_count": str(len(self._streets_data["streets"]))
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

        options = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds() / 60
                ),
            ): cv.positive_int,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))