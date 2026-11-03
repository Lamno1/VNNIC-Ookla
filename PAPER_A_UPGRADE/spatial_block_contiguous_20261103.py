"""Contiguous spatial blocks and sensitivity over the grouping. Specification: reports/spatial_block_bootstrap_20261103/AMENDMENT_2.md
(SHA-256 in AMENDMENT_2.sha256, written before this run). Statistic definitions are executed from the source of
spatial_block_bootstrap_20261103.py (arrays and stat_set), so they cannot drift. Nominal intervals; no p-values."""
import json, hashlib, itertools
from upg_common import *
from scipy.sparse.csgraph import connected_components
from sklearn.cluster import AgglomerativeClustering
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer

D = Data(with_ext=True)
n = D.n
OUT = HERE / "results_spatial_block_20261103"
SPEC = ROOT / "reports" / "spatial_block_bootstrap_20261103"
YRS = (2021, 2022, 2023, 2024)
KS = (8, 10, 12, 15, 20)

src = open(HERE / "spatial_block_bootstrap_20261103.py", encoding="utf-8").read()
a = src.index("# ---------------- arrays"); b = src.index("# ---------------- point estimates")
exec(compile(src[a:b], "stat_definitions", "exec"))

# ---------------- adjacency (A1) and contiguous blocks (A2)
gj = json.load(open(r"D:\Q1_RESEARCH\GIS_DERIVED\CANONICAL_ADM1_63.geojson", encoding="utf-8"))
tr = Transformer.from_crs(4326, 32648, always_xy=True)
geom = {f["properties"]["shapeISO"]: transform(tr.transform, shape(f["geometry"])).buffer(0) for f in gj["features"]}
isos = [D.iso[p] for p in D.pids]
xy = np.array([(geom[i].centroid.x, geom[i].centroid.y) for i in isos])
A = np.zeros((n, n), int)
for i in range(n):
    for j in range(i + 1, n):
        if geom[isos[i]].intersects(geom[isos[j]]):
            A[i, j] = A[j, i] = 1
nc, _ = connected_components(A)
assert nc == 1 and A.sum() // 2 == 135, (nc, A.sum() // 2)

lab = {}
for k in KS:
    l = AgglomerativeClustering(n_clusters=k, linkage="ward", connectivity=A).fit_predict(xy)
    for c in range(k):   # every block must be a connected set of provinces
        m = np.where(l == c)[0]
        assert connected_components(A[np.ix_(m, m)])[0] == 1
    lab[k] = l
pd.DataFrame({"province": D.pids, "shapeISO": isos, **{f"contig{k}": lab[k] for k in KS}}).to_csv(OUT / "block_assignments_contig.csv", index=False, encoding="utf-8-sig")
pd.DataFrame([dict(k=k, block=c, size=int((lab[k] == c).sum())) for k in KS for c in range(k)]).to_csv(OUT / "block_sizes_contig.csv", index=False)
print({k: sorted(np.bincount(lab[k]).tolist()) for k in KS})

# ---------------- bootstrap (A5)
pt = stat_set(np.arange(n)); keys = list(pt)
ref = pd.read_csv(OUT / "intervals.csv").set_index("stat")
assert max(abs(pt[k] - ref.loc[k, "estimate"]) for k in keys) < 1e-9
res = {}
for k in KS:
    bl = [np.where(lab[k] == c)[0] for c in range(k)]
    draws = np.random.default_rng(SEED).integers(0, k, (B, k))
    res[k] = run([np.concatenate([bl[j] for j in row]) for row in draws])
    res[k].to_csv(OUT / f"draws_contig{k}.csv", index=False)
rows = []
for key in keys:
    r = dict(stat=key, estimate=pt[key])
    for k in KS:
        lo, hi = ci(res[k][key])
        r.update({f"contig{k}_lo": lo, f"contig{k}_hi": hi, f"contig{k}_excl0": bool(lo > 0 or hi < 0), f"contig{k}_undefined": int(res[k][key].isna().sum())})
    for nm, c in (("neigh12", "ward12"), ("region6", "region6")):
        r.update({f"{c}_lo": ref.loc[key, f"{nm}_lo"], f"{c}_hi": ref.loc[key, f"{nm}_hi"], f"{c}_excl0": bool(ref.loc[key, f"{nm}_excl0"])})
    r["province_lo"] = ref.loc[key, "province_lo"]; r["province_hi"] = ref.loc[key, "province_hi"]; r["province_excl0"] = bool(ref.loc[key, "province_excl0"])
    names = [f"contig{k}" for k in KS] + ["ward12", "region6"]
    r["n_groupings_excl0"] = int(sum(r[f"{g}_excl0"] for g in names)); r["n_groupings"] = len(names)
    r["sign_of_estimate"] = int(np.sign(pt[key]))
    r["groupings_same_sign_interval"] = int(sum(1 for g in names if r[f"{g}_excl0"] and np.sign(r[f"{g}_lo"] + r[f"{g}_hi"]) == np.sign(pt[key])))
    rows.append(r)
tab = pd.DataFrame(rows); tab.to_csv(OUT / "intervals_contig.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
show = ["A_L1_diff_log_ratio_q1", "A_L1_diff_log_ratio_q2", "A_L1_diff_log_ratio_q3", "A_L1_diff_log_ratio_q4",
        "A_L3_change_2024_minus_2021_q1", "A_L3_change_2024_minus_2021_q2", "A_L3_change_2024_minus_2021_q3", "A_L3_change_2024_minus_2021_q4",
        "A_L4_log_q1", "A_L4_log_q2", "A_L4_log_q3", "A_L4_log_q4", "A_stab_diff_O_minus_V", "B_L1_diff_log_ratio_q1",
        "B_main_L4_log_q4", "B_main_stab_diff_V_minus_O", "B_xAM_stab_diff_V_minus_O"]
t = tab.set_index("stat").loc[[s for s in show if s in tab.stat.values]]
print(t[["estimate", "contig12_lo", "contig12_hi", "n_groupings_excl0", "n_groupings"]].round(3).to_string())
json.dump(dict(amendment2_sha256=open(SPEC / "AMENDMENT_2.sha256").read().split()[0], B=B, seed=SEED, KS=KS,
               block_sizes={str(k): sorted(np.bincount(lab[k]).tolist()) for k in KS},
               inputs_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE / "upg_common.py", Path(__file__), HERE / "spatial_block_bootstrap_20261103.py")}),
          open(OUT / "run_log_contig.json", "w"), indent=1)
