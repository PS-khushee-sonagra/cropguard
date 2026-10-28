"""Read-only validation for the crop-specific JSON data files."""

import argparse
import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "Data"
REQUIRED_FIELDS = (
    "crop",
    "symptoms",
    "organic_control",
    "chemical_control",
    "prevention",
    "sources",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit with status 1 if any treatment entry is not expert-reviewed",
    )
    args = parser.parse_args(argv)
    unreviewed_count = 0

    for path in sorted(DATA_DIR.glob("*.json"), key=lambda item: item.name.casefold()):
        try:
            with path.open(encoding="utf-8") as file:
                data: Any = json.load(file)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, RecursionError) as error:
            print(f"BROKEN FILE {path.name}: {error}")
            continue

        if not isinstance(data, dict):
            print(f"{path.name}: top-level JSON value must be an object")
            continue

        filename_prefix = path.stem.casefold()
        for key, entry in data.items():
            if not isinstance(key, str) or not key.casefold().startswith(filename_prefix):
                print(f"{path.name}: key {key!r} should start with {filename_prefix!r}")
            if not isinstance(entry, dict):
                print(f"{path.name}: {key!r} entry must be an object")
                continue

            missing = [
                field
                for field in REQUIRED_FIELDS
                if entry.get(field) is None
                or entry.get(field) == ""
                or entry.get(field) == []
            ]
            if missing:
                print(f"{path.name}: {key!r} is missing {missing}")
            reviewer = entry.get("verified_by")
            reviewer = " ".join(reviewer.split()) if isinstance(reviewer, str) else ""
            if reviewer.casefold() in {
                "",
                "not yet",
                "not reviewed",
                "unreviewed",
                "unknown",
                "none",
                "n/a",
            }:
                unreviewed_count += 1
                print(f"{path.name}: {key!r} is not yet reviewed by an expert")

            products = entry.get("registered_products", [])
            if isinstance(products, list):
                for index, product in enumerate(products, start=1):
                    if not isinstance(product, dict) or not (
                        product.get("source") and product.get("date_checked")
                    ):
                        print(
                            f"{path.name}: {key!r} registered_products row {index} "
                            "is missing source or date_checked"
                        )

    print("Check finished.")
    return int(args.strict and unreviewed_count > 0)


if __name__ == "__main__":
    raise SystemExit(main())
