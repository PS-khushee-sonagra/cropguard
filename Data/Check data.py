import json
from pathlib import Path

REQUIRED = ["crop", "symptoms", "organic_control", "chemical_control", "prevention", "sources"]

for f in sorted((Path(__file__).parent / "Data").glob("*.json")):
    try:
        data = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print(f"BROKEN FILE {f.name}: {e}")
        continue
    for k, v in data.items():
        missing = [r for r in REQUIRED if not v.get(r)]
        if not k.startswith(f.stem):
            print(f"{f.name}: key '{k}' should start with '{f.stem}'")
        if missing:
            print(f"{f.name}: '{k}' is missing {missing}")
        if v.get("verified_by", "not yet") == "not yet":
            print(f"{f.name}: '{k}' is not yet reviewed by an expert")
        for p in v.get("registered_products", []):
            if not (p.get("source") and p.get("date_checked")):
                print(f"{f.name}: '{k}' has a product row without source or date")
print("Check finished.")