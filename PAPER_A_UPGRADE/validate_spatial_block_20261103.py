"""Second implementation (explicit loops, separate code path) of L1 and L4 block-bootstrap percentiles; SPEC.md section 7."""
import numpy as np, pandas as pd, json
from upg_common import Data, B, SEED
D = Data(with_ext=True); n = D.n
ba = pd.read_csv("results_spatial_block_20261103/block_assignments.csv", encoding="utf-8-sig")
assert list(ba.province) == list(D.pids)
tab = pd.read_csv("results_spatial_block_20261103/intervals.csv").set_index("stat")
def rank(x):
    o = sorted(range(len(x)), key=lambda i: x[i]); r = [0.0] * len(x); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r
def sp(a, b):
    ra, rb = rank(list(a)), rank(list(b)); ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** .5
    return num / den
V = {q: (D.V(2021, q), D.V(2024, q)) for q in (1, 2, 3, 4)}; O = {q: (D.O[(2021, q)], D.O[(2024, q)]) for q in (1, 2, 3, 4)}
dev = 0.0
for rule, col in (("neigh12", "neigh12"), ("region6", "region6")):
    lab = ba[col].tolist(); names = sorted(set(lab)); bl = [[i for i, l in enumerate(lab) if l == nm] for nm in names]; K = len(bl)
    draws = np.random.default_rng(SEED).integers(0, K, (B, K))
    out = {f"A_L4_log_q{q}": [] for q in (1, 2, 3, 4)}; out.update({f"A_L1_diff_log_ratio_q{q}": [] for q in (1, 2, 3, 4)})
    for row in draws:
        ids = [i for j in row for i in bl[j]]
        for q in (1, 2, 3, 4):
            v0, v1, o0, o1 = V[q][0], V[q][1], O[q][0], O[q][1]
            cv = [np.log(v1[i]) - np.log(v0[i]) for i in ids]; co = [np.log(o1[i]) - np.log(o0[i]) for i in ids]
            out[f"A_L4_log_q{q}"].append(sp(cv, co))
            m = lambda a: float(np.median([a[i] for i in ids]))
            out[f"A_L1_diff_log_ratio_q{q}"].append(np.log(m(v1) / m(v0)) - np.log(m(o1) / m(o0)))
    for k, v in out.items():
        lo, hi = np.percentile(v, [2.5, 97.5]); dev = max(dev, abs(lo - tab.loc[k, f"{rule}_lo"]), abs(hi - tab.loc[k, f"{rule}_hi"]))
    print(rule, "done", flush=True)
print("max abs deviation of percentiles (8 statistics x 2 rules):", dev)
json.dump(dict(max_abs_dev=dev, passed=bool(dev < 1e-9), same_team=True), open("results_spatial_block_20261103/validation.json", "w"))
