"""X12 per x12_local_scan_specification.md incl. D1 (hash chain x12_spec_hash.txt). Deterministic; labels applied mechanically."""
import json, math
from upg_common import *

D = Data(with_ext=True)
R = HERE / "results_x12"; R.mkdir(exist_ok=True)
X9 = pd.read_parquet(HERE / "data" / "ookla_x9_province_quarter.parquet"); inv = {v: k for k, v in D.iso.items()}; X9["pid"] = X9.shapeISO.map(inv)
fact = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet"); fact["month"] = pd.to_datetime(fact["month"])
def vpiv(net, col): return fact[fact.network == net].pivot_table(index="month", columns="province_id_legacy63", values=col, aggfunc="first").reindex(columns=D.pids)
FAM = {"F1": vpiv("ftth", "download"), "F2": vpiv("ftth", "upload"), "F3": vpiv("ftth", "ping"), "F4": vpiv("mobile", "download")}
XOC = {"F2": ("fixed", "ul_median"), "F3": ("fixed", "lat_median"), "F4": ("mobile", "dl_median")}
OC = {}
def O(fid, y, q):
    if (fid, y, q) in OC: return OC[(fid, y, q)]
    if fid == "F1":
        a = D.O.get((y, q), np.full(D.n, np.nan))
    else:
        kind, col = XOC[fid]; g = X9[(X9.kind == kind) & (X9.year == y) & (X9.quarter == q)].set_index("pid")
        if not len(g): a = np.full(D.n, np.nan)
        else:
            a = np.array([g[col].get(p, np.nan) for p in D.pids], float); t = np.array([g.observed_tiles.get(p, np.nan) for p in D.pids], float); a = np.where(t >= 10, a, np.nan)
    OC[(fid, y, q)] = a; return a
def qmonths(y, q): return [pd.Timestamp(y, 3 * (q - 1) + k, 1) for k in (1, 2, 3)]
def prev(y, q): return (y, q - 1) if q > 1 else (y - 1, 4)
def nxt(y, q): return (y, q + 1) if q < 4 else (y + 1, 1)
def Vbase(fid, y, q):
    sub = FAM[fid].reindex(qmonths(y, q)); ok = sub.notna().sum() >= 2
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def save(name, rows):
    df = pd.DataFrame(rows); df.to_csv(R / f"{name}.csv", index=False); return df
def rho_cc(a, b, nmin=30):
    m = np.isfinite(a) & np.isfinite(b)
    return (sp(a[m], b[m]), int(m.sum())) if m.sum() >= nmin else (np.nan, int(m.sum()))
MS = list(pd.date_range("2021-01-01", "2024-12-01", freq="MS"))
def scores(fid):
    s = []
    for m in MS:
        v = FAM[fid].loc[m].to_numpy(float) if m in FAM[fid].index else np.full(D.n, np.nan)
        if np.isfinite(v).sum() < 55: s.append(np.nan); continue
        q = (m.month - 1) // 3 + 1; tq = (m.year, q); rs = [rho_cc(v, O(fid, *t))[0] for t in (prev(*tq), tq, nxt(*tq))]; rs = [r for r in rs if np.isfinite(r)]
        s.append(float(np.mean(rs)) if len(rs) >= 2 else np.nan)
    return np.array(s)
SC = {fid: scores(fid) for fid in FAM}
def mad_z(x, ref, minav):
    ref = ref[np.isfinite(ref)]
    if len(ref) < minav: return np.nan
    med = np.median(ref); mad = 1.4826 * np.median(np.abs(ref - med)); return (x - med) / mad if mad > 0 else np.nan
def local_z(sv, w, minav=None):
    minav = minav if minav is not None else math.ceil(0.6 * 2 * w)
    out = np.full(len(sv), np.nan)
    for i in range(len(sv)):
        if np.isfinite(sv[i]):
            out[i] = mad_z(sv[i], np.array([sv[j] for j in range(max(0, i - w), min(len(sv), i + w + 1)) if j != i]), minav)
    return out
def global_z(sv):
    ref = sv[np.isfinite(sv)]; med = np.median(ref); mad = 1.4826 * np.median(np.abs(ref - med)); return (sv - med) / mad

# ------------------------------------------------ gates
old = pd.read_csv(HERE / "results_x11" / "s1_month_scan.csv"); g = []
for fid in FAM:
    o = old[old.family == fid].score.to_numpy(float); n = SC[fid]; both = np.isfinite(o) & np.isfinite(n)
    g.append(dict(gate="G12.1", item=f"{fid} scores match X11 (max abs diff over {int(both.sum())} months; nan pattern equal {bool((np.isfinite(o) == np.isfinite(n)).all())})", value=float(np.abs(o[both] - n[both]).max()), target=0.001, passed=bool(np.abs(o[both] - n[both]).max() < 0.001 and (np.isfinite(o) == np.isfinite(n)).all())))
lz6 = {fid: local_z(SC[fid], 6, 8) for fid in FAM}
for m, tgt in ((3, -2.87), (4, -5.66), (5, -8.55)):
    i = MS.index(pd.Timestamp(2024, m, 1)); g.append(dict(gate="G12.2", item=f"F1 local z 2024-{m:02d}", value=float(lz6["F1"][i]), target=tgt, passed=abs(lz6["F1"][i] - tgt) < 0.01))
gt = save("gates", g); print(gt.to_string())
if not gt.passed.all():
    print("GATE FAILURE: stop"); raise SystemExit(1)

# ------------------------------------------------ S1 primary scan
rows = []; FLAG = {}; notev = {}
for fid in FAM:
    gz = global_z(SC[fid]); lz = lz6[fid]; fl = np.isfinite(lz) & (lz <= -3.5); wt = np.isfinite(lz) & (lz > -3.5) & (lz <= -2.5)
    FLAG[fid] = {MS[i] for i in range(len(MS)) if fl[i]}
    notev[fid] = [MS[i].strftime("%Y-%m") for i in range(len(MS)) if np.isfinite(SC[fid][i]) and not np.isfinite(lz[i])]
    for i, m in enumerate(MS):
        rows.append(dict(family=fid, month=m.strftime("%Y-%m"), score=SC[fid][i], z_global=gz[i], z_local=lz[i], flagged=bool(fl[i]), watch=bool(wt[i]), locally_evaluable=bool(np.isfinite(lz[i])) or not np.isfinite(SC[fid][i])))
scan = save("s1_local_scan", rows)
save("s1_not_evaluable", [dict(family=f, n=len(v), months=", ".join(v)) for f, v in notev.items()])
low5 = save("s1_lowest5", [dict(family=f, rank=r + 1, month=row.month, score=row.score, z_local=row.z_local, flagged=row.flagged) for f in FAM for r, row in enumerate(scan[(scan.family == f) & scan.z_local.notna()].sort_values("z_local").head(5).itertuples())])
# sensitivity
sens = []
for w in (4, 6, 8):
    for thr in (-3.5, -3.0, -2.5):
        for fid in FAM:
            lz = local_z(SC[fid], w); s_ = {MS[i] for i in range(len(MS)) if np.isfinite(lz[i]) and lz[i] <= thr}
            j = len(s_ & FLAG[fid]) / len(s_ | FLAG[fid]) if (s_ | FLAG[fid]) else 1.0
            sens.append(dict(window=w, threshold=thr, family=fid, n_flagged=len(s_), months=", ".join(sorted(m.strftime("%Y-%m") for m in s_)), jaccard_with_primary=j))
sens = save("s1_sensitivity", sens)

# ------------------------------------------------ controls
f1 = {m.strftime("%Y-%m") for m in FLAG["F1"]}
r122 = "recovers the known window" if {"2024-04", "2024-05"} <= f1 else "does not recover the known window"
n34 = len(FLAG["F3"]) + len(FLAG["F4"]); r123 = "calibrated enough" if n34 <= 2 else "too liberal for these families"
oside = pd.read_csv(HERE / "results_x11" / "s3_ookla_side.csv"); conf_q = {(int(r.quarter[:4]), int(r.quarter[-1])) for r in oside.itertuples() if r.ookla_side}
def confounded(m): return (m.year, (m.month - 1) // 3 + 1) in conf_q
other = [dict(family=f, month=m.strftime("%Y-%m"), z_local=float(lz6[f][MS.index(m)]), ookla_confounded=confounded(m)) for f in FAM for m in sorted(FLAG[f]) if not (pd.Timestamp(2024, 3, 1) <= m <= pd.Timestamp(2024, 5, 1))]
oth = save("s3_flags_outside_mar_may_2024", other or [dict(family="(none)", month="", z_local=np.nan, ookla_confounded=False)])
def r124(T):
    k = sum(1 for m in qmonths(*T) if m in FLAG["F1"]); return "no flagged month" if k == 0 else ("localised" if k < 3 else "quarter-wide"), k
r124s = {f"{T[0]}Q{T[1]}": r124(T) for T in [(2021, 3), (2023, 3), (2024, 2)]}
def jac(a, b): return len(a & b) / len(a | b) if (a | b) else 0.0
j2, j3, j4 = jac(FLAG["F1"], FLAG["F2"]), jac(FLAG["F1"], FLAG["F3"]), jac(FLAG["F1"], FLAG["F4"])
if not FLAG["F1"]: r125 = "not evaluable"
elif FLAG["F2"] and j2 >= 0.5 and j4 < 0.5: r125 = "shared fixed-throughput regime"
elif j2 < 0.5: r125 = "download-specific"
else: r125 = "mixed"
f4_trivial = len(FLAG["F4"]) == 0
cross = save("s4_cross_family", [dict(family=f, n_flagged=len(FLAG[f]), months=", ".join(sorted(m.strftime("%Y-%m") for m in FLAG[f])), jaccard_with_F1=jac(FLAG["F1"], FLAG[f])) for f in FAM])

# ------------------------------------------------ S5 exclusion
Sset = {m for m in FLAG["F1"] if not confounded(m)}
vm1 = FAM["F1"]; TQ16 = [(y, q) for y in range(2021, 2025) for q in (1, 2, 3, 4)]
def Vvar(excl, y, q):
    ms = qmonths(y, q); rem = [m for m in ms if m not in excl]
    if len(rem) == 3: return Vbase("F1", y, q)
    if not rem: return np.full(D.n, np.nan)
    sub = vm1.reindex(rem); ok = sub.notna().sum() >= 1
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def cell(x, y):
    m = np.isfinite(x) & np.isfinite(y); n = int(m.sum()); return dict(N=n, rho=sp(x[m], y[m]) if n >= 10 else np.nan)
def evaluate(excl):
    Vs = {t: Vvar(excl, *t) for t in TQ16}; rh = {t: cell(Vs[t], O("F1", *t)) for t in TQ16}
    empty = [t for t in TQ16 if not np.isfinite(Vs[t]).any()]
    dec = rh[(2021, 2)]["rho"] - rh[(2024, 2)]["rho"] if (np.isfinite(rh[(2021, 2)]["rho"]) and np.isfinite(rh[(2024, 2)]["rho"])) else np.nan
    ch = [cell(np.log(Vs[(2024, q)]) - np.log(Vs[(y0, q)]), np.log(O("F1", 2024, q)) - np.log(O("F1", y0, q))) for y0 in (2021, 2022, 2023) for q in (1, 2, 3, 4)]
    chd = pd.DataFrame(ch); v = chd[(chd.N >= 50) & chd.rho.notna()]; neg = int((v.rho < 0).sum()); med = float(v.rho.median()) if len(v) else np.nan
    lab = "robustly negative" if (neg >= 10 and med <= -0.10) else ("robustly positive" if (neg <= 2 and len(v) >= 10) else "sign unstable")
    sp_ = []
    for y in range(2021, 2025):
        vv = [rh[(y, q)]["rho"] for q in (1, 2, 3, 4) if rh[(y, q)]["N"] >= 50 and np.isfinite(rh[(y, q)]["rho"])]
        if len(vv) >= 2: sp_.append(max(vv) - min(vv))
    spread = float(np.median(sp_)) if sp_ else np.nan
    return dict(W0=rh, empty=len(empty), decline=dec, neg=neg, ncell=len(v), medchg=med, change_label=lab, spread=spread, temporal=("sensitive" if spread >= 0.20 else "stable"))
EVS = {"B": evaluate(set()), "E1": evaluate({pd.Timestamp(2024, m, 1) for m in (3, 4, 5)}), "E2": evaluate({pd.Timestamp(2024, m, 1) for m in (4, 5)}), "E-scan2": evaluate(Sset)}
def status(e): return dict(a=bool(e["decline"] >= 0.20) if np.isfinite(e["decline"]) else None, b=e["change_label"], c=e["temporal"])
stB, stS = status(EVS["B"]), status(EVS["E-scan2"]); nd = sum(stB[k] != stS[k] for k in "abc")
if not Sset: r126 = "vacuous (empty set; E-scan2 = B)"
else: r126 = "claims survive exclusion" if nd == 0 else ("claims depend on the exclusion" if nd >= 2 else "partly depend")
equals_E2 = {m.strftime("%Y-%m") for m in Sset} == {"2024-04", "2024-05"}
s5 = save("s5_exclusion_effect", [dict(variant=k, n_months_excluded=(len(Sset) if k == "E-scan2" else {"B": 0, "E1": 3, "E2": 2}[k]), empty_quarters=e["empty"], decline_Q2=e["decline"], neg_cells=e["neg"], n_cells=e["ncell"], chg_median=e["medchg"], change_label=e["change_label"], spread=e["spread"], temporal=e["temporal"],
                                  **{f"W0_{t[0]}Q{t[1]}": e["W0"][t]["rho"] for t in TQ16}) for k, e in EVS.items()])
lab = dict(R12_2=r122, R12_3=(r123, n34), R12_4=r124s, R12_5=(r125, dict(j_F2=j2, j_F3=j3, j_F4=j4, F4_trivially_below_half=f4_trivial)), R12_6=(r126, dict(a=(stB["a"], stS["a"]), b=(stB["b"], stS["b"]), c=(stB["c"], stS["c"])), dict(equals_X10_E2=equals_E2)),
           S_set=sorted(m.strftime("%Y-%m") for m in Sset), flags={f: sorted(m.strftime("%Y-%m") for m in FLAG[f]) for f in FAM}, not_evaluable=notev)
json.dump({k: str(v) for k, v in lab.items()}, open(R / "labels.json", "w"), indent=1)
rep = ["# X12 report: local robust z scan of VNNIC months\n", "Generated by run_x12.py per x12_local_scan_specification.md incl. D1 (hash chain x12_spec_hash.txt). EXPLORATORY and POST HOC; numbers come from results_x12/*.csv; labels are mechanical.\n", "## Gates\n", md(gt),
       "\n## Flags per family (R12.1, z_local <= -3.5)\n", "\n".join(f"- {f}: {lab['flags'][f]}" for f in FAM), f"\nNot locally evaluable (counted, neither flagged nor cleared): {notev}\n", "\n## Lowest five local z per family\n", md(low5), "\n## Watch and flagged months\n", md(scan[scan.flagged | scan.watch]),
       f"\n## Controls\nR12.2: {r122} (determined by X11 numbers, see D1.3)\nR12.3: {r123} ({n34} months flagged in F3+F4)\n", "\n## Flags outside March-May 2024\n", md(oth), f"\nR12.4: {r124s}\n", "\n## Cross-family\n", md(cross), f"\nR12.5: {r125}; Jaccard F1-F2 {j2:.2f}, F1-F3 {j3:.2f}, F1-F4 {j4:.2f}; F4 condition trivially met: {f4_trivial}\n",
       "\n## Exclusion effect (F1)\n", md(s5[[c for c in s5.columns if not c.startswith('W0_')]]), f"\nS (months excluded, not Ookla-confounded): {lab['S_set']}; equals X10 E2: {equals_E2}\nR12.6: {lab['R12_6']}\n", "\n## Sensitivity (window x threshold)\n", md(sens)]
(HERE / "x12_report.md").write_text("\n".join(rep), encoding="utf-8")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print("flags", lab["flags"]); print("not evaluable", notev); print(low5.round(3).to_string(index=False)); print(oth.to_string(index=False)); print("R12.2", r122, "| R12.3", r123, n34, "| R12.4", r124s, "| R12.5", lab["R12_5"])
print(s5[[c for c in s5.columns if not c.startswith("W0_")]].round(3).to_string(index=False)); print("R12.6", lab["R12_6"], "S", lab["S_set"])
print(sens[sens.window == 6].pivot_table(index="family", columns="threshold", values="n_flagged").to_string()); print(sens.pivot_table(index=["family", "window"], columns="threshold", values="n_flagged").to_string())
