"""Spatial block bootstrap of the provincial intervals. Specification: spatial_block_spec/SPEC.md
(SHA-256 in SPEC.sha256, written and approved before this run). Same data accessors and statistic definitions as
all_quarter_framework.py, run_x18.py and postshift_*_analysis_20261030.py. Nominal intervals; no p-values."""
import sys, json, hashlib, itertools
from upg_common import *
from paths import GEO, SPEC as SPEC_DIR
from scipy.cluster.hierarchy import linkage, fcluster
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer

D = Data(with_ext=True)
n = D.n
OUT = HERE / "results_spatial_block_20261103"; OUT.mkdir(exist_ok=True)
SPEC = SPEC_DIR
YRS = (2021, 2022, 2023, 2024)
K_NEIGH = 12

# ---------------- blocks
gj = json.load(open(GEO, encoding="utf-8"))
tr = Transformer.from_crs(4326, 32648, always_xy=True)
cent = {}
for f in gj["features"]:
    g = transform(tr.transform, shape(f["geometry"])); c = g.centroid; cent[f["properties"]["shapeISO"]] = (c.x, c.y)
xy = np.array([cent[D.iso[p]] for p in D.pids])
lab_neigh = fcluster(linkage(xy, "ward"), t=K_NEIGH, criterion="maxclust") - 1
assert len(set(lab_neigh)) == K_NEIGH
mp = pd.read_csv(SPEC / "region_mapping_6.csv", dtype={"vnnic_code": str}, encoding="utf-8-sig")
mp_iso = dict(zip(mp.shapeISO, mp.nso_region))
regs = sorted(set(mp_iso.values())); lab_reg = np.array([regs.index(mp_iso[D.iso[p]]) for p in D.pids])
assert len(set(lab_reg)) == 6
blocks = {"neigh12": [np.where(lab_neigh == k)[0] for k in range(K_NEIGH)], "region6": [np.where(lab_reg == k)[0] for k in range(6)]}
pd.DataFrame(dict(province=D.pids, shapeISO=[D.iso[p] for p in D.pids], x_utm=xy[:, 0], y_utm=xy[:, 1], neigh12=lab_neigh,
                  region6=[regs[i] for i in lab_reg])).to_csv(OUT / "block_assignments.csv", index=False, encoding="utf-8-sig")
pd.DataFrame([dict(rule=r, block=i, size=len(b)) for r, bl in blocks.items() for i, b in enumerate(bl)]).to_csv(OUT / "block_sizes.csv", index=False)

# ---------------- arrays
V = {(y, q): D.V(y, q) for y in YRS for q in (1, 2, 3, 4)}
O = {(y, q): D.O[(y, q)] for y in YRS for q in (1, 2, 3, 4)}
Vy = {y: D.Vyear(y) for y in YRS}; Oy = {y: D.Oyear(y) for y in YRS}
V24x2 = D.M.loc[pd.Timestamp(2024, 6, 1)].values.astype(float)
for a in (*V.values(), *O.values(), *Vy.values(), *Oy.values(), V24x2):
    assert np.isfinite(a).all() and len(a) == n
PAIRS = list(itertools.combinations((1, 2, 3, 4), 2))


def spear(a, b):
    ra, rb = stats.rankdata(a), stats.rankdata(b); ra = ra - ra.mean(); rb = rb - rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d > 0 else np.nan


def stat_set(ids):
    s = {}
    med = lambda a: float(np.median(a[ids]))
    # ---- 2021 -> 2024
    for q in (1, 2, 3, 4):
        gV = med(V[(2024, q)]) / med(V[(2021, q)]); gO = med(O[(2024, q)]) / med(O[(2021, q)])
        s[f"A_L1_diff_log_ratio_q{q}"] = np.log(gV) - np.log(gO)
    rho = {(y, q): spear(V[(y, q)][ids], O[(y, q)][ids]) for y in YRS for q in (1, 2, 3, 4)}
    for q in (1, 2, 3, 4):
        s[f"A_L3_change_2024_minus_2021_q{q}"] = rho[(2024, q)] - rho[(2021, q)]
    Am = {y: np.mean([rho[(y, q)] for q in (1, 2, 3, 4)]) for y in YRS}
    Ly = {y: spear(Vy[y][ids], Oy[y][ids]) for y in YRS}
    for y in YRS:
        s[f"A_L3_mean4q_{y}"] = Am[y]; s[f"A_L3_yearlevel_{y}"] = Ly[y]
        for q in (1, 2, 3, 4):
            s[f"A_L3_rho_{y}q{q}"] = rho[(y, q)]
    s["A_L3_mean4q_2021_minus_2024"] = Am[2021] - Am[2024]
    s["A_L3_yearlevel_2021_minus_2024"] = Ly[2021] - Ly[2024]
    lcV = {q: (np.log(V[(2024, q)]) - np.log(V[(2021, q)]))[ids] for q in (1, 2, 3, 4)}
    lcO = {q: (np.log(O[(2024, q)]) - np.log(O[(2021, q)]))[ids] for q in (1, 2, 3, 4)}
    for q in (1, 2, 3, 4):
        s[f"A_L4_log_q{q}"] = spear(lcV[q], lcO[q])
    s["A_L4_log_mean4"] = np.mean([s[f"A_L4_log_q{q}"] for q in (1, 2, 3, 4)])
    s["A_L4_yearlevel"] = spear((np.log(Vy[2024]) - np.log(Vy[2021]))[ids], (np.log(Oy[2024]) - np.log(Oy[2021]))[ids])
    s["A_L4_start2022Q2"] = spear((np.log(V[(2024, 2)]) - np.log(V[(2022, 2)]))[ids], (np.log(O[(2024, 2)]) - np.log(O[(2022, 2)]))[ids])
    R = {}
    for nm, lc in (("V", lcV), ("O", lcO)):
        R[nm] = np.mean([spear(lc[a], lc[b]) for a, b in PAIRS]); s[f"A_stab_{nm}"] = R[nm]
    s["A_stab_diff_O_minus_V"] = R["O"] - R["V"]
    # ---- 2023 -> 2024 (main, and variant without April-May 2024 on the VNNIC side)
    for var in ("main", "xAM"):
        lV, lO = {}, {}
        for q in (1, 2, 3, 4):
            v24 = V24x2 if (var == "xAM" and q == 2) else V[(2024, q)]
            if var == "main":
                gV = med(v24) / med(V[(2023, q)]); gO = med(O[(2024, q)]) / med(O[(2023, q)])
                s[f"B_L1_diff_log_ratio_q{q}"] = np.log(gV) - np.log(gO)
            lV[q] = (np.log(v24) - np.log(V[(2023, q)]))[ids]; lO[q] = (np.log(O[(2024, q)]) - np.log(O[(2023, q)]))[ids]
            s[f"B_{var}_L4_log_q{q}"] = spear(lV[q], lO[q])
        RV = np.mean([spear(lV[a], lV[b]) for a, b in PAIRS]); RO = np.mean([spear(lO[a], lO[b]) for a, b in PAIRS])
        s[f"B_{var}_stab_V"] = RV; s[f"B_{var}_stab_O"] = RO; s[f"B_{var}_stab_diff_V_minus_O"] = RV - RO
    return s


def run(ids_list):
    return pd.DataFrame([stat_set(ids) for ids in ids_list])


# ---------------- point estimates and province-bootstrap reproduction gate
pt = stat_set(np.arange(n)); keys = list(pt)
idx = make_idx(n)
prov = run(list(idx))
chk = []
al3 = pd.read_csv(HERE / "results_allq" / "allq_L3_change.csv"); al1 = pd.read_csv(HERE / "results_allq" / "allq_L1_growth.csv")
for r in al3.itertuples():
    k = f"A_L3_change_2024_minus_2021_q{r.quarter}"; chk.append((k, pt[k], r.diff_2024_minus_2021, *ci(prov[k]), r.lo, r.hi))
for r in al1.itertuples():
    k = f"A_L1_diff_log_ratio_q{r.quarter}"; chk.append((k, pt[k], r.diff_log_ratio, *ci(prov[k]), r.diff_lo, r.diff_hi))
ps = pd.read_csv(HERE / "results_postshift_20261030" / "L4.csv"); ps = ps[(ps.scale == "log") & (ps.window != "year")]
for r in ps.itertuples():
    k = f"B_main_L4_log_q{int(r.window)}"; chk.append((k, pt[k], r.rho, *ci(prov[k]), r.lo, r.hi))
st = pd.read_csv(HERE / "results_postshift_20261030" / "stability.csv"); d = st[st.pair == "difference of means"].iloc[0]
chk.append(("B_main_stab_diff_V_minus_O", pt["B_main_stab_diff_V_minus_O"], d.rho, *ci(prov["B_main_stab_diff_V_minus_O"]), d.lo, d.hi))
s2d = pd.read_csv(HERE / "results_x18" / "s2_difference.csv").iloc[0]
chk.append(("A_stab_diff_O_minus_V", pt["A_stab_diff_O_minus_V"], s2d.diff_O_minus_V, *ci(prov["A_stab_diff_O_minus_V"]), s2d.lo, s2d.hi))
g = pd.DataFrame(chk, columns=["stat", "pt_new", "pt_stored", "lo_new", "hi_new", "lo_stored", "hi_stored"])
g["max_abs_dev"] = np.abs(g[["pt_new", "lo_new", "hi_new"]].values - g[["pt_stored", "lo_stored", "hi_stored"]].values).max(axis=1)
g.to_csv(OUT / "reproduction_gate.csv", index=False)
print(g.round(4).to_string())
assert g.max_abs_dev.max() < 1e-9, "REPRODUCTION GATE FAILED"
print("GATE PASSED: point estimates and province-bootstrap intervals reproduce stored results (max dev %.2e)" % g.max_abs_dev.max(), flush=True)

# ---------------- block bootstraps
res = {"province": prov}
for rule, bl in blocks.items():
    K = len(bl); draws = np.random.default_rng(SEED).integers(0, K, (B, K))
    res[rule] = run([np.concatenate([bl[j] for j in row]) for row in draws])
rows = []
for k in keys:
    r = dict(stat=k, estimate=pt[k])
    for nm, df in res.items():
        lo, hi = ci(df[k])
        r.update({f"{nm}_lo": lo, f"{nm}_hi": hi, f"{nm}_excl0": bool(lo > 0 or hi < 0), f"{nm}_undefined_draws": int(df[k].isna().sum())})
    rows.append(r)
tab = pd.DataFrame(rows); tab.to_csv(OUT / "intervals.csv", index=False)
for nm, df in res.items():
    df.to_csv(OUT / f"draws_{nm}.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print(tab[["stat", "estimate", "province_lo", "province_hi", "neigh12_lo", "neigh12_hi", "region6_lo", "region6_hi"]].round(3).to_string())
json.dump(dict(spec_sha256=open(SPEC / "SPEC.sha256").read().split()[0], B=B, seed=SEED, K_neigh=K_NEIGH,
               block_sizes={r: [len(b) for b in bl] for r, bl in blocks.items()},
               inputs_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE / "upg_common.py", Path(__file__), SPEC / "region_mapping_6.csv")}),
          open(OUT / "run_log.json", "w"), indent=1)
