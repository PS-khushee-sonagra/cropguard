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
import time
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
    """Load a crop's knowledge base JSON file, case-insensitively and sanitized against path traversal."""
    if not isinstance(crop, str):
        return None
    crop_key = crop.strip().lower()
    if not crop_key or not re.match(r"^[a-z0-9_-]+$", crop_key):
        return None
    path = (KNOWLEDGE_DIR / f"{crop_key}.json").resolve()
    try:
        if not path.is_relative_to(KNOWLEDGE_DIR.resolve()) or not path.is_file():
            return None
    except AttributeError:
        if KNOWLEDGE_DIR.resolve() not in path.parents or not path.is_file():
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
    return (
        list(crop_data.get("pests", []))
        + list(crop_data.get("diseases", []))
        + list(crop_data.get("disorders", []))
    )


class MatchScore(tuple):
    """Backwards-compatible tuple (matched_count, total_count) with semantic score attribute."""
    def __new__(cls, matched: int, total: int, score: float = 0.0):
        instance = super().__new__(cls, (matched, total))
        instance.matched = matched
        instance.total = total
        instance.score = score
        return instance


GENERIC_STOP_WORDS = {
    "plant", "plants", "crop", "crops", "leaf", "leaves", "foliage",
    "farm", "field", "look", "looks", "looking", "seem", "seems",
    "show", "shows", "showing", "have", "having", "has", "problem",
    "problems", "damage", "damaged", "damages", "strange", "bad", "sick", "help",
    "cotton", "tomato", "wheat", "some", "visible", "observe", "observed",
    "part", "parts", "area", "areas", "find", "finding", "found", "also", "like",
    "from", "with", "when", "into", "under", "over", "that", "this", "then", "they",
    "affect", "affected", "affecting", "what", "is", "are", "these", "disease", "pest",
    "my", "our", "the", "how", "cure", "treat", "cause", "causing", "location", "tell"
}

SYNONYMS = {
    "leaves": "leaf", "leaf": "leaf",
    "flies": "fly", "fly": "fly",
    "whiteflies": "whitefly", "whitefly": "whitefly",
    "caterpillars": "caterpillar", "caterpillar": "caterpillar",
    "larvae": "caterpillar", "larva": "caterpillar", "worms": "caterpillar", "worm": "caterpillar",
    "grub": "caterpillar", "grubs": "caterpillar", "borer": "caterpillar", "borers": "caterpillar",
    "aphids": "aphid", "aphid": "aphid", "louse": "aphid", "lice": "aphid",
    "pustules": "pustule", "pustule": "pustule",
    "spots": "spot", "spot": "spot", "lesion": "spot", "lesions": "spot",
    "blotch": "spot", "blotches": "spot", "patch": "patch", "patches": "patch",
    "rings": "ring", "ring": "ring",
    "powdery": "powder", "powder": "powder", "dust": "powder", "dusty": "powder",
    "sticky": "honeydew", "sap": "honeydew", "honeydew": "honeydew",
    "curling": "curl", "curl": "curl", "curled": "curl", "pucker": "curl", "puckering": "curl",
    "rotting": "rot", "rot": "rot", "rotten": "rot", "decay": "rot",
    "holes": "hole", "hole": "hole", "bored": "hole", "tunnel": "hole", "tunnels": "hole",
    "dropping": "drop", "drop": "drop", "shed": "drop", "shedding": "drop",
    "insects": "insect", "insect": "insect", "bugs": "insect", "bug": "insect"
}


def _normalize_token(w: str) -> str:
    """Normalize word token through agricultural synonym map and morphological stemming."""
    w = w.lower().strip()
    if w in SYNONYMS:
        return SYNONYMS[w]
    if w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("ing") and len(w) > 5:
        w = w[:-3]
    elif w.endswith("es") and len(w) > 4:
        w = w[:-2]
    elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        w = w[:-1]
    return SYNONYMS.get(w, w)


def _extract_semantic_tokens(text: str) -> tuple[set[str], set[str]]:
    """Return (all_normalized_tokens, diagnostic_tokens_excluding_stopwords)."""
    raw_words = [w for w in re.split(r"\W+", text.lower()) if len(w) > 2]
    all_norm = {_normalize_token(t) for t in raw_words}
    diagnostic = {t for t in all_norm if t not in GENERIC_STOP_WORDS}
    return all_norm, diagnostic


def _score_symptom_match(issue: dict[str, Any], query_symptoms: list[str]) -> MatchScore:
    """
    Score symptom match using semantic token overlap, domain synonyms, and diagnostic weight.
    Returns MatchScore(matched_count, total_count, semantic_affinity).
    """
    issue_symptoms = issue.get("symptoms", [])
    issue_text = " ".join(issue_symptoms).lower()
    issue_all, issue_diag = _extract_semantic_tokens(issue_text)

    clean_query = [s.strip().lower() for s in query_symptoms if isinstance(s, str) and s.strip()]
    if not clean_query:
        return MatchScore(0, 0, 0.0)

    matched_phrases = 0
    total_diag_hits = 0

    for qs_clean in clean_query:
        q_all, q_diag = _extract_semantic_tokens(qs_clean)
        # If query has no diagnostic tokens (e.g. only generic stop words), do not grant a hit
        if not q_diag:
            continue
        diag_hits = len(q_diag.intersection(issue_diag))
        # Phrase match requires at least one diagnostic hit and >= half of diagnostic terms, or >= 2 diagnostic hits
        if diag_hits >= 2 or diag_hits >= max(1, (len(q_diag) + 1) // 2):
            matched_phrases += 1
            total_diag_hits += diag_hits

    # Signature phrase matching for high-confidence agronomist patterns
    query_full = " ".join(clean_query).lower()
    sig_bonus = 0.0
    signature_patterns = [
        "white powder", "concentric rings", "target-like", "orange pustules",
        "yellow rust", "pink-colored", "rosette", "deadheart", "honeydew",
        "sooty mold", "white insects flying"
    ]
    for sig in signature_patterns:
        if sig in query_full and sig in issue_text:
            sig_bonus += 3.0

    semantic_affinity = float(total_diag_hits) + sig_bonus
    return MatchScore(matched_phrases, len(clean_query), semantic_affinity)


def _get_with_retry(url: str, params: dict[str, Any], timeout: int = 10, max_retries: int = 2) -> requests.Response:
    """Perform a GET request with retry and exponential backoff for timeouts and 5xx errors."""
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            status_code = getattr(resp, "status_code", 200)
            if status_code >= 500 and attempt < max_retries:
                time.sleep(0.5 * (2 ** attempt))
                continue
            resp.raise_for_status()
            return resp
        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt < max_retries:
                time.sleep(0.5 * (2 ** attempt))
                continue
            raise


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
    try:
        days_int = int(days) if days is not None else 3
    except (ValueError, TypeError):
        days_int = 3
    days = max(1, min(days_int, 7))

    if not isinstance(location, str) or not location.strip():
        return {"status": "error", "message": "location must be a non-empty string"}

    loc_clean = location.strip()
    loc_lower = loc_clean.lower()

    try:
        geo_resp = _get_with_retry(
            GEOCODE_URL,
            params={"name": loc_clean, "count": 20, "language": "en", "format": "json"},
            timeout=10,
        )
        geo_data = geo_resp.json()
    except requests.RequestException as e:
        return {"status": "error", "message": f"geocoding request failed: {e}"}
    except ValueError as e:
        return {"status": "error", "message": f"geocoding response was not valid JSON: {e}"}

    results = geo_data.get("results") or []

    explicit_countries = ["india", "pakistan", "usa", "united states", "canada", "uk", "australia"]
    has_explicit_country = any(
        re.search(r"\b" + re.escape(c) + r"\b", loc_lower)
        for c in explicit_countries
    )

    if not has_explicit_country:
        try:
            geo_in_resp = _get_with_retry(
                GEOCODE_URL,
                params={"name": f"{loc_clean}, India", "count": 20, "language": "en", "format": "json"},
                timeout=10,
            )
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
        weather_resp = _get_with_retry(
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
        weather_data = weather_resp.json()
    except requests.RequestException as e:
        return {"status": "error", "message": f"weather request failed: {e}"}
    except ValueError as e:
        return {"status": "error", "message": f"weather response was not valid JSON: {e}"}

    daily = weather_data.get("daily", {})
    daily_list = []
    times = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    precips = daily.get("precipitation_sum", [])
    for i, date in enumerate(times):
        daily_list.append({
            "date": date,
            "temp_max_c": max_temps[i] if i < len(max_temps) else None,
            "temp_min_c": min_temps[i] if i < len(min_temps) else None,
            "precipitation_mm": precips[i] if i < len(precips) else None,
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
    if not isinstance(crop, str) or not crop.strip():
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
        "known_disorders": [{"id": d["id"], "name": d["name"]} for d in data.get("disorders", [])],
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
            symptom_list = parsed if isinstance(parsed, list) else [str(parsed)]
        except (json.JSONDecodeError, TypeError):
            symptom_list = [s.strip() for s in symptoms.split(",")] if "," in symptoms else [symptoms]
    else:
        symptom_list = []

    if not isinstance(crop, str) or not crop.strip():
        return {"status": "error", "message": "crop must be a non-empty string"}

    clean_symptoms = [s.strip() for s in symptom_list if isinstance(s, str) and s.strip()]
    if not clean_symptoms:
        return {"status": "error", "message": "symptoms must be a non-empty list of strings"}

    data = _load_crop(crop)
    if data is None:
        return {
            "status": "not_found",
            "message": f"no knowledge base entry for crop '{crop}'",
            "available_crops": _available_crops(),
        }

    issues = _all_issues(data)
    scored = []
    for issue in issues:
        match_info = _score_symptom_match(issue, clean_symptoms)
        matched, total = match_info[0], match_info[1]
        sem_score = getattr(match_info, "score", float(matched))
        if matched == 0:
            continue
        ratio = matched / total if total else 0
        # Fix 3: "Strong match" requires several specific symptoms matched and confirmed coverage
        if matched >= 2 and ratio >= 0.6:
            match_type = "strong"
        elif ratio >= 0.33 or matched >= 1:
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
            "_score": sem_score,
        })

    scored.sort(key=lambda x: (x["_score"], x["matched_symptom_count"], x["match_type"] == "strong"), reverse=True)
    for s in scored:
        s.pop("_score", None)

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
    if not isinstance(crop, str) or not crop.strip() or not isinstance(issue_id, str) or not issue_id.strip():
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
    