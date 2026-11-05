import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from train_baselines import grouped_split, make_task


def test_grouped_split_keeps_households_separate():
    X = np.arange(24, dtype=float).reshape(12, 2)
    y = np.array([0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0])
    groups = np.array(["a","a","b","b","c","c","d","d","e","e","f","f"])

    train_index, test_index = grouped_split(X, y, groups)

    assert not (
        set(groups[train_index])
        & set(groups[test_index])
    )


def test_make_task_constructs_entry_and_exit_targets():
    X = np.arange(20, dtype=float).reshape(5, 4)
    groups = np.array(["a", "b", "c", "d", "e"])
    transitions = np.array([
        "stable_above_poverty",
        "entered_poverty",
        "exited_poverty",
        "persistent_poverty",
        "stable_above_poverty",
    ])
    baseline = np.array([False, False, True, True, False])

    entry_X, entry_groups, entry_y = make_task(
        X,
        groups,
        transitions,
        baseline,
        "poverty_entry",
    )
    exit_X, exit_groups, exit_y = make_task(
        X,
        groups,
        transitions,
        baseline,
        "poverty_exit",
    )

    assert len(entry_X) == 3
    assert entry_groups.tolist() == ["a", "b", "e"]
    assert entry_y.tolist() == [0, 1, 0]

    assert len(exit_X) == 2
    assert exit_groups.tolist() == ["c", "d"]
    assert exit_y.tolist() == [1, 0]
