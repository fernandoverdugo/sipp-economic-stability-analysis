import csv
import gzip
import io
import json
from pathlib import Path
import zipfile

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


def parse_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value):
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


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


def selected_rows_from_zip(path, columns):
    member = zip_member(path)
    with zipfile.ZipFile(path) as archive:
        with archive.open(member) as binary:
            with io.TextIOWrapper(binary, encoding="utf-8", newline="") as text:
                reader = csv.reader(text, delimiter="|")
                header = next(reader)
                missing = [column for column in columns if column not in header]
                if missing:
                    raise RuntimeError(
                        f"{Path(path).name} missing columns: {missing}"
                    )
                indices = [header.index(column) for column in columns]
                for row in reader:
                    yield {
                        column: row[index]
                        for column, index in zip(columns, indices)
                    }


def collapse_records(records, year):
    persons = {}

    for row in records:
        ssuid = str(row["SSUID"])
        pnum = parse_int(row["PNUM"])
        if pnum is None:
            continue
        key = (ssuid, pnum)

        month = parse_int(row["MONTHCODE"])
        poverty = parse_float(row["TFCYINCPOV"])
        poverty_flag = parse_int(row["AFCYINCPOV"])
        age = parse_int(row["TAGE"])

        person = persons.setdefault(
            key,
            {
                "SSUID": ssuid,
                "PNUM": pnum,
                "month_mask": 0,
                "poverty_ratio": None,
                "poverty_status_flag": None,
                "age": None,
            },
        )

        if month is not None and 1 <= month <= 12:
            person["month_mask"] |= 1 << (month - 1)

        if poverty is not None:
            current = person["poverty_ratio"]
            if current is not None and abs(current - poverty) > 1e-12:
                raise RuntimeError(
                    f"{year} has inconsistent TFCYINCPOV for person {key}: "
                    f"{current} vs {poverty}"
                )
            person["poverty_ratio"] = poverty

        if poverty_flag is not None and person["poverty_status_flag"] is None:
            person["poverty_status_flag"] = poverty_flag

        if age is not None:
            current_age = person["age"]
            if current_age is not None and current_age != age:
                raise RuntimeError(
                    f"{year} has inconsistent TAGE for person {key}: "
                    f"{current_age} vs {age}"
                )
            person["age"] = age

    for person in persons.values():
        person["month_count"] = person.pop("month_mask").bit_count()
        person["survey_year"] = year

    return persons


def load_person_year(path, year):
    return collapse_records(
        selected_rows_from_zip(path, PRIMARY_COLUMNS),
        year,
    )


def load_weight_map(path):
    result = {}
    for row in selected_rows_from_zip(path, WEIGHT_COLUMNS):
        key = (str(row["SSUID"]), parse_int(row["PNUM"]))
        if key[1] is None:
            continue
        if key in result:
            raise RuntimeError(f"Duplicate longitudinal weight key: {key}")
        result[key] = {
            "SPANEL": parse_int(row["SPANEL"]),
            "FINYR2": parse_float(row["FINYR2"]),
        }
    return result


def load_replicate_full_weight(path):
    result = {}
    for row in selected_rows_from_zip(path, REPLICATE_CHECK_COLUMNS):
        key = (str(row["SSUID"]), parse_int(row["PNUM"]))
        if key[1] is None:
            continue
        if key in result:
            raise RuntimeError(f"Duplicate replicate-weight key: {key}")
        result[key] = parse_float(row["REPWGT0"])
    return result


def valid_poverty(value):
    return value is not None and value >= 0


def build_panel():
    person_2024 = load_person_year(RAW / "pu2024_csv.zip", 2024)
    person_2025 = load_person_year(RAW / "pu2025_csv.zip", 2025)
    weights = load_weight_map(RAW / "lgtwgt2025yr2_csv.zip")
    replicate = load_replicate_full_weight(
        RAW / "lgtrw2025yr2_csv.zip"
    )

    linked_keys = (
        set(person_2024)
        & set(person_2025)
        & set(weights)
        & set(replicate)
    )

    panel = []
    max_weight_difference = 0.0

    for key in sorted(linked_keys):
        baseline = person_2024[key]
        followup = person_2025[key]
        weight = weights[key]["FINYR2"]
        repwgt0 = replicate[key]

        if weight is not None and repwgt0 is not None:
            difference = abs(weight - repwgt0)
            max_weight_difference = max(max_weight_difference, difference)

        poverty_2024 = (
            baseline["poverty_ratio"] < 1.0
            if valid_poverty(baseline["poverty_ratio"])
            else None
        )
        poverty_2025 = (
            followup["poverty_ratio"] < 1.0
            if valid_poverty(followup["poverty_ratio"])
            else None
        )

        transition = None
        if poverty_2024 is not None and poverty_2025 is not None:
            transition = poverty_transition(poverty_2024, poverty_2025)

        panel.append(
            {
                "SSUID": key[0],
                "PNUM": key[1],
                "month_count_2024": baseline["month_count"],
                "month_count_2025": followup["month_count"],
                "poverty_ratio_2024": baseline["poverty_ratio"],
                "poverty_ratio_2025": followup["poverty_ratio"],
                "age_2024": baseline["age"],
                "age_2025": followup["age"],
                "poverty_2024": poverty_2024,
                "poverty_2025": poverty_2025,
                "transition": transition,
                "FINYR2": weight,
                "REPWGT0": repwgt0,
                "SPANEL": weights[key]["SPANEL"],
                "adult_baseline": (
                    baseline["age"] is not None and baseline["age"] >= 18
                ),
            }
        )

    if max_weight_difference > 1e-6:
        raise RuntimeError(
            "FINYR2 and REPWGT0 differ beyond tolerance: "
            f"{max_weight_difference}"
        )

    return person_2024, person_2025, panel, max_weight_difference


def profile(person_2024, person_2025, panel, max_weight_difference):
    adult = [
        row
        for row in panel
        if row["adult_baseline"]
        and row["transition"] is not None
        and row["FINYR2"] is not None
        and row["FINYR2"] > 0
    ]

    counts = {}
    weighted = {}
    for row in adult:
        transition = row["transition"]
        counts[transition] = counts.get(transition, 0) + 1
        weighted[transition] = weighted.get(transition, 0.0) + row["FINYR2"]

    weighted_total = sum(weighted.values())
    weighted_share = {
        key: value / weighted_total
        for key, value in weighted.items()
    }

    return {
        "person_years": {
            "2024": len(person_2024),
            "2025": len(person_2025),
        },
        "linked_with_longitudinal_weights": len(panel),
        "adult_analysis_cohort": len(adult),
        "poverty_measure": {
            "variable": "TFCYINCPOV",
            "threshold": 1.0,
            "definition": "poverty_ratio < 1.0",
        },
        "transition_counts_unweighted": counts,
        "transition_weight_sums": weighted,
        "transition_weighted_shares": weighted_share,
        "weight_validation": {
            "FINYR2_vs_REPWGT0_max_abs_difference": max_weight_difference,
        },
        "monthly_record_coverage": {
            "2024_persons_with_12_months": sum(
                row["month_count"] == 12
                for row in person_2024.values()
            ),
            "2025_persons_with_12_months": sum(
                row["month_count"] == 12
                for row in person_2025.values()
            ),
        },
    }


def write_panel(panel):
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / "panel_core.csv.gz"
    fieldnames = list(panel[0]) if panel else []

    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(panel)


def main():
    person_2024, person_2025, panel, max_diff = build_panel()
    result = profile(person_2024, person_2025, panel, max_diff)

    METADATA.mkdir(parents=True, exist_ok=True)
    write_panel(panel)
    (METADATA / "panel_profile.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
