"""Data coordinator for TrashDay integration."""
import logging
import asyncio
from datetime import datetime, date
import aiohttp
from urllib.parse import quote
from bs4 import BeautifulSoup
import json
import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    MUNICIPALITY_URL,
    STREETS_URL,
    SCHEDULE_URL,
    WASTE_TYPES,
)

_LOGGER = logging.getLogger(__name__)

MUNICIPALITY_RE = re.compile(
    r"woj\.:\s*(.+?)\s+powiat:\s*(.+?)\s+gmina:\s*(.+)$", re.IGNORECASE
)

# Kolor frakcji -> ID (używany, gdy nazwa frakcji nie zostanie rozpoznana)
COLOR_TO_ID = {
    "#9F703B": "B",
    "#596D81": "ZM",
    "#F9C625": "PL",
    "#11ADE4": "PA",
    "#7EC451": "SZ",
    "#626262": "PO",
}


def waste_id_from_name(name: str, color: str = "") -> str:
    """Map waste fraction name (which differs between municipalities) to ID."""
    n = (name or "").lower()
    if "zmiesz" in n:
        return "ZM"
    if "bio" in n:
        return "B"
    if "metal" in n or "tworzyw" in n or "plastik" in n:
        return "PL"
    if "papier" in n or "tektur" in n:
        return "PA"
    if "szkło" in n or "szklo" in n:
        return "SZ"
    if "popiół" in n or "popiol" in n:
        return "PO"
    return COLOR_TO_ID.get((color or "").strip().upper(), "")


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

        raw = []

        # Nowa wersja strony: lista gmin jako JSON w skrypcie (const bazyGmin = [...])
        js_match = re.search(r"bazyGmin\s*=\s*(\[.*?\])\s*;", html, re.S)
        if js_match:
            try:
                raw = [
                    (str(item.get("id", "")), str(item.get("name", "")).strip())
                    for item in json.loads(js_match.group(1))
                ]
            except (ValueError, AttributeError) as err:
                _LOGGER.error("Could not parse municipality list: %s", err)

        # Stara wersja strony: <select id="selGmina">
        if not raw:
            soup = BeautifulSoup(html, "html.parser")
            select_element = soup.find("select", id="selGmina")
            if select_element:
                raw = [
                    (option.get("value"), option.text.strip())
                    for option in select_element.find_all("option")
                ]

        if not raw:
            _LOGGER.error("Could not find municipality list on %s", MUNICIPALITY_URL)
            return []

        municipalities = []
        for value, text in raw:
            if not value:
                continue
            match = MUNICIPALITY_RE.search(text)
            if match:
                province, district, municipality = (g.strip() for g in match.groups())
            else:
                province, district, municipality = "", "", text
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
        municipality_name = "Unknown municipality"
        subtitle = soup.find("div", class_="header-subtitle")
        header = soup.find("h4")
        if subtitle and "gmina" in subtitle.text.lower():
            municipality_name = re.sub(r"^\s*gmina:\s*", "", subtitle.text, flags=re.I).strip()
        elif header:
            match = re.search(r"dla gminy:\s*(.+)", header.text)
            if match:
                municipality_name = match.group(1).strip()

        # Find the streets select element (selUlica / selUlica_ukryty)
        select_element = soup.find("select", id=re.compile(r"^selUlica"))

        if not select_element:
            _LOGGER.error("Could not find streets select element")
            return {"streets": [], "municipality_name": municipality_name}

        streets = []
        for option in select_element.find_all("option"):
            # Skip the hidden/default option
            if (
                option.has_attr("hidden")
                or option.has_attr("disabled")
                or option.get("value") == ""
            ):
                continue
            street_name = option.text.strip()
            if street_name and street_name not in streets:
                streets.append(street_name)

        return {
            "streets": streets,
            "municipality_name": municipality_name,
        }

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            return await self._fetch_schedule()
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error fetching schedule: {err}") from err

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
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            raise UpdateFailed(f"Error fetching schedule: {error}") from error

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")

        dates = []

        # Każdy wpis: (tekst daty, nazwa frakcji, kolor)
        entries = []

        # Nowa wersja strony: <div class="schedule-card">
        for card in soup.find_all("div", class_="schedule-card"):
            date_el = card.find("div", class_="info-full-date")
            name_el = card.find("div", class_="info-fraction-name")
            if not date_el or not name_el:
                continue
            color_match = re.search(r"border-left-color:\s*(#[0-9A-Fa-f]{3,8})", card.get("style", ""))
            entries.append(
                (
                    date_el.text.strip(),
                    name_el.text.strip(),
                    color_match.group(1) if color_match else "",
                )
            )

        # Stara wersja strony: <div class="termin card">
        if not entries:
            for card in soup.find_all("div", class_="termin card"):
                side = card.find("div", class_="bok")
                date_header = card.find("div", class_="naglowek")
                content = card.find("div", class_="srodek")
                title = content.find("h3") if content else None
                if not date_header or not title:
                    continue
                color_match = re.search(r"background-color:(.*?);", side.get("style", "") if side else "")
                entries.append(
                    (
                        date_header.text.strip(),
                        title.text.strip(),
                        color_match.group(1).strip() if color_match else "",
                    )
                )

        if not entries:
            _LOGGER.warning(
                "No schedule entries found for municipality %s, street %s",
                self.municipality_id,
                self.street,
            )

        for date_text, waste_type, color in entries:
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
            if not date_match:
                continue
            date_str = date_match.group(1)
            weekday_match = re.search(r"\((.*?)\)", date_text)
            weekday = weekday_match.group(1) if weekday_match else None

            waste_id = waste_id_from_name(waste_type, color)
            if not waste_id:
                _LOGGER.debug("Unknown waste type skipped: %s", waste_type)
                continue

            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as date_error:
                _LOGGER.error("Invalid date format: %s - %s", date_str, date_error)
                continue

            dates.append(
                {
                    "date": date_str,
                    "date_obj": date_obj,
                    "weekday": weekday,
                    "waste_type": waste_type,
                    "waste_id": waste_id,
                    "color": color,
                }
            )

        # Sort dates by date
        dates.sort(key=lambda x: x["date"] if x["date"] else "")

        # Group dates by waste type
        types_schedules = {}
        today = date.today()

        for waste_id, waste_info in WASTE_TYPES.items():
            # Kilka frakcji może mapować się na ten sam typ (np. szkło kolorowe
            # i bezbarwne) - usuń zduplikowane daty
            seen = set()
            waste_dates = []
            for d in dates:
                if d["waste_id"] == waste_id and d["date"] not in seen:
                    seen.add(d["date"])
                    waste_dates.append(d)

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