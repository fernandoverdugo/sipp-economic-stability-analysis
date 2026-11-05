import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from policy_diagnostics import age_bands, subgroup_values, task_mask
from train_baselines import build_pipeline, load_matrix, make_task
from validate_models import load_weights, metric_set, summarize, task_weights


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data" / "metadata"
REPEATS = 10
TEST_SIZE = 0.25
SEEDS = [699 + index for index in range(REPEATS)]
MIN_ROWS = 50
MIN_POSITIVE = 10
MIN_REPORTABLE_SPLITS = 5


def subgroup_arrays(rows, mask):
    task_rows = [row for row, keep in zip(rows, mask) if keep]
    keep = np.ones(len(task_rows), dtype=bool)
    return {
        "sex": subgroup_values(task_rows, keep, "sex"),
        "race": subgroup_values(task_rows, keep, "race"),
        "hispanic_origin": subgroup_values(
            task_rows,
            keep,
            "hispanic_origin",
        ),
        "born_in_us": subgroup_values(
            task_rows,
            keep,
            "born_in_us",
        ),
        "age_band": age_bands(task_rows, keep),
    }


def split_subgroup_metrics(
    y,
    probabilities,
    weights,
    values,
):
    result = {}
    for value in sorted(set(values)):
        mask = values == value
        rows = int(mask.sum())
        positive = int(y[mask].sum())

        if rows < MIN_ROWS or positive < MIN_POSITIVE or positive == rows:
            result[str(value)] = {
                "rows": rows,
                "positive": positive,
                "status": "insufficient_events",
            }
            continue

        result[str(value)] = {
            "rows": rows,
            "positive": positive,
            "status": "reported",
            "weighted": metric_set(
                y[mask],
                probabilities[mask],
                sample_weight=weights[mask],
            ),
        }
    return result


def aggregate_subgroups(split_results):
    domains = sorted({
        domain
        for split in split_results
        for domain in split["subgroups"]
    })
    aggregate = {}

    for domain in domains:
        values = sorted({
            value
            for split in split_results
            for value in split["subgroups"].get(domain, {})
        })
        aggregate[domain] = {}

        for value in values:
            reported = [
                split["subgroups"][domain][value]
                for split in split_results
                if value in split["subgroups"].get(domain, {})
                and split["subgroups"][domain][value]["status"] == "reported"
            ]

            item = {
                "reportable_splits": len(reported),
                "total_splits": len(split_results),
                "status": (
                    "reported"
                    if len(reported) >= MIN_REPORTABLE_SPLITS
                    else "insufficient_repeated_support"
                ),
            }

            if len(reported) >= MIN_REPORTABLE_SPLITS:
                item["weighted_metrics"] = {
                    metric: summarize([
                        row["weighted"][metric]
                        for row in reported
                    ])
                    for metric in (
                        "roc_auc",
                        "average_precision",
                        "brier_score",
                        "log_loss",
                    )
                }
                item["rows"] = summarize([
                    row["rows"]
                    for row in reported
                ])
                item["positive"] = summarize([
                    row["positive"]
                    for row in reported
                ])

            aggregate[domain][value] = item

    return aggregate


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
    arrays = subgroup_arrays(rows, mask)
    split_results = []

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

        split_results.append({
            "seed": seed,
            "rows": int(len(test_index)),
            "positive": int(y[test_index].sum()),
            "subgroups": {
                domain: split_subgroup_metrics(
                    y[test_index],
                    probability,
                    task_weight[test_index],
                    values[test_index],
                )
                for domain, values in arrays.items()
            },
        })

    aggregate = aggregate_subgroups(split_results)

    return {
        "repeats": REPEATS,
        "reporting_rule": {
            "minimum_rows_per_split": MIN_ROWS,
            "minimum_positive_per_split": MIN_POSITIVE,
            "minimum_reportable_splits": MIN_REPORTABLE_SPLITS,
        },
        "aggregate": aggregate,
        "splits": split_results,
    }


def main():
    from policy_diagnostics import load_feature_rows

    X, groups, transitions, baseline_poverty, contract = load_matrix()
    weights = load_weights()
    rows = load_feature_rows()

    result = {
        "contract_version": contract["version"],
        "method": {
            "split_method": "10 repeated GroupShuffleSplit by SSUID",
            "seeds": SEEDS,
            "weight": "FINYR2",
            "model": "weighted regularized logistic regression",
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
    (METADATA / "subgroup_validation.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
