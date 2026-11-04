"""Dependence range and block extent (AMENDMENT_3.md, C1). Descriptive; uses no statistic of the study."""
import json
from upg_common import *
from paths import GEO
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer

D = Data(with_ext=True)
n = D.n
OUT = HERE / "results_spatial_block_20261103"
YRS = (2021, 2024)
gj = json.load(open(GEO, encoding="utf-8"))
tr = Transformer.from_crs(4326, 32648, always_xy=True)
cent = {f["properties"]["shapeISO"]: transform(tr.transform, shape(f["geometry"])).centroid for f in gj["features"]}
isos = [D.iso[p] for p in D.pids]
xy = np.array([(cent[i].x, cent[i].y) for i in isos]) / 1000.0   # km
dist = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1))

vecs = {"VNNIC": {}, "Ookla": {}}
for q in (1, 2, 3, 4):
    vecs["VNNIC"][f"log2024q{q}"] = np.log(D.V(2024, q)); vecs["Ookla"][f"log2024q{q}"] = np.log(D.O[(2024, q)])
    vecs["VNNIC"][f"chg21_24q{q}"] = np.log(D.V(2024, q)) - np.log(D.V(2021, q))
    vecs["Ookla"][f"chg21_24q{q}"] = np.log(D.O[(2024, q)]) - np.log(D.O[(2021, q)])

BANDS = [(lo, lo + 50) for lo in range(0, 600, 50)]


def moran(z, W):
    z = z - z.mean(); s0 = W.sum()
    return np.nan if s0 == 0 else (len(z) / s0) * (z @ W @ z) / (z @ z)


rng = np.random.default_rng(20261010)
rows = []
for src, d in vecs.items():
    for nm, z in d.items():
        for lo, hi in BANDS:
            W = ((dist > lo) & (dist <= hi)).astype(float) if lo > 0 else ((dist > 0) & (dist <= hi)).astype(float)
            obs = moran(z, W)
            perm = np.array([moran(rng.permutation(z), W) for _ in range(999)])
            rows.append(dict(source=src, vector=nm, band=f"{lo}-{hi}", lo=lo, hi=hi, pairs=int(W.sum() // 2), I=obs,
                             ref_lo=np.nanpercentile(perm, 2.5), ref_hi=np.nanpercentile(perm, 97.5)))
t = pd.DataFrame(rows)
t.to_csv(OUT / "moran_correlogram.csv", index=False)
med = t.groupby(["source", "lo", "hi"]).agg(I=("I", "median"), ref_lo=("ref_lo", "median"), ref_hi=("ref_hi", "median"), pairs=("pairs", "first")).reset_index()
med["inside"] = (med.I >= med.ref_lo) & (med.I <= med.ref_hi)
med.to_csv(OUT / "moran_correlogram_median.csv", index=False)
print(med.round(3).to_string())
rng_out = {}
for src, g in med.groupby("source"):
    g = g.sort_values("lo"); rng_out[src] = None
    ins = g.inside.to_numpy()
    for i in range(len(g)):
        if ins[i:].all():
            rng_out[src] = int(g.hi.iloc[i - 1]) if i > 0 else 0   # last band that is distinguishable from zero
            break
print("dependence range (km, upper edge of the last band outside the reference band):", rng_out)

# block extent
bc = pd.read_csv(OUT / "block_assignments_contig.csv", encoding="utf-8-sig").set_index("shapeISO")
ba = pd.read_csv(OUT / "block_assignments.csv", encoding="utf-8-sig").set_index("shapeISO")
ext = []
for name, lab in [(f"contig{k}", bc.loc[isos, f"contig{k}"].to_numpy()) for k in (8, 10, 12, 15, 20)] + [("region6", ba.loc[isos, "region6"].to_numpy())]:
    e = []
    for c in sorted(set(lab)):
        idx = np.flatnonzero(lab == c)
        if len(idx) >= 3:
            e.append(dist[np.ix_(idx, idx)].max())
    ext.append(dict(grouping=name, blocks_with_3plus=len(e), median_extent_km=float(np.median(e)), min_extent_km=float(np.min(e)), max_extent_km=float(np.max(e))))
ext = pd.DataFrame(ext); ext.to_csv(OUT / "block_extent.csv", index=False)
print(ext.round(0).to_string())
json.dump(dict(range_km=rng_out), open(OUT / "dependence_range.json", "w"))
