"""X9 per x9_replication_specification.md (hash chain x9_spec_hash.txt). Labels applied mechanically."""
import json
import upg_common as U
from upg_common import *
U.SEED, U.PSEED = 20261014, 20261015
U._IDX.clear()

D = Data(with_ext=True)
R = HERE / "results_x9"; R.mkdir(exist_ok=True)
X9 = pd.read_parquet(HERE / "data" / "ookla_x9_province_quarter.parquet")
inv = {v: k for k, v in D.iso.items()}
X9["pid"] = X9.shapeISO.map(inv)
fact = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet"); fact["month"] = pd.to_datetime(fact["month"])
tabs = {}
def vpiv(net, col):
    return fact[fact.network == net].pivot_table(index="month", columns="province_id_legacy63", values=col, aggfunc="first").reindex(columns=D.pids)
VM = {(net, col): vpiv(net, col) for net in ("ftth", "mobile") for col in ("download", "upload", "ping", "value_raw")}
def save(name, rows):
    df = pd.DataFrame(rows); df.to_csv(R / f"{name}.csv", index=False); return df
def Vq(net, col, y, q):
    sub = VM[(net, col)].reindex([pd.Timestamp(y, 3 * (q - 1) + k, 1) for k in (1, 2, 3)]); ok = sub.notna().sum() >= 2
    return np.where(ok.values, sub.median().values, np.nan).astype(float)
def Oq(kind, col, y, q, floor=True):
    g = X9[(X9.kind == kind) & (X9.year == y) & (X9.quarter == q)].set_index("pid")
    a = np.array([g[col].get(p, np.nan) for p in D.pids], float)
    if floor:
        t = np.array([g.observed_tiles.get(p, np.nan) for p in D.pids], float); a = np.where(t >= 10, a, np.nan)
    return a

# ------------------------------------------------ gates
g = []
old = D.oq.set_index(["year", "quarter", "shapeISO"]).ookla_tile_median_download_mbps
okq = True
for y in range(2021, 2025):
    for q in (1, 2, 3, 4):
        new = X9[(X9.kind == "fixed") & (X9.year == y) & (X9.quarter == q)].set_index("shapeISO").dl_median
        both = pd.concat([new, old.loc[(y, q)]], axis=1, keys=["n", "o"]).dropna()
        k = int(((both.n - both.o).abs() <= 0.01).sum()); okq &= k >= 60
        g.append(dict(gate="G9.1", item=f"fixed {y}Q{q}", value=k, target=60, passed=k >= 60))
cnt = X9.groupby(["kind", "year", "quarter"]).agg(n_prov=("shapeISO", "nunique"), tiles=("observed_tiles", "sum"), tests=("total_tests", "sum")).reset_index()
cnt.to_csv(R / "g92_tile_counts.csv", index=False)
g.append(dict(gate="G9.2", item="all kind-quarters assign 63 provinces", value=int((cnt.n_prov == 63).sum()), target=len(cnt), passed=bool((cnt.n_prov == 63).all())))
fam_ok = {}
for net in ("ftth", "mobile"):
    f = fact[(fact.network == net) & (fact.year.between(2021, 2024))]
    for col in ("upload", "ping"):
        s = float(f[col].notna().mean()); g.append(dict(gate="G9.3", item=f"{net} {col} non-missing share", value=s, target=0.95, passed=s >= 0.95)); fam_ok[(net, col)] = s >= 0.95
    s = float((f.value_raw >= 30).mean()); g.append(dict(gate="G9.4", item=f"{net} value_raw>=30 share", value=s, target=0.95, passed=s >= 0.95))
gt = save("gates", g); print(gt.to_string())
if not gt[gt.gate.isin(["G9.1", "G9.2"])].passed.all():
    print("GATE FAILURE G9.1/G9.2: stop"); raise SystemExit(1)

# ------------------------------------------------ families
FAM = {"F1": ("fixed download", "ftth", "download", "fixed", "dl_median"), "F2": ("fixed upload", "ftth", "upload", "fixed", "ul_median"), "F3": ("fixed latency", "ftth", "ping", "fixed", "lat_median"),
       "F4": ("mobile download", "mobile", "download", "mobile", "dl_median"), "F5": ("mobile upload", "mobile", "upload", "mobile", "ul_median"), "F6": ("mobile latency", "mobile", "ping", "mobile", "lat_median")}
TQ = [(y, q) for y in range(2021, 2025) for q in (1, 2, 3, 4)]
idx63 = make_idx(D.n)

def fast_rho(xs, ys):  # xs, ys: (B, n) with NaN; row-wise spearman on finite pairs
    out = np.full(xs.shape[0], np.nan)
    for i in range(xs.shape[0]):
        m = np.isfinite(xs[i]) & np.isfinite(ys[i])
        if m.sum() >= 10:
            a = stats.rankdata(xs[i][m]); b = stats.rankdata(ys[i][m]); a = a - a.mean(); b = b - b.mean(); den = np.sqrt((a * a).sum() * (b * b).sum())
            out[i] = (a * b).sum() / den if den > 0 else np.nan
    return out
def cell(x, y):
    m = np.isfinite(x) & np.isfinite(y); n = int(m.sum())
    if n < 10:
        return dict(N=n, rho=np.nan)
    return dict(N=n, rho=sp(x[m], y[m]))
def boot_cell(x, y): return fast_rho(x[idx63], y[idx63])

summ = []; allcells = {}; changecells = {}
def run_family(fid, floor=True, tag=""):
    name, net, vcol, kind, ocol = FAM[fid]
    Vs = {t: Vq(net, vcol, *t) for t in TQ}; Os = {t: Oq(kind, ocol, *t, floor=floor) for t in TQ}
    # S1 cells and bootstrap
    cells = [cell(Vs[t], Os[t]) for t in TQ]; bcols = [boot_cell(Vs[t], Os[t]) for t in TQ]; Bm = np.column_stack(bcols)
    valid = [c["N"] >= 50 and np.isfinite(c["rho"]) for c in cells]
    rhos = np.array([c["rho"] for c in cells])
    s1 = float(np.nanmedian(rhos[valid])) if any(valid) else np.nan
    s1b = np.nanmedian(np.where(np.array(valid)[None, :], Bm, np.nan), axis=1); s1lo, s1hi = ci(s1b)
    # S2
    rng_y = []
    for yi in range(4):
        v = [rhos[yi * 4 + qi] for qi in range(4) if valid[yi * 4 + qi]]
        if len(v) >= 2: rng_y.append(max(v) - min(v))
    s2 = float(np.median(rng_y)) if rng_y else np.nan
    # S3
    ch = []
    for y0 in (2021, 2022, 2023):
        for q in (1, 2, 3, 4):
            dv = np.log(Vs[(2024, q)]) - np.log(Vs[(y0, q)]); do = np.log(Os[(2024, q)]) - np.log(Os[(y0, q)]); c = cell(dv, do); ch.append(dict(start=y0, q=q, **c))
    chd = pd.DataFrame(ch); vch = chd[(chd.N >= 50) & chd.rho.notna()]
    neg = int((vch.rho < 0).sum()); medc = float(vch.rho.median()) if len(vch) else np.nan
    lab3 = "robustly negative" if (neg >= 10 and medc <= -0.10) else ("robustly positive" if neg <= 2 and len(vch) >= 10 else "sign unstable")
    # S4
    def w0(y, q): return cells[TQ.index((y, q))]["rho"]
    d4 = w0(2024, 2) - 0.5 * (w0(2024, 1) + w0(2024, 3))
    b4 = Bm[:, TQ.index((2024, 2))] - 0.5 * (Bm[:, TQ.index((2024, 1))] + Bm[:, TQ.index((2024, 3))]); l4, h4 = ci(b4)
    dip = bool(np.isfinite(d4) and d4 <= -0.25 and h4 < 0)
    # S5
    sign = -1 if vcol == "ping" else 1
    v21, v24, o21, o24 = Vs[(2021, 2)], Vs[(2024, 2)], Os[(2021, 2)], Os[(2024, 2)]
    dV, dO = sign * (np.log(v24) - np.log(v21)), sign * (np.log(o24) - np.log(o21)); m = np.isfinite(dV) & np.isfinite(dO)
    k_same = int((np.sign(dV[m]) == np.sign(dO[m])).sum()); lo_cp, hi_cp = clopper_pearson(k_same, int(m.sum()))
    def cvr(a24, a21):
        mm = np.isfinite(a24) & np.isfinite(a21); A, Bq = a24[mm], a21[mm]; f = lambda z: z.std(-1, ddof=1) / z.mean(-1); bi = make_idx(len(A))
        return float(np.log(f(A) / f(Bq))), ci(np.log(f(A[bi]) / f(Bq[bi])))
    cvV, cvVc = cvr(v24, v21); cvO, cvOc = cvr(o24, o21)
    # S6
    rV = float(np.nanmedian(Vq(net, vcol, 2025, 2) / Vq(net, vcol, 2024, 4))); rO = float(np.nanmedian(Oq(kind, ocol, 2025, 2, floor) / Oq(kind, ocol, 2024, 4, floor)))
    s6 = "VNNIC jump not mirrored" if (rV >= 1.5 and rO < 1.25) else ("shared increase" if (rV >= 1.25 and rO >= 1.25) else "inconclusive")
    cls = "weak" if s1 < 0.30 else ("moderate" if s1 <= 0.60 else "strong")
    allcells[fid + tag] = pd.DataFrame([dict(family=fid + tag, year=t[0], q=t[1], **c) for t, c in zip(TQ, cells)])
    changecells[fid + tag] = chd.assign(family=fid + tag)
    summ.append(dict(family=fid + tag, name=name + (" (no floor)" if tag else ""), S1_median=s1, S1_lo=s1lo, S1_hi=s1hi, level_class=cls, S2_spread=s2, temporal="sensitive" if s2 >= 0.20 else "stable",
                     S3_neg_cells=neg, S3_n_cells=len(vch), S3_median=medc, change_label=lab3, S4_Q2dip=d4, S4_lo=l4, S4_hi=h4, dip_present=dip,
                     same_sign_k=k_same, same_sign_n=int(m.sum()), same_sign_cp_lo=lo_cp, CV_logratio_V=cvV, CV_V_lo=cvVc[0], CV_V_hi=cvVc[1], CV_logratio_O=cvO, CV_O_lo=cvOc[0], CV_O_hi=cvOc[1],
                     ratio_V=rV, ratio_O=rO, S6=s6, W0_2024=[round(w0(2024, q), 3) for q in (1, 2, 3, 4)], W0_2023=[round(w0(2023, q), 3) for q in (1, 2, 3, 4)]))

for fid in FAM:
    name, net, vcol, kind, ocol = FAM[fid]
    if vcol in ("upload", "ping") and not fam_ok.get((net, vcol), False):
        summ.append(dict(family=fid, name=name + " DROPPED (gate G9.3)")); continue
    run_family(fid)
run_family("F1", floor=False, tag="_nofloor")
S = save("x9_summary", summ)
pd.concat(allcells.values()).to_csv(R / "x9_level_cells.csv", index=False); pd.concat(changecells.values()).to_csv(R / "x9_change_cells.csv", index=False)

# R9.5
ref = S[S.family == "F1"].iloc[0]; others = S[S.family.isin(["F2", "F3", "F4", "F5", "F6"]) & S.S1_median.notna()]
n_level = int((others.level_class == ref.level_class).sum()); n_time = int((others.temporal == ref.temporal).sum()); n_change = int((others.change_label == ref.change_label).sum()); m_ = len(others)
differ = int(((others.level_class != ref.level_class) | (others.change_label != ref.change_label)).sum())
if n_level >= 4 and n_time >= 4 and n_change >= 4 and m_ == 5: verdict = "general across metrics and technology"
elif differ >= 3: verdict = "specific to fixed download"
else: verdict = "partly general"
dips = S[S.get("dip_present", pd.Series(dtype=bool)) == True].family.tolist() if "dip_present" in S else []
rep = ["# X9 report: replication across metrics and technology\n", "Generated by run_x9.py per x9_replication_specification.md (hash chain x9_spec_hash.txt). Numbers come from results_x9/*.csv; labels are mechanical.\n",
       "## Gates\n", md(gt), "\n## Tile counts per technology and quarter\n", md(cnt), "\n## Summary per family\n", md(S.drop(columns=[c for c in ("W0_2024", "W0_2023") if c in S.columns])), "\n## W0 profile 2023 and 2024 (Q1..Q4)\n",
       md(S[["family", "name", "W0_2023", "W0_2024"]].astype(str)) if "W0_2024" in S else "", f"\n## R9.5\nReference F1: class {ref.level_class}, temporal {ref.temporal}, change {ref.change_label}. Replicating F2-F6: level {n_level}/{m_}, temporal {n_time}/{m_}, change {n_change}/{m_}; families differing in level or change: {differ}.\n\nVerdict: **{verdict}**.\n",
       f"\nR9.4 families with Q2-2024 dip present: {dips}\n"]
(HERE / "x9_report.md").write_text("\n".join(rep), encoding="utf-8")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
print(S.drop(columns=[c for c in ("W0_2024", "W0_2023") if c in S.columns]).round(3).to_string())
print(S[["family", "W0_2023", "W0_2024"]].to_string())
print("VERDICT:", verdict, "| level", n_level, "time", n_time, "change", n_change, "differ", differ, "| dips", dips)
