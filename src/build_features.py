import csv
import gzip
import json
from pathlib import Path

from build_panel import parse_float, parse_int, selected_rows_from_zip


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "data" / "metadata"
CONTRACT = ROOT / "config" / "predictors.json"

ID_COLUMNS = ["SSUID", "PNUM", "MONTHCODE"]
EMPLOYED_RMESR = {1, 2, 3, 4, 5}
UNEMPLOYED_RMESR = {6, 7}


def unique_or_none(values, name, key):
    observed = [value for value in values if value is not None]
    if not observed:
        return None
    first = observed[0]
    if any(value != first for value in observed[1:]):
        raise RuntimeError(
            f"Inconsistent annual-constant field {name} for person {key}"
        )
    return first


def safe_sum(values):
    observed = [value for value in values if value is not None]
    return sum(observed) if observed else None


def safe_mean(values):
    observed = [value for value in values if value is not None]
    return sum(observed) / len(observed) if observed else None


def housing_assistance_status(tenure, rent_subsidy, voucher):
    if tenure is None:
        return None
    if tenure == 1:
        return 0
    if rent_subsidy is None:
        return None
    if rent_subsidy != 1:
        return 1
    if voucher is None:
        return None
    return 3 if voucher == 1 else 2


def feature_sources(contract):
    sources = []
    for predictor in contract["predictors"]:
        for variable in predictor["source"]:
            if variable not in sources:
                sources.append(variable)
    return sources


def load_panel(path=PROCESSED / "panel_core.csv.gz"):
    result = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("adult_baseline") != "True":
                continue
            if not row.get("transition"):
                continue
            weight = parse_float(row.get("FINYR2"))
            if weight is None or weight <= 0:
                continue
            key = (str(row["SSUID"]), parse_int(row["PNUM"]))
            result[key] = {
                "transition": row["transition"],
                "poverty_2024": row.get("poverty_2024") == "True",
                "poverty_2025": row.get("poverty_2025") == "True",
                "FINYR2": weight,
            }
    return result


def collect_baseline_rows(panel_keys, contract):
    sources = feature_sources(contract)
    columns = ID_COLUMNS + sources
    people = {}

    for row in selected_rows_from_zip(RAW / "pu2024_csv.zip", columns):
        key = (str(row["SSUID"]), parse_int(row["PNUM"]))
        if key not in panel_keys:
            continue

        month = parse_int(row["MONTHCODE"])
        if month is None or not 1 <= month <= 12:
            continue

        person = people.setdefault(key, {})
        for variable in sources:
            person.setdefault(variable, [])
            person[variable].append(row.get(variable))

    return people


def numeric_values(values):
    return [parse_float(value) for value in values]


def categorical_values(values):
    return [parse_int(value) for value in values]


def build_features(panel, people, contract):
    rows = []

    for key, outcome in panel.items():
        source = people.get(key)
        if source is None:
            continue

        features = {}
        for predictor in contract["predictors"]:
            name = predictor["feature"]
            variables = predictor["source"]
            aggregation = predictor["aggregation"]

            if aggregation == "annual_constant":
                variable = variables[0]
                if predictor["type"] == "continuous":
                    values = numeric_values(source[variable])
                else:
                    values = categorical_values(source[variable])
                features[name] = unique_or_none(values, variable, key)

            elif aggregation == "count_months_employed_from_monthly_status":
                values = categorical_values(source[variables[0]])
                observed = [value for value in values if value is not None]
                features[name] = (
                    sum(value in EMPLOYED_RMESR for value in observed)
                    if observed else None
                )

            elif aggregation == "count_months_unemployed_from_monthly_status":
                values = categorical_values(source[variables[0]])
                observed = [value for value in values if value is not None]
                features[name] = (
                    sum(value in UNEMPLOYED_RMESR for value in observed)
                    if observed else None
                )

            elif aggregation == "mean_across_observed_months":
                features[name] = safe_mean(
                    numeric_values(source[variables[0]])
                )

            elif aggregation == "sum_across_observed_months":
                features[name] = safe_sum(
                    numeric_values(source[variables[0]])
                )

            elif aggregation == "derive_housing_assistance_status":
                tenure = unique_or_none(
                    categorical_values(source[variables[0]]),
                    variables[0],
                    key,
                )
                subsidy = unique_or_none(
                    categorical_values(source[variables[1]]),
                    variables[1],
                    key,
                )
                voucher = unique_or_none(
                    categorical_values(source[variables[2]]),
                    variables[2],
                    key,
                )
                features[name] = housing_assistance_status(
                    tenure,
                    subsidy,
                    voucher,
                )

            else:
                raise RuntimeError(
                    f"Unsupported aggregation rule: {aggregation}"
                )

        rows.append({
            "SSUID": key[0],
            "PNUM": key[1],
            **features,
            **outcome,
        })

    return rows


def feature_profile(rows, contract):
    predictor_names = [
        predictor["feature"]
        for predictor in contract["predictors"]
    ]
    numeric = {
        predictor["feature"]
        for predictor in contract["predictors"]
        if predictor["type"] == "continuous"
    }

    profile = {}
    total = len(rows)

    for name in predictor_names:
        values = [row[name] for row in rows]
        observed = [value for value in values if value is not None]
        item = {
            "observed": len(observed),
            "missing": total - len(observed),
            "missing_share": (
                (total - len(observed)) / total if total else None
            ),
        }

        if name in numeric and observed:
            sorted_values = sorted(observed)
            item.update({
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "mean": sum(sorted_values) / len(sorted_values),
            })
        else:
            counts = {}
            for value in observed:
                key = str(value)
                counts[key] = counts.get(key, 0) + 1
            item["levels"] = counts

        profile[name] = item

    entry_rows = [row for row in rows if not row["poverty_2024"]]
    exit_rows = [row for row in rows if row["poverty_2024"]]

    return {
        "contract_version": contract["version"],
        "baseline_release": contract["baseline_release"],
        "reference_year": contract["reference_year"],
        "feature_count": len(predictor_names),
        "rows": total,
        "model_samples": {
            "poverty_entry": {
                "rows": len(entry_rows),
                "positive": sum(
                    row["transition"] == "entered_poverty"
                    for row in entry_rows
                ),
            },
            "poverty_exit": {
                "rows": len(exit_rows),
                "positive": sum(
                    row["transition"] == "exited_poverty"
                    for row in exit_rows
                ),
            },
        },
        "features": profile,
    }


def write_features(rows):
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = PROCESSED / "baseline_features.csv.gz"
    fieldnames = list(rows[0]) if rows else []
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    panel = load_panel()
    people = collect_baseline_rows(set(panel), contract)
    rows = build_features(panel, people, contract)
    result = feature_profile(rows, contract)

    if len(rows) != len(panel):
        raise RuntimeError(
            f"Feature rows {len(rows)} do not match panel rows {len(panel)}"
        )

    METADATA.mkdir(parents=True, exist_ok=True)
    write_features(rows)
    (METADATA / "feature_profile.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
