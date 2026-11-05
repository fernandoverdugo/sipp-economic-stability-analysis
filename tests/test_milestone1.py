import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cohort import poverty_transition
from registry import load_registry, validate_registry
from source_discovery import classify_asset


def test_registry_contains_required_sipp_releases():
    registry = load_registry()
    years = {source["survey_year"] for source in registry["sources"]}
    assert years == {2024, 2025}


def test_followup_release_requires_longitudinal_assets():
    registry = load_registry()
    source = next(
        source for source in registry["sources"]
        if source["survey_year"] == 2025
    )
    assert "two_year_longitudinal_weights" in source["required_assets"]
    assert "two_year_longitudinal_replicate_weights" in source["required_assets"]


def test_registry_rejects_non_census_source():
    registry = load_registry()
    registry["sources"][0]["url"] = "https://example.com/data"
    try:
        validate_registry(registry)
    except ValueError as exc:
        assert "Census" in str(exc)
    else:
        raise AssertionError("Expected non-Census source to fail validation.")


def test_poverty_transition_states():
    assert poverty_transition(False, False) == "stable_above_poverty"
    assert poverty_transition(False, True) == "entered_poverty"
    assert poverty_transition(True, False) == "exited_poverty"
    assert poverty_transition(True, True) == "persistent_poverty"


def test_asset_classification():
    assert classify_asset(
        "Download 2025 SIPP pipe-delimited 2-year longitudinal weights",
        "weights.zip",
    ) == "two_year_longitudinal_weights"

    assert classify_asset(
        "Download 2025 SIPP pipe-delimited 2-year longitudinal replicate weights",
        "repweights.zip",
    ) == "two_year_longitudinal_replicate_weights"

    assert classify_asset(
        "Data Dictionary",
        "dictionary.txt",
    ) == "data_dictionary"
