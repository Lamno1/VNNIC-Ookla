"""X18 deviation D2 (S10): tile-floor sensitivity. See x18_specification.md, Deviation D2."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import upg_common as u

HERE = Path(__file__).resolve().parent; OUT = HERE / "results_x18"
D = u.Data(); inv = {v_: k for k, v_ in D.iso.items()}
YRS = (2021, 2022, 2023, 2024); tdir = HERE / "data" / "ookla_x18"
tiles = {y: pd.read_parquet(tdir / f"fixed_{y}Q2_tiles.parquet").assign(pid=lambda t: t.shapeISO.map(inv)) for y in YRS}
rows = []
for y in YRS:
    t = tiles[y]; n = len(t)
    rows.append(dict(year=y, tiles=n, share_1=float((t.tests == 1).mean()), share_2=float((t.tests == 2).mean()), share_3_4=float(t.tests.between(3, 4).mean()), share_5plus=float((t.tests >= 5).mean()), median_tests=float(t.tests.median())))
a = pd.DataFrame(rows); a.to_csv(OUT / "s10_tile_test_shares.csv", index=False)
unres = {y: pd.Series(D.fq2["ookla_tile_median_download_mbps"][y], index=D.pids) for y in YRS}
base_rho = {y: u.sp(D.vq2[y], unres[y].values) for y in YRS}
base_ch = u.sp(np.log(D.vq2[2024]) - np.log(D.vq2[2021]), np.log(unres[2024].values) - np.log(unres[2021].values))
rows = []
for m in (3, 5, 10):
    stat = {}
    for y in YRS:
        t = tiles[y]; t = t[t.tests >= m]; g = t.groupby("pid").d
        cnt = g.size(); med = g.median().where(cnt >= 10)
        stat[y] = med.reindex(D.pids)
    for y in YRS:
        ok = stat[y].notna().values
        x = D.vq2[y][ok]; z = stat[y].values[ok]
        bt = u.corr_rows(u.rk(x[np.random.default_rng(u.SEED).integers(0, ok.sum(), (u.B, ok.sum()))]), u.rk(z[np.random.default_rng(u.SEED).integers(0, ok.sum(), (u.B, ok.sum()))]))
        idx = np.random.default_rng(u.SEED).integers(0, ok.sum(), (u.B, ok.sum()))
        bt = u.corr_rows(u.rk(x[idx]), u.rk(z[idx]))
        rows.append(dict(floor=m, year=y, provinces=int(ok.sum()), rho=u.sp(x, z), lo=u.ci(bt)[0], hi=u.ci(bt)[1], unrestricted_rho=base_rho[y]))
    ok = stat[2021].notna().values & stat[2024].notna().values
    cv = np.log(D.vq2[2024][ok]) - np.log(D.vq2[2021][ok]); co = np.log(stat[2024].values[ok]) - np.log(stat[2021].values[ok])
    idx = np.random.default_rng(u.SEED).integers(0, ok.sum(), (u.B, ok.sum()))
    bt = u.corr_rows(u.rk(cv[idx]), u.rk(co[idx]))
    rows.append(dict(floor=m, year="change 2021-2024 (log)", provinces=int(ok.sum()), rho=u.sp(cv, co), lo=u.ci(bt)[0], hi=u.ci(bt)[1], unrestricted_rho=base_ch))
b = pd.DataFrame(rows)
labs = []
for m in (3, 5, 10):
    s = b[b.floor == m]; yr = s[s.year != "change 2021-2024 (log)"]; ch = s[s.year == "change 2021-2024 (log)"].iloc[0]
    same = (np.sign(ch.rho) == np.sign(base_ch)) and bool((abs(yr.rho - yr.unrestricted_rho) < 0.10).all())
    labs.append(dict(floor=m, label="same conclusion as the unrestricted tile median" if same else "differs"))
c = pd.DataFrame(labs); b.to_csv(OUT / "s10_tile_floor.csv", index=False); c.to_csv(OUT / "s10_labels.csv", index=False)
rep = ["", "## S10 (Deviation D2) tile floor sensitivity", "", u.md(a), "", u.md(b), "", u.md(c)]
p = HERE / "x18_report.md"; p.write_text(p.read_text(encoding="utf-8") + "\n".join(rep), encoding="utf-8")
print("\n".join(rep))
