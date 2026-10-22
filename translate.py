# translate.py
import re
import json
import glob
import httpx

# ---------- Languages ----------
LANGS = {"en": "English", "hi": "Hindi", "gu": "Gujarati",
         "mr": "Marathi", "pa": "Punjabi", "te": "Telugu"}

# Unicode ranges for each script (used if the UI language isn't sent)
SCRIPTS = {"gu": (0x0A80, 0x0AFF), "pa": (0x0A00, 0x0A7F),
           "te": (0x0C00, 0x0C7F), "hi": (0x0900, 0x097F)}  # Devanagari: hi/mr


def detect_lang(text: str, ui_lang: str | None = None) -> str:
    if ui_lang and ui_lang in LANGS:
        return ui_lang
    for lang, (lo, hi) in SCRIPTS.items():
        if sum(lo <= ord(c) <= hi for c in text) > 2:
            return lang
    return "en"


# ---------- Translator ----------
class OllamaTranslator:
    def __init__(self, model="qwen3:8b", url="http://localhost:11434"):
        self.model = model
        self.url = url

    def translate(self, text: str, src: str, tgt: str) -> str:
        if src == tgt or not text.strip():
            return text
        prompt = (
            f"Translate the following text from {LANGS[src]} to {LANGS[tgt]}. "
            f"Words like ZZ0ZZ, ZZ1ZZ are placeholders: copy them exactly, unchanged. "
            f"Output only the translation, nothing else.\n\n{text}"
        )
        try:
            r = httpx.post(
                f"{self.url}/api/generate",
                timeout=25,
                json={"model": self.model, "prompt": prompt, "stream": False,
                      "think": False, "options": {"temperature": 0}},
            )
            r.raise_for_status()
            out = r.json().get("response", "")
            out = re.sub(r"<think>.*?</think>", "", out, flags=re.DOTALL)  # safety net
            return out.strip() or text
        except Exception:
            return text


translator = OllamaTranslator()


def to_english(text: str, lang: str) -> str:
    return translator.translate(text, lang, "en")


def from_english(text: str, lang: str) -> str:
    return translator.translate(text, "en", lang)


# ---------- Protect safety-critical terms ----------
KNOWN_TERMS = ["Trichogramma", "Bacillus thuringiensis", "neem oil",
               "Kisan Call Centre", "1800-180-1551"]

DOSE_PATTERN = re.compile(
    r"\d+(?:\.\d+)?\s?(?:ml|g|kg|l|litre|liter|gm|%|ppm)"
    r"(?:\s?/\s?(?:litre|liter|l|ha|acre|hectare))?",
    re.IGNORECASE,
)


def load_terms_from_knowledge(folder="knowledge"):
    """Adds any 'name' or 'chemical'-like values from your JSON files."""
    found = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("chemical", "active_ingredient", "product") and isinstance(v, str):
                    found.add(v)
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    for path in glob.glob(f"{folder}/*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                walk(json.load(f))
        except Exception:
            pass
    return list(found)


KNOWN_TERMS += load_terms_from_knowledge()


def collect_protected_terms(answer_en: str) -> list[str]:
    terms = [t for t in KNOWN_TERMS if t.lower() in answer_en.lower()]
    terms += DOSE_PATTERN.findall(answer_en)
    return terms


def protect(text: str, terms: list[str]):
    mapping = {}
    for i, term in enumerate(sorted(set(terms), key=len, reverse=True)):
        key = f"ZZ{i}ZZ"
        if term in text:
            text = text.replace(term, key)
            mapping[key] = term
    return text, mapping


def restore(text: str, mapping: dict) -> str:
    for key, term in mapping.items():
        text = text.replace(key, term)
    return text