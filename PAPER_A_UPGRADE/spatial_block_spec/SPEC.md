# Specification: spatial block bootstrap for the provincial intervals (written before any computation)

Date: 3 November 2026. Status: APPROVED by the authors on 3 November 2026 (k = 12 and the six-region reference accepted); nothing has been run. Once approved, this file is hashed (SHA-256 recorded in SPEC.sha256) and not edited; changes go into a dated amendment.

## 1. Purpose
The reported intervals resample provinces one at a time and treat them as exchangeable, while the data are spatially dependent (Moran's I of Ookla Q2 2024 = 0.53). This analysis re-computes the intervals with resampling in spatial blocks and states which reported statements survive. It adds no new statistic and changes no point estimate.

## 2. Statistics covered (existing definitions, unchanged)
a. L1: difference of log growth factors, VNNIC minus Ookla, 2021 to 2024, four quarters (Table 2).
b. L3: matched-quarter Spearman correlations, their means and year-level values, and the 2021-to-2024 paired differences.
c. L4: Spearman correlation of log changes for the four core quarterly windows, the year-level change, and the 2022 Q2 start window.
d. 2023-to-2024: the four quarterly log-ratio differences, the four L4 correlations, and the difference of cross-window stability (the only rule that uses an interval), with and without April-May 2024.
Not covered: L2 (24 contrasts), outside-indicator tables S1-S2, half-year and fixed-footprint analyses, and the calendar restriction (it reports no intervals). These keep their province-bootstrap intervals and the existing "nominal" label.

## 3. Block definitions (two rules, one each, fixed now)
**Primary: neighbour blocks.** Project the 63 province centroids of CANONICAL_ADM1_63.geojson to UTM zone 48N (EPSG:32648). Apply Ward agglomerative clustering (squared Euclidean distance on the projected coordinates, no other features) and cut the tree at k = 12 clusters. The procedure is deterministic. k = 12 is fixed in advance (about five provinces per block); it is not tuned. Block sizes are reported descriptively. Singleton blocks are allowed; if the procedure fails technically it is reported and not re-run with another k.
**Reference: 6 administrative regions.** The 63 legacy provinces are assigned to the six socio-economic regions using an official Vietnamese source (General Statistics Office). The mapping table, its source, the document date and the access date are recorded in a file before any bootstrap is run, and shown to the authors for approval. The 8-region scheme is not used. With only six blocks this reference is coarse and its intervals are expected to be less reliable; it is reported for comparison, not as a second primary.

## 4. Resampling
B = 5000 draws; seed 20261010 (the seed of the existing analysis). In each draw, blocks are resampled with replacement until the number of blocks equals the number of blocks in the rule (12, or 6); every province of a drawn block enters with its values for both sources and all quantities (same draw for all statistics, as in the existing bootstrap). A draw may contain duplicated provinces; Spearman uses average ranks. The number of provinces per draw varies, so statistics are computed per draw. Intervals are 2.5th and 97.5th percentiles. Draws with an undefined statistic (for example all-tied ranks) are counted and reported, not dropped silently.

## 5. Coverage simulation (reuse, not extend)
Re-run the matched evaluation of Supplementary Note S1 on the same 63-province geometry: the same six Gaussian-field configurations (VNNIC and Ookla dependence parameters 0 and 0.81; indicator parameters 0.32, 0.71, 0.74), 2,000 datasets each, with the 12-block and the 6-region bootstrap in addition to the province bootstrap. Report empirical coverage of the nominal 95 percent interval for each method and setting. No new settings and no tuning of dependence parameters. The simulation concerns the correlation of a source with an outside indicator, the closest existing setting; it does not certify the L3 or L4 intervals, and the paper must say so.

## 6. Decision rules (fixed now)
R1. Every covered statistic is reported with the province, 12-block and 6-region intervals side by side.
R2. A statement that currently rests on "interval excludes zero" stays as written only if its 12-block interval also excludes zero. Otherwise it is reworded to "not resolved" in the text. The 6-region interval is read as a check: if it disagrees with the 12-block interval for a statement, the statement is also reworded as not resolved.
R3. The stability rule for 2023 to 2024 (difference negative with an interval excluding zero) was not retained under the province interval; it is re-evaluated under the 12-block interval and cannot become retained unless the 12-block interval excludes zero (block intervals are expected to be wider, so a change is not expected).
R4. Point estimates, thresholds, rules for sign variation and for reversal (which use point estimates) are unchanged.
R5. Reporting: results appear in a new supplementary note and in one sentence each in section 4.4 and Limitations. The Abstract changes only if a headline statement fails R2. No interval is described as validated for spatial coverage unless the simulation supports it for the statistic concerned.
R6. If the 12-block intervals change a conclusion, the manuscript is narrowed accordingly; the block rule is not changed.

## 7. Validation
A second implementation (explicit loop over draws, written separately from the vectorised version) must reproduce the 12-block and 6-region percentiles of at least L1 and L4 for the same seed. As before, this is a same-team check and is stated as such.

## 8. Outputs
New folder results_spatial_block_20261103 with: block assignments for both rules, draw-level statistics, interval table, coverage-simulation table, run log with SHA-256 of inputs, code and this specification. Code in PAPER_A_UPGRADE, added to the release branch only after the authors approve.

## 9. Open items before running
1. Authors approve k = 12 and the six-region reference.
2. Mapping table of 63 provinces to 6 regions with source (to be compiled and approved).
3. Confirm that the matched-evaluation code from Note S1 (reviewer_checks) can be reused unchanged for the added methods.
