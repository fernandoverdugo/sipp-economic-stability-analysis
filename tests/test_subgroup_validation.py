import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validate_subgroups import aggregate_subgroups


def test_aggregate_subgroups_requires_repeated_support():
    splits = []
    for seed in range(10):
        status = "reported" if seed < 6 else "insufficient_events"
        item = {
            "rows": 100,
            "positive": 20,
            "status": status,
        }
        if status == "reported":
            item["weighted"] = {
                "roc_auc": 0.7,
                "average_precision": 0.3,
                "brier_score": 0.2,
                "log_loss": 0.6,
            }
        splits.append({
            "subgroups": {
                "sex": {
                    "1": item,
                }
            }
        })

    result = aggregate_subgroups(splits)

    assert result["sex"]["1"]["status"] == "reported"
    assert result["sex"]["1"]["reportable_splits"] == 6
    assert result["sex"]["1"]["weighted_metrics"]["roc_auc"]["mean"] == 0.7
