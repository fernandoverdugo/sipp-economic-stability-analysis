# SIPP Economic Stability & Poverty Transitions

A longitudinal public-policy analysis using the U.S. Census Bureau Survey of Income and Program Participation (SIPP) to study how adults move into and out of poverty over time.

The project is designed as a methodological companion to the NHIS Healthcare Access Analysis, but it answers a different kind of question: **what happens next?**

Rather than classifying a cross-sectional outcome measured at the same time as its predictors, the SIPP design preserves temporal ordering by using baseline characteristics to study economic status in a subsequent survey year.

## Primary research question

> Which baseline economic, employment, demographic, and safety-net characteristics are associated with entering or exiting poverty over time among U.S. adults observed longitudinally in SIPP?

## Initial longitudinal design

The first analytical cohort uses respondents represented in both the **2024 and 2025 SIPP releases**.

- 2024 SIPP: reference period January–December 2023
- 2025 SIPP: reference period January–December 2024
- Census 2-year longitudinal weight: respondents with data in both releases
- Census 2-year longitudinal replicate weights: variance estimation for that same cohort

The project will use the Census longitudinal design rather than substituting cross-sectional survey weights for transition estimates.

## Primary outcomes

The initial annual transition framework defines four mutually exclusive states:

```text
above poverty → above poverty    stable_above_poverty
above poverty → poverty          entered_poverty
poverty       → above poverty    exited_poverty
poverty       → poverty          persistent_poverty
```

The exact poverty variable and threshold will be selected from official Census-created income-to-poverty measures after the SIPP dictionaries are programmatically reviewed.

The project will prefer an official Census-derived poverty measure rather than manually rebuilding poverty thresholds.

## Why SIPP

SIPP is specifically designed to measure changes in:

- income
- employment
- program participation
- health insurance
- assets and liabilities
- family and household composition
- material hardship
- economic well-being

Its longitudinal structure makes it possible to study **transitions and persistence**, not just one-time differences between groups.

## Methodological roadmap

### Population analysis

Estimate nationally representative transition rates using the Census two-year longitudinal weight.

Planned outputs include:

- overall poverty-entry rate
- overall poverty-exit rate
- persistent poverty
- stable-above-poverty prevalence
- subgroup transition estimates
- longitudinal replicate-weight uncertainty

### Prospective prediction

Baseline-year characteristics will be used to predict following-year outcomes.

Initial model families:

1. prevalence-only baseline
2. regularized logistic regression
3. gradient-boosting benchmark

Planned evaluation:

- ROC-AUC
- average precision
- Brier score
- calibration
- risk concentration
- subgroup diagnostics

Predictive models will be treated as **prospective risk-ranking tools**, not causal models.

## Candidate baseline domains

Potential predictor domains include:

- employment and labor-force status
- earned and unearned income
- public-program participation
- health insurance
- education
- household and family structure
- disability
- assets and liabilities
- nativity
- demographic characteristics

Predictors will be selected only after confirming their definitions and timing across releases.

## Survey inference

This project will explicitly separate descriptive population inference from predictive modeling.

Population estimates will use:

- Census two-year longitudinal weights
- Census longitudinal replicate weights
- documented replicate-weight variance estimation

Predictive models may use longitudinal weights as sample weights where appropriate, but model coefficients and machine-learning feature effects will not automatically be interpreted as population-causal estimates.

## Data architecture

The repository separates source registration, asset discovery, downloading, validation, and analysis:

```text
official Census release pages
          ↓
source registry
          ↓
asset discovery
          ↓
downloads + checksums
          ↓
schema validation
          ↓
2024 / 2025 person records
          ↓
longitudinal linkage
          ↓
2-year weights + replicate weights
          ↓
transition outcomes
          ↓
population inference + prospective modeling
```

Large raw Census files will not be committed to Git history.

## Current milestone

### Milestone 3 — longitudinal cohort construction
**Complete**

The official 2024 and 2025 SIPP primary files have now been linked to the Census two-year longitudinal and replicate-weight files.

Validated panel profile:

| Measure | Result |
| --- | ---: |
| 2024 unique persons | 36,915 |
| 2025 unique persons | 32,052 |
| Linked persons with longitudinal weights | 18,207 |
| Adult analytical cohort | **15,034** |

Initial weighted transition point estimates:

| Transition | Weighted share |
| --- | ---: |
| Stable above poverty | **86.28%** |
| Entered poverty | **3.65%** |
| Exited poverty | **4.88%** |
| Persistent poverty | **5.20%** |

Among adults above poverty at baseline, approximately **4.05%** entered poverty in the following year. Among adults below poverty at baseline, approximately **48.43%** exited poverty.

These are point estimates only; replicate-weight uncertainty is reserved for Milestone 4.

The panel builder validates annual-variable consistency across monthly SIPP records, links on `SSUID + PNUM`, checks `FINYR2` against `REPWGT0`, and writes the person-level panel outside Git history.

See [`docs/PANEL_CONSTRUCTION.md`](docs/PANEL_CONSTRUCTION.md) and [`data/metadata/panel_profile.json`](data/metadata/panel_profile.json).

## Planned milestones

### Milestone 1 — longitudinal design and source foundation
**Complete**

Research design, source provenance, transition-state logic, and reproducible source discovery.

### Milestone 2 — verified data acquisition
**Complete**

Verified official asset registry, downloader, checksum generation, remote probing, and schema validation.

### Milestone 3 — longitudinal cohort construction
**Complete**

Validated person-year collapse, `SSUID + PNUM` linkage, adult analytical cohort, longitudinal-weight integration, replicate full-weight validation, and transition-state construction.

### Milestone 4 — poverty transition analysis
**Next**

Select the official poverty measure, create transition outcomes, estimate weighted transition rates, and validate replicate-weight uncertainty.

### Milestone 5 — prospective prediction

Build baseline and machine-learning models using only baseline information to predict following-year poverty entry and exit.

### Milestone 6 — diagnostics and independent validation

Add calibration, subgroup diagnostics, risk concentration, sensitivity checks, and independent R validation of representative longitudinal estimates.

### Milestone 7 — extended dynamics

If supported cleanly by the data, expand to monthly hardship measures, event-history models, and the three- or four-year longitudinal cohorts.

## Responsible interpretation

This is an observational analysis.

The project will not interpret associations as causal effects of government programs or demographic characteristics.

Nativity may be examined descriptively, but SIPP does not identify refugees and foreign-born respondents will **not** be treated as a refugee proxy.

## Repository structure

```text
.
├── .github/workflows/
│   ├── panel-profile.yml
│   └── quality-checks.yml
├── config/
│   ├── assets.json
│   └── source_registry.json
├── data/
│   ├── metadata/
│   │   └── panel_profile.json
│   ├── processed/
│   └── raw/
├── docs/
│   ├── ACQUISITION.md
│   ├── DATA_SOURCES.md
│   ├── PANEL_CONSTRUCTION.md
│   ├── RESEARCH_DESIGN.md
│   └── VARIABLES.md
├── src/
│   ├── assets.py
│   ├── build_panel.py
│   ├── cohort.py
│   ├── download_assets.py
│   ├── registry.py
│   ├── source_discovery.py
│   ├── validate_schemas.py
│   └── verify_remote_assets.py
├── tests/
│   ├── test_milestone1.py
│   ├── test_milestone2.py
│   └── test_milestone3.py
├── .gitignore
├── requirements.txt
└── README.md
```

## Run locally

Create an environment and install the current dependencies:

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

Discover candidate assets from the registered official Census pages:

```bash
python src/source_discovery.py
```

The discovery output is written to:

```text
data/metadata/discovered_assets.json
```

No analytical microdata are committed to Git history.
