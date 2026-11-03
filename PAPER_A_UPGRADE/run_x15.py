"""X15 per x15_nso2025_specification.md incl. D1 (hash chain x15_spec_hash.txt). Labels applied mechanically."""
import json, re, unicodedata, hashlib
import upg_common as U
from upg_common import *
U.SEED, U.PSEED = 20261024, 20261025
U._IDX.clear()

D = Data(with_ext=True)
R = HERE / "results_x15"; R.mkdir(exist_ok=True)
X9 = pd.read_parquet(HERE / "data" / "ookla_x9_province_quarter.parquet"); inv = {v: k for k, v in D.iso.items()}; X9["pid"] = X9.shapeISO.map(inv)
fact = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet"); fact["month"] = pd.to_datetime(fact["month"])
def vpiv(net, col): return fact[fact.network == net].pivot_table(index="month", columns="province_id_legacy63", values=col, aggfunc="first").reindex(columns=D.pids)
FAM = {"F1": (vpiv("ftth", "download"), None), "F2": (vpiv("ftth", "upload"), ("fixed", "ul_median")), "F4": (vpiv("mobile", "download"), ("mobile", "dl_median"))}
CT = vpiv("ftth", "value_raw")
def qm(y, q): return [pd.Timestamp(y, 3 * (q - 1) + k, 1) for k in (1, 2, 3)]
def Vq(fid, y, q, months=None, minm=2):
    sub = FAM[fid][0].reindex(months if months is not None else qm(y, q)); ok = sub.notna().sum() >= minm
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Vh1(fid, y):
    sub = FAM[fid][0].reindex([pd.Timestamp(y, k, 1) for k in range(1, 7)]); ok = sub.notna().sum() >= 4
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Oq(fid, y, q):
    if fid == "F1": return D.O.get((y, q), np.full(D.n, np.nan))
    kind, col = FAM[fid][1]; g = X9[(X9.kind == kind) & (X9.year == y) & (X9.quarter == q)].set_index("pid")
    if not len(g): return np.full(D.n, np.nan)
    a = np.array([g[col].get(p, np.nan) for p in D.pids], float); t = np.array([g.observed_tiles.get(p, np.nan) for p in D.pids], float); return np.where(t >= 10, a, np.nan)
def Oh1(fid, y):
    a, b = Oq(fid, y, 1), Oq(fid, y, 2); return np.where(np.isfinite(a) & np.isfinite(b), (a + b) / 2, np.nan)
def vec(fid, src, y, per):
    if per == "H1": return Vh1(fid, y) if src == "VNNIC" else Oh1(fid, y)
    q = int(per[1]); return Vq(fid, y, q) if src == "VNNIC" else Oq(fid, y, q)
def save(name, rows):
    df = pd.DataFrame(rows); df.to_csv(R / f"{name}.csv", index=False); return df

# ------------------------------------------------ NSO data and gates
def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower().replace("đ", "d")); s = "".join(c for c in s if unicodedata.category(c) != "Mn"); s = s.replace("tp.", "").replace("thanh pho", ""); return re.sub(r"[^a-z0-9]", "", s)
ext = HERE / "data/external"
n24 = pd.read_csv(ext / "nso_yearbook2024/nso_yearbook2024_internet_by_province.csv", encoding="utf-8-sig"); n25 = pd.read_csv(ext / "nso_yearbook2025/nso_yearbook2025_internet_by_province.csv", encoding="utf-8-sig")
popf = pd.read_csv(ROOT / "RED_TEAM_DIAGNOSTICS/population_data/population_province_year_2021_2024.csv"); pop24 = popf[popf.year == 2024].set_index("province_id_legacy63")
key_off = {norm(n): p for p, n in zip(pop24.index, pop24.province_name_official)}
mp = {}
for nm in n24.province_nso_name:
    k = norm(nm); k = "thuathienhue" if k == "hue" else k
    if k in key_off: mp[nm] = key_off[k]
g = [dict(gate="G15.1", item="mapping one-to-one for 63 provinces", value=len(mp), target=63, passed=len(mp) == 63 and set(mp.values()) == set(D.pids) and len(set(mp.values())) == 63)]
order = {mp[nm]: i for i, nm in enumerate(n24.province_nso_name) if nm in mp}
def arr(df, col): return np.array([df[col].iloc[order[p]] for p in D.pids], float)
N1_24 = arr(n24, "pct_households_internet_connection_prelim2024"); N2_24 = arr(n24, "pct_people_using_internet_prelim2024")
N1_25 = arr(n25, "households_prelim2025"); N2_25 = arr(n25, "people_prelim2025")
d1 = np.abs(arr(n25, "households_2024_in_2025book") - N1_24).max(); d2 = np.abs(arr(n25, "people_2024_in_2025book") - N2_24).max()
g.append(dict(gate="G15.5", item="2024 columns of the 2025 file equal the 2024 file (max abs diff, households and people)", value=float(max(d1, d2)), target=0.0, passed=bool(max(d1, d2) == 0.0)))
x13t = {("VNNIC", 1): 0.311, ("VNNIC", 2): 0.123, ("VNNIC", 3): 0.359, ("VNNIC", 4): 0.281, ("Ookla", 1): 0.334, ("Ookla", 2): 0.378, ("Ookla", 3): 0.375, ("Ookla", 4): 0.347}
for (src, q), tg in x13t.items():
    v = vec("F1", src, 2024, f"Q{q}"); m = np.isfinite(v) & np.isfinite(N1_24); r = sp(v[m], N1_24[m]); g.append(dict(gate="G15.2", item=f"{src} 2024Q{q} vs N1", value=float(r), target=tg, passed=abs(r - tg) < 0.005))
for fn, d_ in (("nso_yearbook2024", ext / "nso_yearbook2024"), ("nso_yearbook2025", ext / "nso_yearbook2025")):
    csvp = d_ / f"{fn}_internet_by_province.csv"; sha = hashlib.sha256(open(csvp, "rb").read()).hexdigest(); g.append(dict(gate="G15.3", item=f"{fn} CSV sha256 in provenance.md", value=sha[:16], target="in file", passed=sha in open(d_ / "provenance.md", encoding="utf-8").read()))
for src in ("VNNIC", "Ookla"):
    for q in (1, 2):
        v = vec("F1", src, 2025, f"Q{q}"); g.append(dict(gate="G15.4", item=f"F1 {src} 2025Q{q} provinces", value=int(np.isfinite(v).sum()), target=60, passed=int(np.isfinite(v).sum()) >= 60))
gt = save("gates", g); print(gt.to_string())
if not gt.passed.all():
    print("GATE FAILURE: stop"); raise SystemExit(1)
NS25 = {"N1": N1_25, "N2": N2_25}; NS24 = {"N1": N1_24, "N2": N2_24}; DNS = {"N1": N1_25 - N1_24, "N2": N2_25 - N2_24}
LP = np.log(pop24.loc[D.pids, "pop_thousand"].to_numpy(float))

# ------------------------------------------------ helpers
idx = make_idx(D.n)
def fast_rho(x, y):
    if np.isfinite(x).all() and np.isfinite(y).all(): return corr_rows(rk(x[idx]), rk(y[idx]))
    xs, ys = x[idx], y[idx]; out = np.full(B, np.nan)
    for i in range(B):
        m = np.isfinite(xs[i]) & np.isfinite(ys[i])
        if m.sum() >= 10:
            a = stats.rankdata(xs[i][m]); b = stats.rankdata(ys[i][m]); a = a - a.mean(); b = b - b.mean(); den = np.sqrt((a * a).sum() * (b * b).sum()); out[i] = (a * b).sum() / den if den > 0 else np.nan
    return out
def rho_n(x, y):
    m = np.isfinite(x) & np.isfinite(y); return (sp(x[m], y[m]), int(m.sum())) if m.sum() >= 10 else (np.nan, int(m.sum()))
def pperm(x, y):
    m = np.isfinite(x) & np.isfinite(y); return perm_p(x[m], y[m]) if m.sum() >= 10 else np.nan
def lab_corr(lo, hi, p): return "positive and distinguishable" if (lo > 0 and p < 0.05) else ("negative and distinguishable" if (hi < 0 and p < 0.05) else "not distinguishable from 0")
def cls(r): return "weak" if abs(r) < 0.30 else ("moderate" if abs(r) <= 0.60 else "strong")
def twosided(b):
    b = b[np.isfinite(b)]; return min(1.0, 2 * min((np.sum(b >= 0) + 1) / (len(b) + 1), (np.sum(b <= 0) + 1) / (len(b) + 1)))
def lab_delta(lo, hi): return "VNNIC more strongly associated" if lo > 0 else ("Ookla more strongly associated" if hi < 0 else "no distinguishable difference")
PER25 = ["Q1", "Q2", "H1"]

# ------------------------------------------------ S1, S2
S1, BOOT = [], {}
for fid in FAM:
    for per in PER25:
        for src in ("VNNIC", "Ookla"):
            x = vec(fid, src, 2025, per)
            for nk in ("N1", "N2"):
                r, n = rho_n(x, NS25[nk]); b = fast_rho(x, NS25[nk]); BOOT[(fid, per, src, nk)] = b; lo, hi = ci(b); p = pperm(x, NS25[nk])
                S1.append(dict(family=fid, period=per, source=src, indicator=nk, N=n, rho=r, lo=lo, hi=hi, p=p, label=lab_corr(lo, hi, p), strength=cls(r)))
S1 = pd.DataFrame(S1); H = S1[(S1.family == "F1") & (S1.indicator == "N1") & (S1.period.isin(["Q1", "Q2"]))].index
S1["p_holm_headline"] = np.nan; S1.loc[H, "p_holm_headline"] = holm(S1.loc[H, "p"].to_numpy()); S1.to_csv(R / "s1_associations.csv", index=False)
def adj_rep(fid, src, bootstrap):
    qs = [(2024, 4), (2025, 1), (2025, 2)]; arr_ = {t: vec(fid, src, t[0], f"Q{t[1]}") for t in qs}; zs = []
    for a, b_ in zip(qs[:-1], qs[1:]):
        r = fast_rho(arr_[a], arr_[b_]) if bootstrap else rho_n(arr_[a], arr_[b_])[0]; zs.append(np.arctanh(np.clip(r, -0.999, 0.999)))
    return np.tanh(np.mean(zs, axis=0))
REL = {(f, s): (float(adj_rep(f, s, False)), adj_rep(f, s, True)) for f in FAM for s in ("VNNIC", "Ookla")}
save("s2_reliability", [dict(family=f, source=s, r_2025=v[0], lo=ci(v[1])[0], hi=ci(v[1])[1]) for (f, s), v in REL.items()])
S2 = []
for fid in FAM:
    for per in PER25:
        for nk in ("N1", "N2"):
            sv = S1[(S1.family == fid) & (S1.period == per) & (S1.indicator == nk)].set_index("source"); bV, bO = BOOT[(fid, per, "VNNIC", nk)], BOOT[(fid, per, "Ookla", nk)]
            dlt = sv.loc["VNNIC", "rho"] - sv.loc["Ookla", "rho"]; db = bV - bO; lo, hi = ci(db); rV, rVb = REL[(fid, "VNNIC")]; rO, rOb = REL[(fid, "Ookla")]; fl = lambda r_: np.maximum(r_, 0.05)
            aV, aO = sv.loc["VNNIC", "rho"] / np.sqrt(max(rV, 0.05)), sv.loc["Ookla", "rho"] / np.sqrt(max(rO, 0.05)); dab = bV / np.sqrt(fl(rVb)) - bO / np.sqrt(fl(rOb)); alo, ahi = ci(dab)
            S2.append(dict(family=fid, period=per, indicator=nk, rho_V=sv.loc["VNNIC", "rho"], rho_O=sv.loc["Ookla", "rho"], delta=dlt, lo=lo, hi=hi, p_boot=twosided(db), R15_2=lab_delta(lo, hi), delta_adj=aV - aO, adj_lo=alo, adj_hi=ahi, R15_2b=lab_delta(alo, ahi)))
S2 = pd.DataFrame(S2); Hd = S2[(S2.family == "F1") & (S2.indicator == "N1") & (S2.period.isin(["Q1", "Q2"]))].index
S2["p_holm_headline"] = np.nan; S2.loc[Hd, "p_holm_headline"] = holm(S2.loc[Hd, "p_boot"].to_numpy()); S2.to_csv(R / "s2_delta.csv", index=False)

# ------------------------------------------------ S3 stability
S3 = []
for nk in ("N1", "N2"):
    for src in ("VNNIC", "Ookla"):
        for q in (1, 2):
            x25, x24 = vec("F1", src, 2025, f"Q{q}"), vec("F1", src, 2024, f"Q{q}"); r25, _ = rho_n(x25, NS25[nk]); r24, _ = rho_n(x24, NS24[nk]); db = fast_rho(x25, NS25[nk]) - fast_rho(x24, NS24[nk]); lo, hi = ci(db)
            S3.append(dict(indicator=nk, source=src, quarter=f"Q{q}", rho_2024=r24, rho_2025=r25, stab=r25 - r24, lo=lo, hi=hi, R15_3="stronger in 2025" if lo > 0 else ("weaker in 2025" if hi < 0 else "not distinguishable")))
S3 = save("s3_stability", S3)
pers = []
for nk in ("N1", "N2"):
    r, n = rho_n(NS24[nk], NS25[nk]); lo, hi = ci(fast_rho(NS24[nk], NS25[nk])); pers.append(dict(indicator=nk, rho_NSO2024_NSO2025=r, lo=lo, hi=hi))
pers = save("s3_nso_persistence", pers)

# ------------------------------------------------ S4 change
def partial(x, y, z):
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if m.sum() < 10: return np.nan, None, None, 0
    rx, ry, rz = stats.rankdata(x[m]), stats.rankdata(y[m]), stats.rankdata(z[m]); X = np.column_stack([np.ones(m.sum()), rz])
    ex = rx - X @ np.linalg.lstsq(X, rx, rcond=None)[0]; ey = ry - X @ np.linalg.lstsq(X, ry, rcond=None)[0]; return float(np.corrcoef(ex, ey)[0, 1]), ex, ey, int(m.sum())
def chg(fid, src, per, q1_from_janfeb=False):
    if src == "VNNIC" and q1_from_janfeb and per == "Q1":
        a = Vq(fid, 2024, 1, months=[pd.Timestamp(2024, 1, 1), pd.Timestamp(2024, 2, 1)], minm=1)
    else: a = vec(fid, src, 2024, per)
    b = vec(fid, src, 2025, per); return np.log(b) - np.log(a)
S4 = []
for fid in FAM:
    for per in PER25:
        for src in ("VNNIC", "Ookla"):
            c = chg(fid, src, per)
            for nk in ("N1", "N2"):
                r, n = rho_n(c, DNS[nk]); b = fast_rho(c, DNS[nk]); lo, hi = ci(b); p = pperm(c, DNS[nk])
                S4.append(dict(family=fid, period=per, source=src, indicator="d" + nk, N=n, rho=r, lo=lo, hi=hi, p=p, R15_4=lab_corr(lo, hi, p), primary=(per == "Q1"), note="start of Q2/H1 includes the anomalous VNNIC months of April-May 2024" if (per != "Q1" and src == "VNNIC") else ""))
S4 = save("s4_change", S4)
S4b = []
for nk in ("N1", "N2"):
    c = chg("F1", "VNNIC", "Q1", q1_from_janfeb=True); r, n = rho_n(c, DNS[nk]); b = fast_rho(c, DNS[nk]); lo, hi = ci(b); p = pperm(c, DNS[nk])
    S4b.append(dict(family="F1", source="VNNIC", period="Q1 (2024 start from Jan-Feb only, post hoc)", indicator="d" + nk, N=n, rho=r, lo=lo, hi=hi, p=p, R15_4=lab_corr(lo, hi, p)))
S4b = save("s4b_q1_janfeb", S4b)
S4p = []
for fid in ("F1", "F2"):
    for per in PER25:
        mths = {"Q1": (1, 3), "Q2": (4, 6), "H1": (1, 6)}[per]
        def tot(y): return CT.reindex([pd.Timestamp(y, m, 1) for m in range(mths[0], mths[1] + 1)]).sum().to_numpy(float)
        ratio = np.log(tot(2025) / tot(2024)); c = chg(fid, "VNNIC", per)
        for nk in ("N1", "N2"):
            pr, ex, ey, n = partial(c, DNS[nk], ratio); raw, _ = rho_n(c, DNS[nk])
            if ex is None: continue
            mm = np.isfinite(c) & np.isfinite(DNS[nk]) & np.isfinite(ratio); cc, dd, rr = c[mm], DNS[nk][mm], ratio[mm]; ii = make_idx(len(cc)); bb = np.array([partial(cc[ii[i]], dd[ii[i]], rr[ii[i]])[0] for i in range(B)]); lo, hi = ci(bb)
            rng = np.random.default_rng(U.PSEED); perms = rng.permuted(np.tile(np.arange(n), (NPERM, 1)), axis=1); ps = np.array([np.corrcoef(ex[pi], ey)[0, 1] for pi in perms]); p = (1 + int((np.abs(ps) >= abs(pr) - 1e-12).sum())) / (NPERM + 1)
            S4p.append(dict(family=fid, period=per, indicator="d" + nk, N=n, rho_raw=raw, rho_partial_on_log_test_ratio=pr, lo=lo, hi=hi, p=p, label=lab_corr(lo, hi, p), note="exploratory"))
S4p = save("s4c_partial_participation", S4p)
S4v = []
for fid in FAM:
    for per in PER25:
        cv, co = chg(fid, "VNNIC", per), chg(fid, "Ookla", per); r, n = rho_n(cv, co); lo, hi = ci(fast_rho(cv, co)); S4v.append(dict(family=fid, period=per, N=n, rho_VNNIC_change_vs_Ookla_change=r, lo=lo, hi=hi))
S4v = save("s4d_source_change_agreement", S4v)

# ------------------------------------------------ S5 and summary
S5 = []
for q in (1, 2):
    v, o = vec("F1", "VNNIC", 2025, f"Q{q}"), vec("F1", "Ookla", 2025, f"Q{q}"); ok = np.isfinite(v) & np.isfinite(o) & np.isfinite(N1_25)
    sp_ = np.full(D.n, np.nan); sp_[ok] = stats.rankdata(o[ok]) - stats.rankdata(v[ok]); r, n = rho_n(sp_, N1_25); lo, hi = ci(fast_rho(sp_, N1_25)); p = pperm(sp_, N1_25)
    S5.append(dict(quarter=f"Q{q}", N=n, rho_discrepancy_NSO=r, lo=lo, hi=hi, p=p, R15_5="NSO ordering sides with Ookla" if lo > 0 else ("NSO ordering sides with VNNIC" if hi < 0 else "neither distinguishable")))
S5 = save("s5_discrepancy", S5)
cells = S1[(S1.family == "F1") & (S1.indicator == "N1") & (S1.period.isin(["Q1", "Q2"]))]; npos = int((cells.label == "positive and distinguishable").sum())
nodiff = bool((S2[(S2.family == "F1") & (S2.indicator == "N1") & (S2.period.isin(["Q1", "Q2"]))].R15_2 == "no distinguishable difference").all())
r156 = "2025 replicates 2024" if (npos >= 3 and nodiff) else "2025 differs from 2024"
lab = dict(R15_6=(r156, dict(n_positive_cells=npos, no_difference=nodiff)), headline=cells[["period", "source", "rho", "lo", "hi", "p", "p_holm_headline", "label"]].to_dict("records"))
json.dump({k: str(v) for k, v in lab.items()}, open(R / "labels.json", "w"), indent=1)
rep = ["# X15 report: NSO 2025 external correlates and change 2024 to 2025\n", "Generated by run_x15.py per x15_nso2025_specification.md incl. D1 (hash chain x15_spec_hash.txt). EXPLORATORY; association with adoption is not a measure of accuracy; numbers come from results_x15/*.csv.\n",
       "## Gates\n", md(gt), "\n## S1 associations 2025\n", md(S1), "\n## S2 Delta\n", md(S2), "\n## S3 stability and NSO persistence\n", md(S3), "\n", md(pers), "\n## S4 change\n", md(S4), "\n", md(S4b), "\n", md(S4p), "\n", md(S4v), "\n## S5 discrepancy alignment\n", md(S5), f"\n## Summary\nR15.6: {lab['R15_6']}\n"]
(HERE / "x15_report.md").write_text("\n".join(rep), encoding="utf-8")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(S1[S1.indicator == "N1"].drop(columns=["indicator"]).round(3).to_string(index=False)); print(S2[S2.indicator == "N1"][["family", "period", "rho_V", "rho_O", "delta", "lo", "hi", "R15_2", "delta_adj", "adj_lo", "adj_hi", "R15_2b", "p_holm_headline"]].round(3).to_string(index=False))
print(pd.read_csv(R / "s2_reliability.csv").round(3).to_string(index=False)); print(S3.round(3).to_string(index=False)); print(pers.round(3).to_string(index=False))
print(S4[S4.primary | (S4.family == "F1")].drop(columns=["note", "primary"]).round(3).to_string(index=False)); print(S4b.round(3).to_string(index=False)); print(S4p.round(3).to_string(index=False)); print(S4v.round(3).to_string(index=False)); print(S5.round(3).to_string(index=False)); print("R15.6", lab["R15_6"])
