import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_panel import collapse_records, valid_poverty


def test_person_year_collapse_requires_consistent_annual_poverty():
    rows = [
        {
            "SSUID": "1",
            "PNUM": "1",
            "MONTHCODE": "1",
            "TFCYINCPOV": "0.8",
            "AFCYINCPOV": "0",
            "TAGE": "40",
        },
        {
            "SSUID": "1",
            "PNUM": "1",
            "MONTHCODE": "2",
            "TFCYINCPOV": "1.2",
            "AFCYINCPOV": "0",
            "TAGE": "40",
        },
    ]
    try:
        collapse_records(rows, 2024)
    except RuntimeError as exc:
        assert "inconsistent TFCYINCPOV" in str(exc)
    else:
        raise AssertionError("Expected inconsistent annual poverty ratio to fail.")


def test_person_year_collapse_produces_unique_person_key():
    rows = [
        {
            "SSUID": "1",
            "PNUM": "1",
            "MONTHCODE": "1",
            "TFCYINCPOV": "0.8",
            "AFCYINCPOV": "0",
            "TAGE": "40",
        },
        {
            "SSUID": "1",
            "PNUM": "1",
            "MONTHCODE": "12",
            "TFCYINCPOV": "0.8",
            "AFCYINCPOV": "0",
            "TAGE": "40",
        },
        {
            "SSUID": "2",
            "PNUM": "1",
            "MONTHCODE": "1",
            "TFCYINCPOV": "2.0",
            "AFCYINCPOV": "0",
            "TAGE": "25",
        },
        {
            "SSUID": "2",
            "PNUM": "1",
            "MONTHCODE": "12",
            "TFCYINCPOV": "2.0",
            "AFCYINCPOV": "0",
            "TAGE": "25",
        },
    ]
    result = collapse_records(rows, 2024)
    assert len(result) == 2
    assert result[("1", 1)]["month_count"] == 2
    assert result[("2", 1)]["poverty_ratio"] == 2.0


def test_valid_poverty_excludes_negative_codes():
    assert valid_poverty(0.0)
    assert valid_poverty(0.9)
    assert valid_poverty(1.2)
    assert not valid_poverty(-1.0)
    assert not valid_poverty(None)
