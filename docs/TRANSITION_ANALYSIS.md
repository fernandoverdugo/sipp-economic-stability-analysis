# Poverty Transition Analysis

Milestone 4 adds design-based uncertainty to the validated 2024→2025 SIPP longitudinal panel.

## Estimands

The analysis reports eight weighted proportions:

- stable above poverty
- entered poverty
- exited poverty
- persistent poverty
- baseline poverty prevalence
- follow-up poverty prevalence
- poverty entry among adults above poverty at baseline
- poverty exit among adults below poverty at baseline

All estimates use the Census two-year longitudinal person weight `FINYR2`.

## Replicate-weight variance

Variance estimation uses the 240 Census longitudinal replicate weights:

```text
REPWGT1 ... REPWGT240
```

SIPP replicate weights use Fay's balanced repeated replication method with a coefficient of 0.5. For an estimate `theta`, the project applies:

```text
Var(theta) = 1 / [G * (1 - k)^2] * sum((theta_r - theta)^2)
```

where:

- `G = 240`
- `k = 0.5`
- `theta_r` is the estimate computed with replicate `r`

With these values, the variance denominator is:

```text
240 * 0.5^2 = 60
```

This follows the Census SIPP replicate-weight methodology documented in the SIPP Users' Guide and source-and-accuracy materials.

Official methodology:

- https://www.census.gov/programs-surveys/sipp/methodology/weighting.html
- https://www2.census.gov/programs-surveys/sipp/tech-documentation/methodology/2022_SIPP_Users_Guide_SEP23.pdf

## Confidence intervals

The first implementation reports normal-approximation 95% confidence intervals:

```text
estimate ± 1.959964 * standard error
```

Because all current estimands are proportions, interval endpoints are bounded to `[0, 1]`.

The JSON output retains both the variance and standard error so that alternative interval methods can be evaluated later without changing the underlying replicate-weight calculations.

## Reproducible workflow

After the registered SIPP assets are downloaded and the panel is built:

```bash
python src/analyze_transitions.py
```

The committed aggregate output is:

```text
data/metadata/transition_analysis.json
```

No person-level microdata or replicate-weight records are committed.

## Interpretation

These estimates describe population-level poverty transitions for the longitudinal cohort represented by the Census two-year weight.

They do not identify causal effects of employment, public programs, demographic characteristics, or other exposures. Predictor associations and prospective models are reserved for later milestones.
