import csv
import gzip
import json
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "data" / "metadata"
CONTRACT = ROOT / "config" / "predictors.json"
RANDOM_STATE = 699


def parse_value(value, feature_type):
    if value in (None, ""):
        return np.nan
    if feature_type == "continuous":
        return float(value)
    return float(value)


def load_matrix(path=PROCESSED / "baseline_features.csv.gz"):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    predictors = contract["predictors"]
    names = [item["feature"] for item in predictors]
    types = [item["type"] for item in predictors]

    rows = []
    groups = []
    transitions = []
    baseline_poverty = []

    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append([
                parse_value(row[name], feature_type)
                for name, feature_type in zip(names, types)
            ])
            groups.append(row["SSUID"])
            transitions.append(row["transition"])
            baseline_poverty.append(row["poverty_2024"] == "True")

    return (
        np.asarray(rows, dtype=float),
        np.asarray(groups),
        np.asarray(transitions),
        np.asarray(baseline_poverty),
        contract,
    )


def make_task(X, groups, transitions, baseline_poverty, task):
    if task == "poverty_entry":
        mask = ~baseline_poverty
        target = transitions[mask] == "entered_poverty"
    elif task == "poverty_exit":
        mask = baseline_poverty
        target = transitions[mask] == "exited_poverty"
    else:
        raise ValueError(f"Unknown task: {task}")

    return X[mask], groups[mask], target.astype(int)


def grouped_split(X, y, groups):
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=RANDOM_STATE,
    )
    train_index, test_index = next(splitter.split(X, y, groups))
    return train_index, test_index


def build_pipeline(contract):
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
        ("scale", StandardScaler()),
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=True,
            ),
        ),
    ])

    preprocessing = ColumnTransformer([
        ("continuous", numeric_pipeline, continuous),
        ("categorical", categorical_pipeline, categorical),
    ])

    return Pipeline([
        ("preprocess", preprocessing),
        (
            "model",
            LogisticRegression(
                penalty="l2",
                C=1.0,
                solver="lbfgs",
                max_iter=2000,
            ),
        ),
    ])


def metrics(y_true, probabilities):
    return {
        "roc_auc": roc_auc_score(y_true, probabilities),
        "average_precision": average_precision_score(y_true, probabilities),
        "brier_score": brier_score_loss(y_true, probabilities),
        "log_loss": log_loss(y_true, probabilities),
    }


def evaluate_task(X, groups, transitions, baseline_poverty, contract, task):
    task_X, task_groups, y = make_task(
        X,
        groups,
        transitions,
        baseline_poverty,
        task,
    )
    train_index, test_index = grouped_split(task_X, y, task_groups)

    X_train = task_X[train_index]
    X_test = task_X[test_index]
    y_train = y[train_index]
    y_test = y[test_index]
    groups_train = task_groups[train_index]
    groups_test = task_groups[test_index]

    if set(groups_train) & set(groups_test):
        raise RuntimeError("Household groups overlap between train and test.")
    if len(np.unique(y_train)) != 2 or len(np.unique(y_test)) != 2:
        raise RuntimeError(f"{task} split does not contain both classes.")

    prevalence = float(y_train.mean())
    baseline_probability = np.full(len(y_test), prevalence)

    pipeline = build_pipeline(contract)
    pipeline.fit(X_train, y_train)
    logistic_probability = pipeline.predict_proba(X_test)[:, 1]

    feature_names = pipeline.named_steps["preprocess"].get_feature_names_out()
    coefficients = pipeline.named_steps["model"].coef_[0]
    ranked = sorted(
        zip(feature_names, coefficients),
        key=lambda item: abs(item[1]),
        reverse=True,
    )[:15]

    return {
        "sample": {
            "rows": int(len(y)),
            "positive": int(y.sum()),
            "prevalence": float(y.mean()),
        },
        "split": {
            "train_rows": int(len(train_index)),
            "test_rows": int(len(test_index)),
            "train_positive": int(y_train.sum()),
            "test_positive": int(y_test.sum()),
            "train_households": int(len(set(groups_train))),
            "test_households": int(len(set(groups_test))),
            "household_overlap": 0,
        },
        "prevalence_baseline": {
            "train_prevalence": prevalence,
            "metrics": metrics(y_test, baseline_probability),
        },
        "regularized_logistic": {
            "metrics": metrics(y_test, logistic_probability),
            "transformed_feature_count": int(len(feature_names)),
            "top_absolute_coefficients": [
                {
                    "feature": str(name),
                    "coefficient": float(coefficient),
                }
                for name, coefficient in ranked
            ],
        },
    }


def main():
    X, groups, transitions, baseline_poverty, contract = load_matrix()
    result = {
        "contract_version": contract["version"],
        "random_state": RANDOM_STATE,
        "split_method": "GroupShuffleSplit by SSUID",
        "test_group_share": 0.25,
        "models": [
            "prevalence_only",
            "l2_regularized_logistic_regression",
        ],
        "tasks": {
            task: evaluate_task(
                X,
                groups,
                transitions,
                baseline_poverty,
                contract,
                task,
            )
            for task in ("poverty_entry", "poverty_exit")
        },
    }

    METADATA.mkdir(parents=True, exist_ok=True)
    (METADATA / "baseline_models.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
