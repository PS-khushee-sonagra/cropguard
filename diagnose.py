import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from gemini_retry import generate_content_with_retry

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

MODEL = "gemini-3.5-flash-lite"
PROMPT = """Farmer says: {desc}
Treat the farmer's crop name as the crop identity. If the image appears to show a
different crop, report the crop actually visible; the application will stop on mismatch.
Treat image clues as observations, not proof of a disease. Separate what is visible from
what the farmer reports. Describe ONLY what you can see in the photo. Never copy the
farmer's words into the symptoms. Add the key "photo_shows": one short phrase saying
which plant part is in the photo and what it looks like. Add the key
"description_mismatch": true if the photo shows a different plant part or problem from
what the farmer described (for example a bulb or roots in the photo but leaf spots in
the text), otherwise false. If it is true, confidence must be "low" or "medium".
Do not provide treatment, pesticide names, brands, doses, or spray schedules.
Return exactly ONE JSON object (not a list) with all these keys:
crop (string), disease (string; use 'unclear' if not sufficiently supported),
disease_key (lowercase crop and disease key, or empty string if unclear),
confidence ('low', 'medium', or 'high'), symptoms (observed signs as a string),
is_fungal (true or false), what_i_see (only visible image observations),
photo_shows (string), and description_mismatch (true or false).
Use low confidence and disease='unclear' if the image is blurry, poorly lit, does not
clearly show a plant/leaf, or evidence cannot distinguish a possible issue."""


def _json_object(text: str | None) -> dict[str, Any]:
    if not text:
        return {"error": "diagnosis failed: Gemini returned an empty response"}
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        return {"error": f"diagnosis failed: Gemini did not return valid JSON ({error})"}
    if isinstance(value, list):
        value = value[0] if value and isinstance(value[0], dict) else {}
    if not isinstance(value, dict):
        return {"error": "diagnosis failed: Gemini did not return a JSON object"}
    required_strings = (
        "crop",
        "disease",
        "disease_key",
        "confidence",
        "symptoms",
        "what_i_see",
        "photo_shows",
    )
    if any(not isinstance(value.get(key), str) for key in required_strings):
        return {"error": "diagnosis failed: required diagnosis fields are missing or invalid"}
    if value["confidence"].casefold() not in {"low", "medium", "high"}:
        return {"error": "diagnosis failed: confidence must be low, medium, or high"}
    if not isinstance(value.get("is_fungal"), bool):
        return {"error": "diagnosis failed: is_fungal must be a boolean"}
    if not isinstance(value.get("description_mismatch"), bool):
        return {"error": "diagnosis failed: description_mismatch must be a boolean"}
    return value


def diagnose(image_path: str, description: str = "") -> str:
    """Return one JSON object as text; errors are returned in the same JSON shape."""
    try:
        path = Path(image_path)
        if not path.is_absolute():
            path = BASE / path
        path = path.resolve()
        if not path.is_file():
            return json.dumps({"error": f"image not found: {path}"})
        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type or not mime_type.startswith("image/"):
            return json.dumps({"error": f"unsupported image type: {path.suffix or 'unknown'}"})

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return json.dumps({"error": "GEMINI_API_KEY is missing from the environment or .env"})
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=30_000),
        )
        image_bytes = path.read_bytes()
        response = generate_content_with_retry(
            client.models.generate_content,
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                PROMPT.format(desc=description),
            ],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        out = _json_object(response.text)
        if out.get("error"):
            return json.dumps(out, ensure_ascii=False)

        conf = out["confidence"].casefold()

        def _words(s):
            return set(re.findall(r"[a-z]{4,}", str(s).lower()))

        sym = out.get("symptoms")
        sym_text = " ".join(map(str, sym)) if isinstance(sym, list) else str(sym or "")
        a, b = _words(sym_text), _words(description)
        if a and b and len(a & b) / len(a | b) > 0.4:
            out["symptoms_copied"] = True
            out["symptoms"] = ""
            if conf == "high":
                out["confidence"], conf = "medium", "medium"
        if out.get("description_mismatch") and conf == "high":
            out["confidence"] = "medium"
        return json.dumps(out, ensure_ascii=False)
    except Exception as error:
        return json.dumps({"error": f"diagnosis failed: {error}"}, ensure_ascii=False)


if __name__ == "__main__":
    import sys

    image = sys.argv[1] if len(sys.argv) > 1 else ""
    description = sys.argv[2] if len(sys.argv) > 2 else ""
    print(diagnose(image, description))
