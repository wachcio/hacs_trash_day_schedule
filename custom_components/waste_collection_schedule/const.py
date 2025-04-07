"""Constants for the TrashDay integration."""
from datetime import timedelta

DOMAIN = "trash_day"

# Configuration options
CONF_MUNICIPALITY_ID = "municipality_id"
CONF_MUNICIPALITY_NAME = "municipality_name"
CONF_STREET = "street"
CONF_SCAN_INTERVAL = "scan_interval"

# Default values
DEFAULT_SCAN_INTERVAL = timedelta(hours=12)
DEFAULT_NAME = "Waste Collection"

# API URLs
BASE_URL = "https://cloud.fxsystems.com.pl/OdbiorySmieci/HarmonogramOnline.dll"
MUNICIPALITY_URL = BASE_URL
STREETS_URL = BASE_URL + "?gmina_id={municipality_id}"
SCHEDULE_URL = BASE_URL + "?gmina_id={municipality_id}&ulica={street}"

# Attributes
ATTR_NEXT_COLLECTION = "next_collection"
ATTR_WASTE_TYPE = "waste_type"
ATTR_WASTE_ID = "waste_id"
ATTR_DAYS_UNTIL = "days_until"
ATTR_COLLECTIONS = "collections"
ATTR_ALL_COLLECTIONS = "all_collections"
ATTR_SCHEDULE = "schedule"

# Waste types
WASTE_TYPES = {
    "B": {"name": "Biodegradable", "name_pl": "Biodegradowalne", "icon": "mdi:recycle", "color": "#9F703B"},
    "ZM": {"name": "Mixed", "name_pl": "Zmieszane", "icon": "mdi:trash-can", "color": "#596D81"},
    "PL": {"name": "Plastic and Metal", "name_pl": "Metale i tworzywa sztuczne", "icon": "mdi:bottle-soda-outline", "color": "#F9C625"},
    "PA": {"name": "Paper", "name_pl": "Papier i tektura", "icon": "mdi:file-outline", "color": "#11ADE4"},
    "SZ": {"name": "Glass", "name_pl": "Szkło", "icon": "mdi:bottle-wine", "color": "#7EC451"},
    "PO": {"name": "Ash", "name_pl": "Popiół", "icon": "mdi:fire", "color": "#626262"}
}

# Translation keys
SELECTOR_MUNICIPALITY = "selector_municipality"
SELECTOR_STREET = "selector_street"
OPTION_SCAN_INTERVAL = "option_scan_interval"