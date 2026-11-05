import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

from train_baselines import build_pipeline, load_matrix, make_task


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "data" / "metadata"
REPEATS = 10
TEST_SIZE = 0.25
SEEDS = [699 + index for index in range(REPEATS)]


def load_weights(path=PROCESSED / "baseline_features.csv.gz"):
    import csv
    import gzip

    weights = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            weights.append(float(row["FINYR2"]))
    return np.asarray(weights, dtype=float)


def task_weights(weights, baseline_poverty, task):
    if task == "poverty_entry":
        return weights[~baseline_poverty]
    if task == "poverty_exit":
        return weights[baseline_poverty]
    raise ValueError(f"Unknown task: {task}")


def metric_set(y_true, probabilities, sample_weight=None):
    return {
        "roc_auc": float(
            roc_auc_score(
                y_true,
                probabilities,
                sample_weight=sample_weight,
            )
        ),
        "average_precision": float(
            average_precision_score(
                y_true,
                probabilities,
                sample_weight=sample_weight,
            )
        ),
        "brier_score": float(
            brier_score_loss(
                y_true,
                probabilities,
                sample_weight=sample_weight,
            )
        ),
        "log_loss": float(
            log_loss(
                y_true,
                probabilities,
                sample_weight=sample_weight,
            )
        ),
    }


def calibration_intercept_slope(y_true, probabilities, sample_weight=None):
    epsilon = 1e-6
    clipped = np.clip(probabilities, epsilon, 1 - epsilon)
    logits = np.log(clipped / (1 - clipped)).reshape(-1, 1)

    model = LogisticRegression(
        C=1e6,
        solver="lbfgs",
        max_iter=2000,
    )
    model.fit(logits, y_true, sample_weight=sample_weight)

    return {
        "intercept": float(model.intercept_[0]),
        "slope": float(model.coef_[0][0]),
    }


def calibration_bins(y_true, probabilities, sample_weight=None, bins=10):
    if sample_weight is None:
        sample_weight = np.ones(len(y_true), dtype=float)

    order = np.argsort(probabilities)
    y_sorted = y_true[order]
    p_sorted = probabilities[order]
    w_sorted = sample_weight[order]

    chunks = np.array_split(np.arange(len(y_true)), bins)
    result = []

    for index, chunk in enumerate(chunks, start=1):
        if len(chunk) == 0:
            continue
        weights = w_sorted[chunk]
        weight_sum = weights.sum()
        result.append({
            "bin": index,
            "rows": int(len(chunk)),
            "mean_predicted": float(
                np.average(p_sorted[chunk], weights=weights)
            ),
            "observed_rate": float(
                np.average(y_sorted[chunk], weights=weights)
            ),
        })

    return result


def summarize(values):
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(array.mean()),
        "std": float(array.std(ddof=1)),
        "min": float(array.min()),
        "max": float(array.max()),
    }


def summarize_runs(runs, section, metric):
    return summarize([
        run[section][metric]
        for run in runs
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

        train_groups = task_groups[train_index]
        test_groups = task_groups[test_index]
        if set(train_groups) & set(test_groups):
            raise RuntimeError("Household overlap detected.")

        X_train = task_X[train_index]
        X_test = task_X[test_index]
        y_train = y[train_index]
        y_test = y[test_index]
        w_train = task_weight[train_index]
        w_test = task_weight[test_index]

        pipeline = build_pipeline(contract)
        pipeline.fit(
            X_train,
            y_train,
            model__sample_weight=w_train,
        )
        probabilities = pipeline.predict_proba(X_test)[:, 1]

        runs.append({
            "seed": seed,
            "test_rows": int(len(test_index)),
            "test_positive": int(y_test.sum()),
            "unweighted": metric_set(y_test, probabilities),
            "weighted": metric_set(
                y_test,
                probabilities,
                sample_weight=w_test,
            ),
            "calibration_unweighted": calibration_intercept_slope(
                y_test,
                probabilities,
            ),
            "calibration_weighted": calibration_intercept_slope(
                y_test,
                probabilities,
                sample_weight=w_test,
            ),
        })

    final_seed = SEEDS[0]
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=TEST_SIZE,
        random_state=final_seed,
    )
    train_index, test_index = next(
        splitter.split(task_X, y, task_groups)
    )
    pipeline = build_pipeline(contract)
    pipeline.fit(
        task_X[train_index],
        y[train_index],
        model__sample_weight=task_weight[train_index],
    )
    probabilities = pipeline.predict_proba(task_X[test_index])[:, 1]

    summary = {
        "sample": {
            "rows": int(len(y)),
            "positive": int(y.sum()),
            "unweighted_prevalence": float(y.mean()),
            "weighted_prevalence": float(
                np.average(y, weights=task_weight)
            ),
        },
        "repeats": REPEATS,
        "metrics": {},
        "calibration": {
            "unweighted_intercept": summarize([
                run["calibration_unweighted"]["intercept"]
                for run in runs
            ]),
            "unweighted_slope": summarize([
                run["calibration_unweighted"]["slope"]
                for run in runs
            ]),
            "weighted_intercept": summarize([
                run["calibration_weighted"]["intercept"]
                for run in runs
            ]),
            "weighted_slope": summarize([
                run["calibration_weighted"]["slope"]
                for run in runs
            ]),
        },
        "representative_holdout": {
            "seed": final_seed,
            "unweighted_bins": calibration_bins(
                y[test_index],
                probabilities,
            ),
            "weighted_bins": calibration_bins(
                y[test_index],
                probabilities,
                sample_weight=task_weight[test_index],
            ),
        },
        "runs": runs,
    }

    for weighting in ("unweighted", "weighted"):
        summary["metrics"][weighting] = {
            metric: summarize_runs(runs, weighting, metric)
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

    if len(weights) != len(X):
        raise RuntimeError("Feature rows and survey weights do not align.")

    result = {
        "contract_version": contract["version"],
        "evaluation": {
            "split_method": "Repeated GroupShuffleSplit by SSUID",
            "repeats": REPEATS,
            "test_group_share": TEST_SIZE,
            "seeds": SEEDS,
            "weighted_model_fit": True,
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
    (METADATA / "model_validation.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
