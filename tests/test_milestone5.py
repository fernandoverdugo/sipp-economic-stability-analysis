import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validate_predictors import required_variables, validate_contract


def test_predictor_contract_has_no_followup_sources():
    contract = json.loads(
        (ROOT / "config" / "predictors.json").read_text(encoding="utf-8")
    )
    assert contract["rules"]["baseline_only"]
    assert contract["rules"]["prohibit_followup_predictors"]


def test_predictor_contract_excludes_identifiers_as_features():
    contract = json.loads(
        (ROOT / "config" / "predictors.json").read_text(encoding="utf-8")
    )
    feature_sources = required_variables(contract)
    assert "SSUID" not in feature_sources
    assert "PNUM" not in feature_sources
    assert "FINYR2" not in feature_sources
    assert "REPWGT0" not in feature_sources


def test_schema_validation_reports_missing_variables():
    contract = {
        "version": "test",
        "baseline_release": 2024,
        "outcome_release": 2025,
        "predictors": [
            {"feature": "age", "source": ["TAGE"]},
            {"feature": "missing", "source": ["MISSING_VARIABLE"]},
        ],
    }
    schemas = {
        2024: {"TAGE": {"label": "Age", "dtype": "integer"}},
        2025: {"TAGE": {"label": "Age", "dtype": "integer"}},
    }
    result = validate_contract(contract, schemas)
    assert not result["all_variables_present_in_both_releases"]
    assert result["schemas"]["2024"]["missing"] == ["MISSING_VARIABLE"]
    assert result["schemas"]["2025"]["missing"] == ["MISSING_VARIABLE"]
