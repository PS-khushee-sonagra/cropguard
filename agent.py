"""Interactive CLI entry point that shares the guarded Streamlit agent loop."""

import asyncio
import re
import time
from pathlib import Path
from typing import Any

from agent_core import chat_turn, new_context

BASE = Path(__file__).resolve().parent
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

def _image_from_message(message: str) -> str | None:
    """Find a farmer-provided image path token without guessing a path."""
    for token in re.findall(r"""(?:"[^"]+"|'[^']+'|\S+)""", message):
        candidate = token.strip("\"'").rstrip(".,;)")
        path = Path(candidate)
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if not path.is_absolute():
            path = BASE / path
        return str(path.resolve())
    return None


async def main() -> None:
    crop = "Not sure"
    conversation: dict[str, Any] = {
        "crop": crop,
        "context": new_context(crop),
        "memory": [],
        "created": time.time(),
    }
    print("Crop Guard CLI")
    print("Describe a crop concern. Include an image path such as Uploads\\tomato.webp.")
    print("Type 'exit' to finish.")

    while True:
        try:
            message = input("\nFarmer: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.lower() in {"exit", "quit"}:
            break
        if not message:
            continue

        image_path = _image_from_message(message)
        try:
            result = await chat_turn(
                conversation,
                message,
                image_path,
                on_step=lambda step: print(f"[Agent] {step}"),
            )
            print("\nCrop Guard:\n" + result["reply"])
        except Exception as error:
            print(f"\nCrop Guard could not complete the request: {type(error).__name__}: {error}")


if __name__ == "__main__":
    asyncio.run(main())
