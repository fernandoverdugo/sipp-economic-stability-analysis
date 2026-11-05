# Research Design

## Primary question

Which baseline economic, employment, demographic, and safety-net characteristics are associated with entering or exiting poverty over time among U.S. adults observed longitudinally in SIPP?

## Initial cohort

Milestone 1 targets the Census Bureau's two-year longitudinal cohort represented in both the 2024 and 2025 SIPP releases.

The 2024 SIPP release covers calendar year 2023. The 2025 SIPP release covers calendar year 2024. The initial analytical panel therefore follows the same eligible respondents across two consecutive reference years.

## Primary outcomes

The first analysis will construct mutually exclusive annual poverty-transition states:

- stable above poverty
- entered poverty
- exited poverty
- persistent poverty

The exact poverty variable and threshold will be selected from Census-created income-to-poverty measures after the data dictionaries are programmatically reviewed. The project will prefer an official Census-derived poverty measure rather than reconstructing poverty thresholds manually.

## Population inference

Population estimates will use the Census two-year longitudinal weight appropriate for respondents observed in both releases.

Variance estimation will use the corresponding Census longitudinal replicate weights. Replicate-weight methodology will be documented before inferential estimates are published.

Cross-sectional weights will not be substituted for longitudinal weights in transition estimates.

## Prospective modeling

The predictive design will preserve temporal ordering:

- predictors: baseline-year characteristics
- outcome: poverty status or transition in the following year

This is intentionally different from a cross-sectional classification problem. Predictors measured after the outcome period begins will be excluded from the prospective model.

Initial model families:

1. prevalence-only baseline
2. regularized logistic regression
3. gradient-boosting benchmark

Evaluation will emphasize discrimination, calibration, and risk concentration. Predictive results will not be interpreted causally.

## Candidate baseline domains

Potential baseline predictors include:

- employment and labor-force status
- earned and unearned income
- public-program participation
- health-insurance status
- education
- household and family structure
- disability
- assets and liabilities where appropriate
- nativity
- demographic characteristics

Variables will be selected only after confirming consistent definitions and timing across releases.

## Secondary analyses

After the poverty-transition pipeline is validated, the project may add:

- food-security measures
- missed rent or mortgage payments
- utility hardship
- persistent versus transient hardship
- monthly poverty spells
- discrete-time event-history models
- three- and four-year longitudinal cohorts

## Responsible interpretation

The project is observational. Associations and predictive importance will not be presented as causal effects of safety-net participation or demographic characteristics.

Nativity may be used for descriptive subgroup analysis, but SIPP does not identify refugees and this project will not treat foreign-born respondents as a refugee proxy.
