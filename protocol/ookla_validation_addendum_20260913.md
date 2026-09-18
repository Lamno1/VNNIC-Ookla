# Ookla Measurement Validation Addendum — 2026-09-13

Status: frozen before spatial aggregation and validation results.

## Scope and identities

Only fixed-broadband Q2 files for 2021, 2022, 2023 and 2024 are authorized, with the paths, byte sizes, row counts and SHA256 identities stated in the measurement-validation sprint. The 2024Q2 file is processed first. The other three partitions may be processed only after the 2024 pilot passes. Mobile, other quarters, loose Parquet files and the full archive are prohibited.

Canonical geography is `CANONICAL_ADM1_63.geojson`, SHA256 `c64a07c3fd5d3ca0339a5002983dc76ddd60a0ef88e889522e37ca2408f74400`.

## Spatial and measurement rules

- Decode and audit zoom-16 quadkey centroids against `tile_x`/`tile_y`; use the supplied centroid coordinates after agreement is established.
- Filter to the canonical Vietnam total bounding box before deterministic point-in-polygon assignment.
- A point must be inside exactly one Polygon/MultiPolygon exterior and outside its holes. Boundary or multiple assignments are quarantined and excluded from aggregates.
- Convert `avg_d_kbps / 1000` to Mbps.
- Primary aggregate: unweighted median of observed tile-level download Mbps.
- Sensitivities: unweighted mean, tests-weighted mean, devices-weighted mean; retain tile, tests and devices accounting.
- Missing values are not imputed. Invalid or ambiguous rows never enter aggregates.

## Matched VNNIC rule

Primary comparison uses the unweighted median of VNNIC FTTH April, May and June in each province-year, with exactly three observations. The April–December exposure is secondary and carries a temporal-mismatch warning. `value` is not used.

## Resource and execution limits

- Sequential batches no larger than 250,000 rows; at most two workers (implementation uses one).
- Target peak RSS no greater than 4 GiB.
- Store province aggregates, manifests, accounting and deterministic audit samples only.
- Completed partitions use hash-bound checkpoints. No silently failed batch is permitted.

## Classification thresholds

`CONVERGENT_MEASUREMENT_SUPPORT` requires 63 provinces in all four years; annual Spearman at least 0.70 in at least three years and never below 0.50; at least 70% same direction for 2021–2024 change; at least four of six dispersion directions agree; and no reversal across all reasonable aggregate sensitivities. Coverage with materially inconsistent evidence is `MIXED_MEASUREMENT_SUPPORT`. Persistently weak rankings, mostly opposed changes, or conflicting dispersion is `NONCONVERGENT_MEASUREMENT`. Inadequate coverage is `INSUFFICIENT_MEASUREMENT_COVERAGE`. These are researcher-defined decision rules, not universal standards.

## Claim ceiling

Measurement validation only. Agreement cannot establish infrastructure activation, population coverage, treatment, enterprise effects or causality. H2 remains `REGISTERED_NOT_TESTED`. The VNNIC `DESCRIPTIVE_DIVERGENCE` classification is not overwritten.
