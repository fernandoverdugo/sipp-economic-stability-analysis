import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from cohort import poverty_transition


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "data" / "metadata"


PRIMARY_COLUMNS = [
    "SSUID",
    "PNUM",
    "MONTHCODE",
    "TFCYINCPOV",
    "AFCYINCPOV",
    "TAGE",
]

WEIGHT_COLUMNS = [
    "SSUID",
    "PNUM",
    "SPANEL",
    "FINYR2",
]

REPLICATE_CHECK_COLUMNS = [
    "SSUID",
    "PNUM",
    "REPWGT0",
]


def zip_member(path):
    with zipfile.ZipFile(path) as archive:
        members = [
            name
            for name in archive.namelist()
            if not name.endswith("/")
            and name.lower().endswith((".csv", ".txt"))
        ]
        if len(members) != 1:
            raise RuntimeError(
                f"Expected one tabular member in {Path(path).name}; found {members}"
            )
        return members[0]


def read_zip_table(path, usecols):
    member = zip_member(path)
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as handle:
            return pd.read_csv(
                handle,
                sep="|",
                usecols=usecols,
                low_memory=False,
            )


def collapse_person_year(frame, year):
    required = set(PRIMARY_COLUMNS)
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"{year} primary file missing columns: {sorted(missing)}")

    frame = frame.copy()
    frame["SSUID"] = frame["SSUID"].astype(str)
    frame["PNUM"] = pd.to_numeric(frame["PNUM"], errors="coerce")
    frame["MONTHCODE"] = pd.to_numeric(frame["MONTHCODE"], errors="coerce")
    frame["TFCYINCPOV"] = pd.to_numeric(frame["TFCYINCPOV"], errors="coerce")
    frame["AFCYINCPOV"] = pd.to_numeric(frame["AFCYINCPOV"], errors="coerce")
    frame["TAGE"] = pd.to_numeric(frame["TAGE"], errors="coerce")

    key = ["SSUID", "PNUM"]

    poverty_nunique = (
        frame.groupby(key, observed=True)["TFCYINCPOV"]
        .nunique(dropna=True)
    )
    inconsistent_poverty = int((poverty_nunique > 1).sum())
    if inconsistent_poverty:
        raise RuntimeError(
            f"{year} has {inconsistent_poverty} persons with inconsistent "
            "annual TFCYINCPOV across monthly records."
        )

    age_nunique = frame.groupby(key, observed=True)["TAGE"].nunique(dropna=True)
    inconsistent_age = int((age_nunique > 1).sum())
    if inconsistent_age:
        raise RuntimeError(
            f"{year} has {inconsistent_age} persons with inconsistent "
            "annual TAGE across monthly records."
        )

    grouped = frame.groupby(key, observed=True, as_index=False)
    collapsed = grouped.agg(
        month_count=("MONTHCODE", "nunique"),
        poverty_ratio=("TFCYINCPOV", "first"),
        poverty_status_flag=("AFCYINCPOV", "first"),
        age=("TAGE", "first"),
    )

    if collapsed.duplicated(key).any():
        raise RuntimeError(f"{year} person-year collapse did not produce unique keys.")

    collapsed["survey_year"] = year
    return collapsed


def valid_poverty(series):
    return series.notna() & (series >= 0)


def build_panel():
    primary_2024 = read_zip_table(
        RAW / "pu2024_csv.zip",
        PRIMARY_COLUMNS,
    )
    primary_2025 = read_zip_table(
        RAW / "pu2025_csv.zip",
        PRIMARY_COLUMNS,
    )

    person_2024 = collapse_person_year(primary_2024, 2024)
    person_2025 = collapse_person_year(primary_2025, 2025)

    key = ["SSUID", "PNUM"]
    panel = person_2024.merge(
        person_2025,
        on=key,
        how="inner",
        suffixes=("_2024", "_2025"),
        validate="one_to_one",
    )

    weights = read_zip_table(
        RAW / "lgtwgt2025yr2_csv.zip",
        WEIGHT_COLUMNS,
    )
    weights["SSUID"] = weights["SSUID"].astype(str)
    weights["PNUM"] = pd.to_numeric(weights["PNUM"], errors="coerce")
    weights["FINYR2"] = pd.to_numeric(weights["FINYR2"], errors="coerce")

    if weights.duplicated(key).any():
        raise RuntimeError("Two-year longitudinal weight file has duplicate person keys.")

    panel = panel.merge(
        weights,
        on=key,
        how="inner",
        validate="one_to_one",
    )

    replicate = read_zip_table(
        RAW / "lgtrw2025yr2_csv.zip",
        REPLICATE_CHECK_COLUMNS,
    )
    replicate["SSUID"] = replicate["SSUID"].astype(str)
    replicate["PNUM"] = pd.to_numeric(replicate["PNUM"], errors="coerce")
    replicate["REPWGT0"] = pd.to_numeric(replicate["REPWGT0"], errors="coerce")

    if replicate.duplicated(key).any():
        raise RuntimeError("Two-year replicate-weight file has duplicate person keys.")

    panel = panel.merge(
        replicate,
        on=key,
        how="inner",
        validate="one_to_one",
    )

    valid_weight = panel["FINYR2"].notna() & panel["REPWGT0"].notna()
    max_weight_difference = float(
        np.abs(
            panel.loc[valid_weight, "FINYR2"]
            - panel.loc[valid_weight, "REPWGT0"]
        ).max()
    )
    if max_weight_difference > 1e-6:
        raise RuntimeError(
            "FINYR2 and REPWGT0 differ beyond tolerance: "
            f"{max_weight_difference}"
        )

    valid_transition = (
        valid_poverty(panel["poverty_ratio_2024"])
        & valid_poverty(panel["poverty_ratio_2025"])
    )
    panel["poverty_2024"] = np.where(
        valid_poverty(panel["poverty_ratio_2024"]),
        panel["poverty_ratio_2024"] < 1.0,
        pd.NA,
    )
    panel["poverty_2025"] = np.where(
        valid_poverty(panel["poverty_ratio_2025"]),
        panel["poverty_ratio_2025"] < 1.0,
        pd.NA,
    )

    panel["transition"] = pd.NA
    panel.loc[valid_transition, "transition"] = [
        poverty_transition(baseline, followup)
        for baseline, followup in zip(
            panel.loc[valid_transition, "poverty_2024"],
            panel.loc[valid_transition, "poverty_2025"],
        )
    ]

    panel["adult_baseline"] = panel["age_2024"].ge(18)

    return person_2024, person_2025, panel, max_weight_difference


def profile(person_2024, person_2025, panel, max_weight_difference):
    adult = panel[
        panel["adult_baseline"]
        & panel["transition"].notna()
        & panel["FINYR2"].notna()
        & panel["FINYR2"].gt(0)
    ].copy()

    counts = adult["transition"].value_counts().to_dict()
    weighted = (
        adult.groupby("transition", observed=True)["FINYR2"]
        .sum()
        .sort_index()
        .to_dict()
    )
    weighted_total = float(adult["FINYR2"].sum())
    weighted_share = {
        name: float(value / weighted_total)
        for name, value in weighted.items()
    }

    return {
        "person_years": {
            "2024": int(len(person_2024)),
            "2025": int(len(person_2025)),
        },
        "linked_with_longitudinal_weights": int(len(panel)),
        "adult_analysis_cohort": int(len(adult)),
        "poverty_measure": {
            "variable": "TFCYINCPOV",
            "threshold": 1.0,
            "definition": "poverty_ratio < 1.0",
        },
        "transition_counts_unweighted": {
            key: int(value)
            for key, value in counts.items()
        },
        "transition_weight_sums": {
            key: float(value)
            for key, value in weighted.items()
        },
        "transition_weighted_shares": weighted_share,
        "weight_validation": {
            "FINYR2_vs_REPWGT0_max_abs_difference": max_weight_difference,
        },
        "monthly_record_coverage": {
            "2024_persons_with_12_months": int(
                (person_2024["month_count"] == 12).sum()
            ),
            "2025_persons_with_12_months": int(
                (person_2025["month_count"] == 12).sum()
            ),
        },
    }


def main():
    person_2024, person_2025, panel, max_diff = build_panel()
    result = profile(person_2024, person_2025, panel, max_diff)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    METADATA.mkdir(parents=True, exist_ok=True)

    panel.to_csv(
        PROCESSED / "panel_core.csv.gz",
        index=False,
        compression="gzip",
    )
    (METADATA / "panel_profile.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
