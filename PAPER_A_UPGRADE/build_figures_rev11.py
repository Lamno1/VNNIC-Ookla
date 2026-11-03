"""Figures 2-5 for manuscript revision 11 (vector PDF + 300 dpi PNG; same CSV inputs as revision 05, nothing recomputed). Values are read from the saved CSVs; nothing is recomputed.
Fig 1 dispersion (X1), Fig 2 yearly cross-source Spearman and quarter grid (X1, X2), Fig 3 ranking of speed changes by starting quarter (X1, X2, X5),
Fig 4 Delta VNNIC - Ookla against outside indicators (supplement S-Ext, headline rows). Output: PAPER_A_UPGRADE/figures_rev05/*.png (200 dpi)."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
H = Path(__file__).parent; O = H / "figures_rev11"; O.mkdir(exist_ok=True); R = H / "results"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 100, "font.family": "serif", "font.serif": ["Times New Roman", "STIXGeneral"], "mathtext.fontset": "stix", "axes.unicode_minus": True})
CV, CO, CG = "#1b4f8a", "#c0561b", "#555555"
# Fig 1 dispersion
t = pd.read_csv(R / "x1d_dispersion.csv"); order = ["sd_level", "sd_log", "cv", "iqr", "p90_p10", "max_min"]
lab = {"sd_level": "SD of levels", "sd_log": "SD of logs", "cv": "Coeff. of variation", "iqr": "Interquartile range", "p90_p10": "p90/p10", "max_min": "Max/min"}
fig, ax = plt.subplots(figsize=(6.6, 3.6)); y = np.arange(len(order))[::-1]
for off, s, c in ((0.14, "VNNIC", CV), (-0.14, "Ookla", CO)):
    d = t[t.source == s].set_index("indicator").loc[order]
    ax.errorbar(d.log_ratio, y + off, xerr=[d.log_ratio - d.lo, d.hi - d.log_ratio], fmt="o", color=c, capsize=3, label=s, ms=5)
ax.axvline(0, color=CG, lw=1); ax.set_yticks(y); ax.set_yticklabels([lab[i] for i in order]); ax.set_xlabel("Log ratio 2024/2021 (95% province-bootstrap interval)")
ax.legend(frameon=False, loc="lower right"); ax.set_title("Dispersion (log ratio 2024/2021)", fontsize=9, loc="left")
fig.tight_layout(); fig.savefig(O / "fig2_dispersion.png", dpi=300); fig.savefig(O / "fig2_dispersion.pdf"); plt.close(fig)
# Fig 2 yearly + grid
yr = pd.read_csv(R / "x1a_yearly.csv"); g = pd.read_csv(R / "x2a_level_grid.csv")
fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.6), gridspec_kw={"width_ratios": [1, 1.7]})
ax = axs[0]; yrs = [2021, 2022, 2023, 2024]
rr = [yr[yr["item"] == f"yearly Spearman {y_}"].iloc[0] for y_ in yrs]
ax.errorbar(yrs, [r.rho for r in rr], yerr=[[r.rho - r.lo for r in rr], [r.hi - r.rho for r in rr]], fmt="o-", color=CG, capsize=3)
ax.axhline(0, color=CG, lw=1); ax.set_xticks(yrs); ax.set_ylabel("Spearman, Ookla Q2 vs VNNIC Q2"); ax.set_title("Matched second quarters (95% interval)", fontsize=9); ax.set_ylim(-0.1, 0.9)
ax = axs[1]; xs, labs = [], []
for yv in yrs:
    for q in (1, 2, 3, 4):
        xs.append(len(xs) + (0.5 if q == 1 and yv > 2021 else 0)); labs.append(f"{str(yv)[2:]}Q{q}")
xs = np.array(xs, float); i = 0
for yv in yrs:
    for q in (1, 2, 3, 4):
        for w, c, m, dx in (("Wprev", "#9aa5b1", "<", -0.18), ("W0", "black", "o", 0.0), ("Wnext", "#9aa5b1", ">", 0.18)):
            r = g[(g.year == yv) & (g.q == q) & (g.window == w)]
            if len(r): ax.plot(xs[i] + dx, r.rho.iloc[0], m, color=c, ms=5 if w == "W0" else 4)
        i += 1
ax.set_xticks(xs); ax.set_xticklabels(labs, rotation=90, fontsize=7); ax.axhline(0, color=CG, lw=1); ax.set_ylabel("Spearman"); ax.set_ylim(-0.1, 0.9)
ax.set_title("By quarter: matched (circle), VNNIC one quarter earlier (<) or later (>)", fontsize=9)
fig.tight_layout(); fig.savefig(O / "fig3_rank_agreement.png", dpi=300); fig.savefig(O / "fig3_rank_agreement.pdf"); plt.close(fig)
# Fig 3 change ordering by start
cg = pd.read_csv(R / "x2b_change_grid.csv"); w = cg[(cg.kind == "W0 log change") & (cg.start == 2021)].sort_values("q"); yl = cg[(cg.start == 2021) & (cg.kind == "year-level log change")].iloc[0]
v = pd.read_csv(R / "x5_variants.csv"); v1 = v[v.variant.str.startswith("V1")].iloc[0]; v2 = v[v.variant.str.startswith("V2")].iloc[0]
items = [(f"2021 Q{int(r.q)} to 2024 Q{int(r.q)}", r.rho, r.lo, r.hi) for r in w.itertuples()] + [("2021 to 2024, annual", yl.rho, yl.lo, yl.hi), ("2022 Q2 to 2024 Q2", v1.rho, v1.lo, v1.hi), ("2022 to 2024, year means", v2.rho, v2.lo, v2.hi)]
fig, ax = plt.subplots(figsize=(6.6, 3.6)); yy = np.arange(len(items))[::-1]
for k, (nm, r, lo, hi) in enumerate(items): ax.errorbar(r, yy[k], xerr=[[r - lo], [hi - r]], fmt="o", color=CG, capsize=3)
ax.axvline(0, color=CG, lw=1); ax.set_yticks(yy); ax.set_yticklabels([i[0] for i in items]); ax.set_xlabel("Spearman between log speed changes of the two systems (95% interval)")
ax.set_title("Ordering of speed changes depends on the starting quarter", fontsize=9); fig.tight_layout(); fig.savefig(O / "fig4_change_ordering.png", dpi=300); fig.savefig(O / "fig4_change_ordering.pdf"); plt.close(fig)
# Fig 4 Delta against outside indicators (headline rows of Table 2)
sp = pd.read_csv(H / "results_supplement_external_deltas.csv")
sel = [("DTI Digital infrastructure 2021", "X16", "D_inf", "2021 (VNNIC Apr-Dec, Ookla Q2-Q4)"), ("DTI Digital infrastructure 2022", "X17", "D_inf", "2022 (Jan-Dec)"), ("DTI Digital infrastructure 2023", "X16", "D_inf", "2023 (Jan-Dec)"),
       ("NSO people using Internet 2021", "X17", "NSO_ind", "2021 (VNNIC Apr-Dec, Ookla Q2-Q4)"), ("NSO people using Internet 2022", "X17", "NSO_ind", "2022 (Jan-Dec)"), ("NSO people using Internet 2023", "X17", "NSO_ind", "2023 (Jan-Dec)"),
       ("NSO households 2024 Q1", "X13", "N1", "2024 Q1"), ("NSO households 2024 Q2", "X13", "N1", "2024 Q2"), ("NSO households 2024 Q3", "X13", "N1", "2024 Q3"), ("NSO households 2024 Q4", "X13", "N1", "2024 Q4"),
       ("NSO households 2025 Q1", "X15", "N1", "2025 Q1"), ("NSO households 2025 Q2", "X15", "N1", "2025 Q2"), ("DTI Digital infrastructure 2024 (Decision 405)", "X17", "D_inf", "2024 (Jan-Dec)")]
fig, ax = plt.subplots(figsize=(7.4, 4.8)); yy = np.arange(len(sel))[::-1]
for k, (nm, an, ind, win) in enumerate(sel):
    r = sp[sp.analysis.str.startswith(an) & (sp.indicator == ind) & (sp.outcome_family == "F1") & (sp.window == win)].iloc[0]
    resolved = bool(pd.notna(r.p_holm) and r.p_holm < 0.05 and (r.ci_lo > 0 or r.ci_hi < 0))
    ax.errorbar(r.delta, yy[k], xerr=[[r.delta - r.ci_lo], [r.ci_hi - r.delta]], fmt="o" if resolved else "s", mfc=CV if resolved else "white", color=CV, capsize=3)
ax.axvline(0, color=CG, lw=1); ax.set_yticks(yy); ax.set_yticklabels([s[0] for s in sel], fontsize=8); ax.set_xlabel("Delta = VNNIC rho minus Ookla rho (95% paired-bootstrap interval)")
ax.set_title("Filled: Holm p < 0.05 and interval excludes zero. Open: unresolved", fontsize=9, loc="left")
fig.tight_layout(); fig.savefig(O / "fig5_external_delta.png", dpi=300); fig.savefig(O / "fig5_external_delta.pdf"); plt.close(fig)
print(sorted(p.name for p in O.iterdir()))

