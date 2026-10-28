import json
import re
from pathlib import Path
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

from diagnose import diagnose

mcp = FastMCP("CropGuardTools")
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "Data"
LEGACY_TREATMENTS_STEM = "treatments"
# Map common colloquial crop names and plurals to canonical dataset keys.
SYNONYMS = {
    "peanut": "groundnut",
    "peanuts": "groundnut",
    "groundnuts": "groundnut",
    "grapes": "grape",
    "grapevine": "grape",
    "tomatoes": "tomato",
    "potatoes": "potato",
    "onions": "onion",
    "pomegranates": "pomegranate",
}


def normalise(key: str) -> str:
    """Strip parenthetical scientific names and normalize leading crop names."""
    key = re.sub(r"\(.*?\)", "", key).strip()
    words = key.split()
    if words and words[0] in SYNONYMS:
        words[0] = SYNONYMS[words[0]]
    return " ".join(words)


@mcp.tool()
def diagnose_image(image_path: str, description: str = "") -> dict[str, Any]:
    """Diagnose a crop disease from a photo path and farmer description."""
    try:
        path = Path(image_path)
        if not path.is_absolute():
            path = BASE / path
        result = json.loads(diagnose(str(path.resolve()), description))
        if isinstance(result, list):
            result = result[0] if result and isinstance(result[0], dict) else {}
        if not isinstance(result, dict):
            return {"error": "diagnosis failed: the model did not return a JSON object"}
        return result
    except Exception as error:
        return {"error": f"diagnosis failed: {error}"}


# Tool 2: Weather observations and rule-of-thumb fungal risk from Open-Meteo
@mcp.tool()
def get_weather(latitude: float, longitude: float) -> dict[str, Any]:
    """Current humidity and rain over the previous 3 days, with fungal risk."""
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "timezone": "auto",
                "past_days": 3,
                "current": "temperature_2m,relative_humidity_2m,precipitation",
                "daily": "precipitation_sum",
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        current = data.get("current") or {}
        humidity = current.get("relative_humidity_2m")
        if humidity is None:
            return {"error": "weather failed: current humidity was not returned"}
        daily_rain = (data.get("daily") or {}).get("precipitation_sum") or []
        rain_last_3_days_mm = round(
            sum(value for value in daily_rain[:3] if value is not None),
            1,
        )

        # These thresholds are rough rules of thumb, not an agronomic forecast.
        if (humidity >= 80 and rain_last_3_days_mm >= 5) or (
            humidity >= 90 and rain_last_3_days_mm >= 2
        ):
            fungal_risk = "HIGH"
        elif humidity >= 65 or rain_last_3_days_mm >= 2:
            fungal_risk = "MODERATE"
        else:
            fungal_risk = "LOW"

        return {
            "temperature_2m": current.get("temperature_2m"),
            "relative_humidity_2m": humidity,
            "precipitation": current.get("precipitation"),
            "rain_last_3_days_mm": rain_last_3_days_mm,
            "fungal_risk": fungal_risk,
        }
    except Exception as error:
        return {"error": f"weather failed: {error}"}


# Tool 3: Forward geocoding to resolve coordinates from village or city names
@mcp.tool()
def city_to_coords(city: str) -> dict[str, Any]:
    """Find latitude and longitude for a farmer-named place using Open-Meteo."""
    try:
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=20,
        )
        response.raise_for_status()
        results = response.json().get("results") or []
        if not results:
            return {"error": "city not found"}
        result = results[0]
        return {
            "name": result["name"],
            "country": result.get("country"),
            "latitude": result["latitude"],
            "longitude": result["longitude"],
        }
    except Exception as error:
        return {"error": f"geocoding failed: {error}"}


def load_db() -> dict[str, dict[str, Any]]:
    """Merge every Data/*.json file (one file per crop) into one dictionary."""
    db: dict[str, dict[str, Any]] = {}
    for file_path in sorted(DATA_DIR.glob("*.json"), key=lambda item: item.name.casefold()):
        # Skip legacy monolithic treatment file stem if present
        if file_path.stem.casefold() == LEGACY_TREATMENTS_STEM:
            continue
        try:
            with file_path.open(encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, RecursionError):
            continue
        if not isinstance(data, dict):
            continue
        for key, entry in data.items():
            if isinstance(key, str) and isinstance(entry, dict):
                db[key.casefold().strip()] = entry
    return db


def _normal_name(value: Any) -> str:
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def _entry_names(key: str, entry: dict[str, Any]) -> list[str]:
    names = [key]
    aliases = entry.get("aliases", [])
    if isinstance(aliases, str):
        aliases = [aliases]
    if isinstance(aliases, list):
        names.extend(_normal_name(alias) for alias in aliases if isinstance(alias, str))
    return names


# Tool 4: Treatment lookup with 3-tier matching (exact, same-crop, cross-crop fallback)
@mcp.tool()
def lookup_treatment(disease: str) -> dict[str, Any]:
    """Look up crop-file guidance by disease key or alias, with a KVK note for other crops."""
    db = load_db()
    key = normalise(disease.lower().strip())
    if not key:
        return {"error": "No verified entry. Contact your KVK."}

    # Tier 1: Exact disease key or alias match
    entries = list(db.items())
    for stored_key, entry in entries:
        if key in _entry_names(stored_key, entry):
            result = dict(entry)
            result["disease_key"] = stored_key
            return result

    # Tier 2: Same-crop partial substring match
    query_words = key.split()
    crop = query_words[0]
    query_disease = " ".join(query_words[1:])
    for stored_key, entry in entries:
        names = _entry_names(stored_key, entry)
        if stored_key.split(maxsplit=1)[0] != crop:
            continue
        comparable_names = [stored_key, *names[1:]]
        if query_disease:
            comparable_names.extend(
                name[len(crop):].strip()
                for name in names[1:]
                if name.startswith(f"{crop} ")
            )
        if any(
            key in name or (query_disease and query_disease in name)
            for name in comparable_names
            if name
        ):
            result = dict(entry)
            result["disease_key"] = stored_key
            return result

    # Tier 3: Cross-crop fallback (clearly annotated with a warning note)
    if query_disease:
        for stored_key, entry in entries:
            other_crop, _, disease_name = stored_key.partition(" ")
            if other_crop == crop:
                continue
            candidate_names = [disease_name]
            for alias in _entry_names(stored_key, entry)[1:]:
                alias_crop, separator, alias_disease = alias.partition(" ")
                candidate_names.append(alias_disease if separator and alias_crop == other_crop else alias)
            if any(
                query_disease == name or query_disease in name or name in query_disease
                for name in candidate_names
                if len(name) > 4
            ):
                result = dict(entry)
                result["disease_key"] = stored_key
                result["note"] = (
                    f"No entry for '{key}'. The advice shown is for another crop "
                    f"('{other_crop}'); ask your KVK before using it."
                )
                return result
    return {"error": "No verified entry. Contact your KVK."}


if __name__ == "__main__":
    mcp.run()
