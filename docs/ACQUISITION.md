# Verified Data Acquisition

Milestone 2 converts the SIPP release pages into an explicit, reproducible acquisition manifest.

## Registered analytical assets

The project uses official Census Bureau files from the 2024 and 2025 SIPP releases.

### Primary microdata

- `pu2024_csv.zip`
- `pu2025_csv.zip`

These contain the person and person-month records required for baseline and follow-up measurement.

### Primary schemas and dictionaries

- 2024 and 2025 SIPP data dictionaries
- `pu2024_schema.json`
- `pu2025_schema.json`

The JSON schemas are used for machine validation before large microdata files are processed.

### Two-year longitudinal weights

The 2025 longitudinal-weight release provides the weight for respondents represented across the 2024 and 2025 SIPP files.

Required analytical fields:

- `SSUID`
- `PNUM`
- `SPANEL`
- `FINYR2`

`FINYR2` is the final person longitudinal weight covering the two-year reference period.

### Two-year longitudinal replicate weights

The companion replicate-weight file provides:

- linkage keys `SSUID` and `PNUM`
- `SPANEL`
- population-control date
- longitudinal-weight type
- initial and final reference years
- `REPWGT0`
- `REPWGT1` through `REPWGT240`

The project validates that all 240 replicate weights are present before survey-variance work is allowed to proceed.

## Poverty variable

The first annual poverty-transition outcome will use the official family income-to-poverty ratio:

`TFCYINCPOV`

This variable is stored on the person file and represents the family income-to-poverty ratio for the calendar year, excluding Type 2 individuals.

The initial poverty indicator will be based on an income-to-poverty ratio below 1.0, subject to final validation of coding, missingness, and Census guidance after the person files are downloaded.

## Download modes

### Metadata mode

```bash
python src/download_assets.py --mode metadata
```

Downloads lightweight dictionaries and JSON schemas and records SHA-256 checksums in:

```text
data/metadata/checksums.json
```

Large compressed microdata files are intentionally skipped.

### Full mode

```bash
python src/download_assets.py --mode all
```

Downloads every registered asset, including primary microdata and longitudinal weight ZIP files, and records a SHA-256 checksum for each file.

Raw files remain excluded from Git history.

## Remote verification

```bash
python src/verify_remote_assets.py
```

Uses byte-range requests to verify that every registered Census asset is reachable without downloading the full large file during routine CI.

## Schema validation

```bash
python src/validate_schemas.py
```

The validator requires:

- linkage keys in both primary releases
- annual family poverty ratio in both primary releases
- `FINYR2` in the longitudinal-weight schema
- `REPWGT0`
- exactly 240 longitudinal replicate weights

The output is written to:

```text
data/metadata/schema_validation.json
```

This lets the project fail before expensive downloads or analysis if Census changes a file layout unexpectedly.
