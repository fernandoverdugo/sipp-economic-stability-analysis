# Executive Summary

## What this project asks

How often do U.S. adults move into or out of poverty from one year to the next, and how well can baseline economic conditions identify who is at elevated risk of a subsequent poverty transition?

This project uses the **2024 and 2025 Survey of Income and Program Participation (SIPP)** to follow the same adults longitudinally from the 2023 reference year into the 2024 reference year.

## Population findings

The validated longitudinal adult cohort contains **15,034 people**.

Using the Census two-year longitudinal weight and all **240 replicate weights** with Fay's BRR variance estimation:

- **4.05%** of adults above poverty at baseline entered poverty the following year.
- **48.43%** of adults below poverty at baseline exited poverty the following year.
- Baseline poverty prevalence was **10.07%**.
- Follow-up poverty prevalence was **8.84%**.

These are design-based population estimates with replicate-weight standard errors and confidence intervals.

## Predictive findings

The preferred policy-facing model is a weighted regularized logistic regression using **10 baseline features** drawn from:

- education
- employment
- earnings and personal income
- baseline income-to-poverty ratio
- housing tenure
- housing assistance
- SNAP receipt

Across ten household-grouped holdouts, the model averages:

| Task | Weighted ROC-AUC | Weighted average precision | Brier score | Log loss |
| --- | ---: | ---: | ---: | ---: |
| Poverty entry | **0.720** | **0.133** | **0.0394** | **0.1640** |
| Poverty exit | **0.712** | **0.693** | **0.2170** | **0.6251** |

The model therefore demonstrates moderate prospective discrimination without relying on demographic characteristics as predictive inputs.

## Why the final model is deliberately lean

The original feature contract contained 19 predictors.

Repeated ablation showed that:

- removing demographic predictors slightly **improved** performance;
- removing asset variables had essentially no performance cost;
- income and poverty-position measures materially support poverty-exit prediction;
- housing and safety-net information materially support poverty-entry prediction.

The final policy-facing specification therefore excludes:

- age
- sex
- race
- Hispanic origin
- nativity
- citizenship
- net worth
- assets
- debt

Demographic variables remain available exclusively for **subgroup auditing**.

## Operational interpretation

On the fixed policy-diagnostics holdout:

- the highest-risk **10%** contains **32.1%** of observed poverty entries;
- the highest-risk **20%** contains **48.7%** of observed poverty entries.

Weighted capture rates are lower but still concentrated at **27.1%** and **41.1%**, respectively.

This suggests the model can meaningfully rank prospective entry risk, but it is not designed to make automatic eligibility or denial decisions.

## Responsible-use findings

Repeated subgroup validation identifies performance differences that warrant monitoring.

For example:

- weighted poverty-entry ROC-AUC averages **0.661** for ages 18–29 versus **0.759** for ages 45–59;
- weighted poverty-exit ROC-AUC averages **0.620** for ages 75+ versus **0.754** for ages 60–74.

The repository treats these as model-review signals rather than causal or fairness conclusions.

## Technical strengths

The project includes:

- official Census source registration and asset verification
- streaming processing of 4,000+ column SIPP files
- longitudinal linkage on `SSUID + PNUM`
- two-year longitudinal weights
- 240 replicate weights
- Fay BRR uncertainty estimation
- leakage-safe baseline feature construction
- household-grouped train/test separation
- weighted and unweighted predictive evaluation
- calibration testing
- nonlinear gradient-boosting comparison
- risk-concentration analysis
- subgroup auditing
- repeated subgroup validation
- feature ablation
- reproducible GitHub Actions workflows

## Bottom line

The analysis follows a complete public-policy analytics workflow rather than stopping at classifier training.

It moves from survey design and population inference through prospective modeling, validation, responsible-use diagnostics, and model simplification, ending with a more interpretable policy-facing specification that performs slightly better than the larger original model while excluding demographic characteristics from prediction.
