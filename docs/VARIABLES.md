# Initial Variable Contract

This document records the variables already confirmed as structurally necessary for the first longitudinal panel.

## Person linkage

### `SSUID`

Sample unit identifier. Census states that it may be used to match sample units across years.

### `PNUM`

Person number, unique within the sample unit.

The initial person key will therefore be:

```text
SSUID + PNUM
```

Linkage uniqueness will be tested independently in each release before merging.

## Annual poverty outcome

### `TFCYINCPOV`

Family income-to-poverty ratio for the calendar year, excluding Type 2 individuals.

File level: Person.

This is the preferred starting measure for the annual transition analysis because it is an official Census-created annual family poverty ratio rather than a manually reconstructed threshold.

Planned initial transition rule:

```text
poverty = TFCYINCPOV < 1.0
```

This rule remains provisional until the downloaded microdata are inspected for valid values, missingness, universe restrictions, and status flags.

## Longitudinal person weight

### `FINYR2`

Final person longitudinal weight for the two-year reference period.

The 2025 longitudinal-weight dictionary describes this as covering January 2023 through December 2024, corresponding to the reference periods represented by the 2024 and 2025 SIPP releases.

## Replicate weights

### `REPWGT0`

Full longitudinal person weight in the replicate file, equivalent to the corresponding final longitudinal weight.

### `REPWGT1`–`REPWGT240`

The 240 longitudinal replicate weights used for variance estimation.

The variance formula and Census replication factor will be documented and independently validated before confidence intervals are published.

## Next variable review

After the primary files are downloaded, the next pass will identify stable baseline predictors across these domains:

- age and sex
- race and ethnicity
- nativity and citizenship
- education
- employment and labor-force status
- earnings and other income
- SNAP/TANF/other program participation
- health insurance
- disability
- household composition
- assets and liabilities

Predictor selection will require consistent definitions and temporal ordering across the two releases.
