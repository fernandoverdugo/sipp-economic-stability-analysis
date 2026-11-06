# Model Validation

Milestone 5 hardens the initial logistic-regression benchmark before introducing more complex models.

## Why repeated validation

A single holdout can overstate or understate performance because results depend on which households land in the test set.

The validation workflow therefore repeats the household-grouped split ten times.

Each repeat uses:

- `GroupShuffleSplit`
- `SSUID` as the grouping variable
- 75% of household groups for training
- 25% for testing
- deterministic seeds 699 through 708
- zero household overlap

The repeated results report mean, standard deviation, minimum, and maximum for each metric.

## Survey-weighted sensitivity analysis

The validation stage uses the Census two-year longitudinal person weight `FINYR2`.

The logistic model is fit using `FINYR2` as `sample_weight`, and holdout metrics are reported twice:

1. unweighted predictive performance
2. longitudinal-weighted predictive performance

This does not turn the predictive model into a causal or design-based regression. It is a sensitivity analysis asking whether predictive conclusions materially change when observations are weighted toward the longitudinal population represented by SIPP.

## Metrics

Each split reports:

- ROC-AUC
- average precision
- Brier score
- log loss

Average precision is especially important for poverty entry because the positive class is relatively rare.

## Calibration

Calibration is evaluated in two ways.

### Calibration intercept and slope

Predicted probabilities are transformed to logits and regressed against the observed outcome.

Ideal values are approximately:

```text
intercept = 0
slope = 1
```

A nonzero intercept suggests systematic over- or underprediction. A slope below 1 can indicate predictions that are too extreme; a slope above 1 can indicate predictions that are not extreme enough.

### Probability-bin summaries

A representative holdout is divided into ten probability-ranked groups.

For each group the workflow reports:

- row count
- mean predicted probability
- observed outcome rate

Both weighted and unweighted versions are produced.

## Interpretation

Repeated validation is the main checkpoint for deciding whether the initial logistic model is stable enough to serve as the primary benchmark.

Gradient boosting should only be treated as an improvement if it demonstrates a repeatable gain in discrimination or calibration rather than a favorable result on one split.
