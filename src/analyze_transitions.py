import csv
import gzip
import json
import math
from pathlib import Path

from build_panel import parse_float, parse_int, selected_rows_from_zip


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "data" / "metadata"

REPLICATE_COUNT = 240
FAY_COEFFICIENT = 0.5
NORMAL_95 = 1.959963984540054
REPLICATE_COLUMNS = [
    "SSUID",
    "PNUM",
    *[f"REPWGT{i}" for i in range(1, REPLICATE_COUNT + 1)],
]


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


def fay_variance(full_estimate, replicate_estimates, coefficient=FAY_COEFFICIENT):
    if not replicate_estimates:
        raise ValueError("At least one replicate estimate is required.")
    scale = len(replicate_estimates) * (1.0 - coefficient) ** 2
    return sum(
        (estimate - full_estimate) ** 2
        for estimate in replicate_estimates
    ) / scale


def confidence_interval(estimate, standard_error, z=NORMAL_95):
    lower = max(0.0, estimate - z * standard_error)
    upper = min(1.0, estimate + z * standard_error)
    return lower, upper


def load_analysis_cohort(path=PROCESSED / "panel_core.csv.gz"):
    cohort = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            adult = parse_bool(row.get("adult_baseline"))
            transition = row.get("transition") or None
            weight = parse_float(row.get("FINYR2"))
            if not adult or transition is None or weight is None or weight <= 0:
                continue

            key = (str(row["SSUID"]), parse_int(row["PNUM"]))
            if key[1] is None:
                continue

            cohort[key] = {
                "transition": transition,
                "poverty_2024": parse_bool(row.get("poverty_2024")),
                "poverty_2025": parse_bool(row.get("poverty_2025")),
                "FINYR2": weight,
            }
    return cohort


def estimand_flags(row):
    transition = row["transition"]
    baseline_poor = row["poverty_2024"] is True
    followup_poor = row["poverty_2025"] is True

    return {
        "stable_above_poverty_share": (
            transition == "stable_above_poverty",
            True,
        ),
        "entered_poverty_share": (
            transition == "entered_poverty",
            True,
        ),
        "exited_poverty_share": (
            transition == "exited_poverty",
            True,
        ),
        "persistent_poverty_share": (
            transition == "persistent_poverty",
            True,
        ),
        "baseline_poverty_share": (
            baseline_poor,
            True,
        ),
        "followup_poverty_share": (
            followup_poor,
            True,
        ),
        "poverty_entry_rate_among_baseline_nonpoor": (
            transition == "entered_poverty",
            not baseline_poor,
        ),
        "poverty_exit_rate_among_baseline_poor": (
            transition == "exited_poverty",
            baseline_poor,
        ),
    }


def full_sample_estimates(cohort):
    numerators = {}
    denominators = {}

    for row in cohort.values():
        weight = row["FINYR2"]
        for name, (in_numerator, in_denominator) in estimand_flags(row).items():
            numerators.setdefault(name, 0.0)
            denominators.setdefault(name, 0.0)
            if in_denominator:
                denominators[name] += weight
            if in_numerator:
                numerators[name] += weight

    return {
        name: numerators[name] / denominators[name]
        for name in numerators
    }


def replicate_estimates(cohort, path=RAW / "lgtrw2025yr2_csv.zip"):
    names = list(estimand_flags(next(iter(cohort.values()))))
    numerators = {
        name: [0.0] * REPLICATE_COUNT
        for name in names
    }
    denominators = {
        name: [0.0] * REPLICATE_COUNT
        for name in names
    }
    matched = set()

    for source_row in selected_rows_from_zip(path, REPLICATE_COLUMNS):
        key = (str(source_row["SSUID"]), parse_int(source_row["PNUM"]))
        if key not in cohort:
            continue

        matched.add(key)
        flags = estimand_flags(cohort[key])
        weights = [
            parse_float(source_row[f"REPWGT{i}"])
            for i in range(1, REPLICATE_COUNT + 1)
        ]
        if any(weight is None for weight in weights):
            raise RuntimeError(f"Missing replicate weight for person {key}")

        for name, (in_numerator, in_denominator) in flags.items():
            if in_denominator:
                target = denominators[name]
                for index, weight in enumerate(weights):
                    target[index] += weight
            if in_numerator:
                target = numerators[name]
                for index, weight in enumerate(weights):
                    target[index] += weight

    missing = set(cohort) - matched
    if missing:
        raise RuntimeError(
            f"Replicate-weight file missing {len(missing)} analytical persons."
        )

    result = {}
    for name in names:
        values = []
        for numerator, denominator in zip(numerators[name], denominators[name]):
            if denominator <= 0:
                raise RuntimeError(
                    f"Nonpositive replicate denominator for {name}."
                )
            values.append(numerator / denominator)
        result[name] = values

    return result


def analyze(cohort, replicates):
    full = full_sample_estimates(cohort)
    estimates = {}

    for name, estimate in full.items():
        variance = fay_variance(estimate, replicates[name])
        standard_error = math.sqrt(variance)
        lower, upper = confidence_interval(estimate, standard_error)
        estimates[name] = {
            "estimate": estimate,
            "standard_error": standard_error,
            "variance": variance,
            "ci95_lower": lower,
            "ci95_upper": upper,
        }

    return {
        "method": {
            "survey": "Survey of Income and Program Participation",
            "weight": "FINYR2",
            "replicate_weights": "REPWGT1-REPWGT240",
            "replicate_count": REPLICATE_COUNT,
            "variance_method": "Fay BRR",
            "fay_coefficient": FAY_COEFFICIENT,
            "variance_scale_denominator": (
                REPLICATE_COUNT * (1.0 - FAY_COEFFICIENT) ** 2
            ),
            "confidence_interval": "normal 95%, bounded to [0, 1]",
        },
        "analytical_cohort": len(cohort),
        "estimates": estimates,
    }


def main():
    cohort = load_analysis_cohort()
    if not cohort:
        raise RuntimeError(
            "No analytical cohort found. Run src/build_panel.py first."
        )

    replicates = replicate_estimates(cohort)
    result = analyze(cohort, replicates)

    METADATA.mkdir(parents=True, exist_ok=True)
    output = METADATA / "transition_analysis.json"
    output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
