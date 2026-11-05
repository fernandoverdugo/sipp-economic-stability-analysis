import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_panel import collapse_person_year, valid_poverty


def test_person_year_collapse_requires_consistent_annual_poverty():
    frame = pd.DataFrame(
        {
            "SSUID": ["1", "1"],
            "PNUM": [1, 1],
            "MONTHCODE": [1, 2],
            "TFCYINCPOV": [0.8, 1.2],
            "AFCYINCPOV": [0, 0],
            "TAGE": [40, 40],
        }
    )
    try:
        collapse_person_year(frame, 2024)
    except RuntimeError as exc:
        assert "inconsistent annual TFCYINCPOV" in str(exc)
    else:
        raise AssertionError("Expected inconsistent annual poverty ratio to fail.")


def test_person_year_collapse_produces_unique_person_key():
    frame = pd.DataFrame(
        {
            "SSUID": ["1", "1", "2", "2"],
            "PNUM": [1, 1, 1, 1],
            "MONTHCODE": [1, 12, 1, 12],
            "TFCYINCPOV": [0.8, 0.8, 2.0, 2.0],
            "AFCYINCPOV": [0, 0, 0, 0],
            "TAGE": [40, 40, 25, 25],
        }
    )
    result = collapse_person_year(frame, 2024)
    assert len(result) == 2
    assert not result.duplicated(["SSUID", "PNUM"]).any()


def test_valid_poverty_excludes_negative_codes():
    series = pd.Series([0.0, 0.9, 1.2, -1.0, None])
    mask = valid_poverty(series)
    assert mask.tolist() == [True, True, True, False, False]
