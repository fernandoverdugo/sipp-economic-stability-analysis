import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validate_policy_model import policy_matrix_contract


def test_policy_matrix_contract_selects_exact_features():
    X = np.arange(20, dtype=float).reshape(5, 4)
    contract = {
        "predictors": [
            {"feature": "a", "type": "continuous"},
            {"feature": "b", "type": "continuous"},
            {"feature": "c", "type": "continuous"},
            {"feature": "d", "type": "continuous"},
        ]
    }
    policy = {
        "model_features": ["b", "d"],
    }

    reduced_X, reduced_contract = policy_matrix_contract(
        X,
        contract,
        policy,
    )

    assert reduced_X.shape == (5, 2)
    assert [
        item["feature"]
        for item in reduced_contract["predictors"]
    ] == ["b", "d"]


def test_policy_config_separates_prediction_and_audit_features():
    policy = json.loads(
        (ROOT / "config" / "policy_model.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(policy["model_features"]).isdisjoint(
        policy["audit_only_features"]
    )
