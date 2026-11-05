# Prospective Predictor Contract

Milestone 5 begins by freezing the candidate baseline information set before model development.

The contract is stored in:

```text
config/predictors.json
```

This separates research-design decisions from model code and makes leakage rules testable.

## Temporal rule

The prediction task is prospective:

```text
2023 baseline characteristics
        ↓
2024 poverty transition outcome
```

The repository uses the 2024 SIPP release for the 2023 reference year and the 2025 SIPP release for the 2024 reference year.

Only baseline information is eligible as a predictor. Follow-up variables, transition labels, and follow-up poverty status are prohibited from the feature matrix.

## Initial predictor domains

The first contract includes:

- demographics: age, sex, race, Hispanic origin
- education
- nativity and citizenship
- employment: monthly employment-status summaries and hours
- economic resources: earnings, personal income, baseline poverty ratio
- housing and selected safety-net measures
- assets, debt, and net worth

## Monthly variables

SIPP primary records are person-month records, so monthly measures are not treated as if they were annual constants.

The first feature-construction pass will derive:

- number of months employed
- number of months unemployed
- mean weekly hours
- annual earnings from monthly earnings
- annual personal income from monthly income
- any observed SNAP receipt from SNAP spell months

The precise code-to-category mapping for `RMESR` will be documented and tested before modeling.

## Explicit exclusions

The default feature matrix excludes:

- person and household identifiers
- follow-up-year variables
- transition and outcome fields
- longitudinal and replicate weights as predictors
- allocation and status flags as substantive predictors

Survey weights may still be supplied to model fitting or evaluation where methodologically appropriate.

## Leakage controls

Imputation, encoding, and scaling must be learned inside training folds rather than before train/test separation.

This is particularly important for regularized logistic regression and any model-selection workflow.

## Validation

After metadata assets are downloaded:

```bash
python src/validate_predictors.py
```

The validator checks every contracted source variable against both official Census schemas and writes:

```text
data/metadata/predictor_validation.json
```

The next Milestone 5 step is to construct these features from the baseline person-month records and report missingness and distribution diagnostics before fitting any predictive model.
