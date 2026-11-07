# Model Selection

Milestone 5 compares the initial regularized logistic benchmark with an untuned histogram gradient-boosting model using the same repeated household-grouped holdouts.

## Comparison design

Both models use:

- the same 19-feature contract
- the same ten `SSUID`-grouped holdouts
- the same `FINYR2` sample weights during fitting
- the same weighted and unweighted evaluation metrics
- no hyperparameter search

The boosting model is therefore treated as a complexity benchmark rather than a tuned challenger.

## Poverty entry

Mean repeated-holdout performance:

| Metric | Logistic | Boosting |
| --- | ---: | ---: |
| Unweighted ROC-AUC | 0.731 | **0.763** |
| Weighted ROC-AUC | 0.718 | **0.743** |
| Unweighted average precision | **0.158** | 0.153 |
| Weighted average precision | **0.127** | 0.120 |
| Unweighted Brier | 0.04137 | **0.04121** |
| Weighted Brier | **0.03960** | 0.03964 |
| Unweighted log loss | 0.17017 | **0.16534** |
| Weighted log loss | 0.16473 | **0.16224** |

Boosting improves ranking as measured by ROC-AUC and modestly improves log loss, but it does not improve average precision for the rare positive class.

For that reason the project does not declare boosting an unqualified replacement for logistic regression on poverty entry.

## Poverty exit

Mean repeated-holdout performance:

| Metric | Logistic | Boosting |
| --- | ---: | ---: |
| Unweighted ROC-AUC | **0.692** | 0.675 |
| Weighted ROC-AUC | **0.706** | 0.672 |
| Unweighted average precision | **0.679** | 0.653 |
| Weighted average precision | **0.691** | 0.655 |
| Unweighted Brier | **0.2232** | 0.2288 |
| Weighted Brier | **0.2188** | 0.2293 |
| Unweighted log loss | **0.6396** | 0.6501 |
| Weighted log loss | **0.6306** | 0.6512 |

Logistic regression is consistently better for poverty exit across discrimination and probability-accuracy metrics.

## Calibration result

A separate group-aware sigmoid-calibration experiment did not improve overall probability accuracy.

For poverty entry, calibrated probabilities produced essentially unchanged discrimination and negligible weighted log-loss improvement while slightly worsening Brier score.

For poverty exit, calibration worsened both Brier score and log loss.

The project therefore retains the raw logistic probabilities rather than adding a calibration layer that does not provide repeatable benefit.

## Current model-selection conclusion

The evidence supports a task-specific conclusion:

- **Poverty exit:** retain regularized logistic regression as the preferred benchmark.
- **Poverty entry:** retain logistic regression as the interpretable benchmark and histogram gradient boosting as a useful nonlinear challenger, because boosting improves ROC-AUC but not average precision.

This is preferable to selecting one algorithm solely because it is more complex.

## Final model-selection status

Those follow-up diagnostics are now complete. Repeated subgroup validation, risk concentration, calibration testing, and feature ablation all informed the final specification.

The preferred policy-facing model is the 10-feature regularized logistic regression defined in `config/policy_model.json`. Demographic variables are retained for auditing only, and asset variables are excluded because they add negligible incremental predictive value.

Histogram gradient boosting remains documented as a useful nonlinear challenger for poverty entry, but it is not the preferred policy-facing model because its higher ROC-AUC does not translate into better average precision for the rare entry outcome.
