"""
NPTOR Delivery Geolocation & Reverse-Geocoding Service.

Converts GPS coordinates obtained via browser Geolocation API into structured
Nepal delivery addresses while enforcing delivery boundaries, privacy protections,
and robust fallbacks.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger(__name__)

# Approximate geographic bounding box for Nepal
NEPAL_LAT_MIN = 26.0
NEPAL_LAT_MAX = 31.0
NEPAL_LON_MIN = 80.0
NEPAL_LON_MAX = 89.0

NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
DEFAULT_USER_AGENT = "NPTOR-Store-Delivery/1.0 (https://nptor.com; contact@nptor.com)"


class GeolocationService:
    @classmethod
    def is_within_nepal_bounds(cls, lat: float, lon: float) -> bool:
        """Checks whether coordinates fall within Nepal's general geographical bounding box."""
        return (
            NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX
            and NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX
        )

    @classmethod
    def reverse_geocode(cls, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Reverse geocodes coordinates to a structured delivery address.
        Enforces rate-limiting etiquettes, timeout, and Nepal delivery serviceability.
        """
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": "Invalid coordinates provided.",
                "is_serviceable": False,
            }

        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return {
                "success": False,
                "error": "Coordinates are outside valid geographical range.",
                "is_serviceable": False,
            }

        # Bounding box check for Nepal physical delivery
        in_nepal_bbox = cls.is_within_nepal_bounds(lat, lon)

        try:
            response = requests.get(
                NOMINATIM_REVERSE_URL,
                params={
                    "format": "jsonv2",
                    "lat": lat,
                    "lon": lon,
                    "addressdetails": 1,
                    "accept-language": "en,np",
                },
                headers={"User-Agent": DEFAULT_USER_AGENT},
                timeout=4.0,
            )
            if not response.ok:
                logger.warning("Nominatim reverse-geocode returned status %s", response.status_code)
                return {
                    "success": False,
                    "error": "Address lookup service is temporarily busy. Please enter your address manually.",
                    "is_serviceable": in_nepal_bbox,
                }
            data = response.json()
        except requests.RequestException as exc:
            logger.warning("Reverse geocoding network error: %s", exc)
            return {
                "success": False,
                "error": "Could not connect to address lookup service. Please enter your address manually.",
                "is_serviceable": in_nepal_bbox,
            }

        raw_addr = data.get("address", {})
        country_code = (raw_addr.get("country_code") or "").lower()

        # Check delivery serviceability (Nepal only)
        if country_code != "np" and not in_nepal_bbox:
            country_name = raw_addr.get("country") or "your current region"
            return {
                "success": False,
                "is_serviceable": False,
                "error": (
                    f"Your current location is detected in {country_name}. "
                    "Physical store deliveries are currently supported only within Nepal. "
                    "Please enter a delivery address in Nepal manually."
                ),
                "country_code": country_code,
            }

        # Normalize street address parts
        street_parts = []
        for key in ["road", "neighbourhood", "suburb", "hamlet"]:
            val = raw_addr.get(key)
            if val and val not in street_parts:
                street_parts.append(val)
        street_address_1 = ", ".join(street_parts) if street_parts else ""

        # Normalize city / municipality
        city = (
            raw_addr.get("city")
            or raw_addr.get("town")
            or raw_addr.get("municipality")
            or raw_addr.get("village")
            or ""
        )
        # Clean common Nepal municipality suffixes for cleaner form field
        city_clean = re.sub(
            r"\s+(Metropolitan City|Sub-Metropolitan City|Municipality|Rural Municipality)$",
            "",
            city,
            flags=re.IGNORECASE,
        ).strip()

        # District in Nepal corresponds to 'county' in OpenStreetMap
        district = (
            raw_addr.get("county")
            or raw_addr.get("district")
            or city_clean
            or ""
        )
        district_clean = re.sub(r"\s+District$", "", district, flags=re.IGNORECASE).strip()

        # Province in Nepal corresponds to 'state'
        province = raw_addr.get("state") or ""
        province_clean = re.sub(r"\s+Province$", "", province, flags=re.IGNORECASE).strip()

        postal_code = raw_addr.get("postcode") or ""
        display_name = data.get("display_name") or ""

        return {
            "success": True,
            "is_serviceable": True,
            "address": {
                "street_address_1": street_address_1,
                "street_address_2": "",
                "city": city_clean or city,
                "district": district_clean or district,
                "province": province_clean or province,
                "postal_code": postal_code,
                "country": "NP",
            },
            "display_name": display_name,
            "country_code": "np",
        }
