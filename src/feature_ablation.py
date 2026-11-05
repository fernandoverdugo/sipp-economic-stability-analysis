import json
from copy import deepcopy
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from train_baselines import build_pipeline, load_matrix, make_task
from validate_models import load_weights, metric_set, summarize, task_weights


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data" / "metadata"
REPEATS = 10
TEST_SIZE = 0.25
SEEDS = [699 + index for index in range(REPEATS)]

ABLATIONS = {
    "full": [],
    "without_baseline_poverty_ratio": [
        "baseline_poverty_ratio",
    ],
    "without_income_resources": [
        "annual_person_earnings",
        "annual_person_income",
        "baseline_poverty_ratio",
    ],
    "without_assets": [
        "person_net_worth",
        "person_assets",
        "person_debt",
    ],
    "without_safety_net_housing": [
        "housing_tenure",
        "housing_assistance_status",
        "snap_received_year",
    ],
    "without_demographics": [
        "age",
        "sex",
        "race",
        "hispanic_origin",
        "born_in_us",
        "citizenship",
    ],
    "without_demographics_and_assets": [
        "age",
        "sex",
        "race",
        "hispanic_origin",
        "born_in_us",
        "citizenship",
        "person_net_worth",
        "person_assets",
        "person_debt",
    ],
}


def reduced_matrix_contract(X, contract, excluded):
    keep = [
        index
        for index, predictor in enumerate(contract["predictors"])
        if predictor["feature"] not in excluded
    ]
    reduced = deepcopy(contract)
    reduced["predictors"] = [
        contract["predictors"][index]
        for index in keep
    ]
    return X[:, keep], reduced


def evaluate_variant(
    task_X,
    task_groups,
    y,
    task_weight,
    contract,
):
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
            "weighted": metric_set(
                y[test_index],
                probability,
                sample_weight=task_weight[test_index],
            ),
        })

    return {
        metric: summarize([
            run["weighted"][metric]
            for run in runs
        ])
        for metric in (
            "roc_auc",
            "average_precision",
            "brier_score",
            "log_loss",
        )
    }


def evaluate_task(
    X,
    groups,
    transitions,
    baseline_poverty,
    weights,
    contract,
    task,
):
    task_weight = task_weights(weights, baseline_poverty, task)
    result = {}

    for name, excluded in ABLATIONS.items():
        reduced_X, reduced_contract = reduced_matrix_contract(
            X,
            contract,
            excluded,
        )
        task_X, task_groups, y = make_task(
            reduced_X,
            groups,
            transitions,
            baseline_poverty,
            task,
        )
        result[name] = {
            "excluded_features": excluded,
            "remaining_features": len(reduced_contract["predictors"]),
            "weighted_metrics": evaluate_variant(
                task_X,
                task_groups,
                y,
                task_weight,
                reduced_contract,
            ),
        }

    full = result["full"]["weighted_metrics"]
    for name, item in result.items():
        metrics = item["weighted_metrics"]
        item["change_from_full"] = {
            metric: (
                metrics[metric]["mean"]
                - full[metric]["mean"]
            )
            for metric in (
                "roc_auc",
                "average_precision",
                "brier_score",
                "log_loss",
            )
        }

    return result


def main():
    X, groups, transitions, baseline_poverty, contract = load_matrix()
    weights = load_weights()

    result = {
        "contract_version": contract["version"],
        "method": {
            "split_method": "10 repeated GroupShuffleSplit by SSUID",
            "weight": "FINYR2",
            "model": "weighted regularized logistic regression",
            "ablations": ABLATIONS,
            "hyperparameter_retuning": False,
        },
        "tasks": {
            task: evaluate_task(
                X,
                groups,
                transitions,
                baseline_poverty,
                weights,
                contract,
                task,
            )
            for task in ("poverty_entry", "poverty_exit")
        },
    }

    METADATA.mkdir(parents=True, exist_ok=True)
    (METADATA / "feature_ablation.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
