# Measurement-Divergence Paper Protocol

Date locked: 2026-09-13  
Status: protocol only; manuscript not started  
Primary study path: `DESCRIPTIVE_MEASUREMENT_DIVERGENCE`

## 1. Working title

**Common Trends, Different Provincial Signals: Comparing VNNIC i-Speed and Ookla Fixed-Broadband Measurements across Vietnam, 2021–2024**

## 2. Research purpose

This paper studies whether two independently produced fixed-broadband measurement systems support the same descriptive conclusions at three distinct levels:

1. common national-direction trends across provinces;
2. cross-province dispersion;
3. province-specific levels, ranks, and relative changes.

It is a measurement paper. It does not estimate effects of broadband on enterprises or any other outcome.

## 3. Research questions

- **RQ1 — Common trend:** Do VNNIC and Ookla both show broad improvement in measured fixed-broadband download performance from 2021 to 2024?
- **RQ2 — Dispersion:** Do the sources agree on whether cross-province dispersion narrowed or widened?
- **RQ3 — Cross-sectional ranking:** Do the sources rank provinces similarly within each year?
- **RQ4 — Province-specific change:** Do they agree on which provinces improved more between 2021 and 2024?
- **RQ5 — Aggregation and composition:** Are rank and change conclusions robust to reasonable Ookla aggregation choices, leave-one-province-out checks, and observed tests/devices composition?

## 4. Constructs and measurement targets

### 4.1 VNNIC construct

Construct label: **published province-level fixed-broadband user-experience statistic**.

Observed measure: VNNIC i-Speed province-month FTTH download statistic, documented as a median in Mbps and published only when the locality-month meets a minimum 30-sample rule. The main historical description uses the unweighted median of April–December monthly values. Matched cross-source validation uses April–June only.

The measure is not interpreted as physical infrastructure capacity, household coverage, population-weighted quality, or operator rollout. Test/device composition and retrospective revision policy remain incompletely documented.

### 4.2 Ookla construct

Construct label: **spatial distribution of observed fixed-broadband Speedtest tile performance**.

Observed primary measure: province-level unweighted median of zoom-16 tile `avg_d_kbps / 1000` for fixed Q2, 2021–2024. `avg_d_kbps` is an average across tests within each observed tile; the province aggregate is therefore a spatial tile median, not a median across people, firms, tests, households, or devices.

Sensitivity measures are the unweighted tile mean, tests-weighted mean, and devices-weighted mean. None is promoted to the primary construct because it agrees more closely with VNNIC.

### 4.3 Non-equivalence rule

The sources have different aggregation chains and participation processes. Similar labels or units do not imply a common estimand. Cross-source disagreement may reflect different constructs, sampling, aggregation, geography, or revision processes rather than error by either source.

## 5. Geography, period, and estimands

- Geography: fixed historical 63-province analytical reference, metadata `boundaryYear=2016`, distributed in geoBoundaries 2021 release.
- Period: 2021–2024.
- Main descriptive unit: province × year.
- VNNIC main period within year: April–December.
- Cross-source matched period: Q2, with VNNIC April–June.
- Average-province estimand: provinces receive equal weight.
- Ookla primary spatial estimand: unweighted median across observed assigned tiles within province-quarter.
- No population, enterprise, test, or device weighting in the primary comparison.
- No imputation, winsorization, discretionary exclusion, or rank-based sample deletion.

## 6. Locked descriptive propositions

- **P1:** Both sources show broad upward movement in measured fixed-broadband download performance across provinces from 2021 to 2024.
- **P2:** Most preregistered dispersion indicators point toward greater cross-province dispersion over the period in both sources.
- **P3:** Cross-source agreement is materially weaker for yearly provincial ranks than for the common trend.
- **P4:** Cross-source agreement is weak or opposing for province-specific relative improvement ranks.
- **P5:** Reasonable Ookla aggregation alternatives do not restore robust province-specific change agreement.
- **P6:** Observed changes in tests and devices remain a material measurement-composition concern.

These are descriptive measurement claims. They do not imply policy effects, infrastructure activation, enterprise effects, or causality.

## 7. Central claim and claim ladder

Permitted central claim:

> Vietnam recorded broad improvement in measured fixed-broadband performance and increasing cross-province dispersion according to both VNNIC and Ookla. However, provincial rankings and relative improvement intensity depend materially on the measurement source.

Claim ladder:

1. **Documented fact:** sources, files, hashes, units, time windows, geographic assignment, and coverage.
2. **Within-source description:** levels, distributions, ranks, changes, and dispersion.
3. **Cross-source measurement comparison:** common trend, dispersion direction, rank agreement, change agreement, and aggregation sensitivity.
4. **Construct interpretation:** evidence is consistent with distinct measurement estimands and participation processes.

Prohibited ladder steps:

- connectivity caused enterprise change;
- one source is the true measure because it is favorable;
- observed tiles equal geographic or population coverage;
- weighting removes composition bias;
- Decision 2269 or another policy caused the common trend or divergence;
- rank disagreement proves source error.

Maximum claim level: `DESCRIPTIVE_MEASUREMENT`.

## 8. Evidence decomposition

The manuscript must keep these layers separate and must not collapse them into a single convergence score:

- **Common trend agreement:** sign and breadth of 2021–2024 change.
- **Dispersion agreement:** direction across six declared dispersion statistics.
- **Cross-sectional level/rank agreement:** yearly Spearman and log-level Pearson.
- **Province-specific change agreement:** sign agreement and change-rank Spearman.
- **Composition sensitivity:** relationships with observed tiles, tests, and devices.

## 9. Tables authorized for the manuscript

- `table_02_connectivity_summary_by_year.csv`
- `table_04_connectivity_dispersion.csv`
- `table_05_connectivity_rank_persistence.csv`
- `table_06_connectivity_quartile_transitions.csv`
- connectivity rows only from `table_07_change_distributions.csv`
- `table_08_measurement_validation_by_year.csv`
- `table_09_measurement_change_concordance.csv`
- `table_10_dispersion_source_comparison.csv`
- `table_11_ookla_aggregation_sensitivity.csv`
- `table_12_aggregation_agreement.csv`
- `table_13_measurement_influence_audit.csv`
- `table_14_composition_sensitivity.csv`

Enterprise rows, enterprise tables, and enterprise outcomes are prohibited.

## 10. Figures authorized for the manuscript

- Figures 01–05: VNNIC connectivity distribution, trend, maps, change, and rank mobility.
- Figures 10–12: cross-source rank, change, and dispersion comparisons.

Figures 06–09 and any enterprise-related figure are prohibited. The enterprise-oriented theoretical conceptual-framework figure is not part of this paper.

New manuscript figures may only be deterministic transformations of authorized connectivity tables and must have companion data and lineage. No new raw Ookla partition may be opened during manuscript drafting.

## 11. Robustness inventory

Mandatory robustness reporting:

- four Ookla aggregation variants reported symmetrically;
- matched Q2 VNNIC comparison as primary cross-source timing;
- April–December VNNIC comparison labeled temporal-mismatch sensitivity;
- six dispersion measures shown together;
- yearly rank agreement and 2021–2024 change-rank agreement kept separate;
- leave-one-province-out ranges with every province retained;
- tests/devices composition diagnostics using Pearson and Spearman;
- exact 63-province coverage and assignment accounting;
- source-vintage and retrospective-revision limitations;
- centroid assignment and observed-tile estimand limitations.

No robustness result may replace the primary definition because it appears more favorable.

## 12. Counter-hypotheses and rival interpretations

- **CH3 — Speed-test composition:** `HEIGHTENED_CONCERN_PENDING_REVIEW`. Both sources depend on voluntary participation; Ookla speed changes co-vary with tests/devices changes. This cannot be marked eliminated.
- **Different-estimand interpretation:** VNNIC province-month publication and Ookla spatial-tile aggregation may represent distinct user/sample/geographic mixtures.
- **Aggregation interpretation:** rankings may vary because averaging within tiles and aggregating tiles give different implicit weights.
- **Revision interpretation:** retrospective revisions may differ across systems.
- **Boundary interpretation:** centroid assignment can differ from area allocation near borders, although no ambiguous centroid entered the pilot aggregates.

The paper may compare plausibility and observable implications but cannot identify a single cause of divergence.

## 13. Quality and lineage requirements

Every reported number must trace to the authoritative Stage A artifacts and their hashes. Manuscript build must fail if:

- the canonical geometry, panel, VNNIC facts, Ookla aggregates, or measurement-decision hashes drift;
- an enterprise outcome is referenced as analytical evidence;
- a mobile or unauthorized Ookla partition appears;
- the original `MIXED_MEASUREMENT_SUPPORT` decision or failed rank threshold is overwritten;
- CH3 is weakened below `HEIGHTENED_CONCERN_PENDING_REVIEW` without a new independent protocol;
- any province is silently excluded;
- causal or enterprise-effect wording appears;
- a table/figure lacks lineage or companion data.

## 14. Manuscript structure

1. Introduction: why agreement among measurement systems matters.
2. Institutional and measurement context.
3. Data provenance and distinct construct definitions.
4. Fixed geography and aggregation methods.
5. Within-source trends and dispersion.
6. Cross-source rank and change agreement.
7. Aggregation, influence, and composition diagnostics.
8. Interpretation as measurement divergence.
9. Limitations.
10. Conclusion with descriptive claim ceiling.

## 15. Governance state

```text
PRIMARY_STUDY_PATH = DESCRIPTIVE_MEASUREMENT_DIVERGENCE
H2_RECOVERY_PATH = SEPARATE_PROTOCOL_REQUIRED
H2_STATUS = NOT_TESTABLE_WITH_CURRENT_EXPOSURE
MODEL_RUN = false
CAUSAL_GATE = CLOSED
MANUSCRIPT_STATUS = NOT_STARTED_PROTOCOL_LOCK_REQUIRED
```

Drafting may begin only after this protocol is hashed, its artifact allow-list validates, and the protocol validator passes.
