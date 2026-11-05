import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analyze_transitions import (
    confidence_interval,
    fay_variance,
    full_sample_estimates,
)


def test_fay_variance_uses_documented_scale():
    full = 0.5
    replicates = [0.4, 0.6, 0.45, 0.55]
    observed = fay_variance(full, replicates, coefficient=0.5)
    expected = sum((value - full) ** 2 for value in replicates) / (
        4 * 0.5 ** 2
    )
    assert math.isclose(observed, expected)


def test_confidence_interval_is_bounded_for_proportions():
    lower, upper = confidence_interval(0.01, 0.02)
    assert lower == 0.0
    assert 0.01 < upper < 1.0

    lower, upper = confidence_interval(0.99, 0.02)
    assert 0.0 < lower < 0.99
    assert upper == 1.0


def test_full_sample_transition_estimands():
    cohort = {
        ("a", 1): {
            "transition": "stable_above_poverty",
            "poverty_2024": False,
            "poverty_2025": False,
            "FINYR2": 2.0,
        },
        ("b", 1): {
            "transition": "entered_poverty",
            "poverty_2024": False,
            "poverty_2025": True,
            "FINYR2": 1.0,
        },
        ("c", 1): {
            "transition": "exited_poverty",
            "poverty_2024": True,
            "poverty_2025": False,
            "FINYR2": 3.0,
        },
        ("d", 1): {
            "transition": "persistent_poverty",
            "poverty_2024": True,
            "poverty_2025": True,
            "FINYR2": 4.0,
        },
    }

    estimates = full_sample_estimates(cohort)

    assert math.isclose(estimates["stable_above_poverty_share"], 0.2)
    assert math.isclose(estimates["entered_poverty_share"], 0.1)
    assert math.isclose(estimates["exited_poverty_share"], 0.3)
    assert math.isclose(estimates["persistent_poverty_share"], 0.4)
    assert math.isclose(estimates["baseline_poverty_share"], 0.7)
    assert math.isclose(estimates["followup_poverty_share"], 0.5)
    assert math.isclose(
        estimates["poverty_entry_rate_among_baseline_nonpoor"],
        1.0 / 3.0,
    )
    assert math.isclose(
        estimates["poverty_exit_rate_among_baseline_poor"],
        3.0 / 7.0,
    )
