"""Post-shift window analysis, 2023 to 2024 (specification: postshift_specification_20261030.md, written before this run).
Same data accessors, definitions and common province resamples as all_quarter_framework.py. Exploratory; nominal intervals; no p-values."""
import sys, json, hashlib, itertools
from upg_common import *

D = Data(with_ext=True)
idx = make_idx(D.n)
OUT = HERE / "results_postshift_20261030"; OUT.mkdir(exist_ok=True)
Y0, Y1 = 2023, 2024
KEYS = ["sd_level", "sd_log", "cv", "iqr", "p90_p10", "max_min"]


def indicators(a):
    sd = a.std(-1, ddof=1); sdl = np.log(a).std(-1, ddof=1); mean = a.mean(-1)
    q = np.percentile(a, [10, 25, 75, 90], axis=-1)
    return dict(sd_level=sd, sd_log=sdl, cv=sd / mean, iqr=q[2] - q[1], p90_p10=q[3] / q[0], max_min=a.max(-1) / a.min(-1))


def series(q):
    V = {y: D.V(y, q) for y in (Y0, Y1)}; O = {y: D.O[(y, q)] for y in (Y0, Y1)}
    for arr in (*V.values(), *O.values()):
        assert np.isfinite(arr).all() and len(arr) == D.n, (q, "missing values")
    return V, O


def year_series():
    V = {y: D.Vyear(y) for y in (Y0, Y1)}; O = {y: D.Oyear(y) for y in (Y0, Y1)}
    for arr in (*V.values(), *O.values()):
        assert np.isfinite(arr).all() and len(arr) == D.n, "missing year values"
    return V, O


L1, L2, L3, L4 = [], [], [], []
logch = {"VNNIC": {}, "Ookla": {}}
cases = [(q, *series(q)) for q in (1, 2, 3, 4)] + [("year", *year_series())]
for q, V, O in cases:
    dV, dO = V[Y1] - V[Y0], O[Y1] - O[Y0]
    gV = np.median(V[Y1]) / np.median(V[Y0]); gO = np.median(O[Y1]) / np.median(O[Y0])
    bV = np.median(V[Y1][idx], axis=1) / np.median(V[Y0][idx], axis=1)
    bO = np.median(O[Y1][idx], axis=1) / np.median(O[Y0][idx], axis=1)
    lv, hv = ci(bV); lo_, ho_ = ci(bO); ld, hd = ci(np.log(bV) - np.log(bO))
    L1.append(dict(window=q, V_med0=np.median(V[Y0]), V_med1=np.median(V[Y1]), V_ratio=gV, V_lo=lv, V_hi=hv,
                   O_med0=np.median(O[Y0]), O_med1=np.median(O[Y1]), O_ratio=gO, O_lo=lo_, O_hi=ho_,
                   diff_log_ratio=np.log(gV) - np.log(gO), diff_lo=ld, diff_hi=hd,
                   ookla_larger_growth_n=int(((O[Y1] / O[Y0]) > (V[Y1] / V[Y0])).sum()),
                   both_positive=int(((dV > 0) & (dO > 0)).sum()), same_sign=int((np.sign(dV) == np.sign(dO)).sum()), n=D.n))
    # L2
    boots = {}
    for src, arr in (("VNNIC", V), ("Ookla", O)):
        i0, i1 = indicators(arr[Y0]), indicators(arr[Y1]); b0, b1 = indicators(arr[Y0][idx]), indicators(arr[Y1][idx])
        for k in KEYS:
            lb = np.log(b1[k] / b0[k]); lo, hi = ci(lb); boots[(src, k)] = (float(np.log(i1[k] / i0[k])), lb)
            L2.append(dict(window=q, source=src, indicator=k, kind="log_ratio", est=boots[(src, k)][0], lo=lo, hi=hi))
    for k in KEYS:
        a, b = boots[("VNNIC", k)], boots[("Ookla", k)]; lo, hi = ci(a[1] - b[1])
        L2.append(dict(window=q, source="V-O", indicator=k, kind="difference", est=a[0] - b[0], lo=lo, hi=hi))
    # L3
    r0, r1 = sp(V[Y0], O[Y0]), sp(V[Y1], O[Y1])
    d_b = sp_boot(V[Y1], O[Y1]) - sp_boot(V[Y0], O[Y0]); lo, hi = ci(d_b)
    L3.append(dict(window=q, rho_2023=r0, rho_2023_lo=ci(sp_boot(V[Y0], O[Y0]))[0], rho_2023_hi=ci(sp_boot(V[Y0], O[Y0]))[1],
                   rho_2024=r1, rho_2024_lo=ci(sp_boot(V[Y1], O[Y1]))[0], rho_2024_hi=ci(sp_boot(V[Y1], O[Y1]))[1], diff=r1 - r0, diff_lo=lo, diff_hi=hi))
    # L4 (log change of each source; Mbps change too)
    cV, cO = np.log(V[Y1]) - np.log(V[Y0]), np.log(O[Y1]) - np.log(O[Y0])
    for scale, (xv, xo) in (("log", (cV, cO)), ("Mbps", (dV, dO))):
        lo, hi = ci(sp_boot(xv, xo))
        L4.append(dict(window=q, scale=scale, rho=sp(xv, xo), lo=lo, hi=hi))
    if q != "year":
        logch["VNNIC"][q] = cV; logch["Ookla"][q] = cO

# cross-window stability within each source (six pairs among four quarterly log-change vectors)
pairs = list(itertools.combinations((1, 2, 3, 4), 2)); stab = []; mean_boot = {}
for src in ("VNNIC", "Ookla"):
    vals, boots = [], []
    for a, b in pairs:
        r = sp(logch[src][a], logch[src][b]); vals.append(r); boots.append(sp_boot(logch[src][a], logch[src][b]))
        stab.append(dict(source=src, pair="Q%d-Q%d" % (a, b), rho=r))
    mean_boot[src] = np.mean(boots, axis=0); m = float(np.mean(vals)); lo, hi = ci(mean_boot[src])
    stab.append(dict(source=src, pair="mean of six", rho=m, lo=lo, hi=hi, min=float(min(vals)), max=float(max(vals))))
dlo, dhi = ci(mean_boot["VNNIC"] - mean_boot["Ookla"])
dm = [s for s in stab if s["source"] == "VNNIC" and s["pair"] == "mean of six"][0]["rho"] - [s for s in stab if s["source"] == "Ookla" and s["pair"] == "mean of six"][0]["rho"]
stab.append(dict(source="V-O", pair="difference of means", rho=dm, lo=dlo, hi=dhi))

pd.DataFrame(L1).to_csv(OUT / "L1.csv", index=False); pd.DataFrame(L2).to_csv(OUT / "L2.csv", index=False)
pd.DataFrame(L3).to_csv(OUT / "L3.csv", index=False); pd.DataFrame(L4).to_csv(OUT / "L4.csv", index=False); pd.DataFrame(stab).to_csv(OUT / "stability.csv", index=False)

# decision rules from the specification
l1 = pd.DataFrame(L1).set_index("window"); l4 = pd.DataFrame(L4); l4 = l4[(l4.scale == "log") & (l4.window != "year")]
rule1 = bool(dm < 0 and dhi < 0)
signs = np.sign(l4.rho.values); rule2 = bool((signs > 0).any() and (signs < 0).any()) or bool(((l4.lo <= 0) & (l4.hi >= 0)).all())
dq = l1.loc[[1, 2, 3, 4], "diff_log_ratio"].values; rule3 = bool(not (np.all(dq > 0) or np.all(dq < 0)))
rep = dict(spec="postshift_specification_20261030.md", B=B, seed=SEED, n=D.n, window=[Y0, Y1],
           rule1_vnnic_less_stable_retained=rule1, stability_diff_means=dm, stability_diff_ci=[dlo, dhi],
           rule2_no_stable_sign_retained=rule2, L4_log_quarterly=l4[["window", "rho", "lo", "hi"]].to_dict("records"),
           rule3_growth_sign_reversal_retained=rule3, growth_diff_by_quarter=[float(x) for x in dq],
           inputs_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE / "upg_common.py", Path(__file__))})
json.dump(rep, open(OUT / "report.json", "w"), indent=1, default=str)
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
print(pd.DataFrame(L1).round(3).to_string()); print(pd.DataFrame(L3).round(3).to_string()); print(pd.DataFrame(L4).round(3).to_string()); print(pd.DataFrame(stab).round(3).to_string())
print(json.dumps({k: v for k, v in rep.items() if k.startswith("rule")}, indent=1, default=str))
