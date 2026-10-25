import asyncio
import json
import tempfile
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

import agent_core
import diagnose
import server


def _diagnosis(**changes):
    value = {
        "crop": "Tomato",
        "disease": "early blight",
        "disease_key": "tomato early blight",
        "confidence": "high",
        "symptoms": "Brown spots on older leaves.",
        "is_fungal": True,
        "what_i_see": "Brown spots are visible on the leaf.",
    }
    value.update(changes)
    return value


def _treatment(**changes):
    value = {
        "crop": "Tomato",
        "disease_key": "tomato early blight",
        "cause": "Fungal disease.",
        "symptoms": "Brown spots on older leaves.",
        "organic_control": ["Remove affected leaves."],
        "chemical_control": "Use only a fungicide registered for the crop; check the label.",
        "prevention": ["Avoid prolonged leaf wetness."],
        "sources": ["TNAU Agritech (verify before use)."],
    }
    value.update(changes)
    return value


class FakeSession:
    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def initialize(self):
        return None

    async def list_tools(self):
        specifications = {
            "diagnose_image": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["image_path", "description"],
                "additionalProperties": False,
            },
            "city_to_coords": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
                "additionalProperties": False,
            },
            "get_weather": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required": ["latitude", "longitude"],
                "additionalProperties": False,
            },
            "lookup_treatment": {
                "type": "object",
                "properties": {"disease": {"type": "string"}},
                "required": ["disease"],
                "additionalProperties": False,
            },
        }
        return SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name=name,
                    description=name,
                    inputSchema=schema,
                    outputSchema=None,
                )
                for name, schema in specifications.items()
            ]
        )

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        value = self.results.get(name)
        if isinstance(value, Exception):
            raise value
        if callable(value):
            value = value(args)
        if value is None:
            value = {}
        return SimpleNamespace(
            isError=False,
            content=[SimpleNamespace(text=json.dumps(value))],
        )


def run_turn(_testcase, decisions, results, *, crop="Tomato", city="", lat=20.0, lon=73.78, text="spots"):
    session = FakeSession(results)
    iterator = iter(decisions)

    @asynccontextmanager
    async def fake_stdio(*_args, **_kwargs):
        yield "reader", "writer"

    with (
        patch.object(agent_core, "stdio_client", fake_stdio),
        patch.object(agent_core, "ClientSession", lambda *_args: session),
        patch.object(agent_core, "llm_json", side_effect=lambda *_args: next(iterator)),
        patch.object(
            agent_core,
            "ollama_chat",
            return_value={"message": {"content": "looks good"}},
        ),
    ):
        conversation = {
            "crop": crop,
            "context": agent_core.new_context(crop),
            "memory": [],
            "created": 1,
            "safety_version": 1,
        }
        conversation["context"]["city"] = city
        conversation["context"]["lat"] = lat
        conversation["context"]["lon"] = lon
        result = asyncio.run(agent_core.chat_turn(conversation, text, "Uploads/leaf.jpg"))
    return result, session, conversation


class DiagnosisAndGuardTests(unittest.TestCase):
    def test_unclear_image_stops_without_other_tools(self):
        result, session, _ = run_turn(
            self,
            [{"action": "diagnose_image", "args": {}}],
            {"diagnose_image": _diagnosis(disease="unclear", disease_key="", confidence="low")},
        )
        self.assertEqual([name for name, _ in session.calls], ["diagnose_image"])
        self.assertIn("well-lit photo", result["reply"])
        self.assertIsNone(result["treatment"])

    def test_description_mismatch_stops_before_treatment(self):
        result, session, _ = run_turn(
            self,
            [
                {"action": "diagnose_image", "args": {}},
                {"action": "lookup_treatment", "args": {}},
                {"action": "final", "answer": "done"},
            ],
            {
                "diagnose_image": _diagnosis(
                    confidence="high",
                    photo_shows="a bulb with visible rot",
                    description_mismatch=True,
                ),
                "lookup_treatment": _treatment(),
            },
            text="The leaves have spots.",
        )
        self.assertEqual([name for name, _ in session.calls], ["diagnose_image"])
        self.assertIn("your photo shows a bulb with visible rot", result["reply"])
        self.assertIn("send a close photo of the plant part", result["reply"])

    def test_crop_mismatch_stops_before_treatment(self):
        result, session, conversation = run_turn(
            self,
            [{"action": "diagnose_image", "args": {}}],
            {"diagnose_image": _diagnosis(crop="Potato", disease_key="potato early blight")},
        )
        self.assertEqual([name for name, _ in session.calls], ["diagnose_image"])
        self.assertIn("selected crop is Tomato", result["reply"])
        self.assertIn("no crop-specific treatment", result["reply"])
        followup = asyncio.run(
            agent_core.chat_turn(conversation, "Can I use the treatment anyway?")
        )
        self.assertIn("previous photo did not match", followup["reply"])

    def test_crop_and_disease_key_inconsistency_is_rejected(self):
        result, session, _ = run_turn(
            self,
            [{"action": "diagnose_image", "args": {}}],
            {
                "diagnose_image": _diagnosis(
                    disease="early blight",
                    disease_key="tomato late blight",
                )
            },
        )
        self.assertEqual([name for name, _ in session.calls], ["diagnose_image"])
        self.assertIn("inconsistent", result["reply"].lower())
        self.assertIsNone(result["treatment"])

    def test_ambiguous_symptoms_without_photo_request_more_evidence(self):
        session = FakeSession()

        @asynccontextmanager
        async def fake_stdio(*_args, **_kwargs):
            yield "reader", "writer"

        with (
            patch.object(agent_core, "stdio_client", fake_stdio),
            patch.object(agent_core, "ClientSession", lambda *_args: session),
            patch.object(
                agent_core,
                "llm_json",
                return_value={"action": "final", "answer": "This is definitely a fungal disease."},
            ),
        ):
            conversation = {
                "crop": "Tomato",
                "context": agent_core.new_context("Tomato"),
                "memory": [],
            }
            result = asyncio.run(
                agent_core.chat_turn(conversation, "What is wrong? There are some spots.")
            )
        self.assertEqual(session.calls, [])
        self.assertIn("attach a clear, close photo", result["reply"])
        self.assertNotIn("definitely", result["reply"])

    def test_legacy_unverified_chat_facts_are_not_reused(self):
        session = FakeSession()

        @asynccontextmanager
        async def fake_stdio(*_args, **_kwargs):
            yield "reader", "writer"

        with (
            patch.object(agent_core, "stdio_client", fake_stdio),
            patch.object(agent_core, "ClientSession", lambda *args: session),
            patch.object(
                agent_core,
                "llm_json",
                return_value={"action": "final", "answer": "Use mancozeb."},
            ),
            patch.object(
                agent_core,
                "ollama_chat",
                return_value={"message": {"content": "looks good"}},
            ),
        ):
            conversation = {
                "crop": "Tomato",
                "context": {
                    **agent_core.new_context("Tomato"),
                    "diagnosis": _diagnosis(),
                    "treatment": _treatment(),
                },
                "memory": [
                    {"role": "assistant", "content": "Use mancozeb at 2 ml per litre."}
                ],
                "messages": [{"role": "assistant", "content": "Old result"}],
            }
            result = asyncio.run(
                agent_core.chat_turn(conversation, "Should I spray anything?")
            )
        self.assertEqual(session.calls, [])
        self.assertEqual(conversation["memory"][-2:], [
            {"role": "user", "content": "Should I spray anything?"},
            {"role": "assistant", "content": result["reply"][:1800]},
        ])
        self.assertTrue(conversation["legacy_results_notice"])
        self.assertIn("No verified entry. Contact your KVK.", result["reply"])
        self.assertNotIn("mancozeb", result["reply"].lower())

    def test_missing_location_is_requested_and_not_guessed(self):
        result, session, _ = run_turn(
            self,
            [
                {"action": "diagnose_image", "args": {}},
                {"action": "lookup_treatment", "args": {}},
                {"action": "final", "answer": "done"},
            ],
            {
                "diagnose_image": _diagnosis(),
                "lookup_treatment": _treatment(),
            },
            lat=None,
            lon=None,
        )
        self.assertEqual(
            [name for name, _ in session.calls],
            ["diagnose_image", "lookup_treatment"],
        )
        self.assertIn("add your city in the sidebar", result["reply"])
        self.assertIsNone(result["weather"])

    def test_city_is_geocoded_before_weather_and_model_coordinates_are_ignored(self):
        result, session, conversation = run_turn(
            self,
            [
                {"action": "diagnose_image", "args": {}},
                {"action": "get_weather", "args": {"latitude": 1, "longitude": 2}},
                {"action": "city_to_coords", "args": {"city": "invented"}},
                {"action": "get_weather", "args": {"latitude": 1, "longitude": 2}},
                {"action": "lookup_treatment", "args": {}},
                {"action": "final", "answer": "done"},
            ],
            {
                "diagnose_image": _diagnosis(),
                "city_to_coords": {
                    "name": "Nashik",
                    "latitude": 19.9975,
                    "longitude": 73.7898,
                },
                "get_weather": {
                    "fungal_risk": "MODERATE",
                    "relative_humidity_2m": 75,
                    "rain_last_3_days_mm": 3,
                },
                "lookup_treatment": _treatment(),
            },
            city="",
            text="I'm in Nashik, brown spots after rain",
        )
        self.assertEqual(
            [name for name, _ in session.calls],
            ["diagnose_image", "city_to_coords", "get_weather", "lookup_treatment"],
        )
        weather_call = next(args for name, args in session.calls if name == "get_weather")
        self.assertEqual(weather_call, {"latitude": 19.9975, "longitude": 73.7898})
        self.assertEqual(conversation["context"]["place"], "Nashik")
        self.assertIn("MODERATE", result["reply"])

    def test_geocoding_failure_is_reported_without_weather_substitution(self):
        result, session, _ = run_turn(
            self,
            [
                {"action": "diagnose_image", "args": {}},
                {"action": "city_to_coords", "args": {"city": "Nashik"}},
                {"action": "lookup_treatment", "args": {}},
                {"action": "final", "answer": "done"},
            ],
            {
                "diagnose_image": _diagnosis(),
                "city_to_coords": {"error": "city not found"},
                "lookup_treatment": _treatment(),
            },
            city="Nashik",
            lat=None,
            lon=None,
        )
        self.assertEqual(
            [name for name, _ in session.calls],
            ["diagnose_image", "city_to_coords", "lookup_treatment"],
        )
        self.assertIn("Location lookup failed: city not found", result["reply"])
        self.assertIsNone(result["weather"].get("fungal_risk"))

    def test_diagnosis_tool_failure_is_reported(self):
        result, session, _ = run_turn(
            self,
            [{"action": "diagnose_image", "args": {}}],
            {"diagnose_image": RuntimeError("camera file unavailable")},
        )
        self.assertEqual([name for name, _ in session.calls], ["diagnose_image"])
        self.assertIn("camera file unavailable", result["reply"])
        self.assertIsNone(result["treatment"])

    def test_weather_failure_does_not_invent_weather(self):
        result, session, _ = run_turn(
            self,
            [
                {"action": "diagnose_image", "args": {}},
                {"action": "get_weather", "args": {"latitude": 0, "longitude": 0}},
                {"action": "lookup_treatment", "args": {}},
                {"action": "final", "answer": "done"},
            ],
            {
                "diagnose_image": _diagnosis(),
                "get_weather": RuntimeError("weather offline"),
                "lookup_treatment": _treatment(),
            },
        )
        self.assertEqual(
            [name for name, _ in session.calls],
            ["diagnose_image", "get_weather", "lookup_treatment"],
        )
        self.assertIn("weather offline", result["reply"])
        self.assertNotIn("rain None mm", result["reply"])

    def test_treatment_failure_reports_no_verified_entry(self):
        result, session, _ = run_turn(
            self,
            [
                {"action": "diagnose_image", "args": {}},
                {"action": "get_weather", "args": {}},
                {"action": "lookup_treatment", "args": {}},
                {"action": "final", "answer": "use a spray"},
            ],
            {
                "diagnose_image": _diagnosis(),
                "get_weather": {
                    "fungal_risk": "MODERATE",
                    "relative_humidity_2m": 75,
                    "rain_last_3_days_mm": 3,
                },
                "lookup_treatment": {"error": "No verified entry. Contact your KVK."},
            },
        )
        self.assertEqual(
            [name for name, _ in session.calls],
            ["diagnose_image", "get_weather", "lookup_treatment"],
        )
        self.assertIn("No verified entry. Contact your KVK.", result["reply"])

    def test_invented_dose_is_blocked(self):
        reply = agent_core._safe_followup(
            "Use 2 ml per litre on the leaves.",
            {"diagnosis": _diagnosis(), "treatment": _treatment()},
            "How much should I spray?",
        )
        self.assertIn("can't give a verified dose", reply)
        self.assertNotIn("2 ml per litre", reply)

    def test_identical_tool_call_is_not_repeated(self):
        result, session, _ = run_turn(
            self,
            [
                {"action": "diagnose_image", "args": {}},
                {"action": "lookup_treatment", "args": {}},
                {"action": "lookup_treatment", "args": {}},
                {"action": "final", "answer": "done"},
            ],
            {
                "diagnose_image": _diagnosis(is_fungal=False),
                "lookup_treatment": _treatment(),
            },
        )
        self.assertEqual([name for name, _ in session.calls].count("lookup_treatment"), 1)
        self.assertTrue(result["reply"].startswith("Crop: Tomato"))

    def test_treatment_for_wrong_crop_is_rejected(self):
        result, session, _ = run_turn(
            self,
            [
                {"action": "diagnose_image", "args": {}},
                {"action": "lookup_treatment", "args": {}},
                {"action": "final", "answer": "use the treatment"},
            ],
            {
                "diagnose_image": _diagnosis(is_fungal=False),
                "lookup_treatment": _treatment(crop="Potato"),
            },
        )
        self.assertEqual([name for name, _ in session.calls], ["diagnose_image", "lookup_treatment"])
        self.assertIn("No verified entry. Contact your KVK.", result["reply"])

    def test_maximum_iterations_returns_partial_evidence(self):
        result, session, _ = run_turn(
            self,
            [{"action": "city_to_coords", "args": {"city": "Nashik"}}] * agent_core.MAX_STEPS,
            {
                "city_to_coords": {
                    "name": "Nashik",
                    "latitude": 19.9975,
                    "longitude": 73.7898,
                }
            },
            city="Nashik",
            lat=None,
            lon=None,
            text="check today's weather",
        )
        self.assertEqual(len(session.calls), 1)
        self.assertIn("step limit", result["reply"])
        self.assertNotIn("HIGH fungal-weather risk", result["reply"])


class SchemaAndTreatmentTests(unittest.TestCase):
    def test_invalid_model_decision_is_rejected(self):
        with self.assertRaises(ValueError):
            agent_core._validate_decision({"action": "final", "answer": ["not", "text"]}, set())

    def test_mcp_output_schema_is_enforced(self):
        tool = SimpleNamespace(outputSchema={"type": "object", "required": ["crop"]})
        invalid_result = SimpleNamespace(
            isError=False,
            content=[SimpleNamespace(text=json.dumps({"disease": "early blight"}))],
        )
        checked = agent_core._validate_tool_result("diagnose_image", invalid_result, tool)
        self.assertIn("schema", checked.get("error", ""))

    def test_missing_location_weather_question_asks_without_calling_api(self):
        session = FakeSession()

        @asynccontextmanager
        async def fake_stdio(*_args, **_kwargs):
            yield "reader", "writer"

        with patch.object(agent_core, "stdio_client", fake_stdio):
            conversation = {
                "crop": "Tomato",
                "context": agent_core.new_context("Tomato"),
                "memory": [],
            }
            result = asyncio.run(
                agent_core.chat_turn(conversation, "What is the weather for my field?")
            )
        self.assertEqual(session.calls, [])
        self.assertIn("What city or village", result["reply"])

    def test_lookup_supports_exact_and_same_crop_partial_matches(self):
        exact = server.lookup_treatment("tomato early blight")
        partial = server.lookup_treatment("tomato blight")
        self.assertEqual(exact.get("disease_key"), "tomato early blight")
        self.assertEqual(partial.get("disease_key"), "tomato early blight")

    def test_lookup_alias_and_cross_crop_match_are_marked(self):
        alias = server.lookup_treatment("tikka")
        peanut_alias = server.lookup_treatment("peanut early leaf spot")
        tomato_leaf_spot = server.lookup_treatment("tomato leaf spot")
        other_crop = server.lookup_treatment("banana target spot")
        self.assertEqual(alias.get("disease_key"), "groundnut leaf spot")
        self.assertEqual(peanut_alias.get("disease_key"), "groundnut leaf spot")
        self.assertIn(tomato_leaf_spot.get("crop"), {"Tomato", None})
        if tomato_leaf_spot.get("crop") != "Tomato":
            self.assertIn("note", tomato_leaf_spot)
        self.assertEqual(other_crop.get("disease_key"), "cotton alternaria leaf spot")
        self.assertIn("another crop", other_crop.get("note", ""))
        self.assertEqual(other_crop.get("registered_products"), [])

    def test_report_accepts_object_sources_and_missing_treatment_fields(self):
        report = agent_core._report(
            {
                "crop": "Tomato",
                "diagnosis": {"crop": "Tomato", "disease": "early blight", "confidence": "high"},
                "treatment": {
                    "organic_control": "Remove affected leaves.",
                    "chemical_control": "Use a registered product.",
                    "sources": [{"name": "TNAU", "url": "https://example.com"}],
                },
            }
        )
        self.assertIn("Remove affected leaves.", report)
        self.assertIn("Reference sources (verify before use): TNAU", report)
        self.assertNotIn("https://example.com", report)

    def test_report_uses_photo_evidence_and_answers_unverified_spray_request(self):
        report = agent_core._report(
            {
                "crop": "Onion",
                "reported_symptoms": "Can I spray something for purple-brown blotches?",
                "diagnosis": {
                    "crop": "Onion",
                    "disease": "unclear",
                    "confidence": "medium",
                    "photo_shows": "a bulb with visible rot",
                    "description_mismatch": True,
                },
                "treatment": {"error": "No verified entry."},
            }
        )
        self.assertIn("What I can see in the photo: a bulb with visible rot", report)
        self.assertIn("your photo shows a bulb with visible rot", report)
        self.assertIn("I can’t recommend a pesticide or a dose", report)
        self.assertNotIn("Reported symptoms:", report)
        self.assertNotIn("purple-brown blotches", report)

    def test_diagnose_clears_copied_symptoms_and_lowers_confidence(self):
        model_result = {
            "crop": "Onion",
            "disease": "purple blotch",
            "disease_key": "onion purple blotch",
            "confidence": "high",
            "symptoms": "Purple-brown blotches and drying tips.",
            "is_fungal": True,
            "what_i_see": "Blotches are visible on the leaf.",
            "photo_shows": "a leaf with visible blotches",
            "description_mismatch": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            image_path = f"{directory}\\test.jpg"
            with open(image_path, "wb") as image_file:
                image_file.write(b"mock image")
            fake_client = SimpleNamespace(
                models=SimpleNamespace(generate_content=lambda **_kwargs: None)
            )
            with (
                patch("diagnose.genai.Client", return_value=fake_client),
                patch.dict("os.environ", {"GEMINI_API_KEY": "test"}),
                patch(
                    "diagnose.generate_content_with_retry",
                    return_value=SimpleNamespace(text=json.dumps(model_result)),
                ),
            ):
                result = json.loads(
                    diagnose.diagnose(
                        image_path,
                        "purple-brown blotches and drying tips",
                    )
                )
        self.assertEqual(result["symptoms"], "")
        self.assertTrue(result["symptoms_copied"])
        self.assertEqual(result["confidence"], "medium")

    def test_diagnosis_parser_rejects_missing_schema_fields(self):
        parsed = diagnose._json_object('{"crop":"Tomato","disease":"early blight"}')
        self.assertIn("error", parsed)


if __name__ == "__main__":
    unittest.main()
