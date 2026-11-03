"""Builds the supplementary table of VNNIC-minus-Ookla Delta comparisons (one comparison per row) by COPYING rows from
results_x13, results_x15, results_x16 and results_x17 (s2_delta.csv). No statistic is recomputed and no family is re-corrected.
Holm columns are the ones written by the original runs: X13 headline m=4 (F1, N1, Q1-Q4); X15 headline m=2 (F1, N1, Q1-Q2);
X16 headline m=2 (F1, D_inf, 2021 and 2023); X17 H17a m=2, H17b m=3, HH m=1. All other rows: unadjusted, exploratory.
Version 2 (2026-10-10): the two X16 rows F4/2021Q2 (D_inf, D_tot) are replaced by the D3 rows of results_x16/s2_delta_d3.csv (both rho, Delta, CI, p,
N_common, label); the originals stay in results_x16/s2_delta.csv and are recorded in the CSV column original_values. N_common for X13, X15 and X16 is the
minimum of the N of the two source cells in the corresponding s1_associations.csv. Row count stays 129."""
import pandas as pd, numpy as np
from pathlib import Path
H = Path(__file__).parent; rows = []
def s1n(x, fam, per, ind):
    d = pd.read_csv(H / f"results_{x}/s1_associations.csv"); m = d[(d.family == fam) & (d.period == per) & (d.indicator == ind)]
    assert len(m) == 2, (x, fam, per, ind, len(m)); return int(m.N.min())
def FRAME(ind, yr):
    yr = str(yr)
    if ind in ("D_inf", "D_tot"): return "Decision 405 framework (max 200 points for Ha tang so)" if yr == "2024" else "Decision 922 framework"
    if ind == "NSO_ind": return "VHLSS individual use (Thong tin gioi tables)"
    if ind == "NSO_hh2023": return "disability survey 2023 households"
    if ind in ("N1", "N2"): return "PX-Web household series (N1 households, N2 people)"
    return ""
d3 = pd.read_csv(H / "results_x16/s2_delta_d3.csv")
def add(src, yr_fn, win_fn, fam_id, fam_m, df, cols, nfn):
    for _, r in df.iterrows():
        rows.append(dict(analysis=src, outcome_family=r[cols["fid"]], indicator=r[cols["ind"]], window_year=yr_fn(r), window=win_fn(r), external_framework=FRAME(r[cols["ind"]], yr_fn(r)),
                         N_common=nfn(r), rho_VNNIC=r.rho_V, rho_Ookla=r.rho_O, delta=r.delta, ci_lo=r.lo, ci_hi=r.hi, p_boot_raw=r.p_boot, holm_family=fam_id(r), holm_family_size=fam_m(r),
                         p_holm=r[cols["holm"]], label_unadjusted=r[cols["lab_un"]], label_reported=r[cols["lab"]], source_file=cols["file"], source_version="as run", original_values=""))
x13 = pd.read_csv(H / "results_x13/s2_delta.csv")
hd = lambda r: "X13 F1-N1-Q1..Q4" if (r.family == "F1" and r.indicator == "N1" and r.period in ("Q1", "Q2", "Q3", "Q4")) else "none (exploratory, unadjusted)"
add("X13 (NSO households 2024)", lambda r: 2024, lambda r: f"2024 {r.period}" if r.period != "year" else "2024 whole year", hd, lambda r: 4 if hd(r).startswith("X13") else np.nan, x13,
    dict(fid="family", ind="indicator", holm="p_holm_headline", lab_un="R13_2", lab="R13_2", file="results_x13/s2_delta.csv"), lambda r: s1n("x13", r.family, r.period, r.indicator))
x15 = pd.read_csv(H / "results_x15/s2_delta.csv")
hd = lambda r: "X15 F1-N1-Q1,Q2" if (r.family == "F1" and r.indicator == "N1" and r.period in ("Q1", "Q2")) else "none (exploratory, unadjusted)"
add("X15 (NSO households 2025)", lambda r: 2025, lambda r: f"2025 {r.period}", hd, lambda r: 2 if hd(r).startswith("X15") else np.nan, x15,
    dict(fid="family", ind="indicator", holm="p_holm_headline", lab_un="R15_2", lab="R15_2", file="results_x15/s2_delta.csv"), lambda r: s1n("x15", r.family, r.period, r.indicator))
x16 = pd.read_csv(H / "results_x16/s2_delta.csv")
hd = lambda r: "X16 F1-D_inf-2021,2023" if (r.family == "F1" and r.indicator == "D_inf" and r.period in ("2021", "2023")) else "none (exploratory, unadjusted)"
W16 = lambda r: {"2021": "2021 (VNNIC Apr-Dec, Ookla Q2-Q4)", "2022": "2022 (Jan-Dec)", "2023": "2023 (Jan-Dec)", "2021H2": "2021 H2 sensitivity (Jul-Dec)"}.get(r.period, r.period)
add("X16 (DTI reports 2021 and 2023)", lambda r: int(r.period[:4]), W16, hd, lambda r: 2 if hd(r).startswith("X16") else np.nan, x16,
    dict(fid="family", ind="indicator", holm="p_holm_headline", lab_un="R16_2_unadjusted", lab="R16_2", file="results_x16/s2_delta.csv"), lambda r: s1n("x16", r.family, r.period, r.indicator))
n_rep = 0
for rec in rows:  # D3 replacement of the two F4/2021Q2 rows
    if rec["analysis"].startswith("X16") and rec["outcome_family"] == "F4" and rec["window"] == "2021Q2":
        m = d3[(d3.family == "F4") & (d3.period == "2021Q2") & (d3.indicator == rec["indicator"])]; assert len(m) == 1; r = m.iloc[0]
        rec["original_values"] = (f"original run: N={rec['N_common']}, rho_V={rec['rho_VNNIC']:.4f}, rho_O={rec['rho_Ookla']:.4f}, delta={rec['delta']:.4f}, "
                                  f"CI [{rec['ci_lo']:.4f}, {rec['ci_hi']:.4f}], p={rec['p_boot_raw']:.4f}")
        rec.update(N_common=int(r.N_common), rho_VNNIC=r.rho_V, rho_Ookla=r.rho_O, delta=r.delta, ci_lo=r.lo, ci_hi=r.hi, p_boot_raw=r.p_boot, label_unadjusted=r.R16_2_d3, label_reported=r.R16_2_d3,
                   source_file="results_x16/s2_delta_d3.csv", source_version="D3 replacement (common province set)"); n_rep += 1
assert n_rep == 2
x17 = pd.read_csv(H / "results_x17/s2_delta.csv"); x17["indicator"] = x17.ext
fam = {"H17a": ("X17 H17a (D_inf 2022, 2024)", 2), "H17b": ("X17 H17b (NSO individual 2021-2023)", 3), "HH": ("X17 HH (household 2023, single cell)", 1)}
hd = lambda r: fam[r.family][0] if r.family in fam else "none (exploratory, unadjusted)"
W17 = lambda r: "2024 sensitivity (VNNIC Apr-May removed, post hoc)" if r.per == "2024s" else ("2021 (VNNIC Apr-Dec, Ookla Q2-Q4)" if r.per == "2021" else f"{r.per} (Jan-Dec)")
add("X17 (DTI 2022 and 2024, NSO individual 2021-2023, household 2023)", lambda r: int(str(r.per)[:4]), W17, hd, lambda r: fam[r.family][1] if r.family in fam else np.nan, x17,
    dict(fid="fid", ind="indicator", holm="p_holm", lab_un="label_unadj", lab="label", file="results_x17/s2_delta.csv"), lambda r: int(r.N_common))
out = pd.DataFrame(rows); assert len(out) == 129
out.to_csv(H / "results_supplement_external_deltas.csv", index=False)
def fp(x): return "" if pd.isna(x) else ("<0.001" if x < 0.001 else f"{x:.3f}")
def f(x): return "" if pd.isna(x) else (f"{x:.3f}" if isinstance(x, (float, np.floating)) else str(x))
cols = ["analysis", "outcome_family", "indicator", "external_framework", "window", "N_common", "rho_VNNIC", "rho_Ookla", "delta", "ci_lo", "ci_hi", "p_boot_raw", "holm_family", "holm_family_size", "p_holm", "label_reported", "source_version"]
md = ["# Supplementary table S-Ext: VNNIC - Ookla Delta against outside indicators (one comparison per row)\n",
      "Copied from results_x13, x15, x16 and x17 (s2_delta.csv) by build_external_delta_supplement.py (version 2, 2026-10-10). Nothing recomputed; no family was merged or re-corrected. The two rows X16 F4 / 2021Q2 are the D3 replacements (common province set, N = 62) from results_x16/s2_delta_d3.csv; the original rows stay in results_x16/s2_delta.csv and are quoted in the column original_values of the CSV. p_holm is the Holm value written by the original run within the family named in holm_family (size in holm_family_size); rows outside a named family are unadjusted and exploratory. Raw p below 0.001 is shown as <0.001 (full precision in the CSV). Windows pair year labels with source windows (VNNIC April-December and Ookla Q2-Q4 for 2021; January-December otherwise); NSO and DTI values are annual. DTI 2024 follows the Decision 405 framework and is not a repeat of the Decision 922 years. N_common is the number of provinces with all required values.\n",
      "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
for _, r in out.iterrows():
    md.append("| " + " | ".join((fp(r[c]) if c in ("p_boot_raw", "p_holm") else f(r[c])) for c in cols) + " |")
(H / "results_supplement_external_deltas.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(len(out), "rows;", int((out.N_common < 63).sum()), "rows with N_common < 63")
print(out[out.source_version != "as run"][["indicator", "window", "N_common", "rho_VNNIC", "rho_Ookla", "delta", "ci_lo", "ci_hi", "p_boot_raw"]].round(4).to_string())
