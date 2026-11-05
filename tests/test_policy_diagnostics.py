import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from policy_diagnostics import age_band, risk_concentration


def test_age_band_boundaries():
    assert age_band(18) == "18-29"
    assert age_band(30) == "30-44"
    assert age_band(45) == "45-59"
    assert age_band(60) == "60-74"
    assert age_band(75) == "75+"


def test_risk_concentration_captures_highest_risk_first():
    y = np.array([1, 0, 1, 0, 0, 1, 0, 0, 0, 0])
    p = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05])
    w = np.ones(len(y))

    result = risk_concentration(y, p, w)

    assert result["top_10pct"]["rows"] == 1
    assert result["top_10pct"]["positive_captured"] == 1
    assert result["top_20pct"]["rows"] == 2
    assert result["top_20pct"]["positive_captured"] == 1
