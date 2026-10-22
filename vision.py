# vision.py
import base64, io, json, re
import httpx
from PIL import Image

VISION_MODEL = "qwen2.5vl:7b"
OLLAMA_URL = "http://localhost:11434"

PROMPT = """You are looking at a photo of a crop plant taken by a farmer.
Describe ONLY what is visible in THIS photo. Do NOT name any disease or pest.
Do NOT copy wording from these instructions; describe what you actually see.
Reply with JSON only, in exactly this format:
{
  "crop_visible": "cotton | tomato | wheat | other | unclear",
  "plant_part": "leaf | stem | fruit | boll | flower | root | whole_plant | unclear",
  "symptoms": ["2 to 5 short phrases about what is visible"],
  "spot_color": "color of any spots, lesions or coating, or empty string",
  "spot_shape_and_size": "shape and approximate size, or empty string",
  "pattern": "where on the plant and how spread, e.g. old or new leaves, edges, veins, or empty string",
  "insects_visible": true or false,
  "insect_description": "size, color, location, or empty string",
  "image_quality": "good | poor",
  "notes": "visual observations only, or empty string"
}
If the photo is blurry, dark, or not a plant, set image_quality to "poor"."""


def prepare_image(data: bytes, max_side: int = 640) -> str:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def describe_image(data: bytes, crop_hint: str | None = None, timeout: float = 300.0) -> dict:
    try:
        b64 = prepare_image(data)
    except Exception as e:
        return {
            "image_quality": "poor", "symptoms": [], "crop_visible": "unclear",
            "plant_part": "unclear", "insects_visible": False,
            "insect_description": "", "notes": f"Invalid image format: {e}"
        }

    prompt = PROMPT
    if crop_hint:
        prompt += f"\nThe farmer says this is a {crop_hint} plant."

    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            timeout=timeout,
            json={
                "model": VISION_MODEL,
                "stream": False,
                "format": "json",
                "keep_alive": "30m",
                "options": {"temperature": 0},
                "messages": [{"role": "user", "content": prompt, "images": [b64]}],
            },
        )
        r.raise_for_status()
        raw = r.json().get("message", {}).get("content", "")
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        obs = json.loads(raw)
    except Exception as err:
        return {
            "image_quality": "poor",
            "crop_visible": crop_hint or "unclear",
            "plant_part": "unclear",
            "symptoms": [],
            "spot_color": "",
            "spot_shape_and_size": "",
            "pattern": "",
            "insects_visible": False,
            "insect_description": "",
            "notes": f"Vision analysis failed or timed out: {err}",
        }

    obs.setdefault("symptoms", [])
    obs.setdefault("image_quality", "good")
    obs.setdefault("crop_visible", crop_hint or "unclear")
    return obs


def observation_to_text(obs: dict) -> str:
    parts = []
    if obs.get("plant_part") not in (None, "unclear"):
        parts.append(f"on the {obs['plant_part']}")
    parts += [s for s in obs.get("symptoms", []) if isinstance(s, str)]
    for key in ("spot_color", "spot_shape_and_size", "pattern"):
        if obs.get(key):
            parts.append(str(obs[key]))
    if obs.get("insects_visible") and obs.get("insect_description"):
        parts.append(f"insects: {obs['insect_description']}")
    return ", ".join(parts)