"""
CropGuard MCP Server

Exposes four tools over MCP for the CropGuard agent:
  - get_weather(location, days)
  - get_crop_info(crop)
  - search_pest_disease(crop, symptoms)
  - get_ipm_guidance(crop, issue_id)

Every tool returns a JSON-serializable dict with a "status" field
(one of "ok", "not_found", "error") so the agent and its tests can
handle failures without exceptions leaking through.
"""

import json
import re
from pathlib import Path
from typing import Any

import requests
from mcp.server.mcpserver import MCPServer

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

mcp = MCPServer("cropguard")


# ---------------------------------------------------------------------------
# Knowledge base helpers
# ---------------------------------------------------------------------------

def _load_crop(crop: str) -> dict[str, Any] | None:
    """Load a crop's knowledge base JSON file, case-insensitively."""
    crop_key = crop.strip().lower()
    path = KNOWLEDGE_DIR / f"{crop_key}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _available_crops() -> list[str]:
    if not KNOWLEDGE_DIR.exists():
        return []
    return sorted(p.stem for p in KNOWLEDGE_DIR.glob("*.json"))


def _all_issues(crop_data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(crop_data.get("pests", [])) + list(crop_data.get("diseases", []))


def _score_symptom_match(issue: dict[str, Any], query_symptoms: list[str]) -> tuple[int, int]:
    """Return (matched_count, total_query_symptoms) using loose substring matching."""
    issue_symptom_text = " | ".join(issue.get("symptoms", [])).lower()
    matched = 0
    for qs in query_symptoms:
        qs_clean = qs.strip().lower()
        if not qs_clean:
            continue
        # Loose match: query phrase words mostly present in the issue's symptom text
        words = [w for w in re.split(r"\W+", qs_clean) if len(w) > 2]
        if not words:
            continue
        hits = sum(1 for w in words if w in issue_symptom_text)
        if hits >= max(1, len(words) // 2):
            matched += 1
    return matched, len([s for s in query_symptoms if s.strip()])


# ---------------------------------------------------------------------------
# Tool 1: get_weather
# ---------------------------------------------------------------------------

@mcp.tool()
def get_weather(location: str, days: int = 3) -> dict[str, Any]:
    """
    Get current and short-term forecast weather for a farmer's location.

    Args:
        location: Free-text place name, e.g. "Ahmedabad, India" or "Nashik".
        days: Number of forecast days to return (1-7). Defaults to 3.

    Returns:
        dict with status "ok" | "not_found" | "error", and on success:
        location_resolved, latitude, longitude, current, daily (list of
        per-day summaries with temp range, humidity, and precipitation).
    """
    days = max(1, min(int(days) if days else 3, 7))

    if not location or not location.strip():
        return {"status": "error", "message": "location must be a non-empty string"}

    loc_clean = location.strip()
    loc_lower = loc_clean.lower()

    try:
        geo_resp = requests.get(
            GEOCODE_URL,
            params={"name": loc_clean, "count": 20, "language": "en", "format": "json"},
            timeout=10,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
    except requests.RequestException as e:
        return {"status": "error", "message": f"geocoding request failed: {e}"}
    except ValueError as e:
        return {"status": "error", "message": f"geocoding response was not valid JSON: {e}"}

    results = geo_data.get("results") or []

    has_explicit_country = any(c in loc_lower for c in ["india", "pakistan", "usa", "united states", "canada", "uk", "australia"])

    if not has_explicit_country:
        try:
            geo_in_resp = requests.get(
                GEOCODE_URL,
                params={"name": f"{loc_clean}, India", "count": 20, "language": "en", "format": "json"},
                timeout=10,
            )
            geo_in_resp.raise_for_status()
            in_results = geo_in_resp.json().get("results") or []
            results = in_results + results
        except (requests.RequestException, AttributeError, ValueError):
            pass

    if not results:
        return {"status": "not_found", "message": f"could not resolve location '{location}'"}

    def _score_place(p: dict) -> int:
        p_name = (p.get("name") or "").lower()
        p_admin1 = (p.get("admin1") or "").lower()
        p_country = (p.get("country") or "").lower()
        
        is_name_exact = (p_name == loc_lower)
        is_admin_exact = (p_admin1 == loc_lower)
        is_india = (p_country == "india")

        if is_name_exact and (is_india or has_explicit_country):
            return 100
        if is_admin_exact and is_india:
            return 90
        if is_name_exact:
            return 80
        if is_admin_exact:
            return 70
        if is_india:
            return 50
        return 10

    results.sort(key=_score_place, reverse=True)
    place = results[0]
    lat, lon = place.get("latitude"), place.get("longitude")
    resolved_name = ", ".join(
        part for part in [place.get("name"), place.get("admin1"), place.get("country")] if part
    )

    countries = sorted({p.get("country") for p in results if p.get("country")})
    ambiguity_warning = None
    if not has_explicit_country and len(countries) > 1:
        c_str = ", ".join(countries)
        ambiguity_warning = (
            f"Ambiguous query '{loc_clean}' matched locations across multiple countries ({c_str}). "
            f"Resolved to '{resolved_name}'. If you meant a different country, please specify it explicitly (e.g. '{loc_clean}, Pakistan')."
        )

    try:
        weather_resp = requests.get(
            WEATHER_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,precipitation",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "forecast_days": days,
                "timezone": "auto",
            },
            timeout=10,
        )
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()
    except requests.RequestException as e:
        return {"status": "error", "message": f"weather request failed: {e}"}
    except ValueError as e:
        return {"status": "error", "message": f"weather response was not valid JSON: {e}"}

    daily = weather_data.get("daily", {})
    daily_list = []
    times = daily.get("time", [])
    for i, date in enumerate(times):
        daily_list.append({
            "date": date,
            "temp_max_c": daily.get("temperature_2m_max", [None] * len(times))[i],
            "temp_min_c": daily.get("temperature_2m_min", [None] * len(times))[i],
            "precipitation_mm": daily.get("precipitation_sum", [None] * len(times))[i],
        })

    current = weather_data.get("current", {})

    response_dict = {
        "status": "ok",
        "location_query": location,
        "location_resolved": resolved_name or location,
        "latitude": lat,
        "longitude": lon,
        "units": {
            "temperature": "°C",
            "humidity": "%",
            "precipitation": "mm",
        },
        "current": {
            "timestamp": current.get("time"),
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
        },
        "daily": daily_list,
    }
    if ambiguity_warning:
        response_dict["ambiguity_warning"] = ambiguity_warning

    return response_dict

# ---------------------------------------------------------------------------
# Tool 2: get_crop_info
# ---------------------------------------------------------------------------

@mcp.tool()
def get_crop_info(crop: str) -> dict[str, Any]:
    """
    Get general knowledge base info for a crop: scientific name and the
    list of known pests/diseases tracked for it (names and ids only,
    not full details).

    Args:
        crop: Crop name, e.g. "tomato", "cotton", "wheat".

    Returns:
        dict with status "ok" | "not_found", and on success: crop,
        scientific_name, known_pests (list of {id, name}), known_diseases
        (list of {id, name}).
    """
    if not crop or not crop.strip():
        return {"status": "error", "message": "crop must be a non-empty string", "available_crops": _available_crops()}

    data = _load_crop(crop)
    if data is None:
        return {
            "status": "not_found",
            "message": f"no knowledge base entry for crop '{crop}'",
            "available_crops": _available_crops(),
        }

    return {
        "status": "ok",
        "crop": data.get("crop"),
        "scientific_name": data.get("scientific_name"),
        "known_pests": [{"id": p["id"], "name": p["name"]} for p in data.get("pests", [])],
        "known_diseases": [{"id": d["id"], "name": d["name"]} for d in data.get("diseases", [])],
    }


    # ---------------------------------------------------------------------------
# Tool 3: search_pest_disease
# ---------------------------------------------------------------------------

@mcp.tool()
def search_pest_disease(crop: str, symptoms: str) -> dict[str, Any]:
    """
    Search the knowledge base for pests/diseases matching observed symptoms
    on a given crop. Uses loose keyword matching against known symptom
    descriptions and returns ranked candidates with a match_type indicating
    confidence. This tool identifies POSSIBLE matches, not diagnoses.

    Args:
        crop: Crop name, e.g. "tomato".
         symptoms: List of the farmer's own described symptoms, extracted from
            what they actually said. Do not invent or assume specific symptom
            details the farmer did not mention.

    Returns:
        dict with status "ok" | "not_found" | "error", and on success a
        ranked "matches" list, each with id, name, type, match_type
        ("strong" | "partial" | "weak"), matched_symptom_count,
        confusable_with, and favorable_conditions (for cross-checking
        against weather).
    """
        # Models inconsistently send this as a real list, a JSON-encoded string,
    # or a comma-separated string. Normalize all three to a list here.
    if isinstance(symptoms, list):
        symptom_list = symptoms
    elif isinstance(symptoms, str):
        try:
            parsed = json.loads(symptoms)
            symptom_list = parsed if isinstance(parsed, list) else [symptoms]
        except (json.JSONDecodeError, TypeError):
            symptom_list = [s.strip() for s in symptoms.split(",")] if "," in symptoms else [symptoms]
    else:
        symptom_list = []

    if not crop or not crop.strip():
        return {"status": "error", "message": "crop must be a non-empty string"}

    if not symptom_list or not any(s.strip() for s in symptom_list if isinstance(s, str)):
        return {"status": "error", "message": "symptoms must be a non-empty list of strings"}

    data = _load_crop(crop)
    if data is None:
        return {
            "status": "not_found",
            "message": f"no knowledge base entry for crop '{crop}'",
            "available_crops": _available_crops(),
        }

    clean_symptoms = [s for s in symptom_list if isinstance(s, str) and s.strip()]
    issues = _all_issues(data)
    scored = []
    for issue in issues:
        matched, total = _score_symptom_match(issue, clean_symptoms)
        if matched == 0:
            continue
        ratio = matched / total if total else 0
        if ratio >= 0.66:
            match_type = "strong"
        elif ratio >= 0.33:
            match_type = "partial"
        else:
            match_type = "weak"
        scored.append({
            "id": issue["id"],
            "name": issue["name"],
            "type": issue["type"],
            "match_type": match_type,
            "matched_symptom_count": matched,
            "query_symptom_count": total,
            "confusable_with": issue.get("confusable_with", []),
            "favorable_conditions": issue.get("favorable_conditions", {}),
        })

    scored.sort(key=lambda x: (x["matched_symptom_count"], x["match_type"] == "strong"), reverse=True)

    if not scored:
        return {
            "status": "ok",
            "crop": crop,
            "matches": [],
            "message": "no symptom matches found in knowledge base; consider broader or different symptom terms",
        }

    return {"status": "ok", "crop": crop, "matches": scored[:5]}



    # ---------------------------------------------------------------------------
# Tool 4: get_ipm_guidance
# ---------------------------------------------------------------------------

@mcp.tool()
def get_ipm_guidance(crop: str, issue_id: str) -> dict[str, Any]:
    """
    Get detailed Integrated Pest Management (IPM) guidance for a specific
    pest or disease, identified by the id returned from search_pest_disease
    or get_crop_info.

    Args:
        crop: Crop name, e.g. "tomato".
        issue_id: The pest/disease id, e.g. "tomato_early_blight".

    Returns:
        dict with status "ok" | "not_found" | "error", and on success:
        id, name, type, symptoms, favorable_conditions, confusable_with,
        ipm_steps, sources.
    """
    if not crop or not crop.strip() or not issue_id or not issue_id.strip():
        return {"status": "error", "message": "crop and issue_id must both be non-empty strings"}

    data = _load_crop(crop)
    if data is None:
        return {
            "status": "not_found",
            "message": f"no knowledge base entry for crop '{crop}'",
            "available_crops": _available_crops(),
        }

    for issue in _all_issues(data):
        if issue["id"] == issue_id.strip():
            return {"status": "ok", **issue}

    return {
        "status": "not_found",
        "message": f"no issue with id '{issue_id}' found for crop '{crop}'",
        "available_ids": [i["id"] for i in _all_issues(data)],
    }


if __name__ == "__main__":
    mcp.run()