"""Median and SD (ddof=1) of the 63 provincial values, every source x year x matched quarter. Reads saved inputs through upg_common; writes results_allq/allq_levels.csv.
The Q2 rows must equal results_x18/s5_levels.csv (median and sd)."""
from upg_common import *
import pandas as pd
D = Data(with_ext=True); rows = []
for y in (2021, 2022, 2023, 2024):
    for q in (1, 2, 3, 4):
        for s, a in (("VNNIC", D.V(y, q)), ("Ookla", D.O[(y, q)])):
            assert len(a) == 63 and np.isfinite(a).all()
            rows.append(dict(source=s, year=y, quarter=q, median=float(np.median(a)), sd=float(np.std(a, ddof=1))))
df = pd.DataFrame(rows); df.to_csv(HERE / "results_allq" / "allq_levels.csv", index=False)
s5 = pd.read_csv(HERE / "results_x18" / "s5_levels.csv").set_index(["source", "year"])
for r in df[df.quarter == 2].itertuples():
    assert abs(r.median - s5.loc[(r.source, r.year), "median"]) < 1e-9 and abs(r.sd - s5.loc[(r.source, r.year), "sd"]) < 1e-9, r
print("ok", len(df))
