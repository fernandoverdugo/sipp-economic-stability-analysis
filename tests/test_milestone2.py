import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from assets import load_assets, validate_assets
from validate_schemas import (
    LONGITUDINAL_REPLICATE_REQUIRED,
    LONGITUDINAL_WEIGHT_REQUIRED,
    PRIMARY_REQUIRED,
)


def test_asset_registry_has_verified_longitudinal_files():
    assets = load_assets()["assets"]
    types = {asset["asset_type"] for asset in assets}
    assert "two_year_longitudinal_weights" in types
    assert "two_year_longitudinal_replicate_weights" in types


def test_large_assets_are_excluded_from_routine_downloads():
    assets = load_assets()["assets"]
    zip_assets = [asset for asset in assets if asset["local_name"].endswith(".zip")]
    assert zip_assets
    assert all(asset["large"] for asset in zip_assets)


def test_asset_registry_rejects_non_census_url():
    payload = load_assets()
    payload["assets"][0]["url"] = "https://example.com/file.zip"
    try:
        validate_assets(payload)
    except ValueError as exc:
        assert "official Census URL" in str(exc)
    else:
        raise AssertionError("Expected non-Census asset URL to fail validation.")


def test_primary_schema_requirements_include_linkage_and_poverty():
    assert {"SSUID", "PNUM", "TFCYINCPOV"} <= PRIMARY_REQUIRED


def test_longitudinal_weight_schema_requirements_are_explicit():
    assert LONGITUDINAL_WEIGHT_REQUIRED == {"SSUID", "PNUM", "SPANEL", "FINYR2"}


def test_replicate_schema_requires_full_weight_and_design_metadata():
    assert {"REPWGT0", "LGTWTTYP", "INITIAL_YEAR", "FINAL_YEAR"} <= LONGITUDINAL_REPLICATE_REQUIRED
