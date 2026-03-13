"""
location_helper.py — Dynamic location parsing using Nominatim geocoding API
"""

import requests
from functools import lru_cache
import logging
import time

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1000)
def _geocode(location: str) -> tuple[str, str]:
    """
    Use Nominatim (OpenStreetMap) to resolve any Indian location to (city, state).
    Results are cached to avoid repeated API calls.
    """
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{location}, India", "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": "Swavalambi-AI/1.0"},
            timeout=3
        )

        if response.status_code == 200 and response.json():
            address = response.json()[0].get("address", {})
            city = address.get("city", address.get("town", address.get("village", ""))).lower()
            state = address.get("state", "").lower()
            logger.info(f"Geocoded '{location}' -> city='{city}', state='{state}'")
            return (city, state)

        time.sleep(1)  # Rate limiting for Nominatim

    except Exception as e:
        logger.debug(f"Geocoding failed for '{location}': {e}")

    return ("", "")


def parse_location(location_str: str) -> tuple[str, str]:
    """
    Parse any location string into (city, state) using Nominatim geocoding.

    Examples:
        "Bangalore, Karnataka" -> ("bangalore", "karnataka")
        "Karnataka" -> ("", "karnataka")
        "Ludhiana" -> ("ludhiana", "punjab")
        "All India" -> ("", "")
    """
    if not location_str:
        return ("", "")

    location_str = location_str.strip().lower()

    if "all india" in location_str or location_str == "all":
        return ("", "")

    # Comma-separated — trust the user input
    if "," in location_str:
        parts = [p.strip() for p in location_str.split(",")]
        return (parts[0], parts[1] if len(parts) > 1 else "")

    # Single value — let Nominatim figure out if it's a city or state
    return _geocode(location_str)
