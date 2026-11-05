# Policy Diagnostics

Milestone 5 translates the predictive benchmark into diagnostics that are more useful for public-program decision making.

## Purpose

Overall ROC-AUC is not enough to determine whether a risk model would be useful or responsible in a policy setting.

This stage asks:

1. How concentrated are observed poverty transitions among people assigned the highest predicted risk?
2. Does predictive performance differ materially across major demographic subgroups?
3. Are subgroup estimates supported by enough positive events to report responsibly?

## Model used

The diagnostics use the FINYR2-weighted regularized logistic regression.

The logistic model is used because:

- it is the stable interpretable benchmark across both tasks
- it remains the preferred model for poverty exit
- the nonlinear poverty-entry challenger improves ROC-AUC but not average precision
- one common benchmark makes subgroup comparisons easier to interpret

The diagnostics are descriptive predictive diagnostics, not causal estimates and not a recommendation for automated eligibility or service allocation.

## Holdout

The analysis uses the reproducible household-grouped holdout with:

- `GroupShuffleSplit`
- `SSUID` as the grouping variable
- random seed `699`
- 25% of household groups held out
- zero household overlap between train and test data

All diagnostics are computed on the untouched holdout.

## Risk concentration

The workflow ranks holdout observations by predicted probability and evaluates the:

- top 5%
- top 10%
- top 20%

For each slice it reports:

- number of people
- number of observed positive transitions
- share of all positive transitions captured
- FINYR2-weighted share of positive transitions captured
- mean predicted probability
- observed transition rate
- weighted observed transition rate

This provides a practical view of whether risk scores meaningfully concentrate future poverty transitions.

## Subgroup diagnostics

Performance is evaluated separately by:

- sex
- race
- Hispanic origin
- U.S.-born status
- age group

Age groups are:

- 18–29
- 30–44
- 45–59
- 60–74
- 75+

For each reportable subgroup, the workflow calculates weighted and unweighted ROC-AUC, average precision, Brier score, and log loss.

## Minimum reporting rule

Subgroup metrics are reported only when a holdout subgroup contains at least:

- 50 observations
- 10 positive outcome events

Groups below those thresholds are labeled `insufficient_events` instead of producing unstable headline metrics.

This rule is a reporting safeguard, not a statistical guarantee that every reported subgroup estimate is precise.

## Interpretation boundaries

These diagnostics should not be used to justify automatic targeting decisions.

A higher or lower subgroup metric can reflect:

- sample size
- outcome prevalence
- differences in predictor distributions
- measurement quality
- structural differences not represented by the feature set

The project treats subgroup diagnostics as signals for model review rather than evidence that any demographic characteristic causes economic instability.
