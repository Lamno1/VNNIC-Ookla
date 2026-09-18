# Descriptive Analysis Addendum — 2026-09-13

Status: frozen before descriptive results.

## D1 and H1

D1 asks how the distribution of province-level FTTH download performance changed across the 63 historical provinces during 2021–2024.

H1: cross-province dispersion in log FTTH download performance was lower in 2024 than in 2021. This is a descriptive convergence/divergence hypothesis, not a causal or Decision 2269 claim.

## D2 and future H2

D2 asks how the distribution of active enterprises per 1,000 inhabitants changed across provinces during the same period.

H2: lagged province-level FTTH download performance is positively associated with active enterprises per 1,000 inhabitants.

`H2_STATUS = REGISTERED_NOT_TESTED`

## Locked rules

- Estimand: unweighted average province; no population weights.
- No imputation, winsorization, discretionary outlier deletion, or statistical significance testing.
- Natural logs only for strictly positive values.
- Maps use pooled bins shared across years, resolved from predeclared pooled quantiles.
- No bivariate connectivity–enterprise calculation, plot, table, or claim.
- No treatment, causal estimator, Ookla, WBES, PCI, or entry-intensity analysis.
- Raw sampling uncertainty is unavailable; no confidence intervals will be fabricated.

## Stopping rule

Hard input drift, incomplete lineage, an unauthorized bivariate statistic, or non-reproducible stable artifact blocks the descriptive gate.
