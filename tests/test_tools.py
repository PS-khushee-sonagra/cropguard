"""
Test suite for CropGuard MCP tools and Agent helpers.

Run with: pytest tests/ -v

Notes:
- get_weather tests that require live internet are marked to skip
  automatically if the network call fails (e.g. no internet access).
  This keeps the suite runnable even in restricted environments while
  still exercising the real API when internet is available.
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import agent_cropguard as ac  # noqa: E402
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

    def test_non_string_crop_returns_error(self):
        result = sc.get_crop_info(None)  # type: ignore
        assert result["status"] == "error"

    def test_path_traversal_returns_not_found(self):
        result = sc.get_crop_info("../cotton")
        assert result["status"] == "not_found"

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
        result = sc.search_pest_disease(
            "wheat",
            ["yellow", "spots", "leaves", "growth", "reduced yield", "stunted"],
        )
        assert result["status"] == "ok"
        assert len(result["matches"]) <= 5

    def test_symptoms_as_json_string(self):
        symptoms_json = json.dumps(["dark brown spots with concentric rings", "leaf drop"])
        result = sc.search_pest_disease("tomato", symptoms_json)
        assert result["status"] == "ok"
        assert len(result["matches"]) > 0

    def test_symptoms_as_comma_separated_string(self):
        result = sc.search_pest_disease("tomato", "dark brown spots with concentric rings, leaf drop")
        assert result["status"] == "ok"
        assert len(result["matches"]) > 0

    def test_symptoms_as_single_string(self):
        result = sc.search_pest_disease("tomato", "dark brown spots with concentric rings")
        assert result["status"] == "ok"
        assert len(result["matches"]) > 0

    def test_path_traversal_crop_sanitized(self):
        result = sc.search_pest_disease("../tomato", ["dark spots"])
        assert result["status"] == "not_found"

    def test_invalid_types_return_error(self):
        assert sc.search_pest_disease(None, ["spots"])["status"] == "error"  # type: ignore
        assert sc.search_pest_disease("tomato", None)["status"] == "error"  # type: ignore
        assert sc.search_pest_disease("tomato", 12345)["status"] == "error"  # type: ignore

    def test_v2_semantic_search_ranks_powdery_mildew_above_rust(self):
        # In V1, white powder on wheat leaves falsely ranked stripe rust #1 due to alphabetical/order tie.
        # In V2, semantic diagnostic tokens 'white' and 'powder' rank powdery mildew #1.
        result = sc.search_pest_disease("wheat", ["white powder on wheat leaves"])
        assert result["status"] == "ok"
        assert len(result["matches"]) > 0
        assert result["matches"][0]["id"] == "wheat_powdery_mildew"

    def test_v2_morphological_and_synonym_matching(self):
        # 'pink worms' (synonym for pink caterpillars/larvae) correctly diagnoses pink bollworm
        result = sc.search_pest_disease("cotton", ["holes in bolls with pink worms inside"])
        assert result["status"] == "ok"
        assert len(result["matches"]) > 0
        assert result["matches"][0]["id"] == "cotton_pink_bollworm"

    def test_v2_sticky_sap_and_white_flies_diagnoses_whitefly(self):
        # 'sticky sap' (synonym for honeydew) and 'white flies' (synonym for whitefly)
        result = sc.search_pest_disease("tomato", ["sticky sap on leaf with tiny white flies"])
        assert result["status"] == "ok"
        assert len(result["matches"]) > 0
        assert result["matches"][0]["id"] == "tomato_whitefly"

    def test_v2_vague_description_does_not_hallucinate(self):
        # 'leaves look strange' contains only generic non-diagnostic stop-words
        # Must return empty matches, triggering follow-up questions instead of a false diagnosis
        result = sc.search_pest_disease("cotton", ["leaves look strange"])
        assert result["status"] == "ok"
        assert result["matches"] == []



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

    def test_non_string_arguments_return_error(self):
        assert sc.get_ipm_guidance(None, "cotton_bollworm")["status"] == "error"  # type: ignore
        assert sc.get_ipm_guidance("cotton", None)["status"] == "error"  # type: ignore

    def test_path_traversal_returns_not_found(self):
        result = sc.get_ipm_guidance("../cotton", "cotton_bollworm")
        assert result["status"] == "not_found"


# ---------------------------------------------------------------------------
# get_weather
# ---------------------------------------------------------------------------

class TestGetWeather:
    def test_empty_location_returns_error(self):
        result = sc.get_weather("", 3)
        assert result["status"] == "error"

    def test_non_string_location_returns_error(self):
        result = sc.get_weather(None, 3)  # type: ignore
        assert result["status"] == "error"

    def test_days_non_numeric_handled_gracefully(self):
        result = sc.get_weather("Ahmedabad, India", "invalid")  # type: ignore
        if result["status"] == "error" and "weather request failed" in result.get("message", ""):
            pytest.skip("Network unavailable")
        # Should not raise ValueError/TypeError and should use clamped default
        assert result["status"] in ("ok", "not_found", "error")

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

    def test_uk_substring_does_not_falsely_match_muktsar(self, monkeypatch):
        # "Muktsar" contains "uk" but is not "UK". It should resolve to India fallback
        called_urls = []

        class MockResponse:
            def __init__(self, json_data, status_code=200):
                self._json = json_data
                self.status_code = status_code

            def raise_for_status(self):
                pass

            def json(self):
                return self._json

        def mock_get(url, params=None, timeout=10):
            called_urls.append((url, params))
            if "geocoding-api" in url:
                return MockResponse({"results": [{"name": "Muktsar", "admin1": "Punjab", "country": "India", "latitude": 30.47, "longitude": 74.51}]})
            return MockResponse({
                "current": {"time": "2026-10-11T12:00", "temperature_2m": 30.0, "relative_humidity_2m": 50, "precipitation": 0.0},
                "daily": {"time": ["2026-10-11"], "temperature_2m_max": [31.0], "temperature_2m_min": [20.0], "precipitation_sum": [0.0]},
            })

        import requests
        monkeypatch.setattr(requests, "get", mock_get)

        res = sc.get_weather("Muktsar", 1)
        assert res["status"] == "ok"
        # Should have called secondary India geocode since Muktsar has no explicit country
        india_calls = [p for (u, p) in called_urls if p and p.get("name") == "Muktsar, India"]
        assert len(india_calls) == 1

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
                    },
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
            def __init__(self, json_data, status_code=200):
                self._json = json_data
                self.status_code = status_code

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

    def test_mocked_weather_503_retry_and_graceful_error(self, monkeypatch):
        import requests

        class Mock503Response:
            status_code = 503

            def raise_for_status(self):
                raise requests.HTTPError("503 Server Error: Service Unavailable")

            def json(self):
                return {}

        class MockGeocodeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"results": [{"name": "Nashik", "country": "India", "latitude": 20.0, "longitude": 73.0}]}

        attempts = 0

        def mock_get(url, params=None, timeout=10):
            nonlocal attempts
            if "geocoding-api" in url:
                return MockGeocodeResponse()
            attempts += 1
            return Mock503Response()

        monkeypatch.setattr(requests, "get", mock_get)
        import time
        monkeypatch.setattr(time, "sleep", lambda s: None)

        res = sc.get_weather("Nashik", 1)
        assert res["status"] == "error"
        assert "503" in res["message"]
        assert attempts == 3  # 1 initial + 2 retries


# ---------------------------------------------------------------------------
# agent_cropguard helpers tests
# ---------------------------------------------------------------------------

class TestAgentCropGuardHelpers:
    def test_agent_call_tool_normalizes_ipm_args(self):
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

    def test_agent_call_tool_normalizes_crop_id_param(self):
        agent = ac.CropGuardAgent()
        agent.tool_names = {"get_ipm_guidance"}

        class MockSession:
            async def call_tool(self, name, arguments):
                class Structured:
                    structured_content = {"status": "ok", "received_args": arguments}
                return Structured()

        agent.session = MockSession()

        # Test remapping 'crop_id' -> 'crop'
        res_str = asyncio.run(agent.call_tool("get_ipm_guidance", {"crop_id": "cotton", "issue_id": "cotton_bollworm"}))
        res = json.loads(res_str)
        assert res["received_args"]["crop"] == "cotton"
        assert res["received_args"]["issue_id"] == "cotton_bollworm"

    def test_agent_call_tool_unknown_tool(self):
        agent = ac.CropGuardAgent()
        agent.tool_names = {"get_weather"}
        res = json.loads(asyncio.run(agent.call_tool("nonexistent", {})))
        assert res["status"] == "error"
        assert "unknown tool" in res["message"]

    def test_agent_reflect_handles_nudged_or_none_trace_safely(self, monkeypatch):
        agent = ac.CropGuardAgent()

        class MockMessage:
            content = "Reflected answer based on evidence."

        class MockChatResponse:
            message = MockMessage()

        import ollama
        monkeypatch.setattr(ollama, "chat", lambda **kwargs: MockChatResponse())

        # Trace with None tools should not raise TypeError('<' not supported between str and NoneType)
        trace_with_nudge = [
            {"_nudged": True, "tool": None, "arguments": None, "result": None},
            {"tool": "get_crop_info", "arguments": {"crop": "wheat"}, "result": '{"status": "ok"}'},
        ]
        reflected = asyncio.run(agent.reflect("sample question", "draft answer", trace_with_nudge))
        assert "Reflected answer" in reflected

    def test_search_outcome_classifications(self):
        # Empty trace
        assert ac._search_outcome([]) == ("no_search", {})

        # Empty matches
        empty_trace = [{"tool": "search_pest_disease", "result": json.dumps({"status": "ok", "matches": []})}]
        assert ac._search_outcome(empty_trace) == ("empty", {})

        # Strong match
        strong_trace = [{
            "tool": "search_pest_disease",
            "result": json.dumps({"status": "ok", "matches": [{"id": "cotton_bollworm", "name": "Cotton Bollworm", "match_type": "strong"}]})
        }]
        assert ac._search_outcome(strong_trace) == ("strong", {})

        # Weak matches
        weak_trace = [{
            "tool": "search_pest_disease",
            "result": json.dumps({"status": "ok", "matches": [{"id": "wheat_aphids", "name": "Wheat Aphids", "match_type": "weak"}]})
        }]
        kind, data = ac._search_outcome(weak_trace)
        assert kind == "weak"
        assert len(data["candidates"]) == 1

        # Unknown crop
        unknown_trace = [{
            "tool": "search_pest_disease",
            "result": json.dumps({"status": "not_found", "available_crops": ["cotton", "tomato", "wheat"]})
        }]
        kind, data = ac._search_outcome(unknown_trace)
        assert kind == "unknown_crop"
        assert "cotton" in data["crops"]

    def test_clarification_reply_first_round_and_final_round(self):
        # First round empty
        reply_empty = ac._clarification_reply("empty", {}, final_round=False)
        assert "Could you tell me more?" in reply_empty
        assert "type 'new'" in reply_empty

        # Final round empty
        reply_final = ac._clarification_reply("empty", {}, final_round=True)
        assert "Krishi Vigyan Kendra" in reply_final
        assert "Could you tell me more?" not in reply_final

        # Unknown crop
        reply_crop = ac._clarification_reply("unknown_crop", {"crops": ["cotton", "wheat"]}, final_round=False)
        assert "I don't recognise that crop" in reply_crop
        assert "cotton, wheat" in reply_crop


# ---------------------------------------------------------------------------
# Crop Resolution & Abiotic Blossom End Rot
# ---------------------------------------------------------------------------

class TestCropResolutionAndBlossomEndRot:
    def test_guess_crop_aliases(self):
        import web_server as ws
        assert ws.guess_crop("I am growing tomota plants") == "tomato"
        assert ws.guess_crop("Meri tamatar ki fasal") == "tomato"
        assert ws.guess_crop("kapas ke kide") == "cotton"
        assert ws.guess_crop("gehun ki fasal") == "wheat"
        assert ws.guess_crop("unknown plant") is None

    def test_resolve_crop_single_and_conflict(self):
        import web_server as ws
        # Single candidate
        crop, conflict = ws.resolve_crop(None, "tomato", None)
        assert crop == "tomato"
        assert conflict is None

        # Conflict between selected and seen
        crop, conflict = ws.resolve_crop("cotton", None, "tomato")
        assert crop is None
        assert conflict is not None
        assert "The crop is unclear" in conflict
        assert "cotton" in conflict and "tomato" in conflict

    def test_blossom_end_rot_present_and_diagnosable(self):
        res = sc.search_pest_disease("tomato", ["dark sunken leathery patch at blossom end of fruit"])
        assert res["status"] == "ok"
        matches = [m for m in res["matches"] if m["id"] == "tomato_blossom_end_rot"]
        assert len(matches) > 0
        assert matches[0]["type"] == "physiological_disorder"

        ipm = sc.get_ipm_guidance("tomato", "tomato_blossom_end_rot")
        assert ipm["status"] == "ok"
        assert any("watering" in step.lower() or "irrigation" in step.lower() for step in ipm["ipm_steps"])
        assert any("mulch" in step.lower() for step in ipm["ipm_steps"])

    def test_single_symptom_not_labeled_strong_match(self):
        # A single symptom phrase should never be stamped as a 'strong' match
        res = sc.search_pest_disease("tomato", ["rotting"])
        assert res["status"] == "ok"
        for m in res["matches"]:
            assert m["match_type"] != "strong"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))