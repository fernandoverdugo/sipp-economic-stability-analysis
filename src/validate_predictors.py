import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CONFIG = ROOT / "config" / "predictors.json"
OUTPUT = ROOT / "data" / "metadata" / "predictor_validation.json"


def load_schema(path):
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    return {record["name"]: record for record in records}


def required_variables(contract):
    variables = set()
    for predictor in contract["predictors"]:
        variables.update(predictor["source"])
    return variables


def validate_contract(contract, schemas):
    variables = required_variables(contract)
    results = {}

    for year, schema in schemas.items():
        missing = sorted(variables - set(schema))
        results[str(year)] = {
            "required_count": len(variables),
            "found_count": len(variables) - len(missing),
            "missing": missing,
        }

    common = set.intersection(*(set(schema) for schema in schemas.values()))
    labels = {}
    dtypes = {}

    for variable in sorted(variables):
        if variable in common:
            labels[variable] = {
                str(year): schemas[year][variable]["label"]
                for year in schemas
            }
            dtypes[variable] = {
                str(year): schemas[year][variable]["dtype"]
                for year in schemas
            }

    return {
        "contract_version": contract["version"],
        "baseline_release": contract["baseline_release"],
        "outcome_release": contract["outcome_release"],
        "predictor_count": len(contract["predictors"]),
        "source_variable_count": len(variables),
        "schemas": results,
        "all_variables_present_in_both_releases": all(
            not result["missing"] for result in results.values()
        ),
        "labels": labels,
        "dtypes": dtypes,
    }


def main():
    contract = json.loads(CONFIG.read_text(encoding="utf-8"))
    schemas = {
        2024: load_schema(RAW / "pu2024_schema.json"),
        2025: load_schema(RAW / "pu2025_schema.json"),
    }
    result = validate_contract(contract, schemas)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    if not result["all_variables_present_in_both_releases"]:
        raise RuntimeError(
            "Predictor contract contains variables missing from a registered schema."
        )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
