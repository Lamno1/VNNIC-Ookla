"""X10 per x10_exclusion_specification.md incl. deviation D1 (hash chain x10_spec_hash.txt). Labels applied mechanically."""
import json
import upg_common as U
from upg_common import *
U.SEED, U.PSEED = 20261016, 20261017
U._IDX.clear()

D = Data(with_ext=True)
R = HERE / "results_x10"; R.mkdir(exist_ok=True)
X9 = pd.read_parquet(HERE / "data" / "ookla_x9_province_quarter.parquet"); inv = {v: k for k, v in D.iso.items()}; X9["pid"] = X9.shapeISO.map(inv)
fact = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet"); fact["month"] = pd.to_datetime(fact["month"])
def vpiv(net, col): return fact[fact.network == net].pivot_table(index="month", columns="province_id_legacy63", values=col, aggfunc="first").reindex(columns=D.pids)
FAM = {"F1": ("fixed download", vpiv("ftth", "download"), "dl_fixed"), "F2": ("fixed upload", vpiv("ftth", "upload"), ("fixed", "ul_median")), "F4": ("mobile download", vpiv("mobile", "download"), ("mobile", "dl_median"))}
TQ = [(y, q) for y in range(2021, 2025) for q in (1, 2, 3, 4)]
def qmonths(y, q): return [pd.Timestamp(y, 3 * (q - 1) + k, 1) for k in (1, 2, 3)]
def Oarr(fid, y, q):
    if fid == "F1":
        return D.O[(y, q)]
    kind, col = FAM[fid][2]
    g = X9[(X9.kind == kind) & (X9.year == y) & (X9.quarter == q)].set_index("pid")
    a = np.array([g[col].get(p, np.nan) for p in D.pids], float); t = np.array([g.observed_tiles.get(p, np.nan) for p in D.pids], float)
    return np.where(t >= 10, a, np.nan)
OA = {(fid, t): Oarr(fid, *t) for fid in FAM for t in TQ + [(2020, 4)]}
def Oyear(fid, y):
    arr = np.vstack([OA[(fid, (y, q))] for q in (1, 2, 3, 4)]); ok = np.isfinite(arr).sum(0) >= 3
    return np.where(ok, np.nanmedian(arr, axis=0), np.nan)

def Vq_base(vm, y, q):
    sub = vm.reindex(qmonths(y, q)); ok = sub.notna().sum() >= 2
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Vq_var(vm, excl, y, q):
    ms = qmonths(y, q); rem = [m for m in ms if m not in excl]
    if len(rem) == 3:
        return Vq_base(vm, y, q)
    if not rem:
        return np.full(D.n, np.nan)
    sub = vm.reindex(rem); ok = sub.notna().sum() >= 1
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Vyear_var(vm, excl, y, minm):
    ms = [pd.Timestamp(y, k, 1) for k in range(1, 13) if pd.Timestamp(y, k, 1) not in excl]
    sub = vm.reindex(ms); ok = sub.notna().sum() >= minm
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def vecs(fid, excl):
    vm = FAM[fid][1]; minm = 7 if excl else 9
    return {t: Vq_var(vm, excl, *t) for t in TQ}, {y: Vyear_var(vm, excl, y, minm) for y in range(2021, 2025)}

idx = make_idx(D.n)
def fast_rho(x, y):
    xs, ys = x[idx], y[idx]; out = np.full(B, np.nan)
    if np.isfinite(x).all() and np.isfinite(y).all():
        return corr_rows(rk(xs), rk(ys))
    for i in range(B):
        m = np.isfinite(xs[i]) & np.isfinite(ys[i])
        if m.sum() >= 10:
            a = stats.rankdata(xs[i][m]); b = stats.rankdata(ys[i][m]); a = a - a.mean(); b = b - b.mean(); den = np.sqrt((a * a).sum() * (b * b).sum())
            out[i] = (a * b).sum() / den if den > 0 else np.nan
    return out
def cell(x, y):
    m = np.isfinite(x) & np.isfinite(y); n = int(m.sum())
    return dict(N=n, rho=sp(x[m], y[m]) if n >= 10 else np.nan)

VARS = {"B": set(), "E1": {pd.Timestamp(2024, m, 1) for m in (3, 4, 5)}, "E2": {pd.Timestamp(2024, m, 1) for m in (4, 5)},
        "E3": {pd.Timestamp(2024, m, 1) for m in (3, 4, 5, 6)}, "E4": {pd.Timestamp(2024, m, 1) for m in (2, 3, 4, 5, 6)}}
def save(name, rows):
    df = pd.DataFrame(rows); df.to_csv(R / f"{name}.csv", index=False); return df

# ------------------------------------------------ gates
g = []; x2a = pd.read_csv(HERE / "results" / "x2a_level_grid.csv"); x9c = pd.read_csv(HERE / "results_x9" / "x9_level_cells.csv")
BV = {}
for fid in FAM:
    BV[fid] = vecs(fid, set())
    for t in TQ:
        r = cell(BV[fid][0][t], OA[(fid, t)])["rho"]
        ref = float(x2a[(x2a.year == t[0]) & (x2a.q == t[1]) & (x2a.window == "W0")].rho.iloc[0]) if fid == "F1" else float(x9c[(x9c.family == fid) & (x9c.year == t[0]) & (x9c.q == t[1])].rho.iloc[0])
        g.append(dict(gate="G10.1", item=f"{fid} {t[0]}Q{t[1]}", value=r, target=ref, passed=abs(r - ref) < 0.005))
for m in (3, 4, 5):
    n = int(FAM["F1"][1].reindex([pd.Timestamp(2024, m, 1)]).notna().sum(axis=1).iloc[0]); g.append(dict(gate="G10.2", item=f"F1 month 2024-{m:02d} present", value=n, target=60, passed=n >= 60))
EV = {fid: vecs(fid, VARS["E1"]) for fid in FAM}
for fid in FAM:
    for t in [(2024, 1), (2024, 2)]:
        n = int(np.isfinite(EV[fid][0][t]).sum()); g.append(dict(gate="G10.2", item=f"{fid} E1 {t[0]}Q{t[1]} exists", value=n, target=60, passed=n >= 60))
    same = all(np.allclose(EV[fid][0][t], BV[fid][0][t], equal_nan=True) for t in TQ if t not in [(2024, 1), (2024, 2)])
    g.append(dict(gate="G10.3", item=f"{fid} other 14 quarters unchanged", value=int(same), target=1, passed=same))
gt = save("gates", g); print(gt[~gt.passed].to_string() if (~gt.passed).any() else "all gates pass");
if not gt.passed.all():
    print("GATE FAILURE: stop"); raise SystemExit(1)

# ------------------------------------------------ main computations
BOOT = {}
def boot_series(key, x, y):
    if key not in BOOT:
        BOOT[key] = fast_rho(x, y)
    return BOOT[key]
cellsrows, yrrows, deltarows, declrows, chgrows, summ = [], [], [], [], [], []
RES = {}
for fid in FAM:
    for vn, excl in VARS.items():
        Vs, Vy = (BV[fid] if vn == "B" else vecs(fid, excl))
        Bq = {t: boot_series((fid, vn, t), Vs[t], OA[(fid, t)]) for t in TQ}
        Bq_base = {t: boot_series((fid, "B", t), BV[fid][0][t], OA[(fid, t)]) for t in TQ}
        rhos = {}
        for t in TQ:
            c = cell(Vs[t], OA[(fid, t)]); lo, hi = ci(Bq[t]); rhos[t] = c; cellsrows.append(dict(family=fid, variant=vn, year=t[0], q=t[1], **c, lo=lo, hi=hi))
        for y in range(2021, 2025):
            c = cell(Vy[y], Oyear(fid, y)); rhos[("yr", y)] = c; lo, hi = ci(boot_series((fid, vn, "yr", y), Vy[y], Oyear(fid, y))); yrrows.append(dict(family=fid, variant=vn, year=y, **c, lo=lo, hi=hi))
        # Q2 delta
        dl = {}
        for t in [(2024, 1), (2024, 2)]:
            d = rhos[t]["rho"] - cell(BV[fid][0][t], OA[(fid, t)])["rho"]; lo, hi = ci(Bq[t] - Bq_base[t]); dl[t] = (d, lo, hi)
            deltarows.append(dict(family=fid, variant=vn, quarter=f"{t[0]}Q{t[1]}", rho_B=cell(BV[fid][0][t], OA[(fid, t)])["rho"], rho_E=rhos[t]["rho"], delta=d, lo=lo, hi=hi))
        # Q3 decline
        dec = rhos[(2021, 2)]["rho"] - rhos[(2024, 2)]["rho"]; dlo, dhi = ci(Bq[(2021, 2)] - Bq[(2024, 2)])
        decy = rhos[("yr", 2021)]["rho"] - rhos[("yr", 2024)]["rho"]
        declrows.append(dict(family=fid, variant=vn, decline_Q2=dec, lo=dlo, hi=dhi, decline_year=decy))
        # Q4 change cells
        ch = []
        for y0 in (2021, 2022, 2023):
            for q in (1, 2, 3, 4):
                dv = np.log(Vs[(2024, q)]) - np.log(Vs[(y0, q)]); do = np.log(OA[(fid, (2024, q))]) - np.log(OA[(fid, (y0, q))]); c = cell(dv, do); ch.append(c); chgrows.append(dict(family=fid, variant=vn, start=y0, q=q, **c))
        for y0 in (2021, 2022, 2023):
            dv = np.log(Vy[2024]) - np.log(Vy[y0]); do = np.log(Oyear(fid, 2024)) - np.log(Oyear(fid, y0)); c = cell(dv, do); chgrows.append(dict(family=fid, variant=vn, start=y0, q=0, **c))
        chd = pd.DataFrame(ch); v = chd[(chd.N >= 50) & chd.rho.notna()]; neg = int((v.rho < 0).sum()); med = float(v.rho.median())
        lab_b = "robustly negative" if (neg >= 10 and med <= -0.10) else ("robustly positive" if (neg <= 2 and len(v) >= 10) else "sign unstable")
        # Q5
        spread = []
        for y in range(2021, 2025):
            vv = [rhos[(y, q)]["rho"] for q in (1, 2, 3, 4) if rhos[(y, q)]["N"] >= 50 and np.isfinite(rhos[(y, q)]["rho"])]
            if len(vv) >= 2: spread.append(max(vv) - min(vv))
        q5 = float(np.median(spread))
        RES[(fid, vn)] = dict(rho_Q2=rhos[(2024, 2)]["rho"], rho_Q1=rhos[(2024, 1)]["rho"], dQ2=dl[(2024, 2)], dQ1=dl[(2024, 1)], decline=dec, decline_ci=(dlo, dhi), neg=neg, ncell=len(v), medchg=med, chg_label=lab_b, q5=q5, temporal="sensitive" if q5 >= 0.20 else "stable")
# Q6 single-month penalty
pen = {}
for fid in FAM:
    vm = FAM[fid][1]; qs12 = [t for t in TQ if t[0] <= 2023]; diffs = []; obs = []
    for t in qs12:
        last = vm.reindex([qmonths(*t)[2]]).iloc[0].to_numpy(float); r3 = BV[fid][0][t]
        obs.append(cell(r3, OA[(fid, t)])["rho"] - cell(last, OA[(fid, t)])["rho"]); diffs.append(fast_rho(r3, OA[(fid, t)]) - fast_rho(last, OA[(fid, t)]))
    bm = np.nanmean(np.vstack(diffs), axis=0); lo, hi = ci(bm); pen[fid] = (float(np.mean(obs)), lo, hi)
save("q6_penalty", [dict(family=f, penalty=v[0], lo=v[1], hi=v[2]) for f, v in pen.items()])
# Q7 placebo
plrows = []
starts = pd.date_range("2022-01-01", "2024-10-01", freq="MS"); target = pd.Timestamp(2024, 3, 1)
for fid in FAM:
    vm = FAM[fid][1]
    for s0 in starts:
        ex = {s0 + pd.DateOffset(months=k) for k in range(3)}
        touched = sorted({(m.year, (m.month - 1) // 3 + 1) for m in ex}); deltas = []
        for t in touched:
            rem = [m for m in qmonths(*t) if m not in ex]
            if not rem:
                continue
            e = Vq_var(vm, ex, *t); deltas.append(cell(e, OA[(fid, t)])["rho"] - cell(BV[fid][0][t], OA[(fid, t)])["rho"])
        overlap = bool(ex & {pd.Timestamp(2024, m, 1) for m in (3, 4, 5)}); aligned = len(deltas) < len(touched)
        plrows.append(dict(family=fid, start=s0.strftime("%Y-%m"), touched=len(touched), with_data=len(deltas), mean_delta=float(np.mean(deltas)) if deltas else np.nan, overlaps_target=overlap, dropped_empty_quarter=aligned,
                           is_target=(s0 == target), valid_placebo=(not overlap and not aligned and bool(deltas))))
pl = save("q7_placebo", plrows)
plab = {}
for fid in FAM:
    p = pl[pl.family == fid]; tg = p[p.is_target].mean_delta.iloc[0]; vp = p[p.valid_placebo].mean_delta; m = len(vp)
    plab[fid] = dict(target=float(tg), m=m, placebo_max=float(vp.max()), placebo_median=float(vp.median()), p95=float(vp.quantile(.95)), exceeds_all=bool(tg > vp.max()), p_one_sided=1 / (m + 1), label="unusual" if tg > vp.max() else "not distinguishable from windows chosen blindly")
save("q7_summary", [dict(family=f, **v) for f, v in plab.items()])

# ------------------------------------------------ rules
rows = []
for fid in FAM:
    for vn in VARS:
        r = RES[(fid, vn)]; d, lo, hi = r["dQ2"]
        r101 = "anomaly removed" if (r["rho_Q2"] >= 0.50 and (lo > 0 or hi < 0)) else ("largely unaffected" if d < 0.15 else "partly removed")
        rows.append(dict(family=fid, variant=vn, rho_Q2_2024=r["rho_Q2"], delta_Q2=d, delta_lo=lo, delta_hi=hi, R10_1=r101, rho_Q1_2024=r["rho_Q1"], delta_Q1=r["dQ1"][0],
                         decline_Q2_point=r["decline"], decline_lo=r["decline_ci"][0], decline_hi=r["decline_ci"][1], neg_cells=r["neg"], n_cells=r["ncell"], chg_median=r["medchg"], chg_label=r["chg_label"],
                         spread=r["q5"], temporal=r["temporal"], penalty=pen[fid][0], rho_Q2_penalty_adj=r["rho_Q2"] + pen[fid][0]))
S = save("x10_summary", rows)
def claims(fid, vn):
    b, e = RES[(fid, "B")], RES[(fid, vn)]
    a_b, a_e = b["decline"] >= 0.20, e["decline"] >= 0.20; dep_a = bool(a_b and not a_e)
    dep_b = b["chg_label"] != e["chg_label"]; dep_c = b["temporal"] != e["temporal"]
    n = int(dep_a) + int(dep_b) + int(dep_c)
    return dict(a_B=a_b, a_E=a_e, dep_a=dep_a, b_B=b["chg_label"], b_E=e["chg_label"], dep_b=dep_b, c_B=b["temporal"], c_E=e["temporal"], dep_c=dep_c, n_depend=n,
                R10_5="claims survive exclusion" if n == 0 else ("claims depend on the window" if n >= 2 else "partly depend"))
cl = save("x10_claims", [dict(family=fid, variant=vn, **claims(fid, vn)) for fid in FAM for vn in VARS if vn != "B"])
# R10.4 negative control
f4 = RES[("F4", "E1")]["dQ2"]; pm = plab["F4"]["placebo_median"]
r104 = "as expected" if ((f4[1] <= 0 <= f4[2]) or f4[0] < pm + 0.15) else "unexpected improvement"
lab = dict(headline=cl[(cl.family == "F1") & (cl.variant == "E1")].iloc[0].to_dict(), R10_3_F1=plab["F1"], R10_3_F2=plab["F2"], R10_3_F4=plab["F4"], R10_4=(r104, f4, pm))
json.dump({k: str(v) for k, v in lab.items()}, open(R / "labels.json", "w"), indent=1)
pd.concat([pd.DataFrame(cellsrows).assign(kind="W0")]).to_csv(R / "x10_w0_cells.csv", index=False)
pd.DataFrame(yrrows).to_csv(R / "x10_year_level.csv", index=False); pd.DataFrame(deltarows).to_csv(R / "x10_delta.csv", index=False)
pd.DataFrame(declrows).to_csv(R / "x10_decline.csv", index=False); pd.DataFrame(chgrows).to_csv(R / "x10_change_cells.csv", index=False)
rep = ["# X10 report: exclusion of VNNIC fixed months March-May 2024\n", "Generated by run_x10.py per x10_exclusion_specification.md incl. D1 (hash chain x10_spec_hash.txt). EXPLORATORY, window chosen after X8 (post hoc). Numbers come from results_x10/*.csv; labels are mechanical.\n",
       "## Summary per variant and family\n", md(S), "\n## Claims (R10.2, R10.5), E-variants vs baseline\n", md(cl), "\n## Placebo (Q7, R10.3)\n", md(pd.DataFrame([dict(family=f, **v) for f, v in plab.items()])), f"\n## R10.4 negative control: {lab['R10_4']}\n",
       "\n## Single-month penalty (Q6)\n", md(pd.DataFrame([dict(family=f, penalty=v[0], lo=v[1], hi=v[2]) for f, v in pen.items()])), "\n## Delta in affected quarters\n", md(pd.DataFrame(deltarows))]
(HERE / "x10_report.md").write_text("\n".join(rep), encoding="utf-8")
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
print(S.round(3).to_string()); print(cl.to_string()); print(pd.DataFrame([dict(family=f, **v) for f, v in plab.items()]).round(3).to_string()); print("R10.4", lab["R10_4"])
