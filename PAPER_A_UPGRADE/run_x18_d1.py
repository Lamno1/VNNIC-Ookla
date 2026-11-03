"""X18 deviation D1 (S9): descriptive level-step series. See x18_specification.md, Deviation D1."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import upg_common as u

HERE = Path(__file__).resolve().parent; OUT = HERE / "results_x18"
D = u.Data(with_ext=True)
# (a) VNNIC monthly cross-province median
M = D.M.loc["2021-04-01":"2025-06-01"]
med = M.median(axis=1); ch = np.log(med).diff()
a = pd.DataFrame({"month": med.index.strftime("%Y-%m"), "vnnic_cross_province_median": med.values, "log_change": ch.values})
a.to_csv(OUT / "s9_vnnic_monthly.csv", index=False)
top5 = a.reindex(a.log_change.abs().sort_values(ascending=False).index).head(5)
# (b) Ookla quarterly cross-province median
rows = []
for (y, q), arr in sorted(D.O.items()):
    if (y, q) >= (2021, 1) and (y, q) <= (2025, 2):
        rows.append(dict(year=y, q=q, ookla_cross_province_median=float(np.nanmedian(arr)), n=int(np.isfinite(arr).sum())))
b = pd.DataFrame(rows); b["log_change"] = np.log(b.ookla_cross_province_median).diff(); b.to_csv(OUT / "s9_ookla_quarterly.csv", index=False)
# (c) province ratios
rows = []
for s in ("VNNIC", "Ookla"):
    for y0, y1 in ((2022, 2023), (2023, 2024)):
        x0 = D.vq2[y0] if s == "VNNIC" else D.O[(y0, 2)]; x1 = D.vq2[y1] if s == "VNNIC" else D.O[(y1, 2)]
        r = x1 / x0
        rows.append(dict(source=s, step=f"Q2 {y0} to Q2 {y1}", median_ratio=float(np.median(r)), share_ratio_above_1_5=float(np.mean(r > 1.5)), min_ratio=float(r.min()), max_ratio=float(r.max())))
c = pd.DataFrame(rows); c.to_csv(OUT / "s9_province_ratios.csv", index=False)
# (d) VNNIC counts 2022-2023
raw = pd.read_parquet(u.ROOT / "data/interim/fact_vnnic_province_month.parquet"); raw = raw[raw.network == "ftth"].copy(); raw["month"] = pd.to_datetime(raw["month"])
cnt = raw.pivot_table(index="month", columns="province_id_legacy63", values="value_raw", aggfunc="first").reindex(columns=D.pids)
d = pd.DataFrame({"month": cnt.loc["2022-01-01":"2023-12-01"].index.strftime("%Y-%m"), "national_total": cnt.loc["2022-01-01":"2023-12-01"].sum(axis=1).values})
d["vnnic_cross_province_median"] = med.reindex(cnt.loc["2022-01-01":"2023-12-01"].index).values
d.to_csv(OUT / "s9_vnnic_counts_2022_2023.csv", index=False)
rep = ["", "## S9 (Deviation D1) level step, descriptive", "", "### VNNIC monthly cross-province median, five largest absolute month-to-month log changes", u.md(top5), "",
       "### VNNIC monthly series 2022-2023 with national totals of value_raw", u.md(d), "", "### Ookla quarterly cross-province median", u.md(b), "", "### Province ratios", u.md(c)]
p = HERE / "x18_report.md"; p.write_text(p.read_text(encoding="utf-8") + "\n".join(rep), encoding="utf-8")
print("\n".join(rep))
