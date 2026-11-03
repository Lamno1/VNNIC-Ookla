"""X17 per x17_extended_external_specification.md (D1, D2, D3 govern; hash chain x17_spec_hash.txt). Labels applied mechanically.
Usage: python run_x17.py gates   -> runs only the gates (no source-external statistic is computed)
       python run_x17.py         -> full run (stops if a gate fails)
Reuses the frozen helper code of run_x16.py (windows, vectors, bootstrap, ranks) by executing its text segments; nothing in run_x16.py is modified."""
import json, re, sys, unicodedata, hashlib
import upg_common as U
from upg_common import *

_src = (HERE / "run_x16.py").read_text(encoding="utf-8")
_m1 = "# ------------------------------------------------ DTI data and gates"
_m2 = "# ------------------------------------------------ helpers"
_m3 = "# indicators per label year"
_seg1 = _src.split(_m1)[0].replace("U.SEED, U.PSEED = 20261026, 20261027", "U.SEED, U.PSEED = 20261028, 20261029").replace('R = HERE / "results_x16"', 'R = HERE / "results_x17"')
assert "20261028" in _seg1 and "results_x17" in _seg1
exec(compile(_seg1, "run_x16_seg1", "exec"), globals())
_dti = _src.split(_m1)[1]
_seg_dti = "def norm(s):" + _dti.split("def norm(s):", 1)[1].split("g = []")[0]
exec(compile(_seg_dti, "run_x16_dti_loaders", "exec"), globals())
_seg_help = _src.split(_m2)[1].split(_m3)[0]
exec(compile(_seg_help, "run_x16_helpers", "exec"), globals())
GATES_ONLY = len(sys.argv) > 1 and sys.argv[1] == "gates"

# ------------------------------------------------ X17 data
WIN["2024"] = (mlist(2024, 1, 12), 9, [(2024, 1), (2024, 2), (2024, 3), (2024, 4)], 3)
WIN["2024s"] = (mlist(2024, 1, 3) + mlist(2024, 6, 12), 8, [(2024, 1), (2024, 2), (2024, 3), (2024, 4)], 3)  # D1.6 post hoc sensitivity: VNNIC April-May 2024 removed
EN = HERE / "data/external/nso_internet_historical_2021_2023"; ED = HERE / "data/external/dti_historical_recovery_20261010"
nso = pd.read_csv(EN / "NSO_individual_internet_2021_2023_63_provinces.csv", encoding="utf-8-sig")
hh = pd.read_csv(EN / "NSO_household_internet_2023_VDS_63_provinces.csv", encoding="utf-8-sig")
d22 = pd.read_csv(ED / "DTI_2022_main_indices_63_provinces_official_web.csv", encoding="utf-8-sig")
d24 = pd.read_csv(ED / "DTI_2024_main_indices_63_provinces_official_web.csv", encoding="utf-8-sig")
NSOI = {y: dvec(nso[nso.year == y], "province_name", "internet_users_total_pct") for y in (2021, 2022, 2023)}
HH23 = dvec(hh, "province_name", "household_internet_percent")
D22INF, D22TOT = dvec(d22, "province_name", "digital_infrastructure"), dvec(d22, "province_name", "dti_total")
D24INF, D24TOT = dvec(d24, "province_name", "digital_infrastructure"), dvec(d24, "province_name", "dti_total")
DINF = {2021: dvec(r21, "name", "ha_tang"), 2023: dvec(f23, "province", "digital_infrastructure")}  # as run_x16.py
DTOT = {y: dvec(tot, "province", f"dti_{y}") for y in (2021, 2022, 2023)}
DINF4 = {2021: DINF[2021], 2022: D22INF, 2023: DINF[2023], 2024: D24INF}
LPY[2024] = np.log(popf[popf.year == 2024].set_index("province_id_legacy63").loc[D.pids, "pop_thousand"].to_numpy(float))

# ------------------------------------------------ gates
g = []
def G(gate, item, value, target, passed): g.append(dict(gate=gate, item=item, value=value, target=target, passed=bool(passed)))
ptxt = "".join((p_).read_text(encoding="utf-8", errors="ignore") for p_ in (EN / "checksums.json", EN / "checksums_household_addendum_20261010.json", ED / "checksums.json", EN / "provenance.md", ED / "provenance.md"))
for f_, nm in ((EN / "NSO_individual_internet_2021_2023_63_provinces.csv", "NSO individual"), (EN / "NSO_household_internet_2023_VDS_63_provinces.csv", "NSO household 2023"),
               (ED / "DTI_2022_main_indices_63_provinces_official_web.csv", "DTI 2022"), (ED / "DTI_2024_main_indices_63_provinces_official_web.csv", "DTI 2024")):
    sha = hashlib.sha256(open(f_, "rb").read()).hexdigest(); G("G17.1", f"sha256 of {nm} CSV in the provenance/checksum files", sha[:16], "in files", sha in ptxt)
for nm, df_, col in (("NSO individual 2021", nso[nso.year == 2021], "province_name"), ("NSO individual 2022", nso[nso.year == 2022], "province_name"), ("NSO individual 2023", nso[nso.year == 2023], "province_name"),
                     ("NSO household 2023", hh, "province_name"), ("DTI 2022", d22, "province_name"), ("DTI 2024", d24, "province_name")):
    m_, used = pidmap(df_[col]); G("G17.2", f"{nm}: one-to-one mapping to 63 provinces (hue rule {used['hue_rule']}x)", len(m_), 63, len(m_) == 63 and len(set(m_.values())) == 63 and set(m_.values()) == set(D.pids))
names_by_year = [set(nso[nso.year == y].province_name) for y in (2021, 2022, 2023)]
G("G17.2", "NSO individual province names identical in 2021, 2022, 2023 and equal to the household file", int(names_by_year[0] == names_by_year[1] == names_by_year[2] == set(hh.province_name)), 1, names_by_year[0] == names_by_year[1] == names_by_year[2] == set(hh.province_name))
G("G17.3", "NSO individual rows", len(nso), 189, len(nso) == 189 and (nso.groupby("year").size() == 63).all())
G("G17.3", "NSO individual values within [0,100]", float(nso.internet_users_total_pct.max()), 100, ((nso.internet_users_total_pct >= 0) & (nso.internet_users_total_pct <= 100)).all())
G("G17.3", "NSO household 2023 rows", len(hh), 63, len(hh) == 63 and ((hh.household_internet_percent >= 0) & (hh.household_internet_percent <= 100)).all())
for nm, df_ in (("DTI 2022", d22), ("DTI 2024", d24)):
    ok_ = len(df_) == 63 and ((df_.digital_infrastructure > 0) & (df_.digital_infrastructure <= 1)).all() and ((df_.dti_total > 0) & (df_.dti_total <= 1)).all()
    G("G17.3", f"{nm}: 63 rows, Ha tang so and total in (0,1]", len(df_), 63, ok_)
dm = int((np.abs(D22TOT - DTOT[2022]) > 5e-5).sum()); G("G17.4", "DTI 2022 total (official web) equals report-2023 2022 column (mismatches)", dm, 0, dm == 0)
for nm, df_ in (("2022", d22), ("2024", d24)):
    mm_ = int((stats.rankdata(-df_.dti_total.to_numpy(float), method="min") != df_.rank_dti.to_numpy(float)).sum()); G("G17.4", f"DTI {nm}: printed rank equals minimum rank of total (mismatches)", mm_, 0, mm_ == 0)
for src, per, yr, tg in (("VNNIC", "2021", 2021, 0.313), ("Ookla", "2021", 2021, 0.200), ("VNNIC", "2023", 2023, 0.065), ("Ookla", "2023", 2023, 0.447)):
    x_ = vec("F1", src, per); y_ = DINF[yr]; m_ = np.isfinite(x_) & np.isfinite(y_); r_ = sp(x_[m_], y_[m_]); G("G17.5", f"pipeline: X16 headline rho {src} {per} D_inf", float(r_), tg, abs(r_ - tg) < 0.0005)
xv, xo = vec("F1", "VNNIC", "2023"), vec("F1", "Ookla", "2023"); dl_ = sp(xv, DINF[2023]) - sp(xo, DINF[2023]); G("G17.5", "pipeline: X16 Delta 2023 D_inf", float(dl_), -0.382, abs(dl_ + 0.382) < 0.0006)
for src in ("VNNIC", "Ookla"):
    for per in ("2021", "2022", "2023", "2024", "2024s"):
        n_ = int(np.isfinite(vec("F1", src, per)).sum()); G("G17.6", f"F1 {src} window {per}: provinces with a value", n_, 60, n_ >= 60)
for nm, v_ in (("D_inf 2022", D22INF), ("D_inf 2024", D24INF), ("D_tot 2024", D24TOT), ("NSO 2021", NSOI[2021]), ("NSO 2022", NSOI[2022]), ("NSO 2023", NSOI[2023]), ("household 2023", HH23)):
    G("G17.7", f"{nm}: finite values", int(np.isfinite(v_).sum()), 63, np.isfinite(v_).sum() == 63)
for y in (2022, 2024): G("G17.8", f"log population {y} finite for 63 provinces", int(np.isfinite(LPY[y]).sum()), 63, np.isfinite(LPY[y]).all())
for per in ("2022", "2024"):
    for src in ("VNNIC", "Ookla"):
        c_ = np.log(counts(src, per)); G("G17.8", f"log test count {src} window {per} finite", int(np.isfinite(c_).sum()), 60, np.isfinite(c_).sum() >= 60)
def save(name, rows):
    df = pd.DataFrame(rows); df.to_csv(R / f"{name}.csv", index=False); return df
gt = save("gates", g); pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 110); print(gt.to_string())
if not gt.passed.all(): print("GATE FAILURE: stop"); raise SystemExit(1)
if GATES_ONLY: print("gates only: no source-external statistic computed"); raise SystemExit(0)

# ------------------------------------------------ helpers specific to X17 (D2.3, D3.1)
def fast_minrank(x, y):
    if np.isfinite(x).all() and np.isfinite(y).all():
        return corr_rows(stats.rankdata(x[idx], axis=-1, method="min"), stats.rankdata(y[idx], axis=-1, method="min"))
    xs, ys = x[idx], y[idx]; out = np.full(B, np.nan)
    for i in range(B):
        m = np.isfinite(xs[i]) & np.isfinite(ys[i])
        if m.sum() >= 10:
            a = stats.rankdata(xs[i][m], method="min").astype(float); b = stats.rankdata(ys[i][m], method="min").astype(float); a -= a.mean(); b -= b.mean(); den = np.sqrt((a * a).sum() * (b * b).sum()); out[i] = (a * b).sum() / den if den > 0 else np.nan
    return out
def perm_p_min(x, y):
    n = len(x); rx = stats.rankdata(x, method="min").astype(float); ry = stats.rankdata(y, method="min").astype(float); obs = float(corr_rows(rx, ry))
    rng = np.random.default_rng(U.PSEED); perms = rng.permuted(np.tile(np.arange(n), (NPERM, 1)), axis=1); s = corr_rows(rx[None, :], ry[perms])
    return (1 + int((np.abs(s) >= abs(obs) - 1e-12).sum())) / (NPERM + 1)
PAIRS = {2021: [((2021, 2), (2021, 3)), ((2021, 3), (2021, 4)), ((2021, 4), (2022, 1))],
         2022: [((2021, 4), (2022, 1)), ((2022, 1), (2022, 2)), ((2022, 2), (2022, 3)), ((2022, 3), (2022, 4)), ((2022, 4), (2023, 1))],
         2023: [((2022, 4), (2023, 1)), ((2023, 1), (2023, 2)), ((2023, 2), (2023, 3)), ((2023, 3), (2023, 4)), ((2023, 4), (2024, 1))],
         2024: [((2023, 4), (2024, 1)), ((2024, 1), (2024, 2)), ((2024, 2), (2024, 3)), ((2024, 3), (2024, 4)), ((2024, 4), (2025, 1))]}
REL, REL_ROWS = {}, []
def reliability(yr):  # D2.4: pair valid only if the intersection of VNNIC a, VNNIC b, Ookla a, Ookla b has >= 60 provinces; r on that intersection
    if yr in REL: return REL[yr]
    zs = {"VNNIC": [], "Ookla": []}; zb = {"VNNIC": [], "Ookla": []}
    for a, b_ in PAIRS[yr]:
        va, vb, oa, ob = (vec("F1", s, f"{t[0]}Q{t[1]}") for s, t in (("VNNIC", a), ("VNNIC", b_), ("Ookla", a), ("Ookla", b_)))
        m = np.isfinite(va) & np.isfinite(vb) & np.isfinite(oa) & np.isfinite(ob); n = int(m.sum()); ok = n >= 60
        REL_ROWS.append(dict(window=yr, pair=f"{a[0]}Q{a[1]}-{b_[0]}Q{b_[1]}", N_intersection=n, valid=ok))
        if not ok: continue
        for s, (xa, xb) in (("VNNIC", (va, vb)), ("Ookla", (oa, ob))):
            A, Bv = np.where(m, xa, np.nan), np.where(m, xb, np.nan); zs[s].append(np.arctanh(np.clip(sp(A[m], Bv[m]), -0.999, 0.999))); zb[s].append(np.arctanh(np.clip(fast_rho(A, Bv), -0.999, 0.999)))
    nv = len(zs["VNNIC"])
    REL[yr] = None if nv < 3 else {s: (float(np.tanh(np.mean(zs[s]))), np.tanh(np.mean(zb[s], axis=0))) for s in zs} | {"n_pairs": nv}
    return REL[yr]

# ------------------------------------------------ cells
FLO = lambda r_: np.maximum(r_, 0.05)
def cell(fid, per, extname, ext, popyear):
    v, o = vec(fid, "VNNIC", per), vec(fid, "Ookla", per); m = np.isfinite(v) & np.isfinite(o) & np.isfinite(ext); n = int(m.sum())
    V, O, Y = np.where(m, v, np.nan), np.where(m, o, np.nan), np.where(m, ext, np.nan); tshare = ties(Y)[1] if n else np.nan
    rows, boots = [], {}
    for src, X in (("VNNIC", V), ("Ookla", O)):
        if n < 10: rows.append(dict(fid=fid, per=per, ext=extname, source=src, N=n)); continue
        r = sp(X[m], Y[m]); b = fast_rho(X, Y); lo, hi = ci(b); p = perm_p(X[m], Y[m]); bm = fast_minrank(X, Y); lom, him = ci(bm); pm = perm_p_min(X[m], Y[m]); boots[src] = b
        rows.append(dict(fid=fid, per=per, ext=extname, source=src, N=n, ties_share=tshare, rho=r, lo=lo, hi=hi, p=p, rho_min=rho_minrank(X, Y), lo_min=lom, hi_min=him, p_min=pm, popyear=popyear))
    dl = None
    if n >= 10:
        rV, rO = rows[0]["rho"], rows[1]["rho"]; db = boots["VNNIC"] - boots["Ookla"]; lo, hi = ci(db)
        dl = dict(fid=fid, per=per, ext=extname, N_common=n, rho_V=rV, rho_O=rO, delta=rV - rO, lo=lo, hi=hi, p_boot=twosided(db), delta_adj=np.nan, adj_lo=np.nan, adj_hi=np.nan, adj_note="")
        yr = int(per[:4]) if per[:4].isdigit() else None
        if per == "2024s": dl["adj_note"] = "not computed (post hoc sensitivity)"
        elif yr in PAIRS:
            rl = reliability(yr)
            if rl is None: dl["adj_note"] = "insufficient data (fewer than 3 valid pairs)"
            else:
                rVa, rVb = rl["VNNIC"]; rOa, rOb = rl["Ookla"]; dab = boots["VNNIC"] / np.sqrt(FLO(rVb)) - boots["Ookla"] / np.sqrt(FLO(rOb)); alo, ahi = ci(dab)
                dl.update(delta_adj=rV / np.sqrt(max(rVa, 0.05)) - rO / np.sqrt(max(rOa, 0.05)), adj_lo=alo, adj_hi=ahi, adj_note=f"{rl['n_pairs']} pairs")
    return rows, dl

# (family, fid, per, extname, ext vector, population year)
SPEC = []
for per, yr in (("2022", 2022), ("2024", 2024)): SPEC.append(("H17a", "F1", per, "D_inf", DINF4[yr], yr))
for per, yr in (("2021", 2021), ("2022", 2022), ("2023", 2023)): SPEC.append(("H17b", "F1", per, "NSO_ind", NSOI[yr], yr))
SPEC.append(("HH", "F1", "2023", "NSO_hh2023", HH23, 2023))
SPEC.append(("sens", "F1", "2024s", "D_inf", D24INF, 2024))
for per, yr in (("2022", 2022), ("2024", 2024)): SPEC.append(("sec", "F1", per, "D_tot", {2022: D22TOT, 2024: D24TOT}[yr], yr))
for per, yr in (("2021", 2021), ("2023", 2023)): SPEC.append(("pattern", "F1", per, "D_inf", DINF4[yr], yr))
for fid in ("F2", "F4"):
    for per, yr in (("2022", 2022), ("2024", 2024)): SPEC.append(("sec", fid, per, "D_inf", DINF4[yr], yr))
    for per, yr in (("2021", 2021), ("2022", 2022), ("2023", 2023)): SPEC.append(("sec", fid, per, "NSO_ind", NSOI[yr], yr))
S1r, S2r = [], []
for fam, fid, per, en, ev, py in SPEC:
    rows, dl = cell(fid, per, en, ev, py)
    for r in rows: r["family"] = fam
    S1r += rows
    if dl: dl["family"] = fam; S2r.append(dl)
S1 = pd.DataFrame(S1r); S2 = pd.DataFrame(S2r)
for c_ in ("ties_share", "rho", "lo", "hi", "p", "rho_min", "lo_min", "hi_min", "p_min"):
    if c_ not in S1: S1[c_] = np.nan
S1["label_unadj"] = [lab_corr(a, b, c, n) if np.isfinite(a) else "insufficient common provinces" for a, b, c, n in zip(S1.lo, S1.hi, S1.p, S1.N)]
S1["label_min_unadj"] = [lab_corr(a, b, c, n) if np.isfinite(a) else "insufficient common provinces" for a, b, c, n in zip(S1.lo_min, S1.hi_min, S1.p_min, S1.N)]
S1["p_holm"], S1["p_min_holm"] = np.nan, np.nan
for fam in ("H17a", "H17b", "HH"):
    ix = S1[S1.family == fam].index; S1.loc[ix, "p_holm"] = holm(S1.loc[ix, "p"].to_numpy()); S1.loc[ix, "p_min_holm"] = holm(S1.loc[ix, "p_min"].to_numpy())  # D3.1: Holm over all m cells of the family, main and sensitivity
S1["label"] = S1.label_unadj; S1["label_min"] = S1.label_min_unadj
for i in S1[S1.family.isin(["H17a", "H17b", "HH"])].index:
    S1.loc[i, "label"] = lab_corr(S1.loc[i, "lo"], S1.loc[i, "hi"], S1.loc[i, "p_holm"], int(S1.loc[i, "N"])); S1.loc[i, "label_min"] = lab_corr(S1.loc[i, "lo_min"], S1.loc[i, "hi_min"], S1.loc[i, "p_min_holm"], int(S1.loc[i, "N"]))
S1["tie_sensitive"] = (S1.family.isin(["H17a", "H17b", "HH"])) & (S1.label != S1.label_min)
S1["strength"] = [cls(r) if np.isfinite(r) else "" for r in S1.rho]
S1.to_csv(R / "s1_all_cells.csv", index=False)
S1[S1.family.isin(["H17a", "sens", "sec", "pattern"]) & S1.ext.isin(["D_inf", "D_tot"])].to_csv(R / "s1_dinf.csv", index=False)
S1[S1.ext.isin(["NSO_ind", "NSO_hh2023"])].to_csv(R / "s1_nso.csv", index=False)

# Delta (S2): Holm within H17a (2), H17b (3), HH (1)
S2["p_holm"] = np.nan
for fam in ("H17a", "H17b", "HH"):
    ix = S2[S2.family == fam].index; S2.loc[ix, "p_holm"] = holm(S2.loc[ix, "p_boot"].to_numpy())
S2["label_unadj"] = [lab_delta(a, b, n) for a, b, n in zip(S2.lo, S2.hi, S2.N_common)]
S2["label"] = S2.label_unadj
for i in S2[S2.family.isin(["H17a", "H17b", "HH"])].index:
    if S2.loc[i, "label_unadj"] in ("VNNIC more strongly associated", "Ookla more strongly associated") and S2.loc[i, "p_holm"] >= 0.05: S2.loc[i, "label"] = "no distinguishable difference (CI excludes 0 but Holm p >= 0.05)"
S2["label_adj"] = [lab_delta(a, b, n) if np.isfinite(a) else "n/a" for a, b, n in zip(S2.adj_lo, S2.adj_hi, S2.N_common)]
S2.to_csv(R / "s2_delta.csv", index=False); pd.DataFrame(REL_ROWS).to_csv(R / "s2_reliability_pairs.csv", index=False)
rel_tab = pd.DataFrame([dict(window=y, n_pairs=(v["n_pairs"] if v else 0), r_VNNIC=(v["VNNIC"][0] if v else np.nan), r_Ookla=(v["Ookla"][0] if v else np.nan)) for y, v in REL.items()]); rel_tab.to_csv(R / "s2_reliability.csv", index=False)

# S3 pattern, persistence
pat = S1[(S1.ext == "D_inf") & (S1.fid == "F1") & (S1.family.isin(["pattern", "H17a"]))].copy(); pat["year"] = pat.per.str[:4].astype(int); pat = pat.sort_values(["source", "year"])
pat[["source", "year", "N", "rho", "lo", "hi", "p", "label_unadj", "label", "ties_share"]].to_csv(R / "s3_pattern.csv", index=False)
pers = []
for nm, vs in (("D_inf", DINF4), ("NSO_ind", NSOI)):
    ys = sorted(vs)
    for i_, a in enumerate(ys):
        for b_ in ys[i_ + 1:]:
            r, n = rho_n(vs[a], vs[b_]); lo, hi = ci(fast_rho(vs[a], vs[b_])); pers.append(dict(vector=nm, year_a=a, year_b=b_, N=n, rho=r, lo=lo, hi=hi))
pers = save("s3_external_persistence", pers)

# S4 controls (exploratory, D2.5)
S4 = []
for i in S1[S1.family.isin(["H17a", "H17b"]) & (S1.label == "positive and distinguishable")].index:
    r0 = S1.loc[i]; ev = {("D_inf", "2022"): D22INF, ("D_inf", "2024"): D24INF, ("NSO_ind", "2021"): NSOI[2021], ("NSO_ind", "2022"): NSOI[2022], ("NSO_ind", "2023"): NSOI[2023]}[(r0.ext, r0.per)]
    x = vec(r0.fid, r0.source, r0.per)
    for cn, z in (("log population", LPY[int(r0.popyear)]), ("log test count of the window", np.log(counts(r0.source, r0.per)))):
        d_ = pfull(x, ev, z); ok = d_["lo"] > 0 and d_["p"] < 0.05 and d_["N"] >= 60
        S4.append(dict(ext=r0.ext, per=r0.per, source=r0.source, control=cn, rho_raw=r0.rho, rho_partial=d_["rho_partial"], lo=d_["lo"], hi=d_["hi"], p=d_["p"], N=d_["N"],
                       R17_5="persists after the control" if ok else ("unresolved after control: possible scale" if cn == "log population" else "unresolved after control: possible participation"), note="exploratory; selected by result; no causal reading"))
S4 = save("s4_controls", S4)

# S5 discrepancy alignment
S5 = []
for en, per, ev in (("D_inf", "2022", D22INF), ("D_inf", "2024", D24INF), ("NSO_ind", "2021", NSOI[2021]), ("NSO_ind", "2022", NSOI[2022]), ("NSO_ind", "2023", NSOI[2023])):
    v, o = vec("F1", "VNNIC", per), vec("F1", "Ookla", per); ok = np.isfinite(v) & np.isfinite(o) & np.isfinite(ev); s_ = np.full(D.n, np.nan); s_[ok] = stats.rankdata(o[ok]) - stats.rankdata(v[ok])
    r, n = rho_n(s_, ev); lo, hi = ci(fast_rho(s_, ev)); p = pperm(s_, ev)
    S5.append(dict(ext=en, per=per, N=n, rho=r, lo=lo, hi=hi, p=p, R17_6="insufficient common provinces" if n < 60 else "external ordering sides with Ookla" if lo > 0 else ("external ordering sides with VNNIC" if hi < 0 else "neither distinguishable")))
S5 = save("s5_discrepancy", S5)
tie_rows = [dict(vector=nm, n_unique=ties(v)[0], share_in_ties=ties(v)[1], n_at_max=int((v == np.nanmax(v)).sum())) for nm, v in (("D_inf2021", DINF[2021]), ("D_inf2022", D22INF), ("D_inf2023", DINF[2023]), ("D_inf2024", D24INF), ("D_tot2022", D22TOT), ("D_tot2024", D24TOT), ("NSO2021", NSOI[2021]), ("NSO2022", NSOI[2022]), ("NSO2023", NSOI[2023]), ("HH2023", HH23))]
tiet = save("ties", tie_rows)

# summary R17.1 (D1.1: types, no repeat label)
summ = []
for en, per in (("D_inf", "2022"), ("D_inf", "2024"), ("NSO_ind", "2021"), ("NSO_ind", "2022"), ("NSO_ind", "2023")):
    c_ = S1[(S1.ext == en) & (S1.per == per) & (S1.fid == "F1") & S1.family.isin(["H17a", "H17b"])]; pos = list(c_[c_.label == "positive and distinguishable"].source); npos = len(pos)
    base = "associated with both sources" if npos == 2 else (f"associated with one source ({pos[0]})" if npos == 1 else "not resolved")
    sub = S4[(S4.ext == en) & (S4.per == per) & (S4.control != "log population")]; suf = " (may reflect scale/participation)" if len(sub) and sub.R17_5.str.contains("participation").any() else ""
    typ = ("both" if npos == 2 else (f"{pos[0]}-type" if npos == 1 else "neither")) if en == "D_inf" else ""
    d_ = S2[(S2.ext == en) & (S2.per == per) & (S2.fid == "F1")].iloc[0]
    summ.append(dict(external=en, year=per + (" (Decision 405 framework)" if (en == "D_inf" and per == "2024") else ""), N_common=int(c_.N.min()), R17_1=base + suf, D_inf_type=typ, delta_label=d_.label, delta_p_holm=d_.p_holm))
summ = save("summary_R17_1", summ)
json.dump({"R17_1": summ.to_dict("records"), "X16_types_for_reference": {"2021": "VNNIC-type", "2023": "Ookla-type"}, "note": "types are descriptions of association, not accuracy; 2024 uses a different DTI framework (D2.1)"}, open(R / "labels.json", "w"), indent=1, default=str)

# undefined / missing cases
und = []
for _, r in S1.iterrows():
    if r.N < 60 or not np.isfinite(r.rho): und.append(dict(table="S1", cell=f"{r.fid} {r.per} {r.ext} {r.source}", issue=f"N={r.N}, rho={r.rho}"))
for _, r in S2.iterrows():
    if r.adj_note.startswith("insufficient"): und.append(dict(table="S2", cell=f"{r.fid} {r.per} {r.ext}", issue=r.adj_note))
for _, r in pd.DataFrame(REL_ROWS).iterrows():
    if not r.valid: und.append(dict(table="reliability", cell=f"{r.window} {r.pair}", issue=f"intersection N={r.N_intersection} < 60"))
und = save("undefined_or_missing", und if und else [dict(table="-", cell="-", issue="none")])

# ------------------------------------------------ report
disp = S1[S1.family.isin(["H17a", "H17b", "HH", "sens", "sec", "pattern"])]
cols = ["family", "fid", "per", "ext", "source", "N", "rho", "lo", "hi", "p", "p_holm", "label_unadj", "label"]
sens_cols = ["family", "fid", "per", "ext", "source", "N", "ties_share", "rho_min", "lo_min", "hi_min", "p_min", "p_min_holm", "label_min", "tie_sensitive"]
dcols = ["family", "fid", "per", "ext", "N_common", "rho_V", "rho_O", "delta", "lo", "hi", "p_boot", "p_holm", "label_unadj", "label", "delta_adj", "adj_lo", "adj_hi", "adj_note", "label_adj"]
rep = ["# X17 report: DTI Ha tang so 2022/2024, NSO individual Internet 2021-2023, NSO household 2023\n",
       "Generated by run_x17.py per x17_extended_external_specification.md (D1, D2, D3). Spec sha and run sha are in x17_spec_hash.txt. EXPLORATORY; association only; not a measure of accuracy and not a measure of real change. DTI 2024 uses the Decision 405 framework and is not a replication of X16. Holm is applied within each family only, not across X16 and X17. Numbers come from results_x17/*.csv.\n",
       "## Gates\n", md(gt), "\n## Ties of the external vectors\n", md(tiet),
       "\n## S1 correlations (common set; N is the common N; label_unadj is the unadjusted label, label the Holm-based label for H17a, H17b and HH)\n", md(disp[cols]),
       "\n## Tie sensitivity (shown only where the external vector has more than 5 percent of provinces in tied values; all sensitivity results are in s1_all_cells.csv)\n", md(disp[disp.ties_share > 0.05][sens_cols]),
       "\n## S2 Delta VNNIC minus Ookla (common set)\n", md(S2[dcols]), "\n", md(rel_tab), "\n", md(pd.DataFrame(REL_ROWS)),
       "\n## S3 pattern of rho(source, D_inf) by year and persistence of the external vectors\n", md(pat[["source", "year", "N", "rho", "lo", "hi", "p", "label_unadj", "label", "ties_share"]]), "\n", md(pers),
       "\n## S4 controls (exploratory)\n", md(S4), "\n## S5 discrepancy alignment\n", md(S5), "\n## Summary R17.1\n", md(summ),
       "\n## Undefined or missing cases\n", md(und)]
(HERE / "x17_report.md").write_text("\n".join(rep), encoding="utf-8")
pd.set_option("display.max_columns", 40)
print(S1[S1.family.isin(["H17a", "H17b", "HH"])][["family", "per", "ext", "source", "N", "rho", "lo", "hi", "p", "p_holm", "label_unadj", "label", "ties_share", "label_min", "tie_sensitive"]].round(4).to_string(index=False))
print(S2[S2.family.isin(["H17a", "H17b", "HH"])][["family", "per", "ext", "N_common", "delta", "lo", "hi", "p_boot", "p_holm", "label_unadj", "label", "delta_adj", "adj_note"]].round(4).to_string(index=False))
print(summ.to_string(index=False)); print(und.to_string(index=False))
