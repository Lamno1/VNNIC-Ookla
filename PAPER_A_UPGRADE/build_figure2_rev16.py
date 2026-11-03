"""Figure 2 for manuscript revision 16: dispersion log ratios and direct contrasts for all four matched quarters (no quarter singled out).
Values are read from results_allq/allq_L2_dispersion.csv and allq_L2_contrast.csv; nothing is recomputed."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
H = Path(__file__).parent; A = H / "results_allq"
OUT = H.parent / "submission" / "measurement_divergence_rev16_cas" / "figures"
plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 100,
                     "font.family": "serif", "font.serif": ["Times New Roman", "STIXGeneral"], "mathtext.fontset": "stix", "axes.unicode_minus": True})
CV, CO, CG = "#1b4f8a", "#c0561b", "#555555"
l2 = pd.read_csv(A / "allq_L2_dispersion.csv"); l2c = pd.read_csv(A / "allq_L2_contrast.csv")
order = ["sd_level", "sd_log", "cv", "iqr", "p90_p10", "max_min"]
lab = {"sd_level": "SD of levels", "sd_log": "SD of logs", "cv": "Coeff. of variation", "iqr": "Interquartile range", "p90_p10": "p90/p10", "max_min": "Max/min"}
y = np.arange(len(order))[::-1]
fig = plt.figure(figsize=(7.4, 6.2))
gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.15], hspace=0.55, wspace=0.12)
first = None
for q in (1, 2, 3, 4):
    ax = fig.add_subplot(gs[0, q - 1])
    for off, s, c in ((0.16, "VNNIC", CV), (-0.16, "Ookla", CO)):
        d = l2[(l2.quarter == q) & (l2.source == s)].set_index("indicator").loc[order]
        ax.errorbar(d.log_ratio, y + off, xerr=[d.log_ratio - d.lo, d.hi - d.log_ratio], fmt="o", color=c, capsize=2, ms=3.5, lw=1, label=s)
    ax.axvline(0, color=CG, lw=1)
    ax.set_title("Q%d" % q, fontsize=8.5, loc="left")
    ax.set_yticks(y)
    ax.set_yticklabels([lab[i] for i in order] if q == 1 else [])
    ax.set_xlabel("Log ratio 2024/2021", fontsize=7.5)
    if q == 1:
        ax.legend(frameon=False, loc="lower right", fontsize=7)
fig.text(0.01, 0.955, "(a) Change in each source, by quarter (95% intervals)", fontsize=8.5, ha="left")
ax = fig.add_subplot(gs[1, :])
cols = {1: "#1b4f8a", 2: "#c0561b", 3: "#2e8b57", 4: "#7a3b8f"}
mk = {1: "o", 2: "s", 3: "^", 4: "D"}
for q, off in ((1, 0.27), (2, 0.09), (3, -0.09), (4, -0.27)):
    d = l2c[l2c.quarter == q].set_index("indicator").loc[order]
    ax.errorbar(d.diff_V_minus_O, y + off, xerr=[d.diff_V_minus_O - d.lo, d.hi - d.diff_V_minus_O], fmt=mk[q], color=cols[q], capsize=2.5, ms=4.5, lw=1, label="Q%d" % q)
ax.axvline(0, color=CG, lw=1)
ax.set_yticks(y); ax.set_yticklabels([lab[i] for i in order])
ax.set_xlabel("Difference of log ratios, VNNIC minus Ookla (95% interval)")
ax.set_title("(b) Direct contrast of the two sources, by quarter", fontsize=8.5, loc="left", pad=16)
ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.13), fontsize=7.5)
fig.subplots_adjust(left=0.17, right=0.98, top=0.9, bottom=0.09)
fig.savefig(OUT / "fig2_dispersion.pdf"); fig.savefig(OUT / "fig2_dispersion.png", dpi=300); plt.close(fig)
print("written", OUT / "fig2_dispersion.pdf")
