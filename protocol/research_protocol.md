# Frozen Research Protocol

Protocol status: `FROZEN_BEFORE_MODEL_RESULTS`

## Research question

Did fixed-broadband quality converge or diverge across Vietnam's 63 historical provinces during 2021–2024, and were within-province improvements associated with enterprise density and enterprise entry in the same or following year?

This is a measurement, descriptive, and associational study. It is not a causal evaluation of Decision 2269/QD-TTg.

## Design

- Unit: province × year.
- Geography: fixed historical 63-province system.
- Period: 2021–2024.
- Estimand: average-province association, unweighted across provinces.
- Canonical key: `province_id_legacy63`, constructed from the audited crosswalk; province names are labels only.
- Canonical spatial input: `D:\Q1_RESEARCH\GIS_DERIVED\CANONICAL_ADM1_63.geojson`.
- Canonical boundary SHA256: `c64a07c3fd5d3ca0339a5002983dc76ddd60a0ef88e889522e37ca2408f74400`.
- Boundary description: geoBoundaries ADM1 geometry distributed in the 2021 release, metadata `boundaryYear=2016`, used as a fixed analytical reference.

## Primary exposure

- Source: VNNIC i-Speed.
- Network: FTTH only.
- Variable: annual unweighted median of monthly `download`.
- Window: April through December in each year 2021–2024.
- Completeness: exactly nine distinct monthly observations per province-year.
- Expected complete input: 63 × 4 × 9 = 2,268 province-month observations.
- `value` is retained as `value_raw` and is not used as a weight unless an authoritative codebook verifies its meaning.
- If the definition or unit of `download` is not verified, G2 fails and model construction stops.

Secondary connectivity measures are FTTH upload, ping, and jitter. Mobile is descriptive appendix material only. Ookla is an independent convergent-measurement check, never treatment.

## Outcomes

Primary outcome: active enterprises per 1,000 population from NSO table V05.05.

Secondary outcome: newly registered enterprises in year t from V05.02 divided by active enterprises in year t-1 from V05.04. The rate is not constructed unless numerator, denominator, units, coverage, and timing are verified compatible.

Exploratory outcomes may include employment, revenue, wages/worker income, pretax profit, and profit rate. Monetary outcomes require verified unit, nominal/real basis, and an official deflator. Exploratory outcome families require a declared multiple-testing adjustment; default is Benjamini–Hochberg false-discovery-rate control within each declared family.

## Missing-data and transformation policy

- Construct an explicit 63 × 4 skeleton of exactly 252 rows.
- Preserve missing data as null; never convert missing values to zero.
- No silent imputation, fuzzy matching, row deletion, or sample substitution.
- Every exclusion receives a reason code and lineage.
- Do not invent offsets for nonpositive values. If a logged primary variable is nonpositive, stop and document it.
- Deterministic sorting is required for every artifact.

## Primary specification

`log(active_firms_per_1000_pt) = province FE + year FE + beta × log(FTTH_download_p,t-1) + error_pt`

- Standard errors clustered by province.
- Beta is reported only as a conditional within-province association.
- Required disclosure: estimate, confidence interval, standard error, N, province count, year count, within variation, exact sample, and lag-induced loss.
- Contemporaneous exposure is a sensitivity analysis.
- Specifications and controls may not be selected based on p-values.

## Robustness family

- Contemporaneous exposure.
- Leave-one-province-out range.
- Balanced-cell sensitivity.
- Models with and without only pre-declared, semantically verified covariates.
- VNNIC–Ookla measurement comparison.
- Reverse-timing and competing-explanation checks CH1–CH4 from the master specification.

## Claim policy

Maximum permitted claim: `ASSOCIATIONAL`.

Allowed: “associated with,” “co-moved with,” “conditional within-province association,” “descriptive evidence,” and “measurement convergence.”

Prohibited: causal effect, treatment effect, policy effect, impact of Decision 2269, or equivalent causal wording. Fixed effects, lags, significance, convergence across sources, or pre-trend diagnostics do not establish causality.

`CAUSAL_GATE = CLOSED`

`DECISION_2269_GATE = FAIL_PRIMARY_ROUTE`

## Stopping rules

- Any hard gate failure blocks dependent stages.
- G2 failure for VNNIC or NSO blocks panel modeling.
- G3–G6 must pass before creating the analysis panel.
- G1–G7 must pass before estimation.
- Any unsupported causal claim fails G8.
- Full Ookla processing is prohibited. Only a manifested fixed-broadband pilot, followed on explicit pilot PASS by fixed Q2 2021–2024, is in scope.
- Treatment eligibility/designation, publication dates, VNNIC changes, and Ookla changes may never be encoded as treatment.

## Amendments

This file is frozen before model results. Any change requires a dated entry in `plan_mutations.md`, a new protocol hash, the reason, affected artifacts, and whether prior outputs are invalidated. Silent rewriting is prohibited.
