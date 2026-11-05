# Data Sources

All analytical data will come from official U.S. Census Bureau Survey of Income and Program Participation releases.

## 2024 SIPP

Official release page:

https://www.census.gov/data/datasets/2024/demo/sipp/2024-data.html

Role in the initial design:

- baseline survey release
- reference period: January through December 2023
- person-level characteristics used to define baseline status and predictors

## 2025 SIPP

Official release page:

https://www.census.gov/data/datasets/2025/demo/sipp/2025-data.html

Role in the initial design:

- follow-up survey release
- reference period: January through December 2024
- follow-up poverty status
- source for the Census two-year longitudinal weight
- source for the corresponding longitudinal replicate weights

The Census Bureau identifies the two-year longitudinal group as respondents with data in both the 2024 and 2025 SIPP files.

## Why source discovery is separate from analysis

Census publishes multiple formats and supporting files for each release. The project therefore separates:

1. authoritative release-page registration
2. asset discovery
3. asset download
4. checksum and schema validation
5. analytical processing

This avoids hard-coding an unverified download URL into the analysis pipeline.

## Raw-data policy

Large Census microdata files will not be committed to Git history.

The repository will retain:

- source registry
- discovery metadata
- checksums
- schemas
- processing code
- aggregate analytical outputs

Raw source files will remain reproducibly downloadable from Census.
