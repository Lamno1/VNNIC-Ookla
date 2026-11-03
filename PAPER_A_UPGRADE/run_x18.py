"""X18 runner. Specification: x18_specification.md (hash in x18_spec_hash.txt). Exploratory post-freeze diagnostics."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parent))
import upg_common as u

HERE = Path(__file__).resolve().parent
RES = HERE / "results"; OUT = HERE / "results_x18"; OUT.mkdir(exist_ok=True)
D = u.Data(); n = D.n; idx = u.make_idx(n); B = idx.shape[0]
YRS = (2021, 2022, 2023, 2024)
lines = []; gates = []


def gate(name, ok, detail):
    gates.append(dict(gate=name, ok=bool(ok), detail=detail)); print(("PASS " if ok else "FAIL ") + name, detail, flush=True)
    if not ok:
        pd.DataFrame(gates).to_csv(OUT / "gates.csv", index=False); raise SystemExit(f"GATE FAILED {name}")


def save(name, rows):
    df = pd.DataFrame(rows); df.to_csv(OUT / f"{name}.csv", index=False); return df


def rho_boot(x, y):
    return u.corr_rows(u.rk(x[idx]), u.rk(y[idx]))


# ---------- arrays
Vq = {(y, q): D.V(y, q) for y in YRS for q in (1, 2, 3, 4)}
Oq = {(y, q): D.O[(y, q)] for y in YRS for q in (1, 2, 3, 4)}
for k in Vq:
    assert np.isfinite(Vq[k]).all() and np.isfinite(Oq[k]).all(), k
Vyr = {y: D.Vyear(y) for y in YRS}; Oyr = {y: D.Oyear(y) for y in YRS}

# ---------- gates
g = pd.read_csv(RES / "x2a_level_grid.csv"); g = g[g.window == "W0"]
dev = max(abs(u.sp(Vq[(int(r.year), int(r.q))], Oq[(int(r.year), int(r.q))]) - r.rho) for r in g.itertuples())
gate("G18.1", dev <= 0.005, f"max abs deviation of 16 matched-quarter rho = {dev:.5f}")
c = pd.read_csv(RES / "x2b_change_grid.csv"); c = c[(c.kind == "W0 log change") & (c.start == 2021)]
lcV = {a: np.log(Vq[(2024, a)]) - np.log(Vq[(2021, a)]) for a in (1, 2, 3, 4)}
lcO = {a: np.log(Oq[(2024, a)]) - np.log(Oq[(2021, a)]) for a in (1, 2, 3, 4)}
dev2 = max(abs(u.sp(lcV[int(r.q)], lcO[int(r.q)]) - r.rho) for r in c.itertuples())
gate("G18.2", dev2 <= 0.005, f"max abs deviation of 4 log-change correlations = {dev2:.5f}")


def indicators(a):
    sd = a.std(-1, ddof=1); sdl = np.log(a).std(-1, ddof=1); mean = a.mean(-1)
    q = np.percentile(a, [10, 25, 75, 90], axis=-1)
    return dict(sd_level=sd, sd_log=sdl, cv=sd / mean, iqr=q[2] - q[1], p90_p10=q[3] / q[0], max_min=a.max(-1) / a.min(-1))


OM = "ookla_tile_median_download_mbps"
src = {"VNNIC": D.vq2, "Ookla": D.fq2[OM]}
x1d = pd.read_csv(RES / "x1d_dispersion.csv")
lr_pt = {}; lr_bt = {}
for s, arr in src.items():
    i21, i24 = indicators(arr[2021]), indicators(arr[2024]); b21, b24 = indicators(arr[2021][idx]), indicators(arr[2024][idx])
    for k in i21:
        lr_pt[(s, k)] = float(np.log(i24[k] / i21[k])); lr_bt[(s, k)] = np.log(b24[k] / b21[k])
dev3 = max(abs(lr_pt[(r.source, r.indicator)] - r.log_ratio) for r in x1d.itertuples())
gate("G18.3", dev3 <= 0.001, f"max abs deviation of 12 dispersion log ratios = {dev3:.6f}")

# ---------- S1
rows = []; A_b = {}; L_b = {}; Q2_b = {}
for y in YRS:
    qb = [rho_boot(Vq[(y, q)], Oq[(y, q)]) for q in (1, 2, 3, 4)]
    qp = [u.sp(Vq[(y, q)], Oq[(y, q)]) for q in (1, 2, 3, 4)]
    A_b[y] = np.mean(qb, axis=0); A_pt = float(np.mean(qp))
    L_b[y] = rho_boot(Vyr[y], Oyr[y]); L_pt = u.sp(Vyr[y], Oyr[y]); Q2_b[y] = qb[1]
    rows.append(dict(year=y, A_mean4q=A_pt, A_lo=u.ci(A_b[y])[0], A_hi=u.ci(A_b[y])[1], L_yearlevel=L_pt, L_lo=u.ci(L_b[y])[0], L_hi=u.ci(L_b[y])[1],
                     Q2=qp[1], Q2_lo=u.ci(qb[1])[0], Q2_hi=u.ci(qb[1])[1], qmin=min(qp), qmax=max(qp)))
s1 = save("s1_by_year", rows)
allq = [u.sp(Vq[(y, q)], Oq[(y, q)]) for y in YRS for q in (1, 2, 3, 4)]
drows = []
for nm, bt, pt in (("A_mean4q", A_b, {r.year: r.A_mean4q for r in s1.itertuples()}), ("L_yearlevel", L_b, {r.year: r.L_yearlevel for r in s1.itertuples()}), ("Q2", Q2_b, {r.year: r.Q2 for r in s1.itertuples()})):
    d = bt[2021] - bt[2024]; lo, hi = u.ci(d)
    drows.append(dict(measure=nm, diff_2021_minus_2024=pt[2021] - pt[2024], lo=lo, hi=hi, label="declined" if lo > 0 else ("rose" if hi < 0 else "not distinguishable")))
# companion: exclude VNNIC 2024-04 and 2024-05
def V_excl(y, q, drop):
    m = [pd.Timestamp(y, 3 * (q - 1) + k, 1) for k in (1, 2, 3)]; m = [x for x in m if x not in drop]
    sub = D.M.reindex(m); ok = sub.notna().sum() >= 1
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
drop = {pd.Timestamp(2024, 4, 1), pd.Timestamp(2024, 5, 1)}
V24x = {q: V_excl(2024, q, drop) for q in (1, 2, 3, 4)}
ok = all(np.isfinite(V24x[q]).all() for q in V24x)
if ok:
    qx = [u.sp(V24x[q], Oq[(2024, q)]) for q in (1, 2, 3, 4)]
    qxb = [rho_boot(V24x[q], Oq[(2024, q)]) for q in (1, 2, 3, 4)]
    Ax = float(np.mean(qx)); Axb = np.mean(qxb, axis=0)
    for nm, ptv, bv in (("A_mean4q (2024 without Apr-May VNNIC)", Ax, Axb), ("Q2 (2024 without Apr-May VNNIC)", qx[1], qxb[1])):
        base = s1.set_index("year").loc[2021, "A_mean4q" if nm.startswith("A") else "Q2"]
        bb = (A_b[2021] if nm.startswith("A") else Q2_b[2021]) - bv; lo, hi = u.ci(bb)
        drows.append(dict(measure=nm, diff_2021_minus_2024=base - ptv, lo=lo, hi=hi, label="declined" if lo > 0 else ("rose" if hi < 0 else "not distinguishable")))
    s1c = save("s1_companion", [dict(measure="A_mean4q 2024 excl Apr-May", value=Ax, lo=u.ci(Axb)[0], hi=u.ci(Axb)[1]), dict(measure="Q2 2024 excl Apr-May (June only)", value=qx[1], lo=u.ci(qxb[1])[0], hi=u.ci(qxb[1])[1])])
s1d = save("s1_differences", drows)
s1e = save("s1_range", [dict(n_cells=16, min=min(allq), max=max(allq), share_above_0_5=float(np.mean(np.array(allq) > 0.5)), median=float(np.median(allq)))])

# ---------- S2
pairs = [(a, b) for a in (1, 2, 3, 4) for b in (1, 2, 3, 4) if a < b]
rows = []; Rb = {}
for s, lc in (("VNNIC", lcV), ("Ookla", lcO)):
    vals = []; bts = []
    for a, b in pairs:
        pt = u.sp(lc[a], lc[b]); bt = u.corr_rows(u.rk(lc[a][idx]), u.rk(lc[b][idx])); vals.append(pt); bts.append(bt)
        rows.append(dict(source=s, a=a, b=b, rho=pt, lo=u.ci(bt)[0], hi=u.ci(bt)[1]))
    Rb[s] = np.mean(bts, axis=0); rows.append(dict(source=s, a="mean", b="six pairs", rho=float(np.mean(vals)), lo=u.ci(Rb[s])[0], hi=u.ci(Rb[s])[1]))
s2 = save("s2_pairs", rows)
Rv = float(s2[(s2.source == "VNNIC") & (s2.a == "mean")].rho.iloc[0]); Ro = float(s2[(s2.source == "Ookla") & (s2.a == "mean")].rho.iloc[0])
dlo, dhi = u.ci(Rb["Ookla"] - Rb["VNNIC"])
lab = "change score less repeatable in VNNIC" if dlo > 0 else ("change score less repeatable in Ookla" if dhi < 0 else "not distinguishable")
s2b = save("s2_difference", [dict(R_VNNIC=Rv, R_Ookla=Ro, diff_O_minus_V=Ro - Rv, lo=dlo, hi=dhi, label=lab)])
# year-level view
cyV = np.log(Vyr[2024]) - np.log(Vyr[2021]); cyO = np.log(Oyr[2024]) - np.log(Oyr[2021])
rows = []
for s, lc, cy in (("VNNIC", lcV, cyV), ("Ookla", lcO, cyO)):
    pts = [u.sp(lc[a], cy) for a in (1, 2, 3, 4)]; bts = np.mean([u.corr_rows(u.rk(lc[a][idx]), u.rk(cy[idx])) for a in (1, 2, 3, 4)], axis=0)
    rows.append(dict(source=s, mean_rho_quarter_vs_yearlevel=float(np.mean(pts)), lo=u.ci(bts)[0], hi=u.ci(bts)[1], per_quarter=json.dumps([round(p, 3) for p in pts])))
s2c = save("s2_yearlevel_view", rows)
rows = []
for a in (1, 2, 3, 4):
    obs = u.sp(lcV[a], lcO[a]); ceil = float(np.sqrt(max(Rv, 0.01) * max(Ro, 0.01)))
    rows.append(dict(start_quarter=a, cross_source_rho=obs, ceiling_descriptive=ceil))
s2d = save("s2_ceiling_descriptive", rows)

# ---------- S3
rows = []
for k in ("sd_level", "sd_log", "cv", "iqr", "p90_p10", "max_min"):
    d_pt = lr_pt[("VNNIC", k)] - lr_pt[("Ookla", k)]; d_b = lr_bt[("VNNIC", k)] - lr_bt[("Ookla", k)]; lo, hi = u.ci(d_b)
    rows.append(dict(indicator=k, logratio_VNNIC=lr_pt[("VNNIC", k)], logratio_Ookla=lr_pt[("Ookla", k)], same_sign=bool(np.sign(lr_pt[("VNNIC", k)]) == np.sign(lr_pt[("Ookla", k)])),
                     diff_V_minus_O=d_pt, lo=lo, hi=hi, label="sources differ" if (lo > 0 or hi < 0) else "not distinguishable", scale_free=k in ("sd_log", "cv", "p90_p10", "max_min")))
s3 = save("s3_dispersion_contrast", rows)

# ---------- S4
def ccc(x, y):
    mx, my = x.mean(-1), y.mean(-1); vx, vy = x.var(-1), y.var(-1)
    cov = ((x - mx[..., None]) * (y - my[..., None])).mean(-1)
    return 2 * cov / (vx + vy + (mx - my) ** 2)


def topk(x, y, k=10, bottom=False):
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    if bottom:
        sx, sy = set(np.argsort(rx)[:k]), set(np.argsort(ry)[:k])
    else:
        sx, sy = set(np.argsort(-rx)[:k]), set(np.argsort(-ry)[:k])
    return len(sx & sy)


rows = []; cell_b = {}
for y in YRS:
    for q in (1, 2, 3, 4):
        x, z = np.log(Vq[(y, q)]), np.log(Oq[(y, q)])
        pe_b = u.corr_rows(x[idx], z[idx]); cc_b = ccc(x[idx], z[idx]); sh_b = (z[idx] - x[idx]).mean(-1)
        kb = np.array([stats.kendalltau(x[i], z[i])[0] for i in idx[:1000]])
        cell_b[(y, q)] = dict(pe=pe_b, cc=cc_b, sh=sh_b, ke=kb)
        t10 = topk(Vq[(y, q)], Oq[(y, q)]); b10 = topk(Vq[(y, q)], Oq[(y, q)], bottom=True)
        rows.append(dict(year=y, q=q, pearson_log=u.pe(x, z), pe_lo=u.ci(pe_b)[0], pe_hi=u.ci(pe_b)[1], ccc_log=float(ccc(x, z)), ccc_lo=u.ci(cc_b)[0], ccc_hi=u.ci(cc_b)[1],
                         shift_log_O_over_V=float((z - x).mean()), shift_lo=u.ci(sh_b)[0], shift_hi=u.ci(sh_b)[1], kendall=float(stats.kendalltau(Vq[(y, q)], Oq[(y, q)])[0]),
                         kendall_lo=u.ci(kb)[0], kendall_hi=u.ci(kb)[1], top10_overlap=t10, top10_p=float(stats.hypergeom.sf(t10 - 1, 63, 10, 10)), bottom10_overlap=b10, bottom10_p=float(stats.hypergeom.sf(b10 - 1, 63, 10, 10))))
s4 = save("s4_agreement_measures", rows)
rows = []
for y in YRS:
    sub = s4[s4.year == y]
    rows.append(dict(year=y, **{c_: float(sub[c_].mean()) for c_ in ("pearson_log", "ccc_log", "shift_log_O_over_V", "kendall", "top10_overlap", "bottom10_overlap")},
                     pearson_lo=u.ci(np.mean([cell_b[(y, q)]["pe"] for q in (1, 2, 3, 4)], axis=0))[0], pearson_hi=u.ci(np.mean([cell_b[(y, q)]["pe"] for q in (1, 2, 3, 4)], axis=0))[1],
                     ccc_lo=u.ci(np.mean([cell_b[(y, q)]["cc"] for q in (1, 2, 3, 4)], axis=0))[0], ccc_hi=u.ci(np.mean([cell_b[(y, q)]["cc"] for q in (1, 2, 3, 4)], axis=0))[1]))
s4b = save("s4_mean_over_quarters", rows)

# ---------- S5
rows = []
for s, arr in src.items():
    for y in YRS:
        a = arr[y]; rows.append(dict(source=s, year=y, mean=a.mean(), median=np.median(a), sd=a.std(ddof=1), min=a.min(), max=a.max(), p10=np.percentile(a, 10), p90=np.percentile(a, 90)))
s5a = save("s5_levels", rows)
gv = {s: np.median(arr[2024]) / np.median(arr[2021]) for s, arr in src.items()}
gvb = {s: np.log(np.median(arr[2024][idx], axis=-1) / np.median(arr[2021][idx], axis=-1)) for s, arr in src.items()}
dl = gvb["VNNIC"] - gvb["Ookla"]; dlo2, dhi2 = u.ci(dl)
share = float(np.mean((src["Ookla"][2024] / src["Ookla"][2021]) > (src["VNNIC"][2024] / src["VNNIC"][2021])))
lab5 = "growth factors differ" if (dlo2 > 0 or dhi2 < 0) else "not distinguishable"
s5b = save("s5_growth", [dict(growth_factor_VNNIC=gv["VNNIC"], gf_V_lo=float(np.exp(u.ci(gvb["VNNIC"])[0])), gf_V_hi=float(np.exp(u.ci(gvb["VNNIC"])[1])),
                              growth_factor_Ookla=gv["Ookla"], gf_O_lo=float(np.exp(u.ci(gvb["Ookla"])[0])), gf_O_hi=float(np.exp(u.ci(gvb["Ookla"])[1])),
                              diff_logratio_V_minus_O=float(np.log(gv["VNNIC"] / gv["Ookla"])), lo=dlo2, hi=dhi2, share_provinces_ookla_growth_higher=share, label=lab5)])

# ---------- S6
raw = pd.read_parquet(u.ROOT / "data/interim/fact_vnnic_province_month.parquet"); raw = raw[raw.network == "ftth"].copy(); raw["month"] = pd.to_datetime(raw["month"])
cnt = raw.pivot_table(index="month", columns="province_id_legacy63", values="value_raw", aggfunc="first").reindex(columns=D.pids)
rows = []
for m in list(pd.date_range("2021-01-01", "2021-12-01", freq="MS")) + list(pd.date_range("2024-01-01", "2024-12-01", freq="MS")):
    r = cnt.loc[m] if m in cnt.index else None
    rows.append(dict(month=m.strftime("%Y-%m"), national_total=float(np.nansum(r)) if r is not None else np.nan, provinces=int(r.notna().sum()) if r is not None else 0, min_province=float(np.nanmin(r)) if r is not None else np.nan))
s6 = save("s6_vnnic_counts", rows)
w = cnt.loc["2021-01-01":"2024-12-01"]
gate("G18.5", True, f"minimum fixed province-month value_raw 2021-2024 = {np.nanmin(w.values):.0f}; share >= 30 = {np.nanmean(w.values >= 30):.4f}")

# ---------- S7
rows = []; nVs = {}; Dps = {}
for y in YRS:
    nV = np.array([cnt.loc[[pd.Timestamp(y, 4, 1), pd.Timestamp(y, 5, 1), pd.Timestamp(y, 6, 1)], p].mean() for p in D.pids], float)
    Dp = np.abs(stats.rankdata(D.vq2[y]) - stats.rankdata(Oq[(y, 2)]))
    nO = D.OT[(y, 2)]
    nVs[y] = nV; Dps[y] = Dp
    for nm, vec in (("VNNIC volume", nV), ("Ookla tests", nO)):
        bt = u.sp_boot(np.log(vec), Dp); lo, hi = u.ci(bt)
        rows.append(dict(year=y, volume=nm, rho_logvolume_vs_discrepancy=u.sp(np.log(vec), Dp), lo=lo, hi=hi))
    bt = u.sp_boot(np.log(nV), np.log(nO)); rows.append(dict(year=y, volume="VNNIC vs Ookla volume", rho_logvolume_vs_discrepancy=u.sp(np.log(nV), np.log(nO)), lo=u.ci(bt)[0], hi=u.ci(bt)[1]))
mN = np.mean([np.log(nVs[y]) for y in YRS], axis=0); mD = np.mean([Dps[y] for y in YRS], axis=0)
bt = u.sp_boot(mN, mD); lo, hi = u.ci(bt)
rows.append(dict(year="mean of 4", volume="VNNIC volume", rho_logvolume_vs_discrepancy=u.sp(mN, mD), lo=lo, hi=hi))
s7 = save("s7_volume_discrepancy", rows)
lab7 = "larger discrepancy where VNNIC volume is small" if hi < 0 else ("larger discrepancy where volume is large" if lo > 0 else "no relation")
(OUT / "s7_label.txt").write_text(lab7)

# ---------- S8
tdir = HERE / "data" / "ookla_x18"
rows = []; wm = {}
if all((tdir / f"fixed_{y}Q2_tiles.parquet").exists() for y in YRS):
    inv = {v_: k for k, v_ in D.iso.items()}
    def wmed(d, w):
        o = np.argsort(d.values); d_ = d.values[o]; w_ = w.values[o].astype(float); c_ = np.cumsum(w_)
        return float(d_[np.searchsorted(c_, c_[-1] / 2.0)])
    okgate = True
    for y in YRS:
        t = pd.read_parquet(tdir / f"fixed_{y}Q2_tiles.parquet"); t["pid"] = t.shapeISO.map(inv)
        gm = t.groupby("pid"); med = gm.d.median(); wt = gm.apply(lambda g: wmed(g.d, g.tests)); wd = gm.apply(lambda g: wmed(g.d, g.devices))
        frozen = pd.Series(D.fq2[OM][y], index=D.pids)
        match = int(((med.reindex(D.pids) - frozen).abs() <= 0.01).sum()); okgate &= match >= 60
        rows.append(dict(year=y, gate_match_count=match))
        wm[y] = dict(tests=wt.reindex(D.pids).values.astype(float), devices=wd.reindex(D.pids).values.astype(float), tile=frozen.values)
    gate("G18.4", okgate, json.dumps(rows))
    res = []
    for kind in ("tile", "tests", "devices"):
        for y in YRS:
            x, zz = D.vq2[y], wm[y][kind]; bt = u.sp_boot(x, zz); res.append(dict(statistic=f"{kind} median" if kind == "tile" else f"{kind}-weighted median", year=y, rho=u.sp(x, zz), lo=u.ci(bt)[0], hi=u.ci(bt)[1]))
        ch = np.log(wm[2024][kind]) - np.log(wm[2021][kind]); chv = np.log(D.vq2[2024]) - np.log(D.vq2[2021]); bt = u.sp_boot(chv, ch)
        res.append(dict(statistic=f"{kind} median" if kind == "tile" else f"{kind}-weighted median", year="change 2021-2024 (log)", rho=u.sp(chv, ch), lo=u.ci(bt)[0], hi=u.ci(bt)[1]))
    s8 = save("s8_weighted_medians", res)
    chg = s8[s8.year == "change 2021-2024 (log)"]
    signs = set(np.sign(chg.rho)); cis = [(r.lo <= 0 <= r.hi) for r in chg.itertuples()]
    lab8 = "conclusion about change depends on the Ookla statistic" if (len(signs) > 1 or (any(cis) and not all(cis))) else "does not depend"
    (OUT / "s8_label.txt").write_text(lab8)
else:
    lab8 = "S8 not run (tile rebuild missing)"; s8 = None

pd.DataFrame(gates).to_csv(OUT / "gates.csv", index=False)

# ---------- report
rep = ["# X18 report", "", "Specification x18_specification.md (hash in x18_spec_hash.txt). Exploratory post-freeze diagnostics; nothing here says which source is more accurate.", "", "## Gates", u.md(pd.DataFrame(gates)), "",
       "## S1 agreement by year (all quarters)", u.md(s1), "", u.md(s1d), "", u.md(s1e), ""]
if ok:
    rep += [u.md(s1c), ""]
rep += ["## S2 repeatability of change scores", u.md(s2), "", u.md(s2b), "", u.md(s2c), "", u.md(s2d), "", "## S3 dispersion contrast", u.md(s3), "",
        "## S4 agreement measures (per quarter)", u.md(s4), "", u.md(s4b), "", "## S5 levels and growth", u.md(s5a), "", u.md(s5b), "", "## S6 VNNIC published sample counts", u.md(s6), "",
        "## S7 discrepancy and volume", u.md(s7), "", f"R18.5 label: {lab7}", "", "## S8 weighted medians", (u.md(s8) if s8 is not None else lab8), "", f"R18.6 label: {lab8}"]
(HERE / "x18_report.md").write_text("\n".join(rep), encoding="utf-8")
print("DONE", flush=True)
