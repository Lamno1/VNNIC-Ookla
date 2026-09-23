# Robustness diagnostics supplement (post-hoc, resubmission)

Label: **POST_HOC_ROBUSTNESS_DIAGNOSTIC**. Read-only script over the frozen processed sources already declared allowed in `s11_measurement_review.py`. Does not modify the locked ledger, gate outputs, or any existing table.

## 1. Bootstrap 95% CIs for yearly Spearman rank correlation (primary variant: unweighted_tile_median)

| Year | N | Point estimate | Bootstrap 95% CI |
|---|---|---|---|
| 2021 | 63 | 0.542 | [0.333, 0.705] |
| 2022 | 63 | 0.488 | [0.223, 0.704] |
| 2023 | 63 | 0.296 | [0.060, 0.505] |
| 2024 | 63 | 0.248 | [-0.006, 0.489] |

## 2. Bootstrap 95% CI for the 2021-2024 change-rank correlation, all four Ookla aggregation variants

| Variant | N | Point estimate | Bootstrap 95% CI |
|---|---|---|---|
| unweighted_tile_median | 63 | -0.247 | [-0.474, 0.004] |
| unweighted_tile_mean | 63 | -0.193 | [-0.432, 0.053] |
| tests_weighted_mean | 63 | -0.178 | [-0.411, 0.079] |
| devices_weighted_mean | 63 | -0.169 | [-0.398, 0.074] |

## 3. Formal trend test: is the yearly-correlation decline a real trend?

Block bootstrap (province-resampled, B=10,000) of the slope of Fisher z-transformed yearly Spearman correlations regressed on year.

| Variant | Slope (Fisher z / year) | Bootstrap 95% CI | Two-sided bootstrap p | Monotonic decline |
|---|---|---|---|---|
| unweighted_tile_median | -0.1290 | [-0.2451, -0.0134] | 0.0298 | True |
| unweighted_tile_mean | -0.0748 | [-0.1907, 0.0379] | 0.1960 | True |
| tests_weighted_mean | -0.0617 | [-0.1729, 0.0507] | 0.2838 | False |
| devices_weighted_mean | -0.0807 | [-0.1997, 0.0312] | 0.1538 | True |

Primary variant (unweighted_tile_median): slope = -0.1290 Fisher-z units per year, 95% CI [-0.2451, -0.0134], two-sided bootstrap p = 0.0298. The decline is statistically detectable.

## 4. Top/bottom-k overlap between VNNIC and Ookla (primary variant), k = 5, 10, 15

Chance baseline is the hypergeometric expectation k²/63 for two independent size-k subsets drawn from 63 provinces.

| Rule | k | Overlap | Overlap % | Chance expectation | Overlap / chance |
|---|---|---|---|---|---|
| smallest_2021_2024_gain | 5 | 1/5 | 20% | 0.40 | 2.52x |
| smallest_2021_2024_gain | 10 | 2/10 | 20% | 1.59 | 1.26x |
| smallest_2021_2024_gain | 15 | 4/15 | 27% | 3.57 | 1.12x |
| lowest_absolute_2024_level | 5 | 1/5 | 20% | 0.40 | 2.52x |
| lowest_absolute_2024_level | 10 | 4/10 | 40% | 1.59 | 2.52x |
| lowest_absolute_2024_level | 15 | 6/15 | 40% | 3.57 | 1.68x |

## Headline numbers for Results/Discussion

- Primary change-rank Spearman correlation: -0.247, bootstrap 95% CI [-0.474, 0.004] (province-resampled percentile bootstrap, B=10,000). Confirms the same conclusion as the analytic CI already reported: the interval spans zero.
- Yearly Spearman correlation falls from 0.542 (2021) to 0.248 (2024); bootstrap trend test p = 0.0298 for the null of no linear trend in Fisher-z space — the decline is statistically detectable.
- Bottom-10-by-gain overlap: 2/10 provinces (20%), versus a chance expectation of 1.59/10. Observed agreement is only 1.26x the chance baseline.
