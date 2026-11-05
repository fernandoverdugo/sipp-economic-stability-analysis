import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from train_baselines import build_pipeline, load_matrix, make_task
from validate_models import (
    calibration_intercept_slope,
    load_weights,
    metric_set,
    summarize,
    task_weights,
)


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data" / "metadata"
POLICY_CONFIG = ROOT / "config" / "policy_model.json"
REPEATS = 10
TEST_SIZE = 0.25
SEEDS = [699 + index for index in range(REPEATS)]


def policy_matrix_contract(X, contract, policy_config):
    allowed = set(policy_config["model_features"])
    keep = [
        index
        for index, predictor in enumerate(contract["predictors"])
        if predictor["feature"] in allowed
    ]
    reduced_X = X[:, keep]
    reduced_contract = dict(contract)
    reduced_contract["predictors"] = [
        contract["predictors"][index]
        for index in keep
    ]
    names = [
        predictor["feature"]
        for predictor in reduced_contract["predictors"]
    ]
    expected = policy_config["model_features"]
    if set(names) != set(expected):
        raise RuntimeError(
            "Policy model feature set does not match the predictor contract."
        )
    return reduced_X, reduced_contract


def evaluate_task(
    X,
    groups,
    transitions,
    baseline_poverty,
    weights,
    contract,
    task,
):
    task_X, task_groups, y = make_task(
        X,
        groups,
        transitions,
        baseline_poverty,
        task,
    )
    task_weight = task_weights(weights, baseline_poverty, task)
    runs = []

    for seed in SEEDS:
        splitter = GroupShuffleSplit(
            n_splits=1,
            test_size=TEST_SIZE,
            random_state=seed,
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

        runs.append({
            "seed": seed,
            "test_rows": int(len(test_index)),
            "test_positive": int(y[test_index].sum()),
            "unweighted": metric_set(
                y[test_index],
                probability,
            ),
            "weighted": metric_set(
                y[test_index],
                probability,
                sample_weight=task_weight[test_index],
            ),
            "calibration_unweighted": calibration_intercept_slope(
                y[test_index],
                probability,
            ),
            "calibration_weighted": calibration_intercept_slope(
                y[test_index],
                probability,
                sample_weight=task_weight[test_index],
            ),
        })

    return {
        "sample": {
            "rows": int(len(y)),
            "positive": int(y.sum()),
            "unweighted_prevalence": float(y.mean()),
            "weighted_prevalence": float(
                np.average(y, weights=task_weight)
            ),
        },
        "repeats": REPEATS,
        "metrics": {
            weighting: {
                metric: summarize([
                    run[weighting][metric]
                    for run in runs
                ])
                for metric in (
                    "roc_auc",
                    "average_precision",
                    "brier_score",
                    "log_loss",
                )
            }
            for weighting in ("unweighted", "weighted")
        },
        "calibration": {
            weighting: {
                "intercept": summarize([
                    run[f"calibration_{weighting}"]["intercept"]
                    for run in runs
                ]),
                "slope": summarize([
                    run[f"calibration_{weighting}"]["slope"]
                    for run in runs
                ]),
            }
            for weighting in ("unweighted", "weighted")
        },
        "runs": runs,
    }


def main():
    X, groups, transitions, baseline_poverty, contract = load_matrix()
    weights = load_weights()
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
        "feature_count": len(policy_contract["predictors"]),
        "features": [
            predictor["feature"]
            for predictor in policy_contract["predictors"]
        ],
        "evaluation": {
            "split_method": "10 repeated GroupShuffleSplit by SSUID",
            "test_group_share": TEST_SIZE,
            "seeds": SEEDS,
            "weighted_model_fit": True,
            "weight": "FINYR2",
        },
        "tasks": {
            task: evaluate_task(
                policy_X,
                groups,
                transitions,
                baseline_poverty,
                weights,
                policy_contract,
                task,
            )
            for task in ("poverty_entry", "poverty_exit")
        },
    }

    METADATA.mkdir(parents=True, exist_ok=True)
    (METADATA / "policy_model_validation.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
