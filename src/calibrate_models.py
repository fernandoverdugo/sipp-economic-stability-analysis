import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold

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
REPEATS = 10
OUTER_TEST_SIZE = 0.25
CALIBRATION_FOLDS = 5
SEEDS = [699 + index for index in range(REPEATS)]


def logit(probabilities):
    epsilon = 1e-6
    clipped = np.clip(probabilities, epsilon, 1 - epsilon)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def fit_sigmoid(probabilities, y, weights):
    calibrator = LogisticRegression(
        C=1e6,
        solver="lbfgs",
        max_iter=2000,
    )
    calibrator.fit(
        logit(probabilities),
        y,
        sample_weight=weights,
    )
    return calibrator


def cross_validated_calibrator(
    X,
    y,
    groups,
    weights,
    contract,
    seed,
):
    splitter = StratifiedGroupKFold(
        n_splits=CALIBRATION_FOLDS,
        shuffle=True,
        random_state=seed,
    )
    oof_probability = np.full(len(y), np.nan, dtype=float)

    for fit_index, calibration_index in splitter.split(
        X,
        y,
        groups=groups,
    ):
        if set(groups[fit_index]) & set(groups[calibration_index]):
            raise RuntimeError("Calibration fold household overlap detected.")

        pipeline = build_pipeline(contract)
        pipeline.fit(
            X[fit_index],
            y[fit_index],
            model__sample_weight=weights[fit_index],
        )
        oof_probability[calibration_index] = pipeline.predict_proba(
            X[calibration_index]
        )[:, 1]

    if np.isnan(oof_probability).any():
        raise RuntimeError("Missing out-of-fold calibration probabilities.")

    return fit_sigmoid(
        oof_probability,
        y,
        weights,
    )


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
        outer = GroupShuffleSplit(
            n_splits=1,
            test_size=OUTER_TEST_SIZE,
            random_state=seed,
        )
        train_index, test_index = next(
            outer.split(task_X, y, task_groups)
        )

        X_train = task_X[train_index]
        X_test = task_X[test_index]
        y_train = y[train_index]
        y_test = y[test_index]
        groups_train = task_groups[train_index]
        groups_test = task_groups[test_index]
        weights_train = task_weight[train_index]
        weights_test = task_weight[test_index]

        if set(groups_train) & set(groups_test):
            raise RuntimeError("Outer holdout household overlap detected.")

        calibrator = cross_validated_calibrator(
            X_train,
            y_train,
            groups_train,
            weights_train,
            contract,
            seed,
        )

        base_model = build_pipeline(contract)
        base_model.fit(
            X_train,
            y_train,
            model__sample_weight=weights_train,
        )
        raw_probability = base_model.predict_proba(X_test)[:, 1]
        calibrated_probability = calibrator.predict_proba(
            logit(raw_probability)
        )[:, 1]

        run = {
            "seed": seed,
            "test_rows": int(len(test_index)),
            "test_positive": int(y_test.sum()),
            "raw": {
                "unweighted": metric_set(
                    y_test,
                    raw_probability,
                ),
                "weighted": metric_set(
                    y_test,
                    raw_probability,
                    sample_weight=weights_test,
                ),
                "calibration_unweighted": calibration_intercept_slope(
                    y_test,
                    raw_probability,
                ),
                "calibration_weighted": calibration_intercept_slope(
                    y_test,
                    raw_probability,
                    sample_weight=weights_test,
                ),
            },
            "calibrated": {
                "unweighted": metric_set(
                    y_test,
                    calibrated_probability,
                ),
                "weighted": metric_set(
                    y_test,
                    calibrated_probability,
                    sample_weight=weights_test,
                ),
                "calibration_unweighted": calibration_intercept_slope(
                    y_test,
                    calibrated_probability,
                ),
                "calibration_weighted": calibration_intercept_slope(
                    y_test,
                    calibrated_probability,
                    sample_weight=weights_test,
                ),
            },
        }
        runs.append(run)

    summary = {
        "sample": {
            "rows": int(len(y)),
            "positive": int(y.sum()),
        },
        "repeats": REPEATS,
        "calibration_folds": CALIBRATION_FOLDS,
        "metrics": {},
        "calibration": {},
        "runs": runs,
    }

    for model in ("raw", "calibrated"):
        summary["metrics"][model] = {}
        for weighting in ("unweighted", "weighted"):
            summary["metrics"][model][weighting] = {
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

        summary["calibration"][model] = {}
        for weighting in ("unweighted", "weighted"):
            key = f"calibration_{weighting}"
            summary["calibration"][model][weighting] = {
                "intercept": summarize([
                    run[model][key]["intercept"]
                    for run in runs
                ]),
                "slope": summarize([
                    run[model][key]["slope"]
                    for run in runs
                ]),
            }

    summary["mean_change_calibrated_minus_raw"] = {}
    for weighting in ("unweighted", "weighted"):
        summary["mean_change_calibrated_minus_raw"][weighting] = {
            metric: (
                summary["metrics"]["calibrated"][weighting][metric]["mean"]
                - summary["metrics"]["raw"][weighting][metric]["mean"]
            )
            for metric in (
                "roc_auc",
                "average_precision",
                "brier_score",
                "log_loss",
            )
        }

    return summary


def main():
    X, groups, transitions, baseline_poverty, contract = load_matrix()
    weights = load_weights()

    result = {
        "contract_version": contract["version"],
        "method": {
            "outer_split": "10 repeated GroupShuffleSplit by SSUID",
            "calibration": "weighted sigmoid calibration from out-of-fold predictions",
            "calibration_cv": "5-fold StratifiedGroupKFold by SSUID",
            "weight": "FINYR2",
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
    (METADATA / "calibration_analysis.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
