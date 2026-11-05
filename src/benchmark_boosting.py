import json
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from train_baselines import build_pipeline, load_matrix, make_task
from validate_models import load_weights, metric_set, summarize, task_weights


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data" / "metadata"
REPEATS = 10
TEST_SIZE = 0.25
SEEDS = [699 + index for index in range(REPEATS)]


def build_boosting_pipeline(contract, seed):
    continuous = [
        index
        for index, predictor in enumerate(contract["predictors"])
        if predictor["type"] == "continuous"
    ]
    categorical = [
        index
        for index, predictor in enumerate(contract["predictors"])
        if predictor["type"] != "continuous"
    ]

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
            ),
        ),
    ])

    preprocessing = ColumnTransformer([
        ("continuous", numeric_pipeline, continuous),
        ("categorical", categorical_pipeline, categorical),
    ])

    model = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=200,
        max_leaf_nodes=15,
        min_samples_leaf=20,
        l2_regularization=1.0,
        early_stopping=True,
        random_state=seed,
    )

    return Pipeline([
        ("preprocess", preprocessing),
        ("model", model),
    ])


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

        X_train = task_X[train_index]
        X_test = task_X[test_index]
        y_train = y[train_index]
        y_test = y[test_index]
        w_train = task_weight[train_index]
        w_test = task_weight[test_index]
        train_groups = task_groups[train_index]
        test_groups = task_groups[test_index]

        if set(train_groups) & set(test_groups):
            raise RuntimeError("Household overlap detected.")

        logistic = build_pipeline(contract)
        logistic.fit(
            X_train,
            y_train,
            model__sample_weight=w_train,
        )
        logistic_probability = logistic.predict_proba(X_test)[:, 1]

        boosting = build_boosting_pipeline(contract, seed)
        boosting.fit(
            X_train,
            y_train,
            model__sample_weight=w_train,
        )
        boosting_probability = boosting.predict_proba(X_test)[:, 1]

        runs.append({
            "seed": seed,
            "test_rows": int(len(test_index)),
            "test_positive": int(y_test.sum()),
            "logistic": {
                "unweighted": metric_set(
                    y_test,
                    logistic_probability,
                ),
                "weighted": metric_set(
                    y_test,
                    logistic_probability,
                    sample_weight=w_test,
                ),
            },
            "hist_gradient_boosting": {
                "unweighted": metric_set(
                    y_test,
                    boosting_probability,
                ),
                "weighted": metric_set(
                    y_test,
                    boosting_probability,
                    sample_weight=w_test,
                ),
                "iterations": int(
                    boosting.named_steps["model"].n_iter_
                ),
            },
        })

    result = {
        "sample": {
            "rows": int(len(y)),
            "positive": int(y.sum()),
        },
        "repeats": REPEATS,
        "metrics": {},
        "runs": runs,
    }

    for model in ("logistic", "hist_gradient_boosting"):
        result["metrics"][model] = {}
        for weighting in ("unweighted", "weighted"):
            result["metrics"][model][weighting] = {
                metric: summarize([
                    run[model][weighting][metric]
                    for run in runs
                ])
                for metric in (
                    "roc_auc",
                    "average_precision",
                    "brier_score",
                    "log_loss",
                )
            }

    result["mean_change_boosting_minus_logistic"] = {}
    for weighting in ("unweighted", "weighted"):
        result["mean_change_boosting_minus_logistic"][weighting] = {
            metric: (
                result["metrics"]["hist_gradient_boosting"][weighting][metric]["mean"]
                - result["metrics"]["logistic"][weighting][metric]["mean"]
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
        "comparison": {
            "split_method": "10 repeated GroupShuffleSplit by SSUID",
            "test_group_share": TEST_SIZE,
            "weight": "FINYR2",
            "logistic": "L2 regularized logistic regression",
            "boosting": {
                "estimator": "HistGradientBoostingClassifier",
                "learning_rate": 0.05,
                "max_iter": 200,
                "max_leaf_nodes": 15,
                "min_samples_leaf": 20,
                "l2_regularization": 1.0,
                "early_stopping": True,
                "hyperparameter_tuning": False,
            },
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
    (METADATA / "boosting_benchmark.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
