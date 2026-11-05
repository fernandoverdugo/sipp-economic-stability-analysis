import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from feature_ablation import reduced_matrix_contract


def test_reduced_matrix_contract_removes_named_feature():
    X = np.arange(12, dtype=float).reshape(4, 3)
    contract = {
        "predictors": [
            {"feature": "a", "type": "continuous"},
            {"feature": "b", "type": "continuous"},
            {"feature": "c", "type": "continuous"},
        ]
    }

    reduced_X, reduced_contract = reduced_matrix_contract(
        X,
        contract,
        ["b"],
    )

    assert reduced_X.shape == (4, 2)
    assert [
        item["feature"]
        for item in reduced_contract["predictors"]
    ] == ["a", "c"]
