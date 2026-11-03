"""Figures 2-5 for manuscript revision 14 (vector PDF + 300 dpi PNG). Values are read from the saved CSVs of the earlier analyses and from results_x18 (nothing is recomputed here).
Fig 2 dispersion log ratios and direct contrast; Fig 3 agreement by quarter and sensitivity to the VNNIC window; Fig 4 change ordering by quarterly window and cross-window stability within each source;
Fig 5 Delta VNNIC - Ookla against outside indicators (headline rows)."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
H = Path(__file__).parent; O = H / "figures_rev14"; O.mkdir(exist_ok=True); R = H / "results"; X = H / "results_x18"
plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 100, "font.family": "serif", "font.serif": ["Times New Roman", "STIXGeneral"], "mathtext.fontset": "stix", "axes.unicode_minus": True})
CV, CO, CG = "#1b4f8a", "#c0561b", "#555555"
# ---------------- Fig 2 dispersion: log ratios (left) and direct contrast (right)
t = pd.read_csv(R / "x1d_dispersion.csv"); c3 = pd.read_csv(X / "s3_dispersion_contrast.csv").set_index("indicator")
order = ["sd_level", "sd_log", "cv", "iqr", "p90_p10", "max_min"]
lab = {"sd_level": "SD of levels", "sd_log": "SD of logs", "cv": "Coeff. of variation", "iqr": "Interquartile range", "p90_p10": "p90/p10", "max_min": "Max/min"}
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={"width_ratios": [1.15, 1]}, sharey=True); y = np.arange(len(order))[::-1]
ax = axs[0]
for off, s, c in ((0.14, "VNNIC", CV), (-0.14, "Ookla", CO)):
    d = t[t.source == s].set_index("indicator").loc[order]
    ax.errorbar(d.log_ratio, y + off, xerr=[d.log_ratio - d.lo, d.hi - d.log_ratio], fmt="o", color=c, capsize=3, label=s, ms=5)
ax.axvline(0, color=CG, lw=1); ax.set_yticks(y); ax.set_yticklabels([lab[i] for i in order]); ax.set_xlabel("Log ratio 2024/2021 (95% interval)")
ax.legend(frameon=False, loc="lower right"); ax.set_title("(a) Change in each source", fontsize=8, loc="left")
ax = axs[1]; d = c3.loc[order]
ax.errorbar(d.diff_V_minus_O, y, xerr=[d.diff_V_minus_O - d.lo, d.hi - d.diff_V_minus_O], fmt="s", color=CG, capsize=3, ms=5)
ax.axvline(0, color=CG, lw=1); ax.set_xlabel("Difference of log ratios, VNNIC minus Ookla (95% interval)"); ax.set_title("(b) Direct contrast of the two sources", fontsize=8, loc="left")
fig.tight_layout(); fig.savefig(O / "fig2_dispersion.png", dpi=300); fig.savefig(O / "fig2_dispersion.pdf"); plt.close(fig)
# ---------------- Fig 3 rank agreement by quarter
g = pd.read_csv(R / "x2a_level_grid.csv"); s1 = pd.read_csv(X / "s1_by_year.csv").set_index("year"); yrs = [2021, 2022, 2023, 2024]
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.2), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axs[0]; xs = []; k = 0
for yi, yv in enumerate(yrs):
    for q in (1, 2, 3, 4):
        r = g[(g.year == yv) & (g.q == q) & (g.window == "W0")].iloc[0]; x = yi * 5 + q
        col = CO if q == 2 else CG
        ax.errorbar(x, r.rho, yerr=[[r.rho - r.lo], [r.hi - r.rho]], fmt="o", color=col, capsize=2, ms=4.5)
    a = s1.loc[yv]; ax.plot([yi * 5 + 0.6, yi * 5 + 4.4], [a.A_mean4q] * 2, color="black", lw=1.2)
    ax.plot(yi * 5 + 2.5, a.L_yearlevel, "D", mfc="white", mec="black", ms=6)
ax.set_xticks([yi * 5 + 2.5 for yi in range(4)]); ax.set_xticklabels([str(y_) for y_ in yrs]); ax.axhline(0, color=CG, lw=1); ax.set_ylim(-0.1, 0.95)
ax.set_ylabel("Spearman, Ookla vs VNNIC"); ax.set_title("(a) Quarters (orange = Q2), mean (line), year (diamond)", fontsize=8, loc="left")
ax = axs[1]; xs, labs = [], []
for yi, yv in enumerate(yrs):
    for q in (1, 2, 3, 4):
        xs.append(yi * 5 + q); labs.append(f"{str(yv)[2:]}Q{q}")
i = 0
for yi, yv in enumerate(yrs):
    for q in (1, 2, 3, 4):
        for w, c, m, dx in (("Wprev", "#9aa5b1", "<", -0.22), ("W0", "black", "o", 0.0), ("Wnext", "#9aa5b1", ">", 0.22)):
            r = g[(g.year == yv) & (g.q == q) & (g.window == w)]
            if len(r): ax.plot(xs[i] + dx, r.rho.iloc[0], m, color=c, ms=5 if w == "W0" else 4)
        i += 1
ax.set_xticks(xs); ax.set_xticklabels(["Q" + l[-1] for l in labs], fontsize=7); ax.axhline(0, color=CG, lw=1); ax.set_ylim(-0.1, 0.95)
for yi, yv in enumerate(yrs):
    ax.text(np.mean(xs[yi * 4:yi * 4 + 4]), -0.13, str(yv), transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=8)
ax.set_ylabel("Spearman, Ookla vs VNNIC")
ax.set_title("(b) Matched (circle), VNNIC window earlier (<), later (>)", fontsize=8, loc="left")
fig.tight_layout(); fig.savefig(O / "fig3_rank_agreement.png", dpi=300); fig.savefig(O / "fig3_rank_agreement.pdf"); plt.close(fig)
# ---------------- Fig 4 change ordering and repeatability
cg = pd.read_csv(R / "x2b_change_grid.csv"); w = cg[(cg.kind == "W0 log change") & (cg.start == 2021)].sort_values("q"); yl = cg[(cg.start == 2021) & (cg.kind == "year-level log change")].iloc[0]
v = pd.read_csv(R / "x5_variants.csv"); v1 = v[v.variant.str.startswith("V1")].iloc[0]; v2 = v[v.variant.str.startswith("V2")].iloc[0]
items = [(f"2021 Q{int(r.q)} to 2024 Q{int(r.q)}", r.rho, r.lo, r.hi) for r in w.itertuples()] + [("2021 to 2024, annual", yl.rho, yl.lo, yl.hi), ("2022 Q2 to 2024 Q2", v1.rho, v1.lo, v1.hi), ("2022 to 2024, year means", v2.rho, v2.lo, v2.hi)]
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.4), gridspec_kw={"width_ratios": [1, 1]})
ax = axs[0]; yy = np.arange(len(items))[::-1]
for k, (nm, r, lo, hi) in enumerate(items): ax.errorbar(r, yy[k], xerr=[[r - lo], [hi - r]], fmt="o", color=CG, capsize=3)
ax.axvline(0, color=CG, lw=1); ax.set_yticks(yy); ax.set_yticklabels([i[0] for i in items], fontsize=8); ax.set_xlabel("Spearman, log changes of the two sources")
ax.set_title("(a) Across sources, by window", fontsize=8, loc="left")
p2 = pd.read_csv(X / "s2_pairs.csv"); p2 = p2[p2.a != "mean"].copy(); p2["a"] = p2.a.astype(int); p2["b"] = p2.b.astype(int)
ax = axs[1]; pairs = [(a, b) for a in (1, 2, 3, 4) for b in (1, 2, 3, 4) if a < b]; yy = np.arange(len(pairs))[::-1]
for off, s, c in ((0.15, "VNNIC", CV), (-0.15, "Ookla", CO)):
    d = p2[p2.source == s]
    for k, (a, b) in enumerate(pairs):
        r = d[(d.a == a) & (d.b == b)].iloc[0]; ax.errorbar(r.rho, yy[k] + off, xerr=[[r.rho - r.lo], [r.hi - r.rho]], fmt="o", color=c, capsize=2.5, ms=4.5, label=s if k == 0 else None)
ax.axvline(0, color=CG, lw=1); ax.set_yticks(yy); ax.set_yticklabels([f"Q{a} vs Q{b} window" for a, b in pairs], fontsize=8)
ax.set_xlabel("Spearman between log changes of one source"); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2); ax.set_title("(b) Within each source, between windows", fontsize=8, loc="left")
fig.tight_layout(); fig.savefig(O / "fig4_change_ordering.png", dpi=300); fig.savefig(O / "fig4_change_ordering.pdf"); plt.close(fig)
# ---------------- Fig 5 Delta against outside indicators (headline rows)
sp = pd.read_csv(H / "results_supplement_external_deltas.csv")
sel = [("DTI Digital infrastructure 2021", "X16", "D_inf", "2021 (VNNIC Apr-Dec, Ookla Q2-Q4)"), ("DTI Digital infrastructure 2022", "X17", "D_inf", "2022 (Jan-Dec)"), ("DTI Digital infrastructure 2023", "X16", "D_inf", "2023 (Jan-Dec)"),
       ("NSO people using Internet 2021", "X17", "NSO_ind", "2021 (VNNIC Apr-Dec, Ookla Q2-Q4)"), ("NSO people using Internet 2022", "X17", "NSO_ind", "2022 (Jan-Dec)"), ("NSO people using Internet 2023", "X17", "NSO_ind", "2023 (Jan-Dec)"),
       ("NSO households 2024 Q1", "X13", "N1", "2024 Q1"), ("NSO households 2024 Q2", "X13", "N1", "2024 Q2"), ("NSO households 2024 Q3", "X13", "N1", "2024 Q3"), ("NSO households 2024 Q4", "X13", "N1", "2024 Q4"),
       ("NSO households 2025 Q1 (prelim.)", "X15", "N1", "2025 Q1"), ("NSO households 2025 Q2 (prelim.)", "X15", "N1", "2025 Q2"), ("DTI Digital infrastructure 2024 (Decision 405)", "X17", "D_inf", "2024 (Jan-Dec)")]
fig, ax = plt.subplots(figsize=(6.2, 4.2)); yy = np.arange(len(sel))[::-1]
for k, (nm, an, ind, win) in enumerate(sel):
    r = sp[sp.analysis.str.startswith(an) & (sp.indicator == ind) & (sp.outcome_family == "F1") & (sp.window == win)].iloc[0]
    resolved = bool(pd.notna(r.p_holm) and r.p_holm < 0.05 and (r.ci_lo > 0 or r.ci_hi < 0))
    ax.errorbar(r.delta, yy[k], xerr=[[r.delta - r.ci_lo], [r.ci_hi - r.delta]], fmt="o" if resolved else "s", mfc=CV if resolved else "white", color=CV, capsize=3)
ax.axvline(0, color=CG, lw=1); ax.set_yticks(yy); ax.set_yticklabels([s[0] for s in sel], fontsize=7.5); ax.set_xlabel("Delta = VNNIC rho minus Ookla rho (95% paired-bootstrap interval)")
ax.set_title("Filled: Holm p < 0.05 and interval excludes zero. Open: otherwise", fontsize=8, loc="left")
fig.tight_layout(); fig.savefig(O / "fig5_external_delta.png", dpi=300); fig.savefig(O / "fig5_external_delta.pdf"); plt.close(fig)
print(sorted(p.name for p in O.iterdir()))
