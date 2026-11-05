# Feature Ablation

Milestone 5 includes a repeated feature-ablation analysis to test whether model performance depends heavily on one predictor or feature domain.

## Design

Each ablation uses:

- the same 10 household-grouped holdouts
- the same FINYR2-weighted regularized logistic regression
- the same preprocessing pipeline
- no hyperparameter retuning

The comparison therefore isolates the effect of removing feature blocks.

## Weighted mean results

### Poverty entry

| Variant | ROC-AUC | Average precision | Change in ROC-AUC | Change in AP |
| --- | ---: | ---: | ---: | ---: |
| Full 19-feature model | 0.718 | 0.127 | — | — |
| No baseline poverty ratio | 0.705 | 0.125 | -0.013 | -0.002 |
| No income-resource block | 0.705 | 0.124 | -0.013 | -0.003 |
| No asset block | 0.718 | 0.127 | +0.000 | -0.000 |
| No safety-net/housing block | 0.706 | 0.099 | -0.012 | **-0.028** |
| No demographic block | 0.720 | **0.133** | +0.002 | +0.006 |
| No demographics or assets | **0.720** | **0.133** | +0.002 | +0.006 |

### Poverty exit

| Variant | ROC-AUC | Average precision | Change in ROC-AUC | Change in AP |
| --- | ---: | ---: | ---: | ---: |
| Full 19-feature model | 0.706 | 0.691 | — | — |
| No baseline poverty ratio | 0.670 | 0.648 | **-0.036** | **-0.043** |
| No income-resource block | 0.665 | 0.644 | **-0.041** | **-0.047** |
| No asset block | 0.707 | 0.687 | +0.000 | -0.004 |
| No safety-net/housing block | 0.674 | 0.679 | -0.032 | -0.011 |
| No demographic block | **0.713** | **0.696** | +0.006 | +0.005 |
| No demographics or assets | 0.712 | 0.693 | +0.006 | +0.002 |

## Interpretation

The ablation results show that the model is **not** simply a proxy for baseline poverty ratio.

Baseline poverty ratio and the broader income-resource block matter substantially for predicting poverty exit, but their removal has a smaller effect on poverty-entry discrimination.

Housing and safety-net information is particularly useful for poverty entry. Removing that block reduces weighted average precision from 0.127 to 0.099.

The asset block contributes almost no incremental predictive value in this specification.

Most importantly, removing the demographic block—age, sex, race, Hispanic origin, U.S.-born status, and citizenship—does not harm performance. Mean discrimination and average precision improve slightly on both tasks.

## Combined lean specification

Removing the demographic and asset blocks together leaves a 10-feature model.

Compared with the full 19-feature specification, the combined lean model:

- raises weighted poverty-entry ROC-AUC from 0.718 to 0.720
- raises weighted poverty-entry average precision from 0.127 to 0.133
- raises weighted poverty-exit ROC-AUC from 0.706 to 0.712
- raises weighted poverty-exit average precision from 0.691 to 0.693
- improves Brier score and log loss on both tasks

The improvement is modest, but it is directionally consistent across all four probability/discrimination metrics.

## Policy-model implication

Demographic characteristics are therefore better positioned as **audit variables rather than predictive inputs** in the next model specification.

This separation has two advantages:

1. it simplifies the predictive model without sacrificing performance;
2. it preserves demographic fields for subgroup diagnostics without allowing them to directly determine predicted risk.

This result does not prove that the remaining features are free of indirect demographic correlation. Subgroup auditing remains necessary because non-demographic predictors can still encode structural differences.

## Next specification

The preferred candidate policy-facing specification is now defined in `config/policy_model.json`.

It:

- excludes demographic predictors from model fitting;
- retains demographic variables only for evaluation and subgroup auditing;
- excludes the asset block because it adds negligible incremental performance;
- retains education, employment, income, housing, and safety-net predictors.

The reduced specification should still be re-run through the full repeated validation and subgroup-diagnostic workflow before being treated as the final policy-facing benchmark.
