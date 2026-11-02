"""X1, X2, X4, X5, X7 per upgrade_specification.md (hash chain in spec_hash.txt). Labels are applied mechanically."""
import sys, json
from upg_common import *

D = Data(with_ext=True)
R = HERE / "results"; R.mkdir(exist_ok=True)
OM = "ookla_tile_median_download_mbps"
out = {}   # name -> DataFrame
lab = {}   # mechanical labels


def save(name, rows):
    df = pd.DataFrame(rows); out[name] = df; df.to_csv(R / f"{name}.csv", index=False); return df


def cell(x, y, perm=True):
    x = np.asarray(x, float); y = np.asarray(y, float); m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    n = len(x)
    if n < 10:
        return dict(N=n, rho=np.nan, lo=np.nan, hi=np.nan, p=np.nan)
    r = sp(x, y); lo, hi = ci(sp_boot(x, y))
    return dict(N=n, rho=r, lo=lo, hi=hi, p=perm_p(x, y) if perm else np.nan)


# ---------------------------------------------------------------- X1
yrs = range(2021, 2025)
rows = []
for y in yrs:
    x, z = D.vq2[y], D.fq2[OM][y]
    c = cell(x, z); pc = pe(np.log(x), np.log(z)); plo, phi = ci(pe_boot(np.log(x), np.log(z)))
    rows.append(dict(item=f"yearly Spearman {y}", **c, pearson_log=pc, pearson_lo=plo, pearson_hi=phi))
x1a = save("x1a_yearly", rows)
# change-rank, 4 aggregations, raw and log
aggs = {"tile_median": OM, "tile_mean": "ookla_tile_mean_download_mbps", "tests_weighted": "ookla_tests_weighted_mean_download_mbps", "devices_weighted": "ookla_devices_weighted_mean_download_mbps"}
rows = []
for nm, col in aggs.items():
    for scale in ("raw", "log"):
        f = (lambda a: a) if scale == "raw" else np.log
        dv = f(D.vq2[2024]) - f(D.vq2[2021]); do = f(D.fq2[col][2024]) - f(D.fq2[col][2021])
        rows.append(dict(item=f"change-rank {nm} ({scale})", **cell(dv, do)))
x1b = save("x1b_change_rank", rows)
# Holm family: 4 yearly + change tile_median raw
fam = [x1a.p[i] for i in range(4)] + [x1b.p[0]]
hp = holm(fam)
x1a["p_holm"] = list(hp[:4]); x1b["p_holm"] = [hp[4]] + [np.nan] * (len(x1b) - 1)
x1a.to_csv(R / "x1a_yearly.csv", index=False); x1b.to_csv(R / "x1b_change_rank.csv", index=False)
# difference rho2021 - rho2024 (paired bootstrap)
idx = make_idx(D.n)
d_b = sp_boot(D.vq2[2021], D.fq2[OM][2021]) - sp_boot(D.vq2[2024], D.fq2[OM][2024])
d_obs = sp(D.vq2[2021], D.fq2[OM][2021]) - sp(D.vq2[2024], D.fq2[OM][2024]); dlo, dhi = ci(d_b)
x1c = save("x1c_rho_decline", [dict(item="rho2021 - rho2024", est=d_obs, lo=dlo, hi=dhi, label="declined" if dlo > 0 or dhi < 0 else "not distinguishable")])


def indicators(a):  # a: (..., n)
    sd = a.std(-1, ddof=1); sdl = np.log(a).std(-1, ddof=1); mean = a.mean(-1)
    q = np.percentile(a, [10, 25, 75, 90], axis=-1)
    return dict(sd_level=sd, sd_log=sdl, cv=sd / mean, iqr=q[2] - q[1], p90_p10=q[3] / q[0], max_min=a.max(-1) / a.min(-1))


rows = []
conc = {}
for src, arr in (("VNNIC", D.vq2), ("Ookla", D.fq2[OM])):
    i21, i24 = indicators(arr[2021]), indicators(arr[2024])
    b21, b24 = indicators(arr[2021][idx]), indicators(arr[2024][idx])
    for k in i21:
        lr = np.log(i24[k] / i21[k]); lb = np.log(b24[k] / b21[k]); lo, hi = ci(lb)
        sign = 0 if (lo <= 0 <= hi) else int(np.sign(lr))
        conc.setdefault(k, {})[src] = sign
        rows.append(dict(source=src, indicator=k, v2021=float(i21[k]), v2024=float(i24[k]), log_ratio=float(lr), lo=lo, hi=hi, sign_if_CI_excludes_0=sign))
x1d = save("x1d_dispersion", rows)
x1d_sum = pd.DataFrame([dict(indicator=k, VNNIC=v["VNNIC"], Ookla=v["Ookla"], same_direction=(v["VNNIC"] == v["Ookla"] != 0)) for k, v in conc.items()])
x1d_sum.to_csv(R / "x1d_dispersion_concordance.csv", index=False)
# direction
rows = []
dV = D.vq2[2024] - D.vq2[2021]; dO = D.fq2[OM][2024] - D.fq2[OM][2021]
for nm, k in (("VNNIC positive", int((dV > 0).sum())), ("Ookla positive", int((dO > 0).sum())), ("both positive", int(((dV > 0) & (dO > 0)).sum())), ("same sign", int((np.sign(dV) == np.sign(dO)).sum()))):
    lo, hi = clopper_pearson(k, D.n); rows.append(dict(item=nm, k=k, n=D.n, lo=lo, hi=hi))
x1e = save("x1e_direction", rows)

# ---------------------------------------------------------------- X2
rows = []
def prev(y, q): return (y, q - 1) if q > 1 else (y - 1, 4)
def nxt(y, q): return (y, q + 1) if q < 4 else (y + 1, 1)
W0 = {}
for y in yrs:
    for q in (1, 2, 3, 4):
        o = D.O[(y, q)]
        c0 = cell(D.V(y, q), o); W0[(y, q)] = c0["rho"]
        rows.append(dict(year=y, q=q, window="W0", **c0))
        py, pq_ = prev(y, q); ny, nq = nxt(y, q)
        rows.append(dict(year=y, q=q, window="Wprev", **cell(D.V(py, pq_), o)))
        if (ny, nq) <= (2024, 4):
            rows.append(dict(year=y, q=q, window="Wnext", **cell(D.V(ny, nq), o)))
    rows.append(dict(year=y, q=0, window="WyearMed", **cell(D.Vyear(y), D.Oyear(y))))
    rows.append(dict(year=y, q=2, window="WaprDec", **cell(D.vaprdec[y], D.O[(y, 2)])))
x2a = save("x2a_level_grid", rows)
rng_by_year = []
for y in yrs:
    v = [W0[(y, q)] for q in (1, 2, 3, 4)]; rng_by_year.append(max(v) - min(v))
med_range = float(np.median(rng_by_year)); lab["R2.1"] = ("sensitive" if med_range >= 0.20 else "stable", med_range, rng_by_year)
cnt = tot = 0
for y in yrs:
    for q in (1, 2, 3, 4):
        r0 = W0[(y, q)]
        sub = x2a[(x2a.year == y) & (x2a.q == q)]
        hit = False
        for w in ("Wprev", "Wnext"):
            s = sub[sub.window == w]
            if len(s) and abs(float(s.rho.iloc[0]) - r0) >= 0.10:
                hit = True
        cnt += hit; tot += 1
lab["R2.2"] = ("timing-sensitive" if cnt / tot >= 0.5 else "not timing-sensitive", cnt / tot, (cnt, tot))
# change cells
rows = []
for y0 in (2021, 2022, 2023):
    for q in (1, 2, 3, 4):
        dv = np.log(D.V(2024, q)) - np.log(D.V(y0, q)); do = np.log(D.O[(2024, q)]) - np.log(D.O[(y0, q)])
        rows.append(dict(start=y0, q=q, kind="W0 log change", **cell(dv, do)))
    dv = np.log(D.Vyear(2024)) - np.log(D.Vyear(y0)); do = np.log(D.Oyear(2024)) - np.log(D.Oyear(y0))
    rows.append(dict(start=y0, q=0, kind="year-level log change", **cell(dv, do)))
tq = [(y, q) for y in yrs for q in (1, 2, 3, 4)]
def slopes(get):
    out_ = np.full(D.n, np.nan)
    for j in range(D.n):
        yv = np.array([np.log(get(y, q)[j]) for (y, q) in tq]); t = np.arange(16); m = np.isfinite(yv)
        if m.sum() >= 12:
            out_[j] = np.polyfit(t[m], yv[m], 1)[0]
    return out_
sV, sO = slopes(D.V), slopes(lambda y, q: D.O[(y, q)])
rows.append(dict(start=2021, q=-1, kind="slope 2021Q1-2024Q4", **cell(sV, sO)))
x2b = save("x2b_change_grid", rows)
cc = x2b[x2b.kind == "W0 log change"]
neg = int((cc.rho < 0).sum()); medc = float(cc.rho.median())
lab["R2.3"] = ("robustly negative" if neg >= 10 and medc <= -0.10 else ("robustly positive" if neg <= 2 else "sign unstable"), neg, medc)
sl = x2b[x2b.kind.str.startswith("slope")].iloc[0]
lab["R2.4"] = ("negative and distinguishable" if (sl.hi < 0 and sl.p < 0.05) else ("positive and distinguishable" if (sl.lo > 0 and sl.p < 0.05) else "not distinguishable from 0"), float(sl.rho), (float(sl.lo), float(sl.hi), float(sl.p)))

# ---------------------------------------------------------------- X4
tt = [(y, q) for y in yrs for q in (1, 2, 3, 4)]
def mat(get):
    A = np.vstack([get(y, q) for (y, q) in tt]); assert np.isfinite(A).all(), "missing quarter values"; return A
AV, AO = mat(D.V), mat(lambda y, q: D.O[(y, q)])
def adj_rep(A, idx_=None, years_idx=None):
    idx_ = make_idx(D.n) if idx_ is None else idx_
    zs = []
    for t in range(15):
        if years_idx is not None and not ((t // 4) == years_idx or ((t + 1) // 4) == years_idx):
            continue
        r = sp_boot(A[t], A[t + 1], idx_) if idx_ is not None else None
        zs.append(np.arctanh(np.clip(r, -0.999, 0.999)))
    return np.tanh(np.mean(zs, axis=0))
def adj_rep_obs(A, years_idx=None):
    zs = []
    for t in range(15):
        if years_idx is not None and not ((t // 4) == years_idx or ((t + 1) // 4) == years_idx):
            continue
        zs.append(np.arctanh(np.clip(sp(A[t], A[t + 1]), -0.999, 0.999)))
    return float(np.tanh(np.mean(zs)))
rows = []
rV_b, rO_b = adj_rep(AV), adj_rep(AO)
rows.append(dict(scope="all adjacent pairs", source="VNNIC", r=adj_rep_obs(AV), lo=ci(rV_b)[0], hi=ci(rV_b)[1]))
rows.append(dict(scope="all adjacent pairs", source="Ookla", r=adj_rep_obs(AO), lo=ci(rO_b)[0], hi=ci(rO_b)[1]))
x4a = save("x4a_repeatability", rows)
rows = []
for yi, y in enumerate(yrs):
    rV, rO = adj_rep_obs(AV, yi), adj_rep_obs(AO, yi); rVb, rOb = adj_rep(AV, years_idx=yi), adj_rep(AO, years_idx=yi)
    mx = np.sqrt(max(rV, 0) * max(rO, 0)); mxb = np.sqrt(np.clip(rVb, 0, None) * np.clip(rOb, 0, None))
    xo = D.vq2[y]; zo = D.fq2[OM][y]; ro = sp(xo, zo); rob = sp_boot(xo, zo)
    olo, ohi = ci(rob); mlo, mhi = ci(mxb); mmed = float(np.median(mxb))
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = ro / mx if mx > 0 else np.nan; rb = rob / mxb; rlo, rhi = ci(rb)
    label = "NOISE-LIMITED" if (mmed < 0.30 or mhi < 0.40) else ("BELOW CEILING" if ohi < mlo else "INCONCLUSIVE")
    rows.append(dict(level="L3", year=y, rho_obs=ro, obs_lo=olo, obs_hi=ohi, rV=rV, rO=rO, ceiling=mx, ceil_lo=mlo, ceil_hi=mhi, ratio=ratio, ratio_lo=rlo, ratio_hi=rhi, label=label))
# L4 split half
def halfchg(get_v, y0, y1, qs):
    return np.mean([np.log(get_v(y1, q)) for q in qs], axis=0) - np.mean([np.log(get_v(y0, q)) for q in qs], axis=0)
def rel_half(get):
    a = halfchg(get, 2021, 2024, (1, 3)); b = halfchg(get, 2021, 2024, (2, 4)); return a, b
aV, bV = rel_half(D.V); aO, bO = rel_half(lambda y, q: D.O[(y, q)])
def corrected(a, b, idx_=None):
    if idx_ is None:
        r = sp(a, b)
    else:
        r = sp_boot(a, b, idx_)
    return 2 * r / (1 + r)
relV, relO = corrected(aV, bV), corrected(aO, bO); relVb, relOb = corrected(aV, bV, idx), corrected(aO, bO, idx)
mx4 = float(np.sqrt(max(relV, 0) * max(relO, 0))); mx4b = np.sqrt(np.clip(relVb, 0, None) * np.clip(relOb, 0, None))
dv = np.log(D.vq2[2024]) - np.log(D.vq2[2021]); do = np.log(D.fq2[OM][2024]) - np.log(D.fq2[OM][2021])
ro4 = sp(dv, do); ro4b = sp_boot(dv, do); olo, ohi = ci(ro4b); mlo, mhi = ci(mx4b); mmed = float(np.median(mx4b))
label4 = "NOISE-LIMITED" if (mmed < 0.30 or mhi < 0.40) else ("BELOW CEILING" if ohi < mlo else "INCONCLUSIVE")
rows.append(dict(level="L4", year="2021-2024", rho_obs=ro4, obs_lo=olo, obs_hi=ohi, rV=relV, rO=relO, ceiling=mx4, ceil_lo=mlo, ceil_hi=mhi, ratio=(ro4 / mx4 if mx4 > 0 else np.nan), ratio_lo=np.nan, ratio_hi=np.nan, label=label4))
x4b = save("x4b_ceilings", rows)
lab["R4.L4"] = (label4, mx4, (mlo, mhi), dict(relV=relV, relO=relO, ro4=ro4))

# ---------------------------------------------------------------- X5
v21, v24 = D.vq2[2021], D.vq2[2024]; v22 = D.vq2[2022]
o21, o22, o24 = D.fq2[OM][2021], D.fq2[OM][2022], D.fq2[OM][2024]
t21, t22, t24 = D.fq2["total_tests"][2021], D.fq2["total_tests"][2022], D.fq2["total_tests"][2024]
d21, d24 = D.fq2["total_devices"][2021], D.fq2["total_devices"][2024]
n21, n24 = D.fq2["observed_ookla_tiles"][2021], D.fq2["observed_ookla_tiles"][2024]
L = np.log
rows = []
def addv(name, x, y, note=""):
    rows.append(dict(variant=name, note=note, **cell(x, y)))
addv("V0 baseline Q2 2021->2024", L(v24) - L(v21), L(o24) - L(o21))
addv("V1 start 2022Q2", L(v24) - L(v22), L(o24) - L(o22))
vm = lambda y: np.mean([L(D.V(y, q)) for q in (1, 2, 3, 4)], axis=0); om = lambda y: np.mean([L(D.O[(y, q)]) for q in (1, 2, 3, 4)], axis=0)
addv("V2 year-mean 2022->2024", vm(2024) - vm(2022), om(2024) - om(2022))
# V3 residualized
def v3(idx_=None):
    a = L(v24) - L(v21); b = L(o24) - L(o21); x1 = L(t24) - L(t21); x2 = L(d24) - L(d21)
    if idx_ is not None:
        a, b, x1, x2 = a[idx_], b[idx_], x1[idx_], x2[idx_]
    rb_, r1, r2 = rk(b), rk(x1), rk(x2); X = np.column_stack([np.ones(len(rb_)), r1, r2]); beta = np.linalg.lstsq(X, rb_, rcond=None)[0]
    res = rb_ - X @ beta
    return sp(a, res)
v3o = v3(); v3b = np.array([v3(idx[i]) for i in range(B)]); lo, hi = ci(v3b)
rows.append(dict(variant="V3 Ookla change residualized on rank(d log tests), rank(d log devices)", note="CI by province bootstrap; no permutation", N=D.n, rho=v3o, lo=lo, hi=hi, p=np.nan))
m4 = (D.fq2["total_tests"][2021] >= 500) & (t24 >= 500)
addv("V4 tests>=500 at both endpoints", (L(v24) - L(v21))[m4], (L(o24) - L(o21))[m4])
medt = float(np.median(t21)); m5 = (t21 >= medt) & (t24 >= medt)
addv(f"V5 tests>=2021 median ({medt:.0f}) at both endpoints", (L(v24) - L(v21))[m5], (L(o24) - L(o21))[m5])
ratio_t = n24 / n21; m6 = (ratio_t >= 0.67) & (ratio_t <= 1.5)
addv("V6 stable-tile provinces (tiles 2024/2021 in [0.67,1.5])", (L(v24) - L(v21))[m6], (L(o24) - L(o21))[m6])
tw21, tw24 = D.fq2["ookla_tests_weighted_mean_download_mbps"][2021], D.fq2["ookla_tests_weighted_mean_download_mbps"][2024]
addv("V7 tests-weighted mean aggregator", L(v24) - L(v21), L(tw24) - L(tw21))
x5 = save("x5_variants", rows)
core = ["V1", "V2", "V3", "V4", "V5"]
est = {r.variant.split()[0]: r.rho for r in x5.itertuples()}
surv = all(est[k] < 0 for k in core) and float(np.median([est[k] for k in core])) <= -0.10
attrib = est["V1"] >= -0.05 and est["V3"] >= -0.05
lab["R5"] = ("survives" if surv else ("attributable to coverage/composition" if attrib else "mixed"), {k: est[k] for k in est}, float(np.median([est[k] for k in core])))
print("tile-count info: tiles 2021Q2 total", float(n21.sum()), "2024Q2", float(n24.sum()), "| tests", float(t21.sum()), float(t24.sum()))

# ---------------------------------------------------------------- X7
rows = []
def med_ratio(a, b):
    with np.errstate(invalid="ignore", divide="ignore"):
        return float(np.nanmedian(a / b))
V25q2 = D.V(2025, 2); V24q4 = D.V(2024, 4)
ratio_V = med_ratio(V25q2, V24q4); ratio_O = med_ratio(D.O[(2025, 2)], D.O[(2024, 4)])
g72 = "break not mirrored by Ookla" if (ratio_V >= 1.5 and ratio_O < 1.25) else ("shared increase" if (ratio_V >= 1.25 and ratio_O >= 1.25) else "inconclusive")
lab["G7.2"] = (g72, ratio_V, ratio_O)
rows.append(dict(item="ratio VNNIC Apr-Jun 2025 / Oct-Dec 2024 (median over provinces)", value=ratio_V))
rows.append(dict(item="ratio Ookla 2025Q2 / 2024Q4 (tile median, median over provinces)", value=ratio_O))
rows.append(dict(item="G7.2 flag", value=g72))
# VNNIC and Ookla national median by quarter 2024Q1-2025Q2 (descriptive)
for (y, q) in [(2024, 1), (2024, 2), (2024, 3), (2024, 4), (2025, 1), (2025, 2)]:
    rows.append(dict(item=f"national median VNNIC {y}Q{q}", value=float(np.nanmedian(D.V(y, q)))))
    rows.append(dict(item=f"national median Ookla {y}Q{q}", value=float(np.nanmedian(D.O[(y, q)]))))
x7a = save("x7a_gate", rows)
rows = []
for (y, q) in [(2020, 2), (2025, 2)]:
    rows.append(dict(item=f"Spearman {y}Q{q} (W0)", **cell(D.V(y, q), D.O[(y, q)])))
for y0 in (2021, 2022):
    dv_ = np.log(D.V(2025, 2)) - np.log(D.V(y0, 2)); do_ = np.log(D.O[(2025, 2)]) - np.log(D.O[(y0, 2)])
    rows.append(dict(item=f"L4 log change {y0}Q2->2025Q2", **cell(dv_, do_)))
dv_ = np.log(D.V(2024, 2)) - np.log(D.V(2020, 2)); do_ = np.log(D.O[(2024, 2)]) - np.log(D.O[(2020, 2)])
rows.append(dict(item="L4 log change 2020Q2->2024Q2", **cell(dv_, do_)))
x7b = save("x7b_extension", rows)
s25 = x7b.iloc[1]; s21 = x2a[(x2a.year == 2021) & (x2a.q == 2) & (x2a.window == "W0")].iloc[0]; s24 = x2a[(x2a.year == 2024) & (x2a.q == 2) & (x2a.window == "W0")].iloc[0]
dd = sp_boot(D.V(2021, 2), D.O[(2021, 2)]) - sp_boot(D.V(2025, 2), D.O[(2025, 2)]); dlo, dhi = ci(dd)
lvl = (dlo > 0) or (abs(float(s25.rho) - float(s24.rho)) <= 0.10)
sgn = all(np.sign(x7b.iloc[i].rho) == np.sign(est["V0"]) for i in (2, 3))
lab["R7.1"] = ("pattern persists" if (lvl and sgn) else "pattern does not clearly persist", dict(rho2025=float(s25.rho), diff_2021_2025_ci=(dlo, dhi), sign_ok=bool(sgn)), g72)
rows = []
qs = [(y, q) for y in (2019, 2020, 2021, 2022, 2023, 2024, 2025) for q in (1, 2, 3, 4)] + [(2026, 1)]
for (y, q) in qs:
    o = D.O[(y, q)]; t = D.OT[(y, q)]; tl = D.OTL[(y, q)]
    rows.append(dict(year=y, q=q, n_prov=int(np.isfinite(o).sum()), tiles_total=float(np.nansum(tl)), tests_total=float(np.nansum(t)), median_mbps=float(np.nanmedian(o)), cv=float(np.nanstd(o, ddof=1) / np.nanmean(o)), p90_p10=float(np.nanpercentile(o, 90) / np.nanpercentile(o, 10))))
x7c = save("x7c_ookla_only", rows)
def cv_ratio(a_key, b_key):
    A, Bq = D.O[a_key], D.O[b_key]
    ok = np.isfinite(A) & np.isfinite(Bq); A, Bq = A[ok], Bq[ok]
    f = lambda a: a.std(-1, ddof=1) / a.mean(-1)
    lr = np.log(f(A) / f(Bq)); b_ = np.log(f(A[make_idx(len(A))]) / f(Bq[make_idx(len(A))])); return float(lr), ci(b_)
for key in [(2025, 2), (2026, 1)]:
    lr, (lo, hi) = cv_ratio(key, (2021, 2)); lab[f"R7.2 {key}"] = ("widens" if (lr > 0 and lo > 0) else ("compresses" if (lr < 0 and hi < 0) else "not distinguishable"), lr, (lo, hi))

# ---------------------------------------------------------------- report
def fmt(v): return v
rep = []
rep.append("# Paper A upgrade report (X1, X2, X4, X5, X7)\n")
rep.append("Generated by run_upgrade.py from upgrade_specification.md (hash chain in spec_hash.txt). All numbers are read from results/*.csv. Labels are mechanical. Diagnostics, not confirmatory tests.\n")
rep.append("Gates G1-G3: see results/gates.csv (all pass after deviation D1).\n")
rep.append("## X1 uncertainty\n"); rep.append(md(x1a)); rep.append("\n"); rep.append(md(x1b)); rep.append("\n"); rep.append(md(x1c)); rep.append("\nL2 dispersion (log ratio 2024/2021, CI by province bootstrap):\n"); rep.append(md(x1d)); rep.append("\n"); rep.append(md(x1d_sum)); rep.append("\nL1 direction:\n"); rep.append(md(x1e))
rep.append("\n## X2 temporal matching\n"); rep.append(md(x2a)); rep.append("\n"); rep.append(md(x2b))
rep.append(f"\nR2.1 {lab['R2.1']}\n\nR2.2 {lab['R2.2']}\n\nR2.3 {lab['R2.3']}\n\nR2.4 {lab['R2.4']}\n")
rep.append("\n## X4 noise ceilings\n"); rep.append(md(x4a)); rep.append("\n"); rep.append(md(x4b)); rep.append(f"\nL4 label: {lab['R4.L4']}\n")
rep.append("\n## X5 robustness of L4\n"); rep.append(md(x5)); rep.append(f"\nR5 label: {lab['R5']}\n")
rep.append("\n## X7 extension\n"); rep.append(md(x7a)); rep.append("\n"); rep.append(md(x7b)); rep.append("\n"); rep.append(md(x7c)); rep.append(f"\nG7.2: {lab['G7.2']}\n\nR7.1: {lab['R7.1']}\n")
for k in lab:
    if k.startswith("R7.2"):
        rep.append(f"\n{k}: {lab[k]}\n")
(HERE / "upgrade_report.md").write_text("\n".join(rep), encoding="utf-8")
json.dump({k: str(v) for k, v in lab.items()}, open(R / "labels.json", "w"), indent=1)
print("DONE")
for k, v in lab.items():
    print(k, v)
