import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from benchmark_boosting import build_boosting_pipeline


def test_boosting_pipeline_uses_expected_estimator():
    contract = {
        "predictors": [
            {"feature": "x1", "type": "continuous"},
            {"feature": "x2", "type": "categorical"},
        ]
    }

    pipeline = build_boosting_pipeline(contract, seed=699)
    model = pipeline.named_steps["model"]

    assert model.learning_rate == 0.05
    assert model.max_iter == 200
    assert model.max_leaf_nodes == 15
    assert model.l2_regularization == 1.0
