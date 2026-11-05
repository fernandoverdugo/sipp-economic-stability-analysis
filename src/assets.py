import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_REGISTRY = ROOT / "config" / "assets.json"


def load_assets(path=ASSET_REGISTRY):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_assets(payload)
    return payload


def validate_assets(payload):
    if payload.get("version") != "0.2":
        raise ValueError("Expected asset registry version 0.2.")

    assets = payload.get("assets", [])
    if not assets:
        raise ValueError("Asset registry is empty.")

    required_fields = {
        "asset_id",
        "survey_year",
        "asset_type",
        "url",
        "local_name",
        "required",
        "large",
    }

    ids = set()
    names = set()
    for asset in assets:
        missing = required_fields - set(asset)
        if missing:
            raise ValueError(f"Asset missing fields: {sorted(missing)}")
        if asset["asset_id"] in ids:
            raise ValueError(f"Duplicate asset_id: {asset['asset_id']}")
        if asset["local_name"] in names:
            raise ValueError(f"Duplicate local_name: {asset['local_name']}")
        if not asset["url"].startswith("https://www2.census.gov/"):
            raise ValueError(f"Asset is not an official Census URL: {asset['asset_id']}")
        ids.add(asset["asset_id"])
        names.add(asset["local_name"])

    required_types = {
        "primary_data",
        "primary_schema",
        "data_dictionary",
        "two_year_longitudinal_weights",
        "longitudinal_weight_schema",
        "two_year_longitudinal_replicate_weights",
        "longitudinal_replicate_schema",
    }
    present_types = {asset["asset_type"] for asset in assets if asset["required"]}
    missing_types = required_types - present_types
    if missing_types:
        raise ValueError(f"Missing required asset types: {sorted(missing_types)}")
