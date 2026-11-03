"""X16 per x16_dti_specification.md incl. D1 (hash chain x16_spec_hash.txt). Labels applied mechanically.
Usage: python run_x16.py gates   -> runs only the gates (no source-DTI statistic is computed)
       python run_x16.py         -> full run (stops if a gate fails)"""
import json, re, sys, unicodedata, hashlib
import upg_common as U
from upg_common import *
sys.stdout.reconfigure(encoding="utf-8")
GATES_ONLY = len(sys.argv) > 1 and sys.argv[1] == "gates"
U.SEED, U.PSEED = 20261026, 20261027
U._IDX.clear()

D = Data(with_ext=True)
R = HERE / "results_x16"; R.mkdir(exist_ok=True)
X9 = pd.read_parquet(HERE / "data" / "ookla_x9_province_quarter.parquet"); inv = {v: k for k, v in D.iso.items()}; X9["pid"] = X9.shapeISO.map(inv)
fact = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet"); fact["month"] = pd.to_datetime(fact["month"])
def vpiv(net, col): return fact[fact.network == net].pivot_table(index="month", columns="province_id_legacy63", values=col, aggfunc="first").reindex(columns=D.pids)
FAM = {"F1": (vpiv("ftth", "download"), None), "F2": (vpiv("ftth", "upload"), ("fixed", "ul_median")), "F4": (vpiv("mobile", "download"), ("mobile", "dl_median"))}
CT = vpiv("ftth", "value_raw")
def mlist(y, a, b): return [pd.Timestamp(y, m, 1) for m in range(a, b + 1)]
def Vmonths(fid, months, minm):
    sub = FAM[fid][0].reindex(months); ok = sub.notna().sum() >= minm
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Oq(fid, y, q):
    if fid == "F1": return D.O.get((y, q), np.full(D.n, np.nan))
    kind, col = FAM[fid][1]; g = X9[(X9.kind == kind) & (X9.year == y) & (X9.quarter == q)].set_index("pid")
    if not len(g): return np.full(D.n, np.nan)
    a = np.array([g[col].get(p, np.nan) for p in D.pids], float); t = np.array([g.observed_tiles.get(p, np.nan) for p in D.pids], float); return np.where(t >= 10, a, np.nan)
def Oquarters(fid, qs, minq):
    arr_ = np.vstack([Oq(fid, y, q) for y, q in qs]); ok = np.isfinite(arr_).sum(0) >= minq
    with np.errstate(all="ignore"): med = np.nanmedian(arr_, axis=0)
    return np.where(ok, med, np.nan)
# fixed windows (D1 governs where it differs from the text of the specification)
WIN = {"2021": (mlist(2021, 4, 12), 7, [(2021, 2), (2021, 3), (2021, 4)], 2),
       "2022": (mlist(2022, 1, 12), 9, [(2022, 1), (2022, 2), (2022, 3), (2022, 4)], 3),
       "2023": (mlist(2023, 1, 12), 9, [(2023, 1), (2023, 2), (2023, 3), (2023, 4)], 3),
       "2021H2": (mlist(2021, 7, 12), 4, [(2021, 3), (2021, 4)], 2)}
def Vq(fid, y, q): return Vmonths(fid, mlist(y, 3 * (q - 1) + 1, 3 * (q - 1) + 3), 2)
def vec(fid, src, per):
    """per: a window key of WIN or a quarter string like '2021Q2'."""
    if per in WIN:
        mo, mm, qs, mq = WIN[per]; return Vmonths(fid, mo, mm) if src == "VNNIC" else Oquarters(fid, qs, mq)
    y, q = int(per[:4]), int(per[5]); return Vq(fid, y, q) if src == "VNNIC" else Oq(fid, y, q)
def counts(src, per):
    mo, mm, qs, mq = WIN[per]
    if src == "VNNIC": return CT.reindex(mo).mean().to_numpy(float)
    arr_ = np.vstack([D.OT.get(t, np.full(D.n, np.nan)) for t in qs]); return np.where(np.isfinite(arr_).any(0), np.nansum(arr_, axis=0), np.nan)
def save(name, rows):
    df = pd.DataFrame(rows); df.to_csv(R / f"{name}.csv", index=False); return df

# ------------------------------------------------ DTI data and gates
def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower().replace("đ", "d")); s = "".join(c for c in s if unicodedata.category(c) != "Mn"); s = s.replace("tp.", "").replace("thanh pho", ""); return re.sub(r"[^a-z0-9]", "", s)
ext = HERE / "data/external/dti_2021_2023"
r21 = pd.read_csv(ext / "dti2021_report2021_province_indices.csv", encoding="utf-8-sig")
f23 = pd.read_csv(ext / "DTI_2023_main_indices_63_provinces.csv", encoding="utf-8-sig")
tot = pd.read_csv(ext / "DTI_total_2021_2023_63_provinces_report2023.csv", encoding="utf-8-sig")
popf = pd.read_csv(ROOT / "RED_TEAM_DIAGNOSTICS/population_data/population_province_year_2021_2024.csv")
key_off = {norm(n): p for p, n in zip(popf[popf.year == 2024].province_id_legacy63, popf[popf.year == 2024].province_name_official)}
def pidmap(names):
    out, used = {}, {"hue_rule": 0}
    for nm in names:
        k = norm(nm)
        if k == "hue": k = "thuathienhue"; used["hue_rule"] += 1
        if k in key_off: out[nm] = key_off[k]
    return out, used
def dvec(df, namecol, valcol):
    m, _ = pidmap(df[namecol]); s = pd.Series(df[valcol].astype(float).to_numpy(), index=[m.get(n) for n in df[namecol]]); return np.array([s.get(p, np.nan) for p in D.pids], float)
g = []
def G(gate, item, value, target, passed): g.append(dict(gate=gate, item=item, value=value, target=target, passed=bool(passed)))
# G16.1 hashes
prov = open(ext / "provenance.md", encoding="utf-8").read()
for f in ["dti2021_report2021_province_indices.csv", "DTI_2023_main_indices_63_provinces.csv", "DTI_total_2021_2023_63_provinces_report2023.csv", "DTI_total_2020_2023_63_provinces.csv", "QD_922_infrastructure_components.csv"]:
    sha = hashlib.sha256(open(ext / f, "rb").read()).hexdigest(); G("G16.1", f"sha256 of {f} in provenance.md", sha[:16], "in file", sha in prov)
# G16.2 mapping
for nm, df, col in (("report2021", r21, "name"), ("report2023_main", f23, "province"), ("report2023_total", tot, "province")):
    m, used = pidmap(df[col]); G("G16.2", f"{nm}: one-to-one mapping to 63 provinces (hue rule used {used['hue_rule']}x)", len(m), 63, len(m) == 63 and len(set(m.values())) == 63 and set(m.values()) == set(D.pids))
if not all(x["passed"] for x in g if x["gate"] == "G16.2"):
    gt = save("gates", g); print(gt.to_string()); print("GATE FAILURE: stop"); raise SystemExit(1)
DINF = {2021: dvec(r21, "name", "ha_tang"), 2023: dvec(f23, "province", "digital_infrastructure")}
DTOT21A = dvec(r21, "name", "dti")  # report-2021 value, primary for the 2021 cross-section
DTOT = {y: dvec(tot, "province", f"dti_{y}") for y in (2021, 2022, 2023)}  # report-2023 values
# G16.3
diff = np.abs(DTOT[2021] - DTOT21A); n_eq = int((diff < 1e-9).sum()); n_1e4 = int((np.abs(diff - 1e-4) < 1e-9).sum())
named = {key_off[k] for k in ("khanhhoa", "backan", "caobang")}; dp = {p for p, d_ in zip(D.pids, diff) if d_ > 1e-9}
G("G16.3", "2021 total: report-2023 equals report-2021 for 60 provinces", n_eq, 60, n_eq == 60)
G("G16.3", "2021 total: exactly three provinces (Khanh Hoa, Bac Kan, Cao Bang) differ by 0.0001", n_1e4, 3, n_1e4 == 3 and dp == named)
for y, tg in ((2021, 0.4014), (2022, 0.5787), (2023, 0.6783)): G("G16.3", f"mean DTI total {y} (report 2023)", float(np.mean(DTOT[y])), tg, abs(np.mean(DTOT[y]) - tg) < 5e-5)
G("G16.3", "mean DTI total 2021 (report 2021)", float(np.mean(DTOT21A)), 0.4014, abs(np.mean(DTOT21A) - 0.4014) < 5e-5)
G("G16.3", "mean Ha tang so 2021", float(np.mean(DINF[2021])), 0.4680, abs(np.mean(DINF[2021]) - 0.4680) < 5e-5)
tm = {nm: pidmap(tot.province)[0] for nm in ("x",)}["x"]
for y in (2021, 2022, 2023):
    pr = np.array([float(tot.set_index("province").loc[n, f"rank_{y}"]) for n in tot.province]); sc = tot[f"dti_{y}"].to_numpy(float)
    G("G16.3", f"printed rank {y} equals minimum rank of the score (mismatches)", int((stats.rankdata(-sc, method="min") != pr).sum()), 0, (stats.rankdata(-sc, method="min") == pr).all())
for (a, b), tg in (((2021, 2022), 0.809), ((2022, 2023), 0.861), ((2021, 2023), 0.726)):
    r = sp(DTOT[a], DTOT[b]); G("G16.3", f"rank correlation of DTI total {a}-{b}", float(r), tg, abs(r - tg) < 0.002)
# G16.4 pipeline: matched Q2 agreement
for y, tg in ((2021, 0.5424), (2022, 0.4879), (2023, 0.2963)):
    v = D.vq2[y]; o = D.fq2["ookla_tile_median_download_mbps"][y]; m = np.isfinite(v) & np.isfinite(o); r = sp(v[m], o[m]); G("G16.4", f"matched Q2 VNNIC-Ookla Spearman {y}", float(r), tg, abs(r - tg) < 0.0005)
# G16.5 coverage
for src in ("VNNIC", "Ookla"):
    for per in ("2021", "2023"):
        n = int(np.isfinite(vec("F1", src, per)).sum()); G("G16.5", f"F1 {src} window {per}: provinces with a value", n, 60, n >= 60)
# G16.6 components and ranges
comp = pd.read_csv(ext / "QD_922_infrastructure_components.csv", encoding="utf-8-sig"); G("G16.6", "seven components sum to 100", float(comp.max_points.sum()), 100, len(comp) == 7 and comp.max_points.sum() == 100)
for y in (2021, 2023): G("G16.6", f"Ha tang so {y} in (0,1) for 63 provinces", int(((DINF[y] > 0) & (DINF[y] < 1)).sum()), 63, ((DINF[y] > 0) & (DINF[y] < 1)).all())
# G16.7 (D1.7) misalignment checks
rk5 = r21.r_ha_tang_table5.to_numpy(float); G("G16.7", "2021: Table 5 Ha tang so rank equals value-derived minimum rank (mismatches)", int((stats.rankdata(-r21.ha_tang.to_numpy(float), method="min") != rk5).sum()), 0, (stats.rankdata(-r21.ha_tang.to_numpy(float), method="min") == rk5).all())
pr23 = f23["rank"].to_numpy(float); sc23 = f23["dti"].to_numpy(float); G("G16.7", "2023 main-index table: printed DTI rank equals minimum rank of its dti column (mismatches)", int((stats.rankdata(-sc23, method="min") != pr23).sum()), 0, (stats.rankdata(-sc23, method="min") == pr23).all())
# descriptive (not a gate): does the DTI 2023 text mention 98 component indices
t23 = Path("D:/Q1_RESEARCH/SOURCE_ACQUISITION_20261009/DTI_2023.txt")
if t23.exists():
    _t = re.sub(r"\s+", " ", unicodedata.normalize("NFC", t23.read_text(encoding="utf-8", errors="ignore")))
    G("descriptive", "DTI 2023 text: occurrences of '98 chỉ số thành phần' (not a gate)", len(re.findall(r"98 chỉ số thành phần", _t)), "n/a", True)
    G("descriptive", "DTI 2023 text: occurrences of 'Phụ lục I Quyết định số 922/QĐ-BTTTT' (not a gate)", len(re.findall(r"Phụ lục I Quyết định số 922/QĐ-BTTTT", _t)), "n/a", True)
gt = save("gates", g); pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 110); print(gt.to_string())
if not gt.passed.all(): print("GATE FAILURE: stop"); raise SystemExit(1)
if GATES_ONLY: print("gates only: no source-DTI statistic computed"); raise SystemExit(0)

# ------------------------------------------------ helpers
LPY = {y: np.log(popf[popf.year == y].set_index("province_id_legacy63").loc[D.pids, "pop_thousand"].to_numpy(float)) for y in (2021, 2022, 2023)}
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
def lab_corr(lo, hi, p, n=63):
    if n < 60: return "insufficient common provinces"
    return "positive and distinguishable" if (lo > 0 and p < 0.05) else ("negative and distinguishable" if (hi < 0 and p < 0.05) else "not distinguishable from 0")
def cls(r): return "weak" if abs(r) < 0.30 else ("moderate" if abs(r) <= 0.60 else "strong")
def twosided(b):
    b = b[np.isfinite(b)]; return min(1.0, 2 * min((np.sum(b >= 0) + 1) / (len(b) + 1), (np.sum(b <= 0) + 1) / (len(b) + 1)))
def lab_delta(lo, hi, n=63):
    if n < 60: return "insufficient common provinces"
    return "VNNIC more strongly associated" if lo > 0 else ("Ookla more strongly associated" if hi < 0 else "no distinguishable difference")
def partial(x, y, z):
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if m.sum() < 10: return np.nan, None, None, 0
    rx, ry, rz = stats.rankdata(x[m]), stats.rankdata(y[m]), stats.rankdata(z[m]); X = np.column_stack([np.ones(m.sum()), rz])
    ex = rx - X @ np.linalg.lstsq(X, rx, rcond=None)[0]; ey = ry - X @ np.linalg.lstsq(X, ry, rcond=None)[0]; return float(np.corrcoef(ex, ey)[0, 1]), ex, ey, int(m.sum())
def pfull(x, y, z):
    pr, ex, ey, n = partial(x, y, z)
    if ex is None: return dict(rho_partial=np.nan, lo=np.nan, hi=np.nan, p=np.nan, N=n)
    mm = np.isfinite(x) & np.isfinite(y) & np.isfinite(z); cc, dd, rr = x[mm], y[mm], z[mm]; ii = make_idx(len(cc)); bb = np.array([partial(cc[ii[i]], dd[ii[i]], rr[ii[i]])[0] for i in range(B)]); lo, hi = ci(bb)
    rng = np.random.default_rng(U.PSEED); perms = rng.permuted(np.tile(np.arange(n), (NPERM, 1)), axis=1); ps = np.array([np.corrcoef(ex[pi], ey)[0, 1] for pi in perms]); p = (1 + int((np.abs(ps) >= abs(pr) - 1e-12).sum())) / (NPERM + 1)
    return dict(rho_partial=pr, lo=lo, hi=hi, p=p, N=n)
def ties(v): u, c = np.unique(v[np.isfinite(v)], return_counts=True); return int(len(u)), float(c[c > 1].sum() / np.isfinite(v).sum())
def rho_minrank(x, y):
    m = np.isfinite(x) & np.isfinite(y); a = stats.rankdata(x[m], method="min"); b = stats.rankdata(y[m], method="min"); return float(np.corrcoef(a, b)[0, 1])  # Pearson on min-rank vectors, no re-ranking

# indicators per label year: name -> (vector); D_tot_r23 = report-2023 value of the 2021 total (sensitivity)
IND = {2021: {"D_inf": DINF[2021], "D_tot": DTOT21A, "D_tot_r23": DTOT[2021]}, 2022: {"D_tot": DTOT[2022]}, 2023: {"D_inf": DINF[2023], "D_tot": DTOT[2023]}}
PERS = [("2021", 2021), ("2022", 2022), ("2023", 2023), ("2021H2", 2021)] + [(f"2021Q{q}", 2021) for q in (2, 3, 4)] + [(f"2023Q{q}", 2023) for q in (1, 2, 3, 4)]
tie_rows = [dict(vector=f"{k}{y}", n_unique=ties(v)[0], share_in_ties=ties(v)[1]) for y, d_ in IND.items() for k, v in d_.items()]; save("ties", tie_rows)

# ------------------------------------------------ S1
S1, BOOT = [], {}
for fid in FAM:
    for per, yr in PERS:
        if per == "2021H2" and fid != "F1": continue
        for src in ("VNNIC", "Ookla"):
            x = vec(fid, src, per)
            for nk, y in IND[yr].items():
                if nk == "D_tot_r23" and not (fid == "F1" and per == "2021"): continue
                r, n = rho_n(x, y); b = fast_rho(x, y); BOOT[(fid, per, src, nk)] = b; lo, hi = ci(b); p = pperm(x, y)
                S1.append(dict(family=fid, period=per, year=yr, source=src, indicator=nk, N=n, rho=r, lo=lo, hi=hi, p=p, label=lab_corr(lo, hi, p, n), strength=cls(r),
                               headline=bool(fid == "F1" and nk == "D_inf" and per in ("2021", "2023")), rho_minrank_sens=rho_minrank(x, y) if (nk == "D_inf" and ties(y)[1] > 0.05) else np.nan))
S1 = pd.DataFrame(S1); H = S1[S1.headline].index; S1["p_holm_headline"] = np.nan; S1.loc[H, "p_holm_headline"] = holm(S1.loc[H, "p"].to_numpy()); S1["label_unadjusted"] = S1["label"]
for i in H: S1.loc[i, "label"] = lab_corr(S1.loc[i, "lo"], S1.loc[i, "hi"], S1.loc[i, "p_holm_headline"], int(S1.loc[i, "N"]))  # D2.3: headline label uses the Holm-adjusted p
S1.to_csv(R / "s1_associations.csv", index=False)
expl = S1[~S1.headline]; n_pos_expl = int((expl.label == "positive and distinguishable").sum())

# ------------------------------------------------ S2 (D1.3 pairs)
PAIRS = {"2021": [((2021, 2), (2021, 3)), ((2021, 3), (2021, 4)), ((2021, 4), (2022, 1))],
         "2023": [((2022, 4), (2023, 1)), ((2023, 1), (2023, 2)), ((2023, 2), (2023, 3)), ((2023, 3), (2023, 4)), ((2023, 4), (2024, 1))]}
def qv(src, t): return vec("F1", src, f"{t[0]}Q{t[1]}")
REL = {}
for per, prs in PAIRS.items():
    ok = [pr for pr in prs if all(np.isfinite(qv(s, t)).sum() >= 60 for s in ("VNNIC", "Ookla") for t in pr)]
    for s in ("VNNIC", "Ookla"):
        zs_b = [np.arctanh(np.clip(fast_rho(qv(s, a), qv(s, b_)), -0.999, 0.999)) for a, b_ in ok]; zs_p = [np.arctanh(np.clip(rho_n(qv(s, a), qv(s, b_))[0], -0.999, 0.999)) for a, b_ in ok]
        REL[(per, s)] = (float(np.tanh(np.mean(zs_p))), np.tanh(np.mean(zs_b, axis=0)), len(ok))
save("s2_reliability", [dict(window=per, source=s, r=v[0], lo=ci(v[1])[0], hi=ci(v[1])[1], n_pairs=v[2]) for (per, s), v in REL.items()])
S2 = []
for fid in FAM:
    for per, yr in PERS:
        for nk in IND[yr]:
            if (fid, per, "VNNIC", nk) not in BOOT: continue
            sv = S1[(S1.family == fid) & (S1.period == per) & (S1.indicator == nk)].set_index("source"); bV, bO = BOOT[(fid, per, "VNNIC", nk)], BOOT[(fid, per, "Ookla", nk)]
            dlt = sv.loc["VNNIC", "rho"] - sv.loc["Ookla", "rho"]; db = bV - bO; lo, hi = ci(db); row = dict(family=fid, period=per, indicator=nk, rho_V=sv.loc["VNNIC", "rho"], rho_O=sv.loc["Ookla", "rho"], delta=dlt, lo=lo, hi=hi, p_boot=twosided(db), R16_2=lab_delta(lo, hi, int(min(sv.loc["VNNIC", "N"], sv.loc["Ookla", "N"]))), delta_adj=np.nan, adj_lo=np.nan, adj_hi=np.nan, R16_2b="")
            if fid == "F1" and per in ("2021", "2023"):
                rV, rVb, _ = REL[(per, "VNNIC")]; rO, rOb, _ = REL[(per, "Ookla")]; fl = lambda r_: np.maximum(r_, 0.05)
                dab = bV / np.sqrt(fl(rVb)) - bO / np.sqrt(fl(rOb)); alo, ahi = ci(dab); row.update(delta_adj=sv.loc["VNNIC", "rho"] / np.sqrt(max(rV, 0.05)) - sv.loc["Ookla", "rho"] / np.sqrt(max(rO, 0.05)), adj_lo=alo, adj_hi=ahi, R16_2b=lab_delta(alo, ahi, int(min(sv.loc["VNNIC", "N"], sv.loc["Ookla", "N"]))))
            S2.append(row)
S2 = pd.DataFrame(S2); Hd = S2[(S2.family == "F1") & (S2.indicator == "D_inf") & (S2.period.isin(["2021", "2023"]))].index
S2["p_holm_headline"] = np.nan; S2.loc[Hd, "p_holm_headline"] = holm(S2.loc[Hd, "p_boot"].to_numpy()); S2["R16_2_unadjusted"] = S2["R16_2"]
for i in Hd:
    if S2.loc[i, "R16_2"] in ("VNNIC more strongly associated", "Ookla more strongly associated") and S2.loc[i, "p_holm_headline"] >= 0.05: S2.loc[i, "R16_2"] = "no distinguishable difference (CI excludes 0 but Holm p >= 0.05)"  # D2.3
S2.to_csv(R / "s2_delta.csv", index=False)

# ------------------------------------------------ S3 stability (D1.1: D_tot report-2023 values for both years)
S3 = []
for nk, d21, d23 in (("D_inf", DINF[2021], DINF[2023]), ("D_tot", DTOT[2021], DTOT[2023])):
    for src in ("VNNIC", "Ookla"):
        x21, x23 = vec("F1", src, "2021"), vec("F1", src, "2023"); r21_, n21 = rho_n(x21, d21); r23_, n23 = rho_n(x23, d23); db = fast_rho(x23, d23) - fast_rho(x21, d21); lo, hi = ci(db); nn = min(n21, n23)
        S3.append(dict(indicator=nk, source=src, rho_2021=r21_, rho_2023=r23_, stab=r23_ - r21_, lo=lo, hi=hi, N_min=nn, R16_3="insufficient common provinces" if nn < 60 else "stronger in 2023" if lo > 0 else ("weaker in 2023" if hi < 0 else "not distinguishable"), note="D_inf compares two reports (composition not verified identical)" if nk == "D_inf" else ""))
S3 = save("s3_stability", S3)
pers = save("s3_dti_persistence", [dict(indicator=nk, rho_2021_2023=rho_n(a, b)[0], lo=ci(fast_rho(a, b))[0], hi=ci(fast_rho(a, b))[1]) for nk, a, b in (("D_inf", DINF[2021], DINF[2023]), ("D_tot_r23", DTOT[2021], DTOT[2023]))])

# ------------------------------------------------ S4 change (D1.1, D1.2)
CH = {src: np.log(vec("F1", src, "2023")) - np.log(vec("F1", src, "2021")) for src in ("VNNIC", "Ookla")}
LV21 = {src: np.log(vec("F1", src, "2021")) for src in ("VNNIC", "Ookla")}
DCH = {"D_tot": (DTOT[2023] - DTOT[2021], DTOT[2021], "primary"), "D_inf": (DINF[2023] - DINF[2021], DINF[2021], "secondary: two reports")}
S4, S4p = [], []
for nk, (dc, base, note) in DCH.items():
    for src in ("VNNIC", "Ookla"):
        c = CH[src]; r, n = rho_n(c, dc); b = fast_rho(c, dc); lo, hi = ci(b); p = pperm(c, dc)
        S4.append(dict(source=src, indicator="change " + nk, N=n, rho=r, lo=lo, hi=hi, p=p, R16_1=lab_corr(lo, hi, p, n), note=note + "; exploratory; VNNIC 2021 start is in the i-Speed ramp window"))
        for zn, z in (("DTI 2021 score", base), ("own 2021 log level", LV21[src])):
            d_ = pfull(c, dc, z); S4p.append(dict(source=src, indicator="change " + nk, control=zn, rho_raw=r, rho_partial=d_["rho_partial"], lo=d_["lo"], hi=d_["hi"], p=d_["p"], N=d_["N"], label=lab_corr(d_["lo"], d_["hi"], d_["p"], d_["N"]), note="exploratory"))
S4 = save("s4_change", S4); S4p = save("s4b_partial_baseline", S4p)
cv, co = CH["VNNIC"], CH["Ookla"]; r, n = rho_n(cv, co); lo, hi = ci(fast_rho(cv, co)); S4v = save("s4c_source_change_agreement", [dict(N=n, rho_VNNIC_change_vs_Ookla_change=r, lo=lo, hi=hi)])

# ------------------------------------------------ S5 controls and discrepancy
S5 = []
for per, yr in (("2021", 2021), ("2023", 2023)):
    for nk, y in IND[yr].items():
        if nk == "D_tot_r23": continue
        for src in ("VNNIC", "Ookla"):
            x = vec("F1", src, per); raw = S1[(S1.family == "F1") & (S1.period == per) & (S1.source == src) & (S1.indicator == nk)].iloc[0]
            for cn, z in (("log population", LPY[yr]), ("log test count of the window", np.log(counts(src, per)))):
                d_ = pfull(x, y, z); pos_raw = raw.label == "positive and distinguishable"; part_ok = d_["lo"] > 0 and d_["p"] < 0.05 and d_["N"] >= 60
                if not pos_raw: lab = "not applicable"
                else: lab = ("persists after the control" if part_ok else ("association may reflect scale" if cn == "log population" else "association may reflect participation") if d_["lo"] <= 0 else "persists after the control")
                S5.append(dict(window=per, indicator=nk, source=src, control=cn, rho_raw=raw.rho, raw_label=raw.label, rho_partial=d_["rho_partial"], lo=d_["lo"], hi=d_["hi"], p=d_["p"], N=d_["N"], R16_5=lab))
S5 = save("s5_controls", S5)
S5d = []
for per, yr in (("2021", 2021), ("2023", 2023)):
    v, o = vec("F1", "VNNIC", per), vec("F1", "Ookla", per); y = IND[yr]["D_inf"]; ok = np.isfinite(v) & np.isfinite(o) & np.isfinite(y)
    s_ = np.full(D.n, np.nan); s_[ok] = stats.rankdata(o[ok]) - stats.rankdata(v[ok]); r, n = rho_n(s_, y); lo, hi = ci(fast_rho(s_, y)); p = pperm(s_, y)
    S5d.append(dict(window=per, N=n, rho_discrepancy_DInf=r, lo=lo, hi=hi, p=p, R16_4="insufficient common provinces" if n < 60 else "DTI ordering sides with Ookla" if lo > 0 else ("DTI ordering sides with VNNIC" if hi < 0 else "neither distinguishable")))
S5d = save("s5b_discrepancy", S5d)

# ------------------------------------------------ summary R16.6 (D1.6)
summ = []
for per in ("2021", "2023"):
    cells = S1[(S1.headline) & (S1.period == per)]; npos = int((cells.label == "positive and distinguishable").sum())
    base = "associated with both sources" if npos == 2 else ("associated with one source" if npos == 1 else "not resolved")
    pos_srcs = list(cells[cells.label == "positive and distinguishable"].source); sub = S5[(S5.window == per) & (S5.indicator == "D_inf") & (S5.source.isin(pos_srcs))]
    suf = []
    if (sub[sub.control == "log population"].R16_5 == "association may reflect scale").any(): suf.append("scale")
    if (sub[sub.control != "log population"].R16_5 == "association may reflect participation").any(): suf.append("participation")
    d2 = S2[(S2.family == "F1") & (S2.indicator == "D_inf") & (S2.period == per)].iloc[0]
    summ.append(dict(window=per, n_positive_sources=npos, R16_6=base + (f" (may reflect {'/'.join(suf)})" if suf else ""), R16_2=d2.R16_2, R16_2b=d2.R16_2b))
summ = save("summary_R16_6", summ)
json.dump({"R16_6": summ.to_dict("records"), "exploratory_S1_cells": int(len(expl)), "n_positive_distinguishable_exploratory": n_pos_expl, "note": "cells are dependent; no chance benchmark is claimed (D2.4)"}, open(R / "labels.json", "w"), indent=1, default=str)
rep = ["# X16 report: DTI 2021-2023 external correlates\n", "Generated by run_x16.py per x16_dti_specification.md incl. D1 (hash chain x16_spec_hash.txt). EXPLORATORY; association with a composite index is not a measure of accuracy; numbers come from results_x16/*.csv.\n",
       "## Gates\n", md(gt), "\n## Ties\n", md(pd.read_csv(R / "ties.csv")), "\n## S1 associations\n", md(S1), f"\n(exploratory cells: {len(expl)}; labelled positive and distinguishable: {n_pos_expl}; cells are dependent and no chance benchmark is claimed)\n", "\n## S2 reliability and Delta\n", md(pd.read_csv(R / "s2_reliability.csv")), "\n", md(S2),
       "\n## S3 stability and persistence\n", md(S3), "\n", md(pers), "\n## S4 change\n", md(S4), "\n", md(S4p), "\n", md(S4v), "\n## S5 controls and discrepancy\n", md(S5), "\n", md(S5d), "\n## Summary R16.6\n", md(summ)]
(HERE / "x16_report.md").write_text("\n".join(rep), encoding="utf-8")
pd.set_option("display.max_columns", 30)
print(S1[S1.headline].round(3).to_string(index=False)); print(S2[S2.p_holm_headline.notna()].round(3).to_string(index=False)); print(summ.to_string(index=False)); print("exploratory cells", len(expl), "positive and distinguishable", n_pos_expl)
