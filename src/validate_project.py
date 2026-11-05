import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def markdown_paths(text):
    targets = re.findall(r"!?(?:\[[^\]]*\])\(([^)]+)\)", text)
    result = []
    for target in targets:
        target = target.strip()
        if (
            target.startswith("http://")
            or target.startswith("https://")
            or target.startswith("#")
            or target.startswith("mailto:")
        ):
            continue
        path = target.split("#", 1)[0]
        if path:
            result.append(path)
    return result


def validate_markdown_links():
    missing = []
    markdown_files = [ROOT / "README.md"] + sorted(
        (ROOT / "docs").glob("*.md")
    )

    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8")
        for target in markdown_paths(text):
            resolved = (markdown.parent / target).resolve()
            if not resolved.exists():
                missing.append(
                    f"{markdown.relative_to(ROOT)} -> {target}"
                )

    return missing


def validate_policy_model():
    config = json.loads(
        (ROOT / "config" / "policy_model.json").read_text(
            encoding="utf-8"
        )
    )
    results = json.loads(
        (
            ROOT
            / "data"
            / "metadata"
            / "policy_model_validation.json"
        ).read_text(encoding="utf-8")
    )

    if config["status"] != "validated_preferred_policy_benchmark":
        raise RuntimeError("Policy model is not marked as validated.")

    if len(config["model_features"]) != 10:
        raise RuntimeError("Policy model must contain 10 features.")

    if set(config["model_features"]) & set(config["audit_only_features"]):
        raise RuntimeError(
            "Predictive and audit-only feature sets overlap."
        )

    if results["feature_count"] != len(config["model_features"]):
        raise RuntimeError(
            "Policy validation feature count does not match config."
        )

    result_features = set(results["features"])
    if result_features != set(config["model_features"]):
        raise RuntimeError(
            "Validated feature set does not match policy config."
        )

    for task in ("poverty_entry", "poverty_exit"):
        config_metrics = config["validation"]["weighted_metrics"][task]
        result_metrics = results["tasks"][task]["metrics"]["weighted"]

        for metric, expected in config_metrics.items():
            actual = result_metrics[metric]["mean"]
            if abs(actual - expected) > 1e-12:
                raise RuntimeError(
                    f"{task} {metric} differs between config and results."
                )


def validate_required_artifacts():
    required = [
        "data/metadata/panel_profile.json",
        "data/metadata/transition_analysis.json",
        "data/metadata/feature_profile.json",
        "data/metadata/model_validation.json",
        "data/metadata/calibration_analysis.json",
        "data/metadata/boosting_benchmark.json",
        "data/metadata/policy_diagnostics.json",
        "data/metadata/subgroup_validation.json",
        "data/metadata/feature_ablation.json",
        "data/metadata/policy_model_validation.json",
        "data/metadata/policy_model_subgroups.json",
        "docs/EXECUTIVE_SUMMARY.md",
        "docs/figures/transition_rates.svg",
        "docs/figures/policy_model_performance.svg",
        "docs/figures/entry_risk_concentration.svg",
    ]

    missing = [
        path
        for path in required
        if not (ROOT / path).exists()
    ]

    if missing:
        raise RuntimeError(
            "Missing required project artifacts: "
            + ", ".join(missing)
        )


def main():
    validate_required_artifacts()
    validate_policy_model()

    missing_links = validate_markdown_links()
    if missing_links:
        raise RuntimeError(
            "Broken internal markdown links:\n"
            + "\n".join(missing_links)
        )

    print("Project quality validation passed.")


if __name__ == "__main__":
    main()
