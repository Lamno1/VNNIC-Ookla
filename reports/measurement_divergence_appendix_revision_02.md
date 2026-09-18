# Supplementary Appendix for Common Trends and Different Provincial Signals

## A1 Evidence boundary

This appendix reports only previously generated connectivity measurement artifacts authorized by the locked paper protocol. All aggregation and influence checks are labeled `POST_HOC_MEASUREMENT_DIAGNOSTIC`. No additional raw partition was opened and no new statistical result was calculated for manuscript drafting.

## A2 Four Ookla aggregation rules

The primary statistic is the unweighted median of observed tile-level download values. The three sensitivity statistics are the unweighted tile mean, tests-weighted mean, and devices-weighted mean. Full province-year values appear in `table_11_ookla_aggregation_sensitivity.csv`; their cross-source diagnostics appear in `table_12_aggregation_agreement.csv`.

Across the four rules, change-rank Spearman correlations are -0.247, -0.193, -0.178, and -0.169, respectively. None supports a positive source-invariant ordering of province improvement. Because these are reasonable but substantively different weighting schemes, none is promoted based on closer agreement.

## A3 Leave-one-province-out audit

The complete leave-one-province-out results are preserved in `table_13_measurement_influence_audit.csv`. They cover yearly rank comparisons and 2021-to-2024 change-rank comparisons for all four aggregation variants. Every row has disposition `RETAINED`. The diagnostic therefore evaluates influence without changing the 63-province sample.

## A4 Composition diagnostics

The complete Pearson and Spearman diagnostics appear in `table_14_composition_sensitivity.csv`. For the primary tile median, speed change co-varies with changes in tests at 0.591 Pearson and 0.545 Spearman, and with changes in devices at 0.583 Pearson and 0.535 Spearman. Rank-based versions show the same material concern. These associations do not show that composition alone accounts for the cross-source disagreement, and weighting by tests or devices does not remove the concern.

## A5 Timing and dispersion robustness

The primary comparison matches Ookla Q2 to the April-June VNNIC median. The April-December VNNIC comparison is retained only as a temporally mismatched sensitivity. Six dispersion measures are shown together in `table_10_dispersion_source_comparison.csv`; five agree in their endpoint direction across sources. The original `MIXED_MEASUREMENT_SUPPORT` classification and failed rank thresholds remain unchanged.

## A6 Reproducibility inventory

The manuscript draws on the 12 tables and eight figures enumerated in the locked protocol. The figure set is Figures 1-5 and 10-12. Each figure has a companion CSV. Source hashes, manuscript claims, and every manuscript numeric statement are recorded in the manuscript audit artifacts for exact review.
