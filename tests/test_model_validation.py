import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from validate_models import calibration_bins, summarize


def test_summarize_reports_distribution():
    result = summarize([1.0, 2.0, 3.0])
    assert result["mean"] == 2.0
    assert result["min"] == 1.0
    assert result["max"] == 3.0
    assert result["std"] > 0


def test_calibration_bins_cover_all_rows():
    y = np.array([0, 0, 1, 1, 0, 1], dtype=int)
    p = np.array([0.1, 0.2, 0.3, 0.6, 0.7, 0.9], dtype=float)

    bins = calibration_bins(y, p, bins=3)

    assert len(bins) == 3
    assert sum(item["rows"] for item in bins) == len(y)
    assert all(0 <= item["mean_predicted"] <= 1 for item in bins)
    assert all(0 <= item["observed_rate"] <= 1 for item in bins)


def test_weighted_calibration_bins_accept_weights():
    y = np.array([0, 1, 0, 1], dtype=int)
    p = np.array([0.1, 0.2, 0.8, 0.9], dtype=float)
    w = np.array([1.0, 2.0, 3.0, 4.0])

    bins = calibration_bins(y, p, sample_weight=w, bins=2)

    assert len(bins) == 2
    assert bins[0]["rows"] == 2
    assert bins[1]["rows"] == 2
