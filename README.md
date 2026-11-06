# SIPP Economic Stability & Poverty Transitions

A longitudinal public-policy analysis using the U.S. Census Bureau Survey of Income and Program Participation (SIPP) to measure annual poverty transitions and build prospective poverty-entry and poverty-exit models.

The project follows the same adults across the **2024 and 2025 SIPP releases**, preserving temporal ordering between baseline characteristics and following-year economic outcomes.

## Project snapshot

- **15,034** adults in the validated two-year longitudinal cohort
- **4.05%** poverty-entry rate among adults above poverty at baseline
- **48.43%** poverty-exit rate among adults below poverty at baseline
- **240** Census longitudinal replicate weights used for Fay-BRR uncertainty
- **10-feature** preferred policy-facing model
- weighted ROC-AUC: **0.720** for poverty entry and **0.712** for poverty exit
- demographic variables excluded from prediction and retained for subgroup auditing only

[Read the executive summary](docs/EXECUTIVE_SUMMARY.md)

![Weighted poverty transition estimates](docs/figures/transition_rates.svg)

## Research question

> Which baseline economic, employment, and safety-net characteristics are associated with entering or exiting poverty over time among U.S. adults observed longitudinally in SIPP?

## Longitudinal design

The analysis links respondents represented in both releases:

- **2024 SIPP:** January–December 2023 reference period
- **2025 SIPP:** January–December 2024 reference period
- linkage key: `SSUID + PNUM`
- population inference: Census two-year longitudinal person weight `FINYR2`
- variance estimation: `REPWGT1`–`REPWGT240`

Poverty status uses the Census annual family income-to-poverty ratio `TFCYINCPOV`, with poverty defined as a ratio below 1.0.

Four mutually exclusive annual transitions are constructed:

```text
above poverty → above poverty    stable_above_poverty
above poverty → poverty          entered_poverty
poverty       → above poverty    exited_poverty
poverty       → poverty          persistent_poverty
```

## Population findings

The adult analytical cohort contains **15,034 people**.

Design-based estimates use all 240 longitudinal replicate weights with Fay's BRR method.

| Estimand | Estimate | SE | 95% CI |
| --- | ---: | ---: | ---: |
| Stable above poverty | **86.28%** | 0.40 pp | 85.50–87.06% |
| Entered poverty | **3.65%** | 0.22 pp | 3.21–4.08% |
| Exited poverty | **4.88%** | 0.26 pp | 4.37–5.38% |
| Persistent poverty | **5.20%** | 0.22 pp | 4.76–5.63% |
| Baseline poverty prevalence | **10.07%** | 0.33 pp | 9.42–10.72% |
| Follow-up poverty prevalence | **8.84%** | 0.31 pp | 8.24–9.44% |
| Entry among baseline nonpoor adults | **4.05%** | 0.25 pp | 3.57–4.54% |
| Exit among baseline poor adults | **48.43%** | 1.72 pp | 45.06–51.81% |

See [Panel Construction](docs/PANEL_CONSTRUCTION.md) and [Transition Analysis](docs/TRANSITION_ANALYSIS.md).

## Prospective prediction

Two separate binary tasks are modeled:

1. **Poverty entry:** baseline nonpoor adults → entered poverty the following year
2. **Poverty exit:** baseline poor adults → exited poverty the following year

Modeling samples:

- poverty entry: **13,464 adults**, 587 positive cases
- poverty exit: **1,570 adults**, 757 positive cases

Train/test splits are grouped by `SSUID` so members of the same sampled household cannot appear on opposite sides of a holdout.

Preprocessing is learned inside the training pipeline only.

## Preferred policy-facing model

The final policy model is a FINYR2-weighted regularized logistic regression using 10 baseline features:

- education
- months employed
- months unemployed
- mean weekly hours
- annual personal earnings
- annual personal income
- baseline poverty ratio
- housing tenure
- housing-assistance status
- annual SNAP receipt

The specification is stored in [`config/policy_model.json`](config/policy_model.json).

![Validated policy model performance](docs/figures/policy_model_performance.svg)

Across 10 household-grouped holdouts:

| Task | Weighted ROC-AUC | Weighted average precision | Brier score | Log loss |
| --- | ---: | ---: | ---: | ---: |
| Poverty entry | **0.720** | **0.133** | **0.0394** | **0.1640** |
| Poverty exit | **0.712** | **0.693** | **0.2170** | **0.6251** |

## Model comparison and simplification

The project evaluates more than one modeling choice instead of selecting a model from a single favorable split.

### Logistic vs. gradient boosting

For poverty entry, histogram gradient boosting improves weighted ROC-AUC from **0.718 to 0.743**, but slightly reduces average precision.

For poverty exit, logistic regression performs better across ROC-AUC, average precision, Brier score, and log loss.

The project therefore retains logistic regression as the interpretable policy-facing benchmark and treats boosting as a nonlinear challenger rather than an automatic replacement.

### Feature ablation

Repeated feature ablation shows:

- removing demographic predictors slightly improves performance;
- removing asset variables has essentially no performance cost;
- income and baseline poverty position are important for poverty exit;
- housing and safety-net variables add meaningful signal for poverty entry.

A combined 10-feature specification excluding demographics and assets improves all four weighted metrics relative to the original 19-feature logistic model.

See [Feature Ablation](docs/FEATURE_ABLATION.md) and [Model Selection](docs/MODEL_SELECTION.md).

## Responsible-use design

Demographic fields are **not used to generate the preferred model's risk scores**.

The following fields are retained only for subgroup auditing:

- age
- sex
- race
- Hispanic origin
- nativity
- citizenship

This separation is supported by the ablation results rather than imposed after modeling.

It does not imply that the remaining predictors are free of indirect demographic correlation, so subgroup auditing remains part of the validation workflow.

## Risk concentration

On the fixed household-grouped policy-diagnostics holdout:

| Highest predicted-risk group | Observed entries captured | Weighted capture |
| --- | ---: | ---: |
| Top 5% | 20.5% | 14.9% |
| Top 10% | **32.1%** | **27.1%** |
| Top 20% | **48.7%** | **41.1%** |

![Poverty-entry risk concentration](docs/figures/entry_risk_concentration.svg)

These results show useful prospective concentration, but the model is **not** intended for automated eligibility, denial, enforcement, or other high-stakes individual decisions.

## Subgroup diagnostics

Repeated subgroup validation identifies performance differences that warrant review.

Examples:

- weighted entry ROC-AUC averages **0.661** for ages 18–29 versus **0.759** for ages 45–59;
- weighted exit ROC-AUC averages **0.620** for ages 75+ versus **0.754** for ages 60–74;
- sex-group discrimination is comparatively similar across repeated splits.

Subgroups without enough repeated event support are suppressed rather than assigned unstable headline metrics.

These results are model-review signals, not causal or fairness conclusions.

See [Policy Diagnostics](docs/POLICY_DIAGNOSTICS.md).

## Technical highlights

- official Census source registration and verification
- streaming processing for 4,000+ column SIPP files
- person-month to person-year collapse with consistency checks
- longitudinal linkage on `SSUID + PNUM`
- two-year longitudinal weights
- 240 replicate weights and Fay-BRR variance estimation
- leakage-safe feature construction
- household-grouped validation
- weighted and unweighted predictive metrics
- calibration testing
- nonlinear model benchmark
- risk-concentration analysis
- subgroup auditing and repeated subgroup validation
- feature ablation
- reproducible GitHub Actions workflows

## Repository layout

```text
.
├── .github/workflows/         reproducible validation workflows
├── config/
│   ├── assets.json
│   ├── policy_model.json      preferred 10-feature specification
│   ├── predictors.json        full baseline feature contract
│   └── source_registry.json
├── data/
│   ├── metadata/              committed aggregate results
│   ├── processed/             generated locally; not committed
│   └── raw/                   downloaded locally; not committed
├── docs/
│   ├── EXECUTIVE_SUMMARY.md
│   ├── FEATURE_ABLATION.md
│   ├── MODEL_SELECTION.md
│   ├── MODEL_VALIDATION.md
│   ├── PANEL_CONSTRUCTION.md
│   ├── POLICY_DIAGNOSTICS.md
│   ├── TRANSITION_ANALYSIS.md
│   └── figures/
├── src/                       analysis and validation code
├── tests/                     unit and milestone tests
├── requirements.txt
└── README.md
```

No analytical microdata are committed to Git history.

## Reproduce the analysis

Create an environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run tests:

```bash
python -m pytest -q
```

Download the registered Census assets:

```bash
python src/download_assets.py --mode all
```

Build the longitudinal panel and feature matrix:

```bash
python src/build_panel.py
python src/build_features.py
```

Run design-based transition analysis:

```bash
python src/analyze_transitions.py
```

Validate the preferred policy model:

```bash
python src/validate_policy_model.py
python src/audit_policy_model.py
```

## Documentation

- [Executive Summary](docs/EXECUTIVE_SUMMARY.md)
- [Research Design](docs/RESEARCH_DESIGN.md)
- [Data Sources](docs/DATA_SOURCES.md)
- [Panel Construction](docs/PANEL_CONSTRUCTION.md)
- [Transition Analysis](docs/TRANSITION_ANALYSIS.md)
- [Predictor Contract](docs/PREDICTOR_CONTRACT.md)
- [Baseline Modeling](docs/BASELINE_MODELING.md)
- [Model Validation](docs/MODEL_VALIDATION.md)
- [Model Selection](docs/MODEL_SELECTION.md)
- [Policy Diagnostics](docs/POLICY_DIAGNOSTICS.md)
- [Feature Ablation](docs/FEATURE_ABLATION.md)

## Interpretation boundaries

This is an observational analysis.

The project does not interpret associations as causal effects of government programs or demographic characteristics.

SIPP does not identify refugees. Foreign-born respondents are **not** treated as a refugee proxy.

The predictive models are intended as methodological demonstrations of prospective risk ranking and validation, not as decision systems for individual eligibility or service denial.

## Status

**Core analysis complete.**

Optional future extensions include external validation on a later SIPP release, event-history models for monthly transitions, material-hardship outcomes, and longer longitudinal cohorts.


## License

This project is released under the [MIT License](LICENSE).
