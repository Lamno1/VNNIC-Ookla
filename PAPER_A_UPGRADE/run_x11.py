"""X11 per x11_q3_quarters_specification.md incl. D1 and D2 (hash chain x11_spec_hash.txt). Labels applied mechanically."""
import json
import upg_common as U
from upg_common import *
U.SEED, U.PSEED = 20261018, 20261019
U._IDX.clear()

D = Data(with_ext=True)
R = HERE / "results_x11"; R.mkdir(exist_ok=True)
X9 = pd.read_parquet(HERE / "data" / "ookla_x9_province_quarter.parquet"); inv = {v: k for k, v in D.iso.items()}; X9["pid"] = X9.shapeISO.map(inv)
fact = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet"); fact["month"] = pd.to_datetime(fact["month"])
def vpiv(net, col): return fact[fact.network == net].pivot_table(index="month", columns="province_id_legacy63", values=col, aggfunc="first").reindex(columns=D.pids)
names = pd.read_parquet(ROOT / "data/analysis/analysis_panel_2021_2024.parquet").drop_duplicates("province_id_legacy63").set_index("province_id_legacy63").province_name_canonical
pname = np.array([names.get(p, p) for p in D.pids])
FAM = {"F1": vpiv("ftth", "download"), "F2": vpiv("ftth", "upload"), "F3": vpiv("ftth", "ping"), "F4": vpiv("mobile", "download")}
XOC = {"F2": ("fixed", "ul_median"), "F3": ("fixed", "lat_median"), "F4": ("mobile", "dl_median")}
def Oarr(fid, y, q):
    if fid == "F1":
        return D.O.get((y, q), np.full(D.n, np.nan))
    kind, col = XOC[fid]; g = X9[(X9.kind == kind) & (X9.year == y) & (X9.quarter == q)].set_index("pid")
    if not len(g):
        return np.full(D.n, np.nan)
    a = np.array([g[col].get(p, np.nan) for p in D.pids], float); t = np.array([g.observed_tiles.get(p, np.nan) for p in D.pids], float)
    return np.where(t >= 10, a, np.nan)
OC = {}
def O(fid, y, q):
    if (fid, y, q) not in OC:
        OC[(fid, y, q)] = Oarr(fid, y, q)
    return OC[(fid, y, q)]
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

# ------------------------------------------------ gates
g = []
a1 = pd.read_csv(HERE / "results_q2" / "a1_side_attribution.csv")
def a1_point(T):
    p, n = prev(*T), nxt(*T); v = {k: Vbase("F1", *t) for k, t in dict(VT=T, VP=p, VN=n).items()}; o = {k: O("F1", *t) for k, t in dict(OT=T, OP=p, ON=n).items()}
    ok = np.all([np.isfinite(x) for x in list(v.values()) + list(o.values())], axis=0)
    AV = np.mean([sp(v["VT"][ok], x[ok]) for x in (v["VP"], v["VN"], o["OP"], o["ON"])]); AO = np.mean([sp(o["OT"][ok], x[ok]) for x in (o["OP"], o["ON"], v["VP"], v["VN"])])
    return AV, AO, AV - AO
for T in [(2021, 3), (2023, 3)]:
    AV, AO, Dd = a1_point(T); row = a1[(a1.year == T[0]) & (a1.q == T[1])].iloc[0]
    for nm, val, tg in (("A_V", AV, row.A_V), ("A_O", AO, row.A_O), ("D", Dd, row.D)):
        g.append(dict(gate="G11.1", item=f"{T[0]}Q{T[1]} {nm}", value=float(val), target=float(tg), passed=abs(val - tg) < 0.005))
a2i = pd.read_csv(HERE / "results_q2" / "a2i_month_vs_ookla.csv").set_index("month")
for m in (3, 4, 5):
    r = rho_cc(FAM["F1"].loc[pd.Timestamp(2024, m, 1)].to_numpy(float), O("F1", 2024, 2))[0]
    g.append(dict(gate="G11.2", item=f"2024-{m:02d} vs Ookla Q2", value=float(r), target=float(a2i.loc[f"2024-{m:02d}", "rho_Ookla_Q2"]), passed=abs(r - a2i.loc[f"2024-{m:02d}", "rho_Ookla_Q2"]) < 0.005))
MS = list(pd.date_range("2021-01-01", "2024-12-01", freq="MS"))
cov = pd.DataFrame({fid: [int(FAM[fid].loc[m].notna().sum()) if m in FAM[fid].index else 0 for m in MS] for fid in FAM}, index=[m.strftime("%Y-%m") for m in MS])
cov.to_csv(R / "g113_coverage.csv"); insuff = {fid: int((cov[fid] < 55).sum()) for fid in FAM}
g.append(dict(gate="G11.3", item=f"insufficient months per family {insuff}", value=sum(insuff.values()), target=0, passed=True))
gt = save("gates", g); print(gt.to_string())
if not gt[gt.gate.isin(["G11.1", "G11.2"])].passed.all():
    print("GATE FAILURE: stop"); raise SystemExit(1)

# ------------------------------------------------ S1 scan
def mad_z(x, ref):
    ref = ref[np.isfinite(ref)]
    if len(ref) < 8:
        return np.nan
    med = np.median(ref); mad = 1.4826 * np.median(np.abs(ref - med))
    return (x - med) / mad if mad > 0 else np.nan
scan_rows = []; FLAG = {}
for fid in FAM:
    s = []
    for m in MS:
        v = FAM[fid].loc[m].to_numpy(float) if m in FAM[fid].index else np.full(D.n, np.nan)
        if np.isfinite(v).sum() < 55:
            s.append((np.nan, 0)); continue
        q = ((m.month - 1) // 3 + 1); tq = (m.year, q); rs = []
        for t in (prev(*tq), tq, nxt(*tq)):
            r, n = rho_cc(v, O(fid, *t))
            if np.isfinite(r): rs.append(r)
        s.append((float(np.mean(rs)) if len(rs) >= 2 else np.nan, len(rs)))
    sv = np.array([x[0] for x in s]); gz = np.array([mad_z(x, sv) for x in sv]); lz = np.full(len(sv), np.nan)
    for i in range(len(sv)):
        if np.isfinite(sv[i]):
            win = [sv[j] for j in range(max(0, i - 6), min(len(sv), i + 7)) if j != i]
            lz[i] = mad_z(sv[i], np.array(win))
    flag = np.isfinite(gz) & np.isfinite(lz) & (gz <= -2.5) & (lz <= -2.0); watch = np.isfinite(gz) & (gz > -2.5) & (gz <= -2.0)
    FLAG[fid] = {MS[i] for i in range(len(MS)) if flag[i]}
    for i, m in enumerate(MS):
        scan_rows.append(dict(family=fid, month=m.strftime("%Y-%m"), score=sv[i], n_quarters=s[i][1], z_global=gz[i], z_local=lz[i], flagged=bool(flag[i]), watch=bool(watch[i])))
scan = save("s1_month_scan", scan_rows)
nfl = {f: len(FLAG[f]) for f in FAM}; print("flags per family", nfl)

def r111(T, fid="F1"):
    k = sum(1 for m in qmonths(*T) if m in FLAG[fid])
    return "no flagged month" if k == 0 else ("localised" if k < 3 else "quarter-wide"), k

# ------------------------------------------------ S2 adjacent months (F1)
ms2 = MS; z2 = []; rows = []
for a, b in zip(ms2[:-1], ms2[1:]):
    x, y = FAM["F1"].loc[a].to_numpy(float), FAM["F1"].loc[b].to_numpy(float); r, n = rho_cc(x, y, 30); z2.append(np.arctanh(np.clip(r, -0.999, 0.999)) if np.isfinite(r) else np.nan); rows.append(dict(pair=f"{a:%Y-%m}/{b:%Y-%m}", N=n, r=r, z=z2[-1]))
z2 = np.array(z2); fl = []
for i in range(len(z2)):
    o_ = np.delete(z2, i); o_ = o_[np.isfinite(o_)]; fl.append(bool(np.isfinite(z2[i]) and z2[i] < o_.mean() - 2 * o_.std(ddof=1)))
s2 = save("s2_adjacent_months", [dict(**r_, flagged=f) for r_, f in zip(rows, fl)])

# ------------------------------------------------ S3 Ookla adjacent quarters (F1)
TQ16 = [(y, q) for y in range(2021, 2025) for q in (1, 2, 3, 4)]
pairs = list(zip(TQ16[:-1], TQ16[1:])); pr = []; zs = []
for a, b in pairs:
    r, n = rho_cc(O("F1", *a), O("F1", *b), 30); pr.append((a, b, r, n)); zs.append(np.arctanh(np.clip(r, -0.999, 0.999)))
zs = np.array(zs)
def ookla_side(T):
    touch = [i for i, (a, b) in enumerate(pairs) if a == T or b == T]; other = np.delete(zs, touch)
    thr = other.mean() - 2 * other.std(ddof=1); hit = [bool(zs[i] < thr) for i in touch]
    return any(hit), float(thr)
oside = {T: ookla_side(T) for T in TQ16}
s3 = save("s3_ookla_pairs", [dict(pair=f"{a[0]}Q{a[1]}/{b[0]}Q{b[1]}", N=n, r=r, z=float(zs[i])) for i, (a, b, r, n) in enumerate(pr)])
save("s3_ookla_side", [dict(quarter=f"{T[0]}Q{T[1]}", ookla_side=v[0], threshold_z=v[1], tiles=float(np.nansum(D.OTL.get(T, np.nan))), tests=float(np.nansum(D.OT.get(T, np.nan))),
                          tiles_over_mean_neighbours=float(np.nansum(D.OTL.get(T, np.nan)) / np.mean([np.nansum(D.OTL.get(t, np.nan)) for t in (prev(*T), nxt(*T)) if t in D.OTL]))) for T, v in oside.items()])

# ------------------------------------------------ S4 shared displacement
def displacement(fid, T):
    p, n = prev(*T), nxt(*T); vs = [Vbase(fid, *t) for t in (p, T, n)]; os_ = [O(fid, *t) for t in (p, T, n)]
    ok = np.all([np.isfinite(x) for x in vs + os_], axis=0)
    rv = [stats.rankdata(x[ok]) for x in vs]; ro = [stats.rankdata(x[ok]) for x in os_]
    dV = rv[1] - 0.5 * (rv[0] + rv[2]); dO = ro[1] - 0.5 * (ro[0] + ro[2])
    return dV, dO, int(ok.sum())
QS14 = [t for t in TQ16 if (2021, 2) <= t <= (2024, 3)]; rows = []
for fid in ("F1", "F2"):
    for T in QS14:
        dV, dO, n = displacement(fid, T); sh = sp(dV, dO); lo, hi = ci(sp_boot(dV, dO)); pv = perm_p(dV, dO); vr = float(np.var(dV, ddof=1) / np.var(dO, ddof=1))
        rows.append(dict(family=fid, year=T[0], q=T[1], N=n, shared=sh, lo=lo, hi=hi, p=pv, var_ratio_V_over_O=vr))
s4 = save("s4_shared_displacement", rows)
TARG = [(2021, 3), (2023, 3), (2024, 2)]
def r113(fid, T):
    t = s4[(s4.family == fid)]; refs = t[~t.apply(lambda r: (int(r.year), int(r.q)) in TARG, axis=1)].shared; p75 = float(refs.quantile(.75))
    r = t[(t.year == T[0]) & (t.q == T[1])].iloc[0]
    if r.lo > 0 and r.shared > p75: lab = "shared displacement"
    elif r.lo <= 0 and r.var_ratio_V_over_O > 1.5: lab = "source-specific displacement"
    else: lab = "indeterminate"
    return lab, dict(shared=float(r.shared), lo=float(r.lo), hi=float(r.hi), var_ratio=float(r.var_ratio_V_over_O), ref_p75=p75, n_ref=len(refs))

# ------------------------------------------------ S5 provinces and families
def top10(T):
    a, b = Vbase("F1", *T), O("F1", *T); ok = np.isfinite(a) & np.isfinite(b); d = np.full(D.n, -1.0); d[ok] = np.abs(stats.rankdata(a[ok]) - stats.rankdata(b[ok])); return list(np.argsort(-d)[:10])
t24 = top10((2024, 2)); named = {"Son La", "Dien Bien", "Tuyen Quang", "Hoa Binh", "Lam Dong"}
rows = []
for T in TARG:
    tt = top10(T); ov = len(set(tt) & set(t24)); nm = sorted(set(pname[tt]) & named)
    rows.append(dict(quarter=f"{T[0]}Q{T[1]}", top10=", ".join(pname[tt]), overlap_with_2024Q2=ov, named_five_in_top10=", ".join(nm), R11_4="persistent provincial pattern" if ov >= 5 else "not persistent"))
s5a = save("s5a_provinces", rows)
def jac(a, b): return len(a & b) / len(a | b) if (a | b) else 0.0
if len(FLAG["F1"]) == 0:
    r115 = "not evaluable (F1 has no flagged month)"
else:
    j2, j3, j4 = jac(FLAG["F1"], FLAG["F2"]), jac(FLAG["F1"], FLAG["F3"]), jac(FLAG["F1"], FLAG["F4"])
    r115 = "shared fixed-throughput regime" if (j2 >= 0.5 and j4 < 0.5) else ("download-specific" if j2 < 0.5 else "mixed")
s5b = save("s5b_cross_family", [dict(family=f, n_flagged=len(FLAG[f]), months=", ".join(sorted(m.strftime("%Y-%m") for m in FLAG[f])), jaccard_with_F1=jac(FLAG["F1"], FLAG[f])) for f in FAM] + [dict(family="R11.5", n_flagged=np.nan, months=r115, jaccard_with_F1=np.nan)])

# ------------------------------------------------ S6 scan-based exclusion (F1)
Sset = {m for m in FLAG["F1"] if not oside[(m.year, (m.month - 1) // 3 + 1)][0]}
save("s6_exclusion_set", [dict(month=m.strftime("%Y-%m"), flagged=True, kept_in_S=(m in Sset)) for m in sorted(FLAG["F1"])] or [dict(month="(none)", flagged=False, kept_in_S=False)])
vm1 = FAM["F1"]
def Vvar(excl, y, q):
    ms = qmonths(y, q); rem = [m for m in ms if m not in excl]
    if len(rem) == 3: return Vbase("F1", y, q)
    if not rem: return np.full(D.n, np.nan)
    sub = vm1.reindex(rem); ok = sub.notna().sum() >= 1
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Vyr(excl, y, minm):
    ms = [pd.Timestamp(y, k, 1) for k in range(1, 13) if pd.Timestamp(y, k, 1) not in excl]; sub = vm1.reindex(ms); ok = sub.notna().sum() >= minm
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Oyr(y):
    arr = np.vstack([O("F1", y, q) for q in (1, 2, 3, 4)]); ok = np.isfinite(arr).sum(0) >= 3; return np.where(ok, np.nanmedian(arr, axis=0), np.nan)
def cell(x, y):
    m = np.isfinite(x) & np.isfinite(y); n = int(m.sum()); return dict(N=n, rho=sp(x[m], y[m]) if n >= 10 else np.nan)
def evaluate(excl):
    Vs = {t: Vvar(excl, *t) for t in TQ16}; Vy = {y: Vyr(excl, y, 7 if excl else 9) for y in range(2021, 2025)}
    rh = {t: cell(Vs[t], O("F1", *t)) for t in TQ16}
    empty = [t for t in TQ16 if not np.isfinite(Vs[t]).any()]
    dec = rh[(2021, 2)]["rho"] - rh[(2024, 2)]["rho"] if (np.isfinite(rh[(2021, 2)]["rho"]) and np.isfinite(rh[(2024, 2)]["rho"])) else np.nan
    ch = []
    for y0 in (2021, 2022, 2023):
        for q in (1, 2, 3, 4):
            ch.append(cell(np.log(Vs[(2024, q)]) - np.log(Vs[(y0, q)]), np.log(O("F1", 2024, q)) - np.log(O("F1", y0, q))))
    chd = pd.DataFrame(ch); v = chd[(chd.N >= 50) & chd.rho.notna()]; neg = int((v.rho < 0).sum()); med = float(v.rho.median()) if len(v) else np.nan
    lab = "robustly negative" if (neg >= 10 and med <= -0.10) else ("robustly positive" if (neg <= 2 and len(v) >= 10) else "sign unstable")
    sp_ = []
    for y in range(2021, 2025):
        vv = [rh[(y, q)]["rho"] for q in (1, 2, 3, 4) if rh[(y, q)]["N"] >= 50 and np.isfinite(rh[(y, q)]["rho"])]
        if len(vv) >= 2: sp_.append(max(vv) - min(vv))
    spread = float(np.median(sp_)) if sp_ else np.nan
    return dict(W0={f"{t[0]}Q{t[1]}": rh[t]["rho"] for t in TQ16}, empty_quarters=len(empty), decline=dec, neg=neg, ncell=len(v), medchg=med, change_label=lab, spread=spread, temporal=("sensitive" if spread >= 0.20 else "stable") if np.isfinite(spread) else "n/a")
EV = {"B": evaluate(set()), "E1": evaluate({pd.Timestamp(2024, m, 1) for m in (3, 4, 5)}), "E-scan": evaluate(Sset)}
def status(e): return dict(a=(e["decline"] >= 0.20) if np.isfinite(e["decline"]) else None, b=e["change_label"], c=e["temporal"])
stB, stS = status(EV["B"]), status(EV["E-scan"]); dep = [stB[k] != stS[k] for k in "abc"]; nd = sum(dep)
r116 = "claims survive exclusion" if nd == 0 else ("claims depend on the exclusion" if nd >= 2 else "partly depend")
rows = []
for k, e in EV.items():
    rows.append(dict(variant=k, n_months_excluded=(len(Sset) if k == "E-scan" else (3 if k == "E1" else 0)), empty_quarters=e["empty_quarters"], decline_Q2=e["decline"], neg_cells=e["neg"], n_cells=e["ncell"], chg_median=e["medchg"], change_label=e["change_label"], spread=e["spread"], temporal=e["temporal"], **{f"W0_{kk}": vv for kk, vv in e["W0"].items()}))
s6 = save("s6_exclusion_effect", rows)

# ------------------------------------------------ R11.7 summary
summ = []
for T in TARG:
    l1, k = r111(T); r2 = oside[T][0]; l3, d3 = r113("F1", T)
    ov = int(s5a[s5a.quarter == f"{T[0]}Q{T[1]}"].overlap_with_2024Q2.iloc[0])
    if l1 in ("localised", "quarter-wide") and not r2 and l3 == "source-specific displacement": s7 = "VNNIC-localised artifact"
    elif l3 == "shared displacement" and l1 == "no flagged month": s7 = "shared shift"
    elif r2: s7 = "Ookla-related"
    else: s7 = "unexplained by these diagnostics"
    summ.append(dict(quarter=f"{T[0]}Q{T[1]}", R11_1=f"{l1} ({k}/3)", R11_2_ookla_side=r2, R11_3=l3, shared=d3["shared"], shared_lo=d3["lo"], shared_hi=d3["hi"], var_ratio=d3["var_ratio"], ref_p75=d3["ref_p75"], R11_4_overlap=ov, R11_7=s7))
S7 = save("r11_7_summary", summ)
lab = dict(R11_5=r115, R11_6=(r116, dep, stB, stS), flags=nfl, S_set=sorted(m.strftime("%Y-%m") for m in Sset), summary=S7.to_dict("records"))
json.dump({k: str(v) for k, v in lab.items()}, open(R / "labels.json", "w"), indent=1)
rep = ["# X11 report: 2021 Q3 and 2023 Q3 VNNIC-side flags\n", "Generated by run_x11.py per x11_q3_quarters_specification.md incl. D1 and D2 (hash chain x11_spec_hash.txt). Post hoc diagnostic; numbers come from results_x11/*.csv; labels are mechanical.\n",
       "## Gates\n", md(gt), f"\n## S1 flags per family: {nfl}\n", md(scan[scan.flagged | scan.watch]), "\n## S2 adjacent months (F1)\n", md(s2[s2.flagged]), "\n## S3 Ookla-side\n", md(pd.read_csv(R / "s3_ookla_side.csv")), "\n## S4 shared displacement\n", md(s4),
       "\n## S5 provinces\n", md(s5a), "\n", md(s5b), "\n## S6 exclusion effect (F1)\n", md(s6[[c for c in s6.columns if not c.startswith("W0_")]]), f"\nS (months excluded): {lab['S_set']}\nR11.6: {lab['R11_6']}\n", "\n## R11.7 summary\n", md(S7)]
(HERE / "x11_report.md").write_text("\n".join(rep), encoding="utf-8")
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
print(scan[scan.flagged | scan.watch].round(3).to_string()); print(s2[s2.flagged].to_string()); print(pd.read_csv(R / "s3_ookla_side.csv").round(3).to_string())
print(s4.round(3).to_string()); print(s5a.to_string()); print(s5b.to_string()); print(s6[[c for c in s6.columns if not c.startswith("W0_")]].round(3).to_string()); print("R11.6", lab["R11_6"]); print(S7.round(3).to_string())
