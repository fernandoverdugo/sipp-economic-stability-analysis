# Baseline Prospective Models

Milestone 5 begins with deliberately simple predictive baselines before any boosted-tree model or hyperparameter search.

## Tasks

Two binary prospective tasks are evaluated separately:

1. **Poverty entry** — adults above poverty at baseline; positive outcome is entering poverty in the following year.
2. **Poverty exit** — adults below poverty at baseline; positive outcome is exiting poverty in the following year.

The feature matrix uses only baseline-year information.

## Holdout design

Train/test separation is performed with `GroupShuffleSplit` using `SSUID` as the grouping variable.

This prevents people from the same sampled household from appearing in both the training and test sets.

Configuration:

- 75% of household groups for training
- 25% of household groups for testing
- fixed random state: `699`
- no household overlap

This first holdout is a reproducible benchmark, not the final uncertainty estimate for model performance.

## Preprocessing

All preprocessing is fit only on the training data.

Continuous predictors:

- median imputation
- missingness indicators
- standardization

Categorical predictors:

- most-frequent imputation
- one-hot encoding
- unseen test categories ignored safely

The pipeline therefore avoids fitting imputation, scaling, or encoding rules on the holdout set.

## Models

### Prevalence-only baseline

Every test case receives the training-set outcome prevalence as its predicted probability.

This establishes the minimum calibration/probability benchmark.

### L2-regularized logistic regression

The first substantive model uses:

- logistic regression
- L2 regularization
- `C=1.0`
- LBFGS optimization

No hyperparameter tuning is performed at this stage.

## Initial holdout results

| Task | Model | ROC-AUC | Average precision | Brier | Log loss |
| --- | --- | ---: | ---: | ---: | ---: |
| Poverty entry | Prevalence only | 0.500 | 0.046 | 0.0439 | 0.1866 |
| Poverty entry | Logistic regression | **0.724** | **0.176** | **0.0413** | **0.1703** |
| Poverty exit | Prevalence only | 0.500 | 0.516 | 0.2518 | 0.6968 |
| Poverty exit | Logistic regression | **0.724** | **0.719** | **0.2135** | **0.6160** |

The logistic model improves discrimination and probability accuracy on both tasks.

For the rarer poverty-entry outcome, average precision is especially important because ROC-AUC alone can look favorable under class imbalance.

## Interpretation

These results show that the baseline feature set contains prospective signal beyond outcome prevalence.

They do **not** establish causal relationships, and the coefficient ranking should not be interpreted as causal feature importance.

The next modeling stage should add:

- repeated or cross-validated household-grouped evaluation
- calibration diagnostics
- weighted sensitivity analysis
- gradient boosting benchmark
- subgroup diagnostics

The single fixed holdout remains useful as a stable portfolio benchmark while those richer diagnostics are developed.
