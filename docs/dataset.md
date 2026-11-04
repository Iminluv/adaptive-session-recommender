# REES46 Dataset Acquisition and Profile

**Status:** Phase 0 audit started; blocked before profiling/materialization because the source CSVs and Java runtime are unavailable.
**Last checked:** 2026-11-05

## Planned source

- Dataset: REES46 multi-category behavior data, with the October 2019 and November 2019 files only.
- Expected files: `2019-Oct.csv` and `2019-Nov.csv`.
- Source: [Kaggle dataset](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store); [REES46 datasets page](https://rees46.com/en/datasets).
- Local location: not acquired. Expected local destination: `data/raw/` (ignored by Git).
- Source URL/version, license/attribution, acquisition date, byte sizes, and SHA-256 checksums: pending acquisition.

## Phase 0 environment audit

Read-only checks performed on 2026-11-05:

| Item | Observed |
|---|---|
| Device | User-reported Mac M4, 16 GB RAM; runtime reports Apple Silicon `arm64` |
| Free disk | 88 GiB at `/Users/iminluv/Vscode/Bigdata` on `/dev/disk3s5` |
| Python | `python3` 3.11.9 |
| Java | `java -version` reports no Java runtime; `JAVA_HOME` is empty |
| PySpark | Not importable from the default `python3` environment (`ModuleNotFoundError`) |
| CSV presence | Neither expected CSV was found under the repository's `data/` directory or repository root |

The free-space figure is a point-in-time check and must be refreshed after download and before materialization. The project pins PySpark 3.5.8 in `pyproject.toml`; Spark work remains blocked until a compatible Java 17 runtime and project Python dependencies are available.

## Planned bounded sample

Use one deterministic predicate on non-null `user_id` for both source months, retaining every row for each selected user. The initial feasibility pilot is 0.1% of user IDs, for example:

```text
pmod(xxhash64(cast(user_id AS string)), 1000) = 0
```

Record the Spark version and exact expression in the run manifest. The 0.1% pilot is not presumed to support meaningful ALS metrics. Before interpreting ALS results, profile selected users, events by month, interactions per user/item, user/item coverage, and October/November overlap. The sample still requires downloading and scanning both raw CSVs; it only reduces downstream data materialization and model work.

## Data profile and processing record

Not yet run. The following remain pending until both source files and the runtime are available:

- file headers, bytes, checksums, event-time ranges, and source row counts;
- explicit UTC timestamp parsing using `yyyy-MM-dd HH:mm:ss z` and parse-failure reconciliation;
- event-type, null, invalid-price, identifier-cardinality, and interaction-skew profiles;
- October/November user, item, category, and brand overlap and cold-start coverage;
- the sampled row/user counts and ALS graph diagnostics;
- derived Parquet locations, row-count reconciliation, and run manifest.

Raw CSVs and generated Parquet must remain untracked under ignored local data paths. No source data has been downloaded, profiled, transformed, or committed.
