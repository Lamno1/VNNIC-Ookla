# Human Measurement Review Decision Ledger — 2026-09-13

Status: locked before post-hoc Stage A diagnostics.

All Stage A analyses are labeled `POST_HOC_MEASUREMENT_DIAGNOSTIC`. The original preregistered Ookla thresholds failed and remain failed. No diagnostic may retroactively promote the pilot to PASS.

## Locked human-review findings

1. Agreement that 63/63 provinces increased primarily confirms a common national upward trend.
2. Common-direction agreement does not establish reliable province rankings or relative improvement intensity.
3. The 2021–2024 change-rank Spearman of −0.247 indicates unstable province-specific change signals across sources.
4. H2 depends on between-province and within-province relative variation; change-rank disagreement therefore directly threatens exposure validity.
5. Ookla speed changes correlate with changes in tests (approximately 0.545) and devices (approximately 0.535), increasing composition concern.
6. VNNIC, Ookla, or an aggregation weighting must not be selected because it produces favorable results.

Interim status:

`CH3_SPEED_TEST_COMPOSITION = HEIGHTENED_CONCERN_PENDING_REVIEW`

This status cannot be lowered to resolved by a favorable post-hoc diagnostic. CH1, CH2 and CH4 are unchanged.

## Stage boundary

Stage A may read only existing connectivity measurement artifacts. Enterprise outcomes, WBES, PCI, raw Ookla partitions and models are prohibited. Stage B may run only if the Stage A machine-readable decision explicitly records `NEEDS_TEMPORAL_RELIABILITY_EXTENSION` and a separate authorized-file gate passes.
