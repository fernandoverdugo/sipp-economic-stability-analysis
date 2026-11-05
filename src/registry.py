import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "source_registry.json"


def load_registry(path=REGISTRY_PATH):
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_registry(registry)
    return registry


def validate_registry(registry):
    if registry.get("version") != "0.1":
        raise ValueError("Expected source registry version 0.1.")

    sources = registry.get("sources", [])
    if len(sources) < 2:
        raise ValueError("At least two SIPP releases are required.")

    required = {
        "source_id",
        "survey_year",
        "reference_period",
        "role",
        "authority",
        "title",
        "url",
        "required_assets",
    }

    ids = set()
    years = set()

    for source in sources:
        missing = required - set(source)
        if missing:
            raise ValueError(f"Source missing fields: {sorted(missing)}")
        if source["source_id"] in ids:
            raise ValueError(f"Duplicate source_id: {source['source_id']}")
        if source["survey_year"] in years:
            raise ValueError(f"Duplicate survey_year: {source['survey_year']}")
        if not source["url"].startswith("https://www.census.gov/"):
            raise ValueError(f"Source is not a Census HTTPS URL: {source['source_id']}")

        ids.add(source["source_id"])
        years.add(source["survey_year"])

    if {2024, 2025} - years:
        raise ValueError("The initial longitudinal design requires 2024 and 2025 SIPP.")
