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


## Fixed-holdout findings

The seed-699 holdout contains 3,394 adults for the poverty-entry task, including 156 observed entries, and 395 adults for the poverty-exit task, including 204 observed exits.

### Risk concentration

| Task | Risk slice | Observed transitions captured | Weighted transitions captured | Observed rate in slice |
| --- | --- | ---: | ---: | ---: |
| Poverty entry | Top 5% | 20.5% | 14.9% | 18.8% |
| Poverty entry | Top 10% | 32.1% | 27.1% | 14.7% |
| Poverty entry | Top 20% | 48.7% | 41.1% | 11.2% |
| Poverty exit | Top 5% | 7.8% | 8.2% | 80.0% |
| Poverty exit | Top 10% | 15.7% | 17.4% | 80.0% |
| Poverty exit | Top 20% | 30.4% | 35.9% | 78.5% |

For poverty entry, the concentration results are operationally meaningful: the highest-risk 10% contains roughly one-third of observed entries in this holdout.

For poverty exit, the positive class is much more common, so capture rate should be read differently. The highest-scored 20% has a very high observed exit rate, but it necessarily captures a smaller fraction of all exits because exits occur across much of the baseline-poor population.

### Subgroup review signals

The fixed holdout shows meaningful variation in discrimination across some subgroups.

Examples from the weighted analysis include:

- poverty-entry ROC-AUC of 0.565 for ages 18–29 versus 0.774 for ages 45–59
- poverty-entry ROC-AUC of 0.522 for race code 2 versus 0.743 for race code 1
- poverty-exit ROC-AUC of 0.562 for ages 75+ versus 0.804 for ages 45–59

These differences are **review signals**, not final fairness conclusions.

Several subgroup cells contain relatively few positive events, and these results come from one fixed holdout. The next fairness-oriented step should therefore evaluate subgroup metrics across repeated household-grouped splits and summarize their uncertainty before making any stronger claim about differential performance.

Race, sex, Hispanic-origin, and nativity codes in the diagnostic JSON retain their underlying SIPP category codes. Interpretive labels should be added only from the official data dictionary rather than inferred from numeric order.
