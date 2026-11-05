import json
from pathlib import Path

from assets import load_assets


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "metadata" / "schema_validation.json"


PRIMARY_REQUIRED = {
    "SSUID",
    "PNUM",
    "TFCYINCPOV",
}

LONGITUDINAL_WEIGHT_REQUIRED = {
    "SSUID",
    "PNUM",
    "SPANEL",
    "FINYR2",
}

LONGITUDINAL_REPLICATE_REQUIRED = {
    "SSUID",
    "PNUM",
    "SPANEL",
    "CTL_DATE",
    "LGTWTTYP",
    "INITIAL_YEAR",
    "FINAL_YEAR",
    "REPWGT0",
}


def names_from_schema(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [row["name"] for row in payload]


def schema_asset(asset_type, survey_year=None):
    assets = load_assets()["assets"]
    matches = [
        asset
        for asset in assets
        if asset["asset_type"] == asset_type
        and (survey_year is None or asset["survey_year"] == survey_year)
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one {asset_type} asset for {survey_year}; found {len(matches)}."
        )
    return RAW / matches[0]["local_name"]


def require(names, required, label):
    missing = sorted(required - set(names))
    if missing:
        raise RuntimeError(f"{label} missing required variables: {missing}")


def main():
    results = {"primary": {}, "longitudinal_weight": {}, "longitudinal_replicate": {}}

    for year in (2024, 2025):
        path = schema_asset("primary_schema", year)
        names = names_from_schema(path)
        require(names, PRIMARY_REQUIRED, f"{year} primary schema")
        results["primary"][str(year)] = {
            "variables": len(names),
            "required_found": sorted(PRIMARY_REQUIRED),
        }

    weight_names = names_from_schema(
        schema_asset("longitudinal_weight_schema", 2025)
    )
    require(
        weight_names,
        LONGITUDINAL_WEIGHT_REQUIRED,
        "2025 two-year longitudinal-weight schema",
    )
    results["longitudinal_weight"] = {
        "variables": len(weight_names),
        "required_found": sorted(LONGITUDINAL_WEIGHT_REQUIRED),
    }

    replicate_names = names_from_schema(
        schema_asset("longitudinal_replicate_schema", 2025)
    )
    require(
        replicate_names,
        LONGITUDINAL_REPLICATE_REQUIRED,
        "2025 two-year longitudinal replicate schema",
    )

    expected_replicates = {f"REPWGT{i}" for i in range(1, 241)}
    missing_replicates = sorted(expected_replicates - set(replicate_names))
    if missing_replicates:
        raise RuntimeError(
            f"Missing longitudinal replicate weights: {missing_replicates[:10]}"
        )

    results["longitudinal_replicate"] = {
        "variables": len(replicate_names),
        "replicate_weights": 240,
        "full_weight": "REPWGT0",
        "required_found": sorted(LONGITUDINAL_REPLICATE_REQUIRED),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
