"""X14 per x14_surge_specification.md incl. D1 (hash chain x14_spec_hash.txt). Labels applied mechanically."""
import json
import upg_common as U
from upg_common import *
U.SEED, U.PSEED = 20261022, 20261023
U._IDX.clear()

D = Data(with_ext=False)
R = HERE / "results_x14"; R.mkdir(exist_ok=True)
fact = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet"); fact["month"] = pd.to_datetime(fact["month"])
def pv(net, col): return fact[fact.network == net].pivot_table(index="month", columns="province_id_legacy63", values=col, aggfunc="first").reindex(columns=D.pids)
SP, CT = pv("ftth", "download"), pv("ftth", "value_raw"); CTm = pv("mobile", "value_raw")
def mon(s): return pd.Timestamp(s + "-01")
def save(name, rows):
    df = pd.DataFrame(rows); df.to_csv(R / f"{name}.csv", index=False); return df
W = [mon("2024-03"), mon("2024-04"), mon("2024-05")]; RF = [mon(m) for m in ("2023-12", "2024-01", "2024-02", "2024-06", "2024-07", "2024-08")]
OOK = D.O[(2024, 2)]

# ------------------------------------------------ gates
g = []
tot = CT.sum(axis=1)
for m, v in (("2024-02", 268763), ("2024-03", 513772), ("2024-04", 499462), ("2024-05", 485288), ("2024-06", 215717)):
    g.append(dict(gate="G14.1", item=f"national fixed tests {m}", value=float(tot.loc[mon(m)]), target=v, passed=abs(tot.loc[mon(m)] - v) < 0.5))
x12 = pd.read_csv(HERE / "results_x12" / "s1_local_scan.csv"); x12f = x12[x12.family == "F1"].set_index("month")
for m, v in (("2024-04", -5.657), ("2024-05", -8.550)):
    g.append(dict(gate="G14.2", item=f"F1 local z {m}", value=float(x12f.loc[m, "z_local"]), target=v, passed=abs(x12f.loc[m, "z_local"] - v) < 0.01))
def complete(months):
    return (CT.reindex(months).notna().all() & SP.reindex(months).notna().all()).to_numpy()
okT = complete(W + RF); g.append(dict(gate="G14.3", item="provinces with all months of W and R", value=int(okT.sum()), target=60, passed=int(okT.sum()) >= 60))
gt = save("gates", g); print(gt.to_string())
if not gt.passed.all():
    print("GATE FAILURE: stop"); raise SystemExit(1)

# ------------------------------------------------ helpers
def ranks(x): return stats.rankdata(x)
def resid(a, z):
    X = np.column_stack([np.ones(len(z)), z]); return a - X @ np.linalg.lstsq(X, a, rcond=None)[0]
def prc(ls, d, lnr):
    ex, ey = resid(ranks(ls), ranks(lnr)), resid(ranks(d), ranks(lnr)); return float(np.corrcoef(ex, ey)[0, 1]), ex, ey
def stats_window(Wm, Rm, ook=None, prov=None):
    ok = complete(Wm + Rm)
    if prov is not None: ok = ok & prov
    if ok.sum() < 60: return None
    nW = CT.reindex(Wm).to_numpy(float)[:, ok].mean(0); nR = CT.reindex(Rm).to_numpy(float)[:, ok].mean(0)
    vW = np.median(SP.reindex(Wm).to_numpy(float)[:, ok], axis=0); vR = np.median(SP.reindex(Rm).to_numpy(float)[:, ok], axis=0)
    rW, rR = ranks(vW), ranks(vR); d = np.abs(rW - rR); s = nW / nR
    out = dict(ok=ok, nW=nW, nR=nR, s=s, vW=vW, vR=vR, rW=rW, rR=rR, D=d)
    if ook is not None:
        oo = ook[ok]; m = np.isfinite(oo); out["ook_ok"] = m
    return out
def t1p_point(Wm, Rm):
    r = stats_window(Wm, Rm)
    if r is None: return np.nan, 0
    return prc(np.log(r["s"]), r["D"], np.log(r["nR"]))[0], int(r["ok"].sum())

# ------------------------------------------------ S1 monthly
months = list(pd.date_range("2021-04-01", "2025-06-01", freq="MS")); T = tot.reindex(pd.date_range("2021-01-01", "2025-06-01", freq="MS"))
rows = []
for m in months:
    prev3 = [m - pd.DateOffset(months=k) for k in (1, 2, 3)]; qprev = T.loc[m] / np.median([T.loc[x] for x in prev3])
    win = [m + pd.DateOffset(months=k) for k in range(-6, 7) if k != 0 and (m + pd.DateOffset(months=k)) in T.index and (m + pd.DateOffset(months=k)) >= mon("2021-04")]
    qcent = T.loc[m] / np.median([T.loc[x] for x in win]); pm = m - pd.DateOffset(months=1)
    a, b = CT.loc[m].to_numpy(float), CT.loc[pm].to_numpy(float) if pm in CT.index else np.full(D.n, np.nan); okk = np.isfinite(a) & np.isfinite(b)
    rc = sp(a[okk], b[okk]) if okk.sum() >= 30 else np.nan
    zl = float(x12f.loc[m.strftime("%Y-%m"), "z_local"]) if m.strftime("%Y-%m") in x12f.index else np.nan
    hv = bool(m >= mon("2022-01") and (qprev >= 1.5 or qcent >= 1.5))
    rows.append(dict(month=m.strftime("%Y-%m"), total_tests=float(T.loc[m]), q_prev3=float(qprev), q_centred=float(qcent), count_rank_corr_prev=rc, z_local_F1=zl, high_volume=hv))
s1 = save("s1_monthly", rows)
tgt = {"2024-03", "2024-04", "2024-05"}
hv_out = s1[s1.high_volume & ~s1.month.isin(tgt) & s1.z_local_F1.notna() & (s1.month <= "2024-12")]
r141 = "not evaluable" if len(hv_out) == 0 else ("volume alone is not sufficient" if (hv_out.z_local_F1 > -2).any() else "volume tracks the anomaly")

# ------------------------------------------------ S2 main test
r = stats_window(W, RF, OOK); ok = r["ok"]; n = int(ok.sum()); ls, d, lnr = np.log(r["s"]), r["D"], np.log(r["nR"])
idx = make_idx(n)
t1 = sp(ls, d); b1 = corr_rows(rk(ls[idx]), rk(d[idx])); lo1, hi1 = ci(b1); p1 = perm_p(ls, d)
t1p, ex, ey = prc(ls, d, lnr)
b1p = np.array([prc(ls[idx[i]], d[idx[i]], lnr[idx[i]])[0] for i in range(B)]); lo1p, hi1p = ci(b1p)
rng = np.random.default_rng(U.PSEED); perms = rng.permuted(np.tile(np.arange(n), (NPERM, 1)), axis=1)
ps = np.array([np.corrcoef(ex[pi], ey)[0, 1] for pi in perms]); p1p = (1 + int((np.abs(ps) >= abs(t1p) - 1e-12).sum())) / (NPERM + 1)
tert = np.argsort(ls); k = n // 3; bot, top = tert[:k], tert[-k:]; gdiff = float(d[top].mean() - d[bot].mean())
gb = []
for i in range(B):
    ii = idx[i]; o = np.argsort(ls[ii]); gb.append(d[ii][o[-k:]].mean() - d[ii][o[:k]].mean())
glo, ghi = ci(gb)
# placebo windows
starts = list(pd.date_range("2022-04-01", "2023-09-01", freq="MS")) + list(pd.date_range("2024-09-01", "2025-01-01", freq="MS")); pl = []
for s0 in starts:
    Wp = [s0 + pd.DateOffset(months=k) for k in range(3)]; Rp = [s0 + pd.DateOffset(months=k) for k in (-3, -2, -1, 3, 4, 5)]
    if set(Wp + Rp) & set(W): continue
    if any(x not in CT.index for x in Wp + Rp): continue
    v, nn = t1p_point(Wp, Rp)
    cc = stats_window(Wp, Rp); comp = np.nan
    if cc is not None: comp = sp(cc["nW"], cc["nR"])
    if np.isfinite(v): pl.append(dict(start=s0.strftime("%Y-%m"), N=nn, T1p=v, composition_rank_corr=comp, in_2025_regime=bool(s0 >= mon("2024-09"))))
pl = save("s2_placebo", pl); m_all = len(pl); mx = float(pl.T1p.max()); red = pl[~pl.in_2025_regime]; mx_red = float(red.T1p.max())
if hi1p < 0: r142 = "reverse association (more tests, smaller displacement; compatible with noise reduction)"
elif lo1p > 0: r142 = "dose-response present" if t1p > mx else "weak"
else: r142 = "dose-response absent"
s2 = save("s2_dose_response", [dict(item="T1 raw Spearman(log s, D)", value=t1, lo=lo1, hi=hi1, p=p1), dict(item="T1p partial on log n_R", value=t1p, lo=lo1p, hi=hi1p, p=p1p),
                                 dict(item="top minus bottom tertile mean D", value=gdiff, lo=glo, hi=ghi, p=np.nan), dict(item="placebo windows valid (m)", value=m_all, lo=np.nan, hi=np.nan, p=1 / (m_all + 1)),
                                 dict(item="placebo T1p max (all)", value=mx, lo=np.nan, hi=np.nan, p=np.nan), dict(item="placebo T1p max (without 2025-regime windows)", value=mx_red, lo=np.nan, hi=np.nan, p=1 / (len(red) + 1)),
                                 dict(item="placebo T1p median", value=float(pl.T1p.median()), lo=np.nan, hi=np.nan, p=np.nan), dict(item="provinces in analysis", value=n, lo=np.nan, hi=np.nan, p=np.nan)])
exceeds_red = bool(t1p > mx_red)

# ------------------------------------------------ S3 cross-source and level shift
mk = r["ook_ok"]; ook = OOK[ok]; ro = np.full(n, np.nan); ro[mk] = stats.rankdata(ook[mk])
sub = np.flatnonzero(mk); rW2, rR2, ro2 = stats.rankdata(r["vW"][sub]), stats.rankdata(r["vR"][sub]), stats.rankdata(ook[sub])
Cp = np.abs(rW2 - ro2) - np.abs(rR2 - ro2); ls2, lnr2 = ls[sub], lnr[sub]
t2, ex2, ey2 = prc(ls2, Cp, lnr2); idx2 = make_idx(len(sub)); b2 = np.array([prc(ls2[idx2[i]], Cp[idx2[i]], lnr2[idx2[i]])[0] for i in range(B)]); lo2, hi2 = ci(b2)
rng2 = np.random.default_rng(U.PSEED + 1); perms2 = rng2.permuted(np.tile(np.arange(len(sub)), (NPERM, 1)), axis=1)
p2 = (1 + int((np.abs(np.array([np.corrcoef(ex2[pi], ey2)[0, 1] for pi in perms2])) >= abs(t2) - 1e-12).sum())) / (NPERM + 1)
t2raw = sp(ls2, Cp)
r143 = "surge provinces agree worse with Ookla" if lo2 > 0 else ("surge provinces agree better with Ookla" if hi2 < 0 else "no relation")
lvl = np.log(r["vW"] / r["vR"]); tl = sp(ls, lvl); bl = corr_rows(rk(ls[idx]), rk(lvl[idx])); llo, lhi = ci(bl)
s3 = save("s3_cross_source", [dict(item="T2 partial Spearman(log s, C)", value=t2, lo=lo2, hi=hi2, p=p2), dict(item="T2 raw Spearman(log s, C)", value=t2raw, lo=np.nan, hi=np.nan, p=np.nan),
                               dict(item="level shift Spearman(log s, log vW/vR)", value=tl, lo=llo, hi=lhi, p=np.nan), dict(item="share of provinces with s >= 2", value=float((r["s"] >= 2).mean()), lo=np.nan, hi=np.nan, p=np.nan),
                               dict(item="provinces in S3", value=len(sub), lo=np.nan, hi=np.nan, p=np.nan)])

# ------------------------------------------------ S4 controls and overall
mobW = CTm.reindex(W).sum(axis=1).mean(); mobR = CTm.reindex(RF).sum(axis=1).mean(); fixW = tot.reindex(W).mean(); fixR = tot.reindex(RF).mean()
r144 = "mobile also surged without the anomaly" if mobW / mobR >= 1.5 else "mobile did not surge"
comp_t = sp(r["nW"], r["nR"]); comp_pl = pl.composition_rank_corr.dropna(); r145 = "composition shift unusual" if comp_t < comp_pl.min() else "not unusual"
s4 = save("s4_controls", [dict(item="fixed national mean monthly tests W / R", value=float(fixW / fixR)), dict(item="mobile national mean monthly tests W / R", value=float(mobW / mobR)),
                           dict(item="composition: rank corr of provincial counts, W vs R (target)", value=comp_t), dict(item="composition: placebo min", value=float(comp_pl.min())), dict(item="composition: placebo median", value=float(comp_pl.median())), dict(item="composition: placebo max", value=float(comp_pl.max()))])
holds = [r142 == "dose-response present", r143 == "surge provinces agree worse with Ookla"]; r146 = "H supported" if all(holds) else ("H partly supported" if any(holds) else "H not supported")
lab = dict(R14_1=(r141, hv_out[["month", "q_prev3", "q_centred", "z_local_F1"]].to_dict("records")), R14_2=(r142, dict(T1p=t1p, ci=(lo1p, hi1p), placebo_max=mx, placebo_max_reduced=mx_red, exceeds_reduced=exceeds_red, m=m_all)),
           R14_3=(r143, dict(T2=t2, ci=(lo2, hi2))), R14_4=r144, R14_5=(r145, dict(target=comp_t, placebo_min=float(comp_pl.min()))), R14_6=r146)
json.dump({k: str(v) for k, v in lab.items()}, open(R / "labels.json", "w"), indent=1)
rep = ["# X14 report: test-volume surge and rank scrambling, VNNIC fixed, March-May 2024\n", "Generated by run_x14.py per x14_surge_specification.md incl. D1 (hash chain x14_spec_hash.txt). EXPLORATORY and POST HOC; association only; numbers come from results_x14/*.csv.\n",
       "## Gates\n", md(gt), "\n## S1 monthly volume (2021-04 to 2025-06)\n", md(s1), f"\nR14.1: {lab['R14_1']}\n", "\n## S2 dose-response\n", md(s2), "\n", md(pl), f"\nR14.2: {lab['R14_2']}\n", "\n## S3 cross-source\n", md(s3), f"\nR14.3: {lab['R14_3']}\n",
       "\n## S4 controls\n", md(s4), f"\nR14.4: {r144}\nR14.5: {lab['R14_5']}\n", f"\n## Overall\nR14.6: {r146}\n"]
(HERE / "x14_report.md").write_text("\n".join(rep), encoding="utf-8")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(s1[(s1.high_volume) | s1.month.isin(["2024-02", "2024-03", "2024-04", "2024-05", "2024-06"])].round(3).to_string(index=False)); print("R14.1", lab["R14_1"][0])
print(s2.round(3).to_string(index=False)); print(pl.round(3).to_string(index=False)); print("R14.2", lab["R14_2"]); print(s3.round(3).to_string(index=False)); print("R14.3", r143); print(s4.round(3).to_string(index=False)); print("R14.4", r144, "| R14.5", lab["R14_5"], "| R14.6", r146)
