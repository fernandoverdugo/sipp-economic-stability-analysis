import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from policy_diagnostics import (
    age_bands,
    load_feature_rows,
    subgroup_report,
    subgroup_values,
    task_mask,
)
from train_baselines import build_pipeline, load_matrix, make_task
from validate_models import load_weights, task_weights
from validate_policy_model import policy_matrix_contract


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data" / "metadata"
POLICY_CONFIG = ROOT / "config" / "policy_model.json"
SEED = 699
TEST_SIZE = 0.25


def evaluate_task(
    X,
    groups,
    transitions,
    baseline_poverty,
    weights,
    contract,
    rows,
    task,
):
    mask = task_mask(baseline_poverty, task)
    task_X, task_groups, y = make_task(
        X,
        groups,
        transitions,
        baseline_poverty,
        task,
    )
    task_weight = task_weights(weights, baseline_poverty, task)

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=TEST_SIZE,
        random_state=SEED,
    )
    train_index, test_index = next(
        splitter.split(task_X, y, task_groups)
    )

    if set(task_groups[train_index]) & set(task_groups[test_index]):
        raise RuntimeError("Household overlap detected.")

    model = build_pipeline(contract)
    model.fit(
        task_X[train_index],
        y[train_index],
        model__sample_weight=task_weight[train_index],
    )
    probability = model.predict_proba(task_X[test_index])[:, 1]

    task_rows = [row for row, keep in zip(rows, mask) if keep]
    test_rows = [task_rows[index] for index in test_index]
    keep = np.ones(len(test_rows), dtype=bool)

    subgroup_arrays = {
        "sex": subgroup_values(test_rows, keep, "sex"),
        "race": subgroup_values(test_rows, keep, "race"),
        "hispanic_origin": subgroup_values(
            test_rows,
            keep,
            "hispanic_origin",
        ),
        "born_in_us": subgroup_values(
            test_rows,
            keep,
            "born_in_us",
        ),
        "age_band": age_bands(test_rows, keep),
    }

    return {
        "holdout": {
            "seed": SEED,
            "rows": int(len(test_index)),
            "positive": int(y[test_index].sum()),
            "households": int(len(set(task_groups[test_index]))),
        },
        "subgroups": {
            name: subgroup_report(
                y[test_index],
                probability,
                task_weight[test_index],
                task_groups[test_index],
                values,
            )
            for name, values in subgroup_arrays.items()
        },
    }


def main():
    X, groups, transitions, baseline_poverty, contract = load_matrix()
    weights = load_weights()
    rows = load_feature_rows()
    policy_config = json.loads(
        POLICY_CONFIG.read_text(encoding="utf-8")
    )

    policy_X, policy_contract = policy_matrix_contract(
        X,
        contract,
        policy_config,
    )

    result = {
        "policy_model_version": policy_config["version"],
        "predictor_contract_version": contract["version"],
        "audit_only_features": policy_config["audit_only_features"],
        "tasks": {
            task: evaluate_task(
                policy_X,
                groups,
                transitions,
                baseline_poverty,
                weights,
                policy_contract,
                rows,
                task,
            )
            for task in ("poverty_entry", "poverty_exit")
        },
    }

    METADATA.mkdir(parents=True, exist_ok=True)
    (METADATA / "policy_model_subgroups.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
