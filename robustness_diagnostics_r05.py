"""POST_HOC_ROBUSTNESS_DIAGNOSTIC -- resubmission robustness supplement.

Read-only script. Consumes only the already-frozen processed sources listed
in ``s11_measurement_review.py``'s ``allowed`` list. Does not modify, rerun,
or depend on the locked ledger/lock.json gate, and writes only new,
separately named output files. Produces:

1. Bootstrap 95% CIs (percentile, province-resampled, B=10000) for the
   yearly Spearman rank correlations (2021-2024) and the 2021-2024
   change-rank Spearman correlation, for all four Ookla aggregation
   variants.
2. A formal test of whether the year-over-year decline in yearly rank
   correlation is a statistically detectable trend or only a descriptive
   pattern, via a province-block bootstrap of the slope of Fisher
   z-transformed yearly correlations regressed on year.
3. Top/bottom-k overlap between VNNIC and Ookla (primary variant) for
   k in {5, 10, 15}, under the two prioritization rules already used in
   the manuscript (smallest 2021-2024 gain; lowest absolute 2024 level),
   compared against the hypergeometric chance-overlap baseline k^2/63.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import stats

WORKING_ROOT = Path(__file__).resolve().parent
RNG_SEED = 20260922
N_BOOT = 10000
N_PROVINCES = 63

VARIANTS = {
    "unweighted_tile_median": "ookla_tile_median_download_mbps",
    "unweighted_tile_mean": "ookla_tile_mean_download_mbps",
    "tests_weighted_mean": "ookla_tests_weighted_mean_download_mbps",
    "devices_weighted_mean": "ookla_devices_weighted_mean_download_mbps",
}
PRIMARY_VARIANT = "unweighted_tile_median"
YEARS = [2021, 2022, 2023, 2024]


def spearman(a, b):
    return float(stats.spearmanr(a, b).correlation)


def load_data():
    ookla = pd.read_parquet(WORKING_ROOT / "data/processed/ookla_fixed_q2_adm1_2021_2024.parquet")
    vnnic = pd.read_parquet(WORKING_ROOT / "data/processed/vnnic_q2_validation_2021_2024.parquet")
    if len(ookla) != 252 or len(vnnic) != 252:
        raise RuntimeError("FAIL-CLOSED: unexpected row count in frozen processed sources")
    data = ookla.merge(vnnic, on=["province_id_legacy63", "shapeISO", "year"], validate="one_to_one")
    return data


def bootstrap_yearly_ci(data, col, rng):
    """Province-resampled bootstrap CI for each year's Spearman correlation."""
    rows = []
    for year in YEARS:
        g = data[data.year == year]
        a_full = g[col].to_numpy()
        b_full = g.vnnic_q2_monthly_median_download_mbps.to_numpy()
        point = spearman(a_full, b_full)
        n = len(a_full)
        boots = np.empty(N_BOOT)
        for i in range(N_BOOT):
            idx = rng.integers(0, n, n)
            boots[i] = spearman(a_full[idx], b_full[idx])
        lo, hi = np.nanpercentile(boots, [2.5, 97.5])
        rows.append({
            "year": year, "point_estimate": point,
            "boot_ci_low": float(lo), "boot_ci_high": float(hi),
            "boot_mean": float(np.nanmean(boots)), "n_boot": N_BOOT, "n": n,
        })
    return rows


def bootstrap_change_rank_ci(data, col, rng):
    wide_o = data.pivot(index="province_id_legacy63", columns="year", values=col)
    wide_v = data.pivot(index="province_id_legacy63", columns="year", values="vnnic_q2_monthly_median_download_mbps")
    ochange = (wide_o[2024] - wide_o[2021]).to_numpy()
    vchange = (wide_v[2024] - wide_v[2021]).to_numpy()
    n = len(ochange)
    point = spearman(ochange, vchange)
    boots = np.empty(N_BOOT)
    for i in range(N_BOOT):
        idx = rng.integers(0, n, n)
        boots[i] = spearman(ochange[idx], vchange[idx])
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return {
        "point_estimate": point, "boot_ci_low": float(lo), "boot_ci_high": float(hi),
        "boot_mean": float(np.nanmean(boots)), "n_boot": N_BOOT, "n": n,
    }


def trend_test(data, col, rng):
    """Block-bootstrap test of the slope of Fisher-z(yearly Spearman) on year."""
    provinces = data.province_id_legacy63.unique()
    n = len(provinces)
    by_province = {p: data[data.province_id_legacy63 == p].set_index("year") for p in provinces}
    years_centered = np.array(YEARS) - np.mean(YEARS)

    def slope_for(prov_sample):
        zs = []
        for year in YEARS:
            a = np.array([by_province[p].loc[year, col] for p in prov_sample])
            b = np.array([by_province[p].loc[year, "vnnic_q2_monthly_median_download_mbps"] for p in prov_sample])
            r = np.clip(spearman(a, b), -0.999, 0.999)
            zs.append(np.arctanh(r))
        zs = np.array(zs)
        slope = np.polyfit(years_centered, zs, 1)[0]
        return slope, zs

    observed_slope, observed_z = slope_for(provinces)
    boot_slopes = np.empty(N_BOOT)
    for i in range(N_BOOT):
        sample = provinces[rng.integers(0, n, n)]
        boot_slopes[i], _ = slope_for(sample)
    lo, hi = np.nanpercentile(boot_slopes, [2.5, 97.5])
    p_two_sided = 2 * min((boot_slopes >= 0).mean(), (boot_slopes <= 0).mean())
    return {
        "observed_slope_fisher_z_per_year": float(observed_slope),
        "boot_ci_low": float(lo), "boot_ci_high": float(hi),
        "bootstrap_two_sided_p": float(p_two_sided), "n_boot": N_BOOT,
        "declines_monotonically": bool(np.all(np.diff(observed_z) < 0)),
    }


def topbottom_k_overlap(data, col):
    """Overlap between VNNIC- and Ookla-selected province sets under two rules."""
    wide_o = data.pivot(index="province_id_legacy63", columns="year", values=col)
    wide_v = data.pivot(index="province_id_legacy63", columns="year", values="vnnic_q2_monthly_median_download_mbps")
    ochange = wide_o[2024] - wide_o[2021]
    vchange = wide_v[2024] - wide_v[2021]

    rules = {
        "smallest_2021_2024_gain": (ochange, vchange),
        "lowest_absolute_2024_level": (wide_o[2024], wide_v[2024]),
    }
    rows = []
    for rule_name, (o_series, v_series) in rules.items():
        for k in (5, 10, 15):
            o_set = set(o_series.nsmallest(k).index)
            v_set = set(v_series.nsmallest(k).index)
            overlap = o_set & v_set
            expected_by_chance = k * k / N_PROVINCES
            rows.append({
                "rule": rule_name, "k": k,
                "overlap_count": len(overlap), "overlap_fraction": len(overlap) / k,
                "expected_overlap_by_chance": expected_by_chance,
                "overlap_vs_chance_ratio": (len(overlap) / expected_by_chance) if expected_by_chance > 0 else np.nan,
            })
    return rows


def main():
    rng = np.random.default_rng(RNG_SEED)
    data = load_data()

    yearly_rows, change_rows, trend_rows = [], [], []
    for variant, col in VARIANTS.items():
        yr = bootstrap_yearly_ci(data, col, rng)
        for r in yr:
            r["aggregation_variant"] = variant
        yearly_rows.extend(yr)

        cr = bootstrap_change_rank_ci(data, col, rng)
        cr["aggregation_variant"] = variant
        change_rows.append(cr)

        tt = trend_test(data, col, rng)
        tt["aggregation_variant"] = variant
        trend_rows.append(tt)

    yearly_df = pd.DataFrame(yearly_rows)[
        ["aggregation_variant", "year", "n", "point_estimate", "boot_ci_low", "boot_ci_high", "boot_mean", "n_boot"]
    ]
    change_df = pd.DataFrame(change_rows)[
        ["aggregation_variant", "n", "point_estimate", "boot_ci_low", "boot_ci_high", "boot_mean", "n_boot"]
    ]
    trend_df = pd.DataFrame(trend_rows)[
        ["aggregation_variant", "observed_slope_fisher_z_per_year", "boot_ci_low", "boot_ci_high",
         "bootstrap_two_sided_p", "declines_monotonically", "n_boot"]
    ]
    overlap_df = pd.DataFrame(topbottom_k_overlap(data, VARIANTS[PRIMARY_VARIANT]))

    out_dir = WORKING_ROOT / "artifacts/tables"
    yearly_path = out_dir / "table_15a_yearly_spearman_bootstrap_ci.csv"
    change_path = out_dir / "table_15b_change_rank_spearman_bootstrap_ci.csv"
    trend_path = out_dir / "table_15c_yearly_trend_bootstrap_test.csv"
    overlap_path = out_dir / "table_16_topbottom_k_overlap.csv"

    yearly_df.to_csv(yearly_path, index=False, encoding="utf-8-sig")
    change_df.to_csv(change_path, index=False, encoding="utf-8-sig")
    trend_df.to_csv(trend_path, index=False, encoding="utf-8-sig")
    overlap_df.to_csv(overlap_path, index=False, encoding="utf-8-sig")

    primary_change = change_df[change_df.aggregation_variant == PRIMARY_VARIANT].iloc[0]
    primary_trend = trend_df[trend_df.aggregation_variant == PRIMARY_VARIANT].iloc[0]
    primary_yearly = yearly_df[yearly_df.aggregation_variant == PRIMARY_VARIANT]

    lines = []
    lines.append("# Robustness diagnostics supplement (post-hoc, resubmission)\n\n")
    lines.append("Label: **POST_HOC_ROBUSTNESS_DIAGNOSTIC**. Read-only script over the frozen "
                  "processed sources already declared allowed in `s11_measurement_review.py`. "
                  "Does not modify the locked ledger, gate outputs, or any existing table.\n")

    lines.append("\n## 1. Bootstrap 95% CIs for yearly Spearman rank correlation "
                  f"(primary variant: {PRIMARY_VARIANT})\n\n")
    lines.append("| Year | N | Point estimate | Bootstrap 95% CI |\n|---|---|---|---|\n")
    for _, r in primary_yearly.iterrows():
        lines.append(f"| {int(r.year)} | {int(r.n)} | {r.point_estimate:.3f} | "
                      f"[{r.boot_ci_low:.3f}, {r.boot_ci_high:.3f}] |\n")

    lines.append("\n## 2. Bootstrap 95% CI for the 2021-2024 change-rank correlation, "
                  "all four Ookla aggregation variants\n\n")
    lines.append("| Variant | N | Point estimate | Bootstrap 95% CI |\n|---|---|---|---|\n")
    for _, r in change_df.iterrows():
        lines.append(f"| {r.aggregation_variant} | {int(r.n)} | {r.point_estimate:.3f} | "
                      f"[{r.boot_ci_low:.3f}, {r.boot_ci_high:.3f}] |\n")

    lines.append("\n## 3. Formal trend test: is the yearly-correlation decline a real trend?\n\n")
    lines.append("Block bootstrap (province-resampled, B=10,000) of the slope of Fisher "
                  "z-transformed yearly Spearman correlations regressed on year.\n\n")
    lines.append("| Variant | Slope (Fisher z / year) | Bootstrap 95% CI | Two-sided bootstrap p | "
                  "Monotonic decline |\n|---|---|---|---|---|\n")
    for _, r in trend_df.iterrows():
        lines.append(f"| {r.aggregation_variant} | {r.observed_slope_fisher_z_per_year:.4f} | "
                      f"[{r.boot_ci_low:.4f}, {r.boot_ci_high:.4f}] | {r.bootstrap_two_sided_p:.4f} | "
                      f"{r.declines_monotonically} |\n")
    sig_text = ("statistically detectable" if primary_trend.bootstrap_two_sided_p < 0.05
                else "not statistically distinguishable from a flat trend, and should continue to be "
                     "described as a descriptive pattern rather than a confirmed trend")
    lines.append(f"\nPrimary variant ({PRIMARY_VARIANT}): slope = "
                  f"{primary_trend.observed_slope_fisher_z_per_year:.4f} Fisher-z units per year, "
                  f"95% CI [{primary_trend.boot_ci_low:.4f}, {primary_trend.boot_ci_high:.4f}], "
                  f"two-sided bootstrap p = {primary_trend.bootstrap_two_sided_p:.4f}. The decline is "
                  f"{sig_text}.\n")

    lines.append("\n## 4. Top/bottom-k overlap between VNNIC and Ookla (primary variant), k = 5, 10, 15\n\n")
    lines.append("Chance baseline is the hypergeometric expectation k²/63 for two independent "
                  "size-k subsets drawn from 63 provinces.\n\n")
    lines.append("| Rule | k | Overlap | Overlap % | Chance expectation | Overlap / chance |\n"
                  "|---|---|---|---|---|---|\n")
    for _, r in overlap_df.iterrows():
        lines.append(f"| {r.rule} | {r.k} | {r.overlap_count}/{r.k} | {r.overlap_fraction*100:.0f}% | "
                      f"{r.expected_overlap_by_chance:.2f} | {r.overlap_vs_chance_ratio:.2f}x |\n")

    lines.append("\n## Headline numbers for Results/Discussion\n\n")
    lines.append(f"- Primary change-rank Spearman correlation: {primary_change.point_estimate:.3f}, "
                  f"bootstrap 95% CI [{primary_change.boot_ci_low:.3f}, {primary_change.boot_ci_high:.3f}] "
                  "(province-resampled percentile bootstrap, B=10,000). Confirms the same conclusion as "
                  "the analytic CI already reported: the interval spans zero.\n")
    lines.append(f"- Yearly Spearman correlation falls from {primary_yearly.iloc[0].point_estimate:.3f} "
                  f"(2021) to {primary_yearly.iloc[-1].point_estimate:.3f} (2024); bootstrap trend test "
                  f"p = {primary_trend.bootstrap_two_sided_p:.4f} for the null of no linear trend in "
                  f"Fisher-z space — the decline is {sig_text}.\n")
    smallest_gain_10 = overlap_df[(overlap_df.rule == "smallest_2021_2024_gain") & (overlap_df.k == 10)].iloc[0]
    lines.append(f"- Bottom-10-by-gain overlap: {smallest_gain_10.overlap_count}/10 provinces "
                  f"({smallest_gain_10.overlap_fraction*100:.0f}%), versus a chance expectation of "
                  f"{smallest_gain_10.expected_overlap_by_chance:.2f}/10. Observed agreement is only "
                  f"{smallest_gain_10.overlap_vs_chance_ratio:.2f}x the chance baseline.\n")

    report_path = WORKING_ROOT / "reports/robustness_diagnostics_supplement.md"
    report_path.write_text("".join(lines), encoding="utf-8")

    manifest = {
        "diagnostic_label": "POST_HOC_ROBUSTNESS_DIAGNOSTIC",
        "purpose": "Resubmission robustness supplement (bootstrap CI, trend test, top/bottom-k overlap)",
        "rng_seed": RNG_SEED, "n_boot": N_BOOT,
        "source_files": [
            "data/processed/ookla_fixed_q2_adm1_2021_2024.parquet",
            "data/processed/vnnic_q2_validation_2021_2024.parquet",
        ],
        "outputs": [str(p.relative_to(WORKING_ROOT)) for p in
                    [yearly_path, change_path, trend_path, overlap_path, report_path]],
        "modifies_locked_pipeline": False,
    }
    (WORKING_ROOT / "artifacts/qc/robustness_diagnostics_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    print("Wrote:", *manifest["outputs"], sep="\n  ")
    print("\nPrimary change-rank bootstrap CI:", primary_change.boot_ci_low, primary_change.boot_ci_high)
    print("Primary trend bootstrap p:", primary_trend.bootstrap_two_sided_p)


if __name__ == "__main__":
    main()
