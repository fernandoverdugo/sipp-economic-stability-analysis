import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_features import (
    EMPLOYED_RMESR,
    UNEMPLOYED_RMESR,
    safe_mean,
    safe_sum,
    snap_any,
    unique_or_none,
)


def test_rmesr_groups_match_contract():
    assert EMPLOYED_RMESR == {1, 2, 3, 4, 5}
    assert UNEMPLOYED_RMESR == {6, 7}
    assert 8 not in EMPLOYED_RMESR
    assert 8 not in UNEMPLOYED_RMESR


def test_safe_aggregations_preserve_missingness():
    assert safe_sum([None, None]) is None
    assert safe_mean([None, None]) is None
    assert safe_sum([1.0, None, 2.0]) == 3.0
    assert safe_mean([2.0, None, 4.0]) == 3.0


def test_snap_receipt_derivation():
    assert snap_any([None, None], [None, None]) is None
    assert snap_any([0.0, 0.0], [0.0, 0.0]) == 0
    assert snap_any([0.0, 3.0], [0.0, 5.0]) == 1


def test_unique_or_none_rejects_inconsistent_annual_values():
    assert unique_or_none([1, 1, None], "X", ("a", 1)) == 1
    try:
        unique_or_none([1, 2], "X", ("a", 1))
    except RuntimeError as exc:
        assert "Inconsistent annual-constant field" in str(exc)
    else:
        raise AssertionError("Expected inconsistent annual field to fail.")
