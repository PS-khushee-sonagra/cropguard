"""
Test suite for CropGuard MCP tools.

Run with: pytest tests/ -v

Notes:
- get_weather tests that require live internet are marked to skip
  automatically if the network call fails (e.g. no internet access).
  This keeps the suite runnable even in restricted environments while
  still exercising the real API when internet is available.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import server_cropguard as sc  # noqa: E402


# ---------------------------------------------------------------------------
# get_crop_info
# ---------------------------------------------------------------------------

class TestGetCropInfo:
    def test_valid_crop_returns_ok(self):
        result = sc.get_crop_info("tomato")
        assert result["status"] == "ok"
        assert result["crop"] == "tomato"
        assert len(result["known_pests"]) > 0
        assert len(result["known_diseases"]) > 0

    def test_case_insensitive_lookup(self):
        result = sc.get_crop_info("ToMaTo")
        assert result["status"] == "ok"

    def test_unknown_crop_returns_not_found(self):
        result = sc.get_crop_info("durian")
        assert result["status"] == "not_found"
        assert "available_crops" in result
        assert "tomato" in result["available_crops"]

    def test_empty_crop_returns_error(self):
        result = sc.get_crop_info("")
        assert result["status"] == "error"

    def test_all_three_crops_load(self):
        for crop in ["tomato", "cotton", "wheat"]:
            result = sc.get_crop_info(crop)
            assert result["status"] == "ok", f"{crop} failed to load"



# ---------------------------------------------------------------------------
# search_pest_disease
# ---------------------------------------------------------------------------

class TestSearchPestDisease:
    def test_strong_match_for_early_blight_symptoms(self):
        result = sc.search_pest_disease(
            "tomato",
            ["dark spots with concentric rings on leaves", "leaves dropping from the bottom of the plant"],
        )
        assert result["status"] == "ok"
        assert len(result["matches"]) > 0
        top = result["matches"][0]
        assert top["id"] == "tomato_early_blight"
        assert top["match_type"] == "strong"

    def test_whitefly_symptoms_match_tylcv_context(self):
        result = sc.search_pest_disease(
            "tomato",
            ["small white insects flying up when disturbed", "sticky honeydew on leaves"],
        )
        assert result["status"] == "ok"
        ids = [m["id"] for m in result["matches"]]
        assert "tomato_whitefly" in ids

    def test_unknown_crop_returns_not_found(self):
        result = sc.search_pest_disease("durian", ["some symptom"])
        assert result["status"] == "not_found"

    def test_empty_symptoms_list_returns_error(self):
        result = sc.search_pest_disease("tomato", [])
        assert result["status"] == "error"

    def test_whitespace_only_symptoms_returns_error(self):
        result = sc.search_pest_disease("tomato", ["   ", ""])
        assert result["status"] == "error"

    def test_nonsense_symptoms_returns_no_matches_gracefully(self):
        result = sc.search_pest_disease("tomato", ["spaceship landed in the field"])
        assert result["status"] == "ok"
        assert result["matches"] == []

    def test_results_capped_at_five(self):
        # Broad symptom terms likely to loosely match many issues
        result = sc.search_pest_disease(
            "wheat",
            ["yellow", "spots", "leaves", "growth", "reduced yield", "stunted"],
        )
        assert result["status"] == "ok"
        assert len(result["matches"]) <= 5


# ---------------------------------------------------------------------------
# get_ipm_guidance
# ---------------------------------------------------------------------------

class TestGetIpmGuidance:
    def test_valid_issue_returns_full_detail(self):
        result = sc.get_ipm_guidance("cotton", "cotton_bollworm")
        assert result["status"] == "ok"
        assert result["name"].startswith("Cotton Bollworm")
        assert len(result["ipm_steps"]) > 0
        assert len(result["sources"]) > 0

    def test_unknown_crop_returns_not_found(self):
        result = sc.get_ipm_guidance("durian", "durian_wilt")
        assert result["status"] == "not_found"

    def test_unknown_issue_id_returns_not_found_with_suggestions(self):
        result = sc.get_ipm_guidance("tomato", "made_up_disease")
        assert result["status"] == "not_found"
        assert "available_ids" in result
        assert "tomato_early_blight" in result["available_ids"]

    def test_empty_issue_id_returns_error(self):
        result = sc.get_ipm_guidance("tomato", "")
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# get_weather
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# get_weather
# ---------------------------------------------------------------------------

class TestGetWeather:
    def test_empty_location_returns_error(self):
        result = sc.get_weather("", 3)
        assert result["status"] == "error"

    def test_live_lookup_valid_location(self):
        result = sc.get_weather("Ahmedabad, India", 3)
        if result["status"] == "error":
            pytest.skip(f"Network unavailable in this environment: {result['message']}")
        assert result["status"] == "ok"
        assert result["latitude"] is not None
        assert len(result["daily"]) == 3
        assert "units" in result
        assert "timestamp" in result["current"]
        assert "humidity_max_pct" not in result["daily"][0]

    def test_live_lookup_nonsense_location(self):
        result = sc.get_weather("Xyzzyplonk Nonexistentville", 3)
        if result["status"] == "error":
            pytest.skip(f"Network unavailable in this environment: {result['message']}")
        assert result["status"] == "not_found"

    def test_days_clamped_to_valid_range(self):
        result = sc.get_weather("Ahmedabad, India", 99)
        if result["status"] == "error":
            pytest.skip(f"Network unavailable in this environment: {result['message']}")
        assert len(result["daily"]) <= 7

    def test_mocked_successful_weather(self, monkeypatch):
        class MockResponse:
            def __init__(self, json_data, status_code=200):
                self._json = json_data
                self.status_code = status_code
            def raise_for_status(self):
                pass
            def json(self):
                return self._json

        def mock_get(url, params=None, timeout=10):
            if "geocoding-api" in url:
                return MockResponse({
                    "results": [{"name": "Ahmedabad", "admin1": "Gujarat", "country": "India", "latitude": 23.02, "longitude": 72.58}]
                })
            elif "forecast" in url:
                return MockResponse({
                    "current": {"time": "2026-09-26T12:00", "temperature_2m": 33.5, "relative_humidity_2m": 55, "precipitation": 0.0},
                    "daily": {
                        "time": ["2026-09-26", "2026-09-27"],
                        "temperature_2m_max": [34.0, 33.0],
                        "temperature_2m_min": [25.0, 24.0],
                        "precipitation_sum": [0.0, 1.2],
                    }
                })
            raise ValueError(f"Unexpected URL {url}")

        import requests
        monkeypatch.setattr(requests, "get", mock_get)

        res = sc.get_weather("Ahmedabad", 2)
        assert res["status"] == "ok"
        assert res["location_resolved"] == "Ahmedabad, Gujarat, India"
        assert res["current"]["temperature_c"] == 33.5
        assert res["current"]["timestamp"] == "2026-09-26T12:00"
        assert res["units"]["temperature"] == "°C"
        assert len(res["daily"]) == 2
        assert res["daily"][0]["temp_max_c"] == 34.0
        assert "humidity_max_pct" not in res["daily"][0]

    def test_mocked_geocoding_failure(self, monkeypatch):
        import requests
        def mock_get(url, params=None, timeout=10):
            raise requests.RequestException("Connection refused")

        monkeypatch.setattr(requests, "get", mock_get)
        res = sc.get_weather("Ahmedabad")
        assert res["status"] == "error"
        assert "geocoding request failed" in res["message"]

    def test_mocked_weather_api_failure(self, monkeypatch):
        class MockResponse:
            def __init__(self, json_data):
                self._json = json_data
            def raise_for_status(self):
                pass
            def json(self):
                return self._json

        import requests
        def mock_get(url, params=None, timeout=10):
            if "geocoding-api" in url:
                return MockResponse({"results": [{"name": "Test", "latitude": 10.0, "longitude": 20.0}]})
            raise requests.RequestException("Weather API timeout")

        monkeypatch.setattr(requests, "get", mock_get)
        res = sc.get_weather("Test")
        assert res["status"] == "error"
        assert "weather request failed" in res["message"]


# ---------------------------------------------------------------------------
# agent_cropguard call_tool helper tests
# ---------------------------------------------------------------------------

def test_agent_call_tool_normalizes_ipm_args():
    import asyncio
    import json
    import agent_cropguard as ac

    agent = ac.CropGuardAgent()
    agent.tool_names = {"get_ipm_guidance"}

    class MockSession:
        async def call_tool(self, name, arguments):
            class Structured:
                structured_content = {"status": "ok", "received_args": arguments}
            return Structured()

    agent.session = MockSession()

    # Test remapping 'id' -> 'issue_id' and inferring 'crop' from trace
    trace = [{"tool": "search_pest_disease", "arguments": {"crop": "tomato"}, "result": "{}"}]
    res_str = asyncio.run(agent.call_tool("get_ipm_guidance", {"id": "tomato_early_blight"}, trace=trace))
    res = json.loads(res_str)
    assert res["received_args"]["issue_id"] == "tomato_early_blight"
    assert res["received_args"]["crop"] == "tomato"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))