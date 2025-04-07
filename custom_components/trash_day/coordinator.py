"""Data coordinator for TrashDay integration."""
import logging
import asyncio
from datetime import datetime, date
import aiohttp
from urllib.parse import quote
from bs4 import BeautifulSoup
import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    DOMAIN,
    MUNICIPALITY_URL,
    STREETS_URL,
    SCHEDULE_URL,
    WASTE_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class WasteCollectionCoordinator(DataUpdateCoordinator):
    """Class to manage fetching waste collection data."""

    def __init__(
        self,
        hass: HomeAssistant,
        municipality_id: str,
        street: str,
        update_interval,
    ):
        """Initialize."""
        self.municipality_id = municipality_id
        self.street = street
        self.session = async_get_clientsession(hass)
        self._hass = hass

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    @staticmethod
    async def get_municipalities(hass: HomeAssistant):
        """Get list of available municipalities."""
        session = async_get_clientsession(hass)
        try:
            async with session.get(MUNICIPALITY_URL) as response:
                response.raise_for_status()
                html = await response.text()
        except (aiohttp.ClientError) as error:
            _LOGGER.error("Error fetching municipalities: %s", error)
            return []

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")
        select_element = soup.find("select", id="selGmina")

        if not select_element:
            _LOGGER.error("Could not find select element with id='selGmina'")
            return []

        options = select_element.find_all("option")
        municipalities = []

        # Parse each option
        for option in options:
            value = option.get("value")
            if not value:  # Skip empty or default option
                continue

            text = option.text.strip()
            match = re.search(
                r"woj\.: ([\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s\-]+) powiat: ([\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s\-]+) gmina: ([\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s\-]+)",
                text,
            )

            if match:
                province = match.group(1).strip()
                district = match.group(2).strip()
                municipality = match.group(3).strip()

                municipalities.append(
                    {
                        "id": value,
                        "province": province,
                        "district": district,
                        "municipality": municipality,
                        "full_name": text,
                    }
                )

        return municipalities

    @staticmethod
    async def get_streets(hass: HomeAssistant, municipality_id: str):
        """Get list of available streets for a municipality."""
        session = async_get_clientsession(hass)
        url = STREETS_URL.format(municipality_id=municipality_id)

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
        except (aiohttp.ClientError) as error:
            _LOGGER.error("Error fetching streets: %s", error)
            return {"streets": [], "municipality_name": "Unknown"}

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")

        # Get municipality name
        try:
            header_text = soup.find("h4").text
            municipality_name = re.search(
                r"dla gminy: ([\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s\-]+)", header_text
            ).group(1).strip()
        except (AttributeError, IndexError):
            municipality_name = "Unknown municipality"
            _LOGGER.warning("Could not find municipality name")

        # Find the streets select element
        select_element = soup.find("select", id="selUlica")

        if not select_element:
            _LOGGER.error("Could not find select element with id='selUlica'")
            return {"streets": [], "municipality_name": municipality_name}

        options = select_element.find_all("option")
        streets = []

        # Parse each option
        for option in options:
            # Skip the hidden default option
            if (
                option.has_attr("hidden")
                or option.has_attr("disabled")
                or option.has_attr("selected")
            ):
                continue

            street_name = option.text.strip()
            streets.append(street_name)

        return {
            "streets": streets,
            "municipality_name": municipality_name,
        }

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            return await self._fetch_schedule()
        except Exception as err:
            _LOGGER.error("Error fetching schedule: %s", err)
            raise

    async def _fetch_schedule(self):
        """Fetch waste collection schedule."""
        encoded_street = quote(self.street)
        url = SCHEDULE_URL.format(
            municipality_id=self.municipality_id, street=encoded_street
        )

        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
        except (aiohttp.ClientError) as error:
            _LOGGER.error("Error fetching schedule: %s", error)
            return {"schedule": [], "waste_types": {}}

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")

        # List for schedule data
        dates = []

        # Finding all cards with dates
        date_cards = soup.find_all("div", class_="termin card")

        # Color to waste type mapping (for verification)
        color_mapping = {
            "#9F703B": {"name": "biodegradowalne", "id": "B"},
            "#596D81": {"name": "zmieszane", "id": "ZM"},
            "#F9C625": {"name": "metale i tworzywa sztuczne", "id": "PL"},
            "#11ADE4": {"name": "papier i tektura", "id": "PA"},
            "#7EC451": {"name": "szkło", "id": "SZ"},
            "#626262": {"name": "popiół", "id": "PO"},
        }

        # Waste type to ID mapping
        waste_type_to_id = {
            "biodegradowalne": "B",
            "zmieszane": "ZM",
            "metale i tworzywa sztuczne": "PL",
            "papier i tektura": "PA",
            "szkło": "SZ",
            "popiół": "PO",
        }

        # Parse each date card
        for card in date_cards:
            try:
                # Get side color
                side = card.find("div", class_="bok")
                color = side.get("style").split("background-color:")[1].strip(";").strip()

                # Get date
                date_text = card.find("div", class_="naglowek").text.strip()
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
                date_str = date_match.group(1) if date_match else None

                # Get weekday
                weekday_match = re.search(r"\((.*?)\)", date_text)
                weekday = weekday_match.group(1) if weekday_match else None

                # Get waste type
                waste_type = card.find("div", class_="srodek").find("h3").text.strip()

                # Verify color and waste type consistency
                expected_type = color_mapping.get(color, {}).get("name")
                if expected_type and expected_type != waste_type:
                    _LOGGER.warning(
                        "Color %s usually means %s, but found %s",
                        color,
                        expected_type,
                        waste_type,
                    )

                # Assign waste type ID
                waste_id = waste_type_to_id.get(waste_type, "")

                # Add date to list
                if date_str:
                    date_entry = {
                        "date": date_str,
                        "date_obj": datetime.strptime(date_str, "%Y-%m-%d").date(),
                        "weekday": weekday,
                        "waste_type": waste_type,
                        "waste_id": waste_id,
                        "color": color,
                    }
                    dates.append(date_entry)

            except Exception as e:
                _LOGGER.error("Error processing date card: %s", e)

        # Sort dates by date
        dates.sort(key=lambda x: x["date"] if x["date"] else "")

        # Group dates by waste type
        types_schedules = {}
        today = date.today()

        for waste_id, waste_info in WASTE_TYPES.items():
            waste_dates = [d for d in dates if d["waste_id"] == waste_id]

            # Find next collection date
            future_dates = [d for d in waste_dates if d["date_obj"] >= today]
            next_collection = future_dates[0] if future_dates else None

            if next_collection:
                days_until = (next_collection["date_obj"] - today).days
            else:
                days_until = None

            types_schedules[waste_id] = {
                "name": waste_info["name"],
                "name_pl": waste_info["name_pl"],
                "dates": [{"date": d["date"], "date_obj": d["date_obj"], "weekday": d["weekday"]} for d in waste_dates],
                "icon": waste_info["icon"],
                "color": waste_info["color"],
                "next_collection": next_collection["date"] if next_collection else None,
                "next_collection_date_obj": next_collection["date_obj"] if next_collection else None,
                "next_collection_weekday": next_collection["weekday"] if next_collection else None,
                "days_until": days_until,
            }

        # Create a list of next collections for all waste types
        next_collections = []
        for waste_id, waste_data in types_schedules.items():
            if waste_data["next_collection"]:
                next_collections.append({
                    "date": waste_data["next_collection"],
                    "date_obj": datetime.strptime(waste_data["next_collection"], "%Y-%m-%d").date(),
                    "weekday": waste_data["next_collection_weekday"],
                    "waste_type": waste_data["name_pl"],
                    "waste_id": waste_id,
                    "days_until": waste_data["days_until"],
                    "icon": waste_data["icon"],
                    "color": waste_data["color"],
                })

        # Sort by date
        next_collections.sort(key=lambda x: x["date_obj"])

        # Find very next collection regardless of type
        next_collection = next_collections[0] if next_collections else None

        # Return processed data
        data = {
            "municipality_id": self.municipality_id,
            "street": self.street,
            "retrieval_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "schedule": dates,
            "waste_types": types_schedules,
            "next_collections": next_collections,
            "next_collection": next_collection,
            "total_dates": len(dates),
        }

        return data