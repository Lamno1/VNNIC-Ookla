"""X8 per q2_2024_anomaly_specification.md (hash chain q2_spec_hash.txt). Labels applied mechanically."""
import json
import upg_common as U
from upg_common import *
U.SEED, U.PSEED = 20261012, 20261013
U._IDX.clear()

D = Data(with_ext=True)
R = HERE / "results_q2"; R.mkdir(exist_ok=True)
lab = {}
names = pd.read_parquet(ROOT / "data/analysis/analysis_panel_2021_2024.parquet").drop_duplicates("province_id_legacy63").set_index("province_id_legacy63").province_name_canonical
pname = np.array([names.get(p, p) for p in D.pids])
fact = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet")
fact = fact[fact.network == "ftth"].copy(); fact["month"] = pd.to_datetime(fact["month"])
RAWV = fact.pivot_table(index="month", columns="province_id_legacy63", values="value_raw", aggfunc="first").reindex(columns=D.pids)
M = D.M
O = D.O; V = D.V
T = (2024, 2)
def prev(y, q): return (y, q - 1) if q > 1 else (y - 1, 4)
def nxt(y, q): return (y, q + 1) if q < 4 else (y + 1, 1)
def save(name, rows):
    df = pd.DataFrame(rows); df.to_csv(R / f"{name}.csv", index=False); return df

# ------------------------------------------------ gates
x2a = pd.read_csv(HERE / "results" / "x2a_level_grid.csv")
g81 = []
for q in (1, 2, 3, 4):
    tgt = float(x2a[(x2a.year == 2024) & (x2a.q == q) & (x2a.window == "W0")].rho.iloc[0]); r = sp(V(2024, q), O[(2024, q)])
    g81.append(dict(gate="G8.1", item=f"2024Q{q}", value=r, target=tgt, passed=abs(r - tgt) < 0.005))
mm = [pd.Timestamp(2024, m, 1) for m in (3, 4, 5, 6, 7)]
n_all = int(M.reindex(mm).notna().all().sum())
g81.append(dict(gate="G8.2", item="provinces with Mar-Jul 2024 all present", value=n_all, target=60, passed=n_all >= 60))
rr = RAWV.reindex([pd.Timestamp(2024, m, 1) for m in range(1, 13)]).to_numpy().ravel(); share = float((rr[np.isfinite(rr)] >= 30).mean())
g81.append(dict(gate="G8.0", item="share value_raw>=30, 2024 ftth", value=share, target=0.95, passed=share >= 0.95))
gt = save("gates", g81); print(gt.to_string())
if not gt.passed.all():
    print("GATE FAILURE: stop"); raise SystemExit(1)
count_ok = bool(gt[gt.gate == "G8.0"].passed.iloc[0])

# ------------------------------------------------ A1
def a1(Tq):
    p, n = prev(*Tq), nxt(*Tq)
    arrs = {"VT": V(*Tq), "VP": V(*p), "VN": V(*n), "OT": O[Tq], "OP": O[p], "ON": O[n]}
    ok = np.all([np.isfinite(a) for a in arrs.values()], axis=0); a = {k: v[ok] for k, v in arrs.items()}; nn = int(ok.sum())
    idx = make_idx(nn)
    def A(x, others): return np.mean([sp_boot(a[x], a[o], idx) for o in others], axis=0)
    AVb = A("VT", ["VP", "VN", "OP", "ON"]); AOb = A("OT", ["OP", "ON", "VP", "VN"])
    AVo = np.mean([sp(a["VT"], a[o]) for o in ("VP", "VN", "OP", "ON")]); AOo = np.mean([sp(a["OT"], a[o]) for o in ("OP", "ON", "VP", "VN")])
    d = AVo - AOo; lo, hi = ci(AVb - AOb)
    label = "VNNIC-side" if (d < -0.15 and hi < 0) else ("Ookla-side" if (d > 0.15 and lo > 0) else "not isolated to one side")
    return dict(year=Tq[0], q=Tq[1], N=nn, A_V=float(AVo), A_O=float(AOo), D=float(d), lo=lo, hi=hi, rho_W0=sp(a["VT"], a["OT"]), label=label)
qs = [(y, q) for y in (2021, 2022, 2023, 2024) for q in (1, 2, 3, 4) if (2021, 2) <= (y, q) <= (2024, 3)]
a1t = save("a1_side_attribution", [a1(t) for t in qs]); lab["R8.1 (2024Q2)"] = a1t[(a1t.year == 2024) & (a1t.q == 2)].iloc[0].to_dict()

# ------------------------------------------------ A2
o2 = O[T]; v2 = V(*T)
mon = [pd.Timestamp(2024, m, 1) for m in range(1, 9)]
rows = []
for m in mon:
    x = M.loc[m].to_numpy(float)
    rows.append(dict(month=m.strftime("%Y-%m"), **{f"rho_Ookla_Q{q}": (lambda a, b: sp(a[np.isfinite(a) & np.isfinite(b)], b[np.isfinite(a) & np.isfinite(b)]))(x, O[(2024, q)]) for q in (1, 2, 3)}))
a2i = save("a2i_month_vs_ookla", rows)
ms = pd.date_range("2023-01-01", "2024-12-01", freq="MS"); zs = []; rowsr = []
for a_, b_ in zip(ms[:-1], ms[1:]):
    x, y = M.loc[a_].to_numpy(float), M.loc[b_].to_numpy(float); ok = np.isfinite(x) & np.isfinite(y); r = sp(x[ok], y[ok]); zs.append(np.arctanh(np.clip(r, -0.999, 0.999)))
    rowsr.append(dict(pair=f"{a_:%Y-%m}/{b_:%Y-%m}", N=int(ok.sum()), r=r, z=zs[-1]))
zs = np.array(zs); flag = []
for i in range(len(zs)):
    o_ = np.delete(zs, i); flag.append(bool(zs[i] < o_.mean() - 2 * o_.std(ddof=1)))
a2ii = save("a2ii_adjacent_month_repeatability", [dict(**r, flagged=f) for r, f in zip(rowsr, flag)])
flagged_pairs = set(a2ii[a2ii.flagged].pair)
three = {m: pd.Timestamp(2024, m, 1) for m in (4, 5, 6)}
base3 = sp(v2[np.isfinite(v2) & np.isfinite(o2)], o2[np.isfinite(v2) & np.isfinite(o2)])
rows = []; crit = {}
lowest = a2i[a2i.month.isin(["2024-04", "2024-05", "2024-06"])].sort_values("rho_Ookla_Q2").month.iloc[0]
import itertools
for k in range(1, 3):
    for sub in itertools.combinations((4, 5, 6), k):
        x = np.nanmedian(np.vstack([M.loc[three[m]].to_numpy(float) for m in sub]), axis=0); ok = np.isfinite(x) & np.isfinite(o2)
        rows.append(dict(months_used="+".join(f"{m:02d}" for m in sub), rho_with_Ookla_Q2=sp(x[ok], o2[ok])))
a2iii = save("a2iii_month_removal", rows)
for mrem in (4, 5, 6):
    others = tuple(m for m in (4, 5, 6) if m != mrem); r = float(a2iii[a2iii.months_used == "+".join(f"{m:02d}" for m in others)].rho_with_Ookla_Q2.iloc[0])
    mlabel = f"2024-{mrem:02d}"
    pairs = {f"2024-{mrem-1:02d}/2024-{mrem:02d}", f"2024-{mrem:02d}/2024-{mrem+1:02d}"}
    flagged = bool(pairs & flagged_pairs) or (mlabel == lowest)
    crit[mrem] = (r >= 0.50 and r - base3 >= 0.20 and flagged, r, flagged)
nmo = [m for m, v in crit.items() if v[0]]
lab["R8.2"] = ("month-driven (month %d)" % nmo[0] if len(nmo) == 1 else "not month-driven", crit, dict(base=base3, lowest_month=lowest, flagged_pairs=sorted(flagged_pairs)))

# ------------------------------------------------ A3
ok = np.isfinite(v2) & np.isfinite(o2); idsel = np.flatnonzero(ok); x, y = v2[ok], o2[ok]; nn = len(x)
loo = np.array([sp(np.delete(x, i), np.delete(y, i)) for i in range(nn)]); base = sp(x, y)
rk_v, rk_o = stats.rankdata(x), stats.rankdata(y); dp = np.abs(rk_v - rk_o)
top5 = np.argsort(-dp)[:5]
keep = np.setdiff1d(np.arange(nn), top5); after5 = sp(x[keep], y[keep])
rng = np.random.default_rng(20261012)
ridx = np.array([np.sort(rng.choice(nn, nn - 5, replace=False)) for _ in range(5000)])
rand_after = corr_rows(rk(x[ridx]), rk(y[ridx])); p95 = float(np.percentile(rand_after, 95))
a3 = save("a3_provinces", [dict(item="base rho", value=base), dict(item="LOO min", value=float(loo.min())), dict(item="LOO max", value=float(loo.max())), dict(item="max |change|", value=float(np.abs(loo - base).max())),
                           dict(item="rho after removing top-5 discrepant", value=after5), dict(item="random 5-removal mean", value=float(rand_after.mean())), dict(item="random 5-removal p95", value=p95)])
top = pd.DataFrame(dict(province=pname[idsel][top5], shapeISO=[D.iso[D.pids[i]] for i in idsel[top5]], d_p=dp[top5], rank_V=rk_v[top5], rank_O=rk_o[top5])); top.to_csv(R / "a3_top5.csv", index=False)
def topset(Tq, k=10):
    a, b = V(*Tq), O[Tq]; ok_ = np.isfinite(a) & np.isfinite(b); d_ = np.full(D.n, -1.0); d_[ok_] = np.abs(stats.rankdata(a[ok_]) - stats.rankdata(b[ok_])); return set(np.argsort(-d_)[:k])
base_top = topset(T); pers = save("a3_persistence", [dict(quarter=f"{y_}Q{q_}", overlap_top10=len(base_top & topset((y_, q_))) / 10) for (y_, q_) in [(2023, 2), (2023, 3), (2024, 1), (2024, 3)]])
lab["R8.3"] = ("few-province driven" if (after5 >= 0.45 and after5 > p95) else "broad-based", dict(after5=after5, p95=p95, base=base))

# ------------------------------------------------ A4
res = {}
Vq1, Vq2 = V(2024, 1), V(2024, 2)
apr, may = M.loc[pd.Timestamp(2024, 4, 1)].to_numpy(float), M.loc[pd.Timestamp(2024, 5, 1)].to_numpy(float)
spike = (apr > 1.25 * Vq1) | (may > 1.25 * Vq1); spike &= np.isfinite(Vq1)
okall = np.isfinite(v2) & np.isfinite(o2) & np.isfinite(O[(2024, 1)])
rho_wo = sp(v2[okall & ~spike], o2[okall & ~spike]) if (okall & ~spike).sum() > 10 else np.nan
chg = np.log(O[(2024, 2)]) - np.log(O[(2024, 1)]); gs, gr = chg[spike & okall], chg[~spike & okall]
mw = stats.mannwhitneyu(gs, gr, alternative="two-sided").pvalue if len(gs) > 2 and len(gr) > 2 else np.nan
rngb = np.random.default_rng(20261012); diffs = []
for _ in range(B):
    if len(gs) > 0 and len(gr) > 0:
        diffs.append(np.median(rngb.choice(gs, len(gs))) - np.median(rngb.choice(gr, len(gr))))
dlo, dhi = ci(diffs) if diffs else (np.nan, np.nan)
a4i = save("a4i_spike", [dict(n_spike=int(spike.sum()), rho_without_spike=rho_wo, rho_all=base, median_chg_spike=float(np.median(gs)) if len(gs) else np.nan, median_chg_rest=float(np.median(gr)), diff_lo=dlo, diff_hi=dhi, mannwhitney_p=mw)])
res["spike"] = bool(np.isfinite(dlo) and (dlo > 0 or dhi < 0))
# depth
dep = np.nanmean(RAWV.reindex([pd.Timestamp(2024, m, 1) for m in (4, 5, 6)]).to_numpy(float), axis=0)
dep_other = {"Q1": np.nanmean(RAWV.reindex([pd.Timestamp(2024, m, 1) for m in (1, 2, 3)]).to_numpy(float), axis=0), "Q3": np.nanmean(RAWV.reindex([pd.Timestamp(2024, m, 1) for m in (7, 8, 9)]).to_numpy(float), axis=0)}
depth_rows = [dict(item="national median monthly count Q2", value=float(np.nanmedian(dep))), dict(item="Q1", value=float(np.nanmedian(dep_other["Q1"]))), dict(item="Q3", value=float(np.nanmedian(dep_other["Q3"])))]
if count_ok:
    sel = np.flatnonzero(np.isfinite(dep) & np.isfinite(v2) & np.isfinite(o2))
    order = sel[np.argsort(dep[sel])]; t3 = np.array_split(order, 3); zt = []
    for g in (t3[0], t3[2]):
        zt.append(np.arctanh(np.clip(sp(v2[g], o2[g]), -0.999, 0.999)))
    dz = zt[0] - zt[1]
    rb = np.random.default_rng(20261012); dbs = []
    for _ in range(B):
        zz = []
        for g in (t3[0], t3[2]):
            s_ = rb.choice(g, len(g)); zz.append(np.arctanh(np.clip(sp(v2[s_], o2[s_]), -0.999, 0.999)))
        dbs.append(zz[0] - zz[1])
    lo_, hi_ = ci(dbs)
    depth_rows += [dict(item="rho lowest tertile", value=sp(v2[t3[0]], o2[t3[0]])), dict(item="rho highest tertile", value=sp(v2[t3[2]], o2[t3[2]])), dict(item="z diff (low-high)", value=float(dz)), dict(item="z diff lo", value=lo_), dict(item="z diff hi", value=hi_)]
    res["depth"] = bool(lo_ > 0 or hi_ < 0)
else:
    res["depth"] = False
a4ii = save("a4ii_depth", depth_rows)
# Ookla universe
tl1, tl2, tl3 = D.OTL[(2024, 1)], D.OTL[(2024, 2)], D.OTL[(2024, 3)]
dp_full = np.full(D.n, np.nan); dp_full[idsel] = dp
lr = np.abs(np.log(tl2 / tl1)); m_ = np.isfinite(dp_full) & np.isfinite(lr)
c = sp(dp_full[m_], lr[m_]); lo_, hi_ = ci(sp_boot(dp_full[m_], lr[m_]))
tiles = save("a4iii_tiles", [dict(quarter=f"{y}Q{q}", national_tiles=float(np.nansum(D.OTL[(y, q)])), national_tests=float(np.nansum(D.OT[(y, q)]))) for y in (2023, 2024) for q in (1, 2, 3, 4)] + [dict(quarter="rho(d_p, |log tile ratio Q2/Q1|)", national_tiles=c, national_tests=np.nan), dict(quarter="  CI lo", national_tiles=lo_, national_tests=np.nan), dict(quarter="  CI hi", national_tiles=hi_, national_tests=np.nan)])
res["tiles"] = bool(lo_ > 0 or hi_ < 0)
# aggregator
rowsg = []
for nm, col in (("tile_median", "ookla_tile_median_download_mbps"), ("tile_mean", "ookla_tile_mean_download_mbps"), ("tests_weighted", "ookla_tests_weighted_mean_download_mbps"), ("devices_weighted", "ookla_devices_weighted_mean_download_mbps")):
    rowsg.append(dict(aggregator=nm, rho_2024Q2=sp(D.vq2[2024], D.fq2[col][2024])))
a4iv = save("a4iv_aggregator", rowsg); hit = a4iv[a4iv.rho_2024Q2 >= 0.50]
res["aggregator"] = bool(len(hit) == 1)
# level vs rank
rowsv = []
for q in (1, 2, 3, 4):
    for src, arr in (("VNNIC", V(2024, q)), ("Ookla", O[(2024, q)])):
        rowsv.append(dict(quarter=f"2024Q{q}", source=src, national_median=float(np.nanmedian(arr)), p90_p10=float(np.nanpercentile(arr, 90) / np.nanpercentile(arr, 10)), cv=float(np.nanstd(arr, ddof=1) / np.nanmean(arr))))
a4v = save("a4v_level_vs_rank", rowsv)
lab["R8.4"] = res

# ------------------------------------------------ report
head = lab["R8.1 (2024Q2)"]["label"]
any_pos = (lab["R8.2"][0].startswith("month")) or (lab["R8.3"][0] == "few-province driven") or any(res.values())
final = head if head != "not isolated to one side" else ("not isolated to one side; mechanisms: " + ("see R8.2-R8.4" if any_pos else "unexplained by these diagnostics"))
rep = ["# X8 report: Q2 2024 anomaly\n", "Generated by run_q2_anomaly.py per q2_2024_anomaly_specification.md (hash chain q2_spec_hash.txt, D1 logged before running). Numbers come from results_q2/*.csv; labels are mechanical.\n",
       "## Gates\n", md(gt), "\n## A1 side attribution (R8.1)\n", md(a1t), "\n## A2 months\n", md(a2i), "\n", md(a2ii), "\n", md(a2iii), f"\nR8.2: {lab['R8.2']}\n",
       "\n## A3 provinces\n", md(a3), "\nTop-5 discrepant provinces 2024Q2:\n", md(top), "\nPersistence of top-10:\n", md(pers), f"\nR8.3: {lab['R8.3']}\n",
       "\n## A4 mechanisms (exploratory)\n", "(i) spike\n", md(a4i), "\n(ii) depth\n", md(a4ii), "\n(iii) Ookla universe\n", md(tiles), "\n(iv) aggregator\n", md(a4iv), "\n(v) level vs rank (descriptive)\n", md(a4v),
       f"\nR8.4 supported flags: {res}\n", f"\n## Summary label\n{final}\n"]
(HERE / "q2_2024_report.md").write_text("\n".join(rep), encoding="utf-8")
print("DONE"); print(final); print(lab["R8.1 (2024Q2)"]); print(lab["R8.2"]); print(lab["R8.3"]); print(res)
