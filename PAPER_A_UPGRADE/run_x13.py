"""X13 per x13_nso_external_specification.md incl. D1 (hash chain x13_spec_hash.txt). Labels applied mechanically."""
import json, re, unicodedata
import upg_common as U
from upg_common import *
U.SEED, U.PSEED = 20261020, 20261021
U._IDX.clear()

D = Data(with_ext=False)
R = HERE / "results_x13"; R.mkdir(exist_ok=True)
X9 = pd.read_parquet(HERE / "data" / "ookla_x9_province_quarter.parquet"); inv = {v: k for k, v in D.iso.items()}; X9["pid"] = X9.shapeISO.map(inv)
fact = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet"); fact["month"] = pd.to_datetime(fact["month"])
def vpiv(net, col): return fact[fact.network == net].pivot_table(index="month", columns="province_id_legacy63", values=col, aggfunc="first").reindex(columns=D.pids)
FAM = {"F1": (vpiv("ftth", "download"), None), "F2": (vpiv("ftth", "upload"), ("fixed", "ul_median")), "F4": (vpiv("mobile", "download"), ("mobile", "dl_median"))}
def qmonths(y, q): return [pd.Timestamp(y, 3 * (q - 1) + k, 1) for k in (1, 2, 3)]
def Vq(fid, y, q):
    sub = FAM[fid][0].reindex(qmonths(y, q)); ok = sub.notna().sum() >= 2
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Vq_E2(fid, y, q):  # exclude April and May 2024
    ex = {pd.Timestamp(2024, 4, 1), pd.Timestamp(2024, 5, 1)}; rem = [m for m in qmonths(y, q) if m not in ex]
    sub = FAM[fid][0].reindex(rem); ok = sub.notna().sum() >= 1
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Vyear(fid, y):
    sub = FAM[fid][0].reindex([pd.Timestamp(y, k, 1) for k in range(1, 13)]); ok = sub.notna().sum() >= 9
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Oq(fid, y, q):
    if fid == "F1": return D.O[(y, q)]
    kind, col = FAM[fid][1]; g = X9[(X9.kind == kind) & (X9.year == y) & (X9.quarter == q)].set_index("pid")
    a = np.array([g[col].get(p, np.nan) for p in D.pids], float); t = np.array([g.observed_tiles.get(p, np.nan) for p in D.pids], float); return np.where(t >= 10, a, np.nan)
def Oyear(fid, y):
    arr = np.vstack([Oq(fid, y, q) for q in (1, 2, 3, 4)]); ok = np.isfinite(arr).sum(0) >= 3; return np.where(ok, np.nanmedian(arr, axis=0), np.nan)
def save(name, rows):
    df = pd.DataFrame(rows); df.to_csv(R / f"{name}.csv", index=False); return df

# ------------------------------------------------ NSO data and gates
def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower().replace("đ", "d").replace("Đ", "d")); s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("tp.", "").replace("thanh pho", ""); return re.sub(r"[^a-z0-9]", "", s)
nso = pd.read_csv(HERE / "data/external/nso_yearbook2024/nso_yearbook2024_internet_by_province.csv", encoding="utf-8-sig")
popf = pd.read_csv(ROOT / "RED_TEAM_DIAGNOSTICS/population_data/population_province_year_2021_2024.csv")
pop24 = popf[popf.year == 2024].set_index("province_id_legacy63")
key_off = {norm(n): p for p, n in zip(pop24.index, pop24.province_name_official)}
g = []; mp = {}; unmatched = []
for _, r in nso.iterrows():
    k = norm(r.province_nso_name); k = "thuathienhue" if k == "hue" else k
    if k in key_off: mp[r.province_nso_name] = key_off[k]
    else: unmatched.append(r.province_nso_name)
one2one = len(mp) == 63 and len(set(mp.values())) == 63 and set(mp.values()) == set(D.pids)
g.append(dict(gate="G13.1", item=f"name mapping one-to-one 63 (unmatched: {unmatched})", value=len(mp), target=63, passed=bool(one2one)))
x2 = np.array([sp(Vq("F1", 2024, q), Oq("F1", 2024, q)) for q in (1, 2, 3, 4)]); tg = [0.718, 0.248, 0.765, 0.684]
for q in range(4): g.append(dict(gate="G13.2", item=f"F1 W0 2024Q{q+1}", value=float(x2[q]), target=tg[q], passed=abs(x2[q] - tg[q]) < 0.005))
import hashlib
sha = hashlib.sha256(open(HERE / "data/external/nso_yearbook2024/nso_yearbook2024_internet_by_province.csv", "rb").read()).hexdigest()
prov = open(HERE / "data/external/nso_yearbook2024/provenance.md", encoding="utf-8").read(); g.append(dict(gate="G13.3", item="CSV sha256 in provenance.md", value=sha, target="in file", passed=sha in prov))
okp = bool(pop24.pop_thousand.notna().all() and set(pop24.index) == set(D.pids)); g.append(dict(gate="G13.4", item="2024 population for 63 provinces", value=int(pop24.pop_thousand.notna().sum()), target=63, passed=okp))
gt = save("gates", g); print(gt.to_string())
if not gt.passed.all():
    print("GATE FAILURE: stop"); raise SystemExit(1)
NS = {"N1": np.array([nso.set_index("province_nso_name").loc[[n for n, p in mp.items() if p == pid][0], "pct_households_internet_connection_prelim2024"] for pid in D.pids], float),
      "N2": np.array([nso.set_index("province_nso_name").loc[[n for n, p in mp.items() if p == pid][0], "pct_people_using_internet_prelim2024"] for pid in D.pids], float)}
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
    m = np.isfinite(x) & np.isfinite(y); return perm_p(x[m], y[m])
def twosided(b):
    b = b[np.isfinite(b)]; return min(1.0, 2 * min((np.sum(b >= 0) + 1) / (len(b) + 1), (np.sum(b <= 0) + 1) / (len(b) + 1)))
def lab_corr(lo, hi, p): return "positive and distinguishable" if (lo > 0 and p < 0.05) else ("negative and distinguishable" if (hi < 0 and p < 0.05) else "not distinguishable from 0")
def cls(r): return "weak" if abs(r) < 0.30 else ("moderate" if abs(r) <= 0.60 else "strong")
PER = ["Q1", "Q2", "Q3", "Q4", "year"]
def vec(fid, src, per, variant=None):
    if per == "year": return Vyear(fid, 2024) if src == "VNNIC" else Oyear(fid, 2024)
    q = int(per[1]);
    if src == "VNNIC": return Vq_E2(fid, 2024, q) if (variant == "E2" and q == 2) else Vq(fid, 2024, q)
    return Oq(fid, 2024, q)

# ------------------------------------------------ S1
S1 = []; BOOT = {}
for fid in FAM:
    for per in PER:
        for src in ("VNNIC", "Ookla"):
            x = vec(fid, src, per)
            for nk in ("N1", "N2"):
                r, n = rho_n(x, NS[nk]); b = fast_rho(x, NS[nk]); BOOT[(fid, per, src, nk)] = b; lo, hi = ci(b); p = pperm(x, NS[nk])
                S1.append(dict(family=fid, period=per, source=src, indicator=nk, N=n, rho=r, lo=lo, hi=hi, p=p, label=lab_corr(lo, hi, p), strength=cls(r)))
S1 = pd.DataFrame(S1)
H = S1[(S1.family == "F1") & (S1.indicator == "N1") & (S1.period != "year")].index
S1["p_holm_headline"] = np.nan; S1.loc[H, "p_holm_headline"] = holm(S1.loc[H, "p"].to_numpy())
S1.to_csv(R / "s1_associations.csv", index=False)

# ------------------------------------------------ S2 and S2b
def adj_rep(fid, src, bootstrap):
    qs = [(2023, 4), (2024, 1), (2024, 2), (2024, 3), (2024, 4)]
    arr = {t: (Vq(fid, *t) if src == "VNNIC" else Oq(fid, *t)) for t in qs}; zs = []
    for a, b_ in zip(qs[:-1], qs[1:]):
        if bootstrap: r = fast_rho(arr[a], arr[b_])
        else: r = rho_n(arr[a], arr[b_])[0]
        zs.append(np.arctanh(np.clip(r, -0.999, 0.999)))
    return np.tanh(np.mean(zs, axis=0))
REL = {}
for fid in FAM:
    for src in ("VNNIC", "Ookla"):
        REL[(fid, src)] = (float(adj_rep(fid, src, False)), adj_rep(fid, src, True))
save("s2b_reliability", [dict(family=f, source=s, r_2024=v[0], lo=ci(v[1])[0], hi=ci(v[1])[1]) for (f, s), v in REL.items()])
def lab_delta(lo, hi): return "VNNIC more strongly associated" if lo > 0 else ("Ookla more strongly associated" if hi < 0 else "no distinguishable difference")
S2 = []
for fid in FAM:
    for per in PER:
        for nk in ("N1", "N2"):
            sv = S1[(S1.family == fid) & (S1.period == per) & (S1.indicator == nk)].set_index("source")
            bV, bO = BOOT[(fid, per, "VNNIC", nk)], BOOT[(fid, per, "Ookla", nk)]; d = sv.loc["VNNIC", "rho"] - sv.loc["Ookla", "rho"]; db = bV - bO; lo, hi = ci(db)
            rV, rVb = REL[(fid, "VNNIC")]; rO, rOb = REL[(fid, "Ookla")]
            fl = lambda r: np.maximum(r, 0.05)
            adjV, adjO = sv.loc["VNNIC", "rho"] / np.sqrt(max(rV, 0.05)), sv.loc["Ookla", "rho"] / np.sqrt(max(rO, 0.05)); dadj = adjV - adjO
            dab = bV / np.sqrt(fl(rVb)) - bO / np.sqrt(fl(rOb)); alo, ahi = ci(dab)
            S2.append(dict(family=fid, period=per, indicator=nk, rho_V=sv.loc["VNNIC", "rho"], rho_O=sv.loc["Ookla", "rho"], delta=d, lo=lo, hi=hi, p_boot=twosided(db), R13_2=lab_delta(lo, hi),
                           rho_adj_V=adjV, rho_adj_O=adjO, delta_adj=dadj, adj_lo=alo, adj_hi=ahi, R13_2b=lab_delta(alo, ahi)))
S2 = pd.DataFrame(S2); Hd = S2[(S2.family == "F1") & (S2.indicator == "N1") & (S2.period != "year")].index
S2["p_holm_headline"] = np.nan; S2.loc[Hd, "p_holm_headline"] = holm(S2.loc[Hd, "p_boot"].to_numpy()); S2.to_csv(R / "s2_delta.csv", index=False)

# ------------------------------------------------ S3 dip
S3 = []
for nk in ("N1", "N2"):
    for src, variant in (("VNNIC", None), ("Ookla", None), ("VNNIC", "E2")):
        rs, bs = {}, {}
        for q in (1, 2, 3):
            x = vec("F1", src, f"Q{q}", variant); rs[q] = rho_n(x, NS[nk])[0]; bs[q] = fast_rho(x, NS[nk])
        dip = rs[2] - 0.5 * (rs[1] + rs[3]); db = bs[2] - 0.5 * (bs[1] + bs[3]); lo, hi = ci(db)
        S3.append(dict(indicator=nk, source=src + (" (excl Apr-May, post hoc)" if variant else ""), rho_Q1=rs[1], rho_Q2=rs[2], rho_Q3=rs[3], dip=dip, lo=lo, hi=hi, R13_3="Q2 dip present against NSO" if (dip <= -0.15 and hi < 0) else "no Q2 dip by rule"))
S3 = save("s3_q2_dip", S3)

# ------------------------------------------------ S4
S4i = []
for per in ["Q1", "Q2", "Q3", "Q4"]:
    q = int(per[1]); v, o = vec("F1", "VNNIC", per), vec("F1", "Ookla", per); ok = np.isfinite(v) & np.isfinite(o) & np.isfinite(NS["N1"])
    sp_ = np.full(D.n, np.nan); sp_[ok] = stats.rankdata(o[ok]) - stats.rankdata(v[ok]); r, n = rho_n(sp_, NS["N1"]); b = fast_rho(sp_, NS["N1"]); lo, hi = ci(b); p = pperm(sp_, NS["N1"])
    S4i.append(dict(period=per, N=n, rho_discrepancy_NSO=r, lo=lo, hi=hi, p=p, R13_4="NSO ordering sides with Ookla" if lo > 0 else ("NSO ordering sides with VNNIC" if hi < 0 else "neither distinguishable")))
S4i = save("s4i_discrepancy", S4i)
def partial_rho(x, y, z):
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if m.sum() < 10: return np.nan
    rx, ry, rz = stats.rankdata(x[m]), stats.rankdata(y[m]), stats.rankdata(z[m]); X = np.column_stack([np.ones(m.sum()), rz])
    ex = rx - X @ np.linalg.lstsq(X, rx, rcond=None)[0]; ey = ry - X @ np.linalg.lstsq(X, ry, rcond=None)[0]; return float(np.corrcoef(ex, ey)[0, 1])
S4ii = []
for per in ["Q1", "Q2", "Q3", "Q4"]:
    for src in ("VNNIC", "Ookla"):
        x = vec("F1", src, per); pr = partial_rho(x, NS["N1"], LP); pb = np.array([partial_rho(x[idx[i]], NS["N1"][idx[i]], LP[idx[i]]) for i in range(B)]); lo, hi = ci(pb)
        raw = S1[(S1.family == "F1") & (S1.period == per) & (S1.source == src) & (S1.indicator == "N1")].iloc[0]
        if raw.label != "positive and distinguishable": l5 = "not applicable"
        else: l5 = "persists after the scale control" if (lo > 0 or hi < 0) else "association may reflect scale"
        S4ii.append(dict(period=per, source=src, rho_raw=raw.rho, rho_partial=pr, lo=lo, hi=hi, R13_5=l5))
S4ii = save("s4ii_partial", S4ii)
lab = dict(headline=S1.loc[H, ["period", "source", "rho", "lo", "hi", "p", "p_holm_headline", "label"]].to_dict("records"), R13_2_headline=S2.loc[Hd, ["period", "delta", "lo", "hi", "p_holm_headline", "R13_2", "R13_2b"]].to_dict("records"))
json.dump({k: str(v) for k, v in lab.items()}, open(R / "labels.json", "w"), indent=1)
rep = ["# X13 report: association of VNNIC and Ookla 2024 with NSO internet use by province\n", "Generated by run_x13.py per x13_nso_external_specification.md incl. D1 (hash chain x13_spec_hash.txt). EXPLORATORY; association with adoption is not a measure of accuracy; numbers come from results_x13/*.csv.\n",
       "## Gates\n", md(gt), "\n## S1 associations (headline family: F1, N1, quarters, Holm column)\n", md(S1), "\n## S2 Delta and reliability-adjusted Delta\n", md(S2), "\n## Reliability used (adjacent-quarter, pairs touching 2024)\n", md(pd.read_csv(R / "s2b_reliability.csv")),
       "\n## S3 Q2 dip\n", md(S3), "\n## S4(i) discrepancy alignment (not independent of S2)\n", md(S4i), "\n## S4(ii) scale control\n", md(S4ii)]
(HERE / "x13_report.md").write_text("\n".join(rep), encoding="utf-8")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(S1[(S1.indicator == "N1")].drop(columns=["indicator"]).round(3).to_string(index=False)); print(S2[S2.indicator == "N1"][["family", "period", "rho_V", "rho_O", "delta", "lo", "hi", "R13_2", "rho_adj_V", "rho_adj_O", "delta_adj", "adj_lo", "adj_hi", "R13_2b", "p_holm_headline"]].round(3).to_string(index=False))
print(pd.read_csv(R / "s2b_reliability.csv").round(3).to_string(index=False)); print(S3.round(3).to_string(index=False)); print(S4i.round(3).to_string(index=False)); print(S4ii.round(3).to_string(index=False))
