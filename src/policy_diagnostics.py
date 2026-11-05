import csv
import gzip
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from train_baselines import build_pipeline, load_matrix, make_task
from validate_models import load_weights, metric_set, task_weights


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "data" / "metadata"
SEED = 699
TEST_SIZE = 0.25


def load_feature_rows(path=PROCESSED / "baseline_features.csv.gz"):
    rows = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    return rows


def task_mask(baseline_poverty, task):
    if task == "poverty_entry":
        return ~baseline_poverty
    if task == "poverty_exit":
        return baseline_poverty
    raise ValueError(f"Unknown task: {task}")


def subgroup_values(rows, mask, field):
    values = []
    for row, keep in zip(rows, mask):
        if not keep:
            continue
        raw = row.get(field)
        if raw in (None, ""):
            values.append("missing")
        else:
            values.append(str(int(float(raw))) if raw.replace(".","",1).isdigit() else str(raw))
    return np.asarray(values, dtype=object)


def age_band(value):
    age = float(value)
    if age < 30:
        return "18-29"
    if age < 45:
        return "30-44"
    if age < 60:
        return "45-59"
    if age < 75:
        return "60-74"
    return "75+"


def age_bands(rows, mask):
    values = []
    for row, keep in zip(rows, mask):
        if not keep:
            continue
        values.append(age_band(row["age"]))
    return np.asarray(values, dtype=object)


def evaluate_subgroup(y, probabilities, weights, groups):
    positive = int(y.sum())
    if len(y) < 50 or positive < 10 or positive == len(y):
        return {
            "rows": int(len(y)),
            "positive": positive,
            "status": "insufficient_events",
        }

    return {
        "rows": int(len(y)),
        "positive": positive,
        "prevalence": float(y.mean()),
        "weighted_prevalence": float(np.average(y, weights=weights)),
        "unweighted": metric_set(y, probabilities),
        "weighted": metric_set(
            y,
            probabilities,
            sample_weight=weights,
        ),
        "households": int(len(set(groups))),
        "status": "reported",
    }


def subgroup_report(
    y,
    probabilities,
    weights,
    groups,
    subgroup_array,
):
    result = {}
    for value in sorted(set(subgroup_array)):
        mask = subgroup_array == value
        result[str(value)] = evaluate_subgroup(
            y[mask],
            probabilities[mask],
            weights[mask],
            groups[mask],
        )
    return result


def risk_concentration(y, probabilities, weights):
    order = np.argsort(-probabilities)
    result = {}
    total_positive = y.sum()
    weighted_positive = np.sum(weights * y)

    for share in (0.05, 0.10, 0.20):
        count = max(1, int(np.ceil(len(y) * share)))
        selected = order[:count]
        selected_positive = y[selected].sum()
        selected_weighted_positive = np.sum(weights[selected] * y[selected])

        result[f"top_{int(share * 100)}pct"] = {
            "rows": int(count),
            "population_share": float(count / len(y)),
            "positive_captured": int(selected_positive),
            "positive_capture_rate": float(
                selected_positive / total_positive
            ) if total_positive else None,
            "weighted_positive_capture_rate": float(
                selected_weighted_positive / weighted_positive
            ) if weighted_positive else None,
            "mean_predicted_risk": float(
                probabilities[selected].mean()
            ),
            "observed_rate": float(
                y[selected].mean()
            ),
            "weighted_observed_rate": float(
                np.average(
                    y[selected],
                    weights=weights[selected],
                )
            ),
        }

    return result


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

    model = build_pipeline(contract)
    model.fit(
        task_X[train_index],
        y[train_index],
        model__sample_weight=task_weight[train_index],
    )
    probability = model.predict_proba(task_X[test_index])[:, 1]

    task_rows = [row for row, keep in zip(rows, mask) if keep]
    test_rows = [task_rows[index] for index in test_index]

    subgroup_arrays = {
        "sex": subgroup_values(test_rows, np.ones(len(test_rows), dtype=bool), "sex"),
        "race": subgroup_values(test_rows, np.ones(len(test_rows), dtype=bool), "race"),
        "hispanic_origin": subgroup_values(test_rows, np.ones(len(test_rows), dtype=bool), "hispanic_origin"),
        "born_in_us": subgroup_values(test_rows, np.ones(len(test_rows), dtype=bool), "born_in_us"),
        "age_band": age_bands(test_rows, np.ones(len(test_rows), dtype=bool)),
    }

    return {
        "holdout": {
            "seed": SEED,
            "rows": int(len(test_index)),
            "positive": int(y[test_index].sum()),
            "households": int(len(set(task_groups[test_index]))),
        },
        "overall": {
            "unweighted": metric_set(
                y[test_index],
                probability,
            ),
            "weighted": metric_set(
                y[test_index],
                probability,
                sample_weight=task_weight[test_index],
            ),
        },
        "risk_concentration": risk_concentration(
            y[test_index],
            probability,
            task_weight[test_index],
        ),
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

    result = {
        "contract_version": contract["version"],
        "method": {
            "holdout": "GroupShuffleSplit by SSUID",
            "seed": SEED,
            "test_group_share": TEST_SIZE,
            "weight": "FINYR2",
            "subgroup_reporting_rule": "At least 50 rows and 10 positive events.",
            "risk_concentration_shares": [0.05, 0.10, 0.20],
        },
        "tasks": {
            task: evaluate_task(
                X,
                groups,
                transitions,
                baseline_poverty,
                weights,
                contract,
                rows,
                task,
            )
            for task in ("poverty_entry", "poverty_exit")
        },
    }

    METADATA.mkdir(parents=True, exist_ok=True)
    (METADATA / "policy_diagnostics.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
