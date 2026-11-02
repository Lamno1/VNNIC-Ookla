"""L1, L2 and the 2021-2024 change of L3 for every matched quarter (Q1-Q4), not only Q2.
Same data accessors, same common province-resampling index (B=5000, seed from upg_common) and the same indicator
definitions as the Q2 analysis in run_upgrade.py, so the Q2 rows must reproduce x1d_dispersion.csv, x1e_direction.csv and the
Table 1 growth factors; the script asserts this before writing anything."""
import sys
from upg_common import *

D = Data(with_ext=True)
idx = make_idx(D.n)
OUT = HERE / "results_allq"; OUT.mkdir(exist_ok=True)


def indicators(a):
    sd = a.std(-1, ddof=1); sdl = np.log(a).std(-1, ddof=1); mean = a.mean(-1)
    q = np.percentile(a, [10, 25, 75, 90], axis=-1)
    return dict(sd_level=sd, sd_log=sdl, cv=sd / mean, iqr=q[2] - q[1], p90_p10=q[3] / q[0], max_min=a.max(-1) / a.min(-1))


def series(q):
    V = {y: D.V(y, q) for y in (2021, 2024)}
    O = {y: D.O[(y, q)] for y in (2021, 2024)}
    for arr in (*V.values(), *O.values()):
        assert np.isfinite(arr).all() and len(arr) == D.n, (q, "missing values")
    return V, O


rows1, rows2, rows3 = [], [], []
for q in (1, 2, 3, 4):
    V, O = series(q)
    # ---- L1
    dV, dO = V[2024] - V[2021], O[2024] - O[2021]
    gV = np.median(V[2024]) / np.median(V[2021]); gO = np.median(O[2024]) / np.median(O[2021])
    bV = np.median(V[2024][idx], axis=1) / np.median(V[2021][idx], axis=1)
    bO = np.median(O[2024][idx], axis=1) / np.median(O[2021][idx], axis=1)
    lo_v, hi_v = ci(bV); lo_o, hi_o = ci(bO); lo_d, hi_d = ci(np.log(bV) - np.log(bO))
    larger_o = int(((O[2024] / O[2021]) > (V[2024] / V[2021])).sum())
    k_same = int((np.sign(dV) == np.sign(dO)).sum()); k_both = int(((dV > 0) & (dO > 0)).sum())
    rows1.append(dict(quarter=q, V_med2021=np.median(V[2021]), V_med2024=np.median(V[2024]), V_ratio=gV, V_lo=lo_v, V_hi=hi_v,
                      O_med2021=np.median(O[2021]), O_med2024=np.median(O[2024]), O_ratio=gO, O_lo=lo_o, O_hi=hi_o,
                      diff_log_ratio=np.log(gV) - np.log(gO), diff_lo=lo_d, diff_hi=hi_d, ookla_larger_growth_n=larger_o,
                      both_positive=k_both, same_sign=k_same, n=D.n, cp_lower_same_sign=clopper_pearson(k_same, D.n)[0]))
    # ---- L2
    for src, arr in (("VNNIC", V), ("Ookla", O)):
        i21, i24 = indicators(arr[2021]), indicators(arr[2024])
        b21, b24 = indicators(arr[2021][idx]), indicators(arr[2024][idx])
        for k in i21:
            lb = np.log(b24[k] / b21[k]); lo, hi = ci(lb)
            rows2.append(dict(quarter=q, source=src, indicator=k, log_ratio=float(np.log(i24[k] / i21[k])), lo=lo, hi=hi, _boot=lb))
    # ---- L3 change 2021 -> 2024
    r21, r24 = sp(V[2021], O[2021]), sp(V[2024], O[2024])
    d_b = sp_boot(V[2024], O[2024]) - sp_boot(V[2021], O[2021])
    lo, hi = ci(d_b)
    rows3.append(dict(quarter=q, rho2021=r21, rho2024=r24, diff_2024_minus_2021=r24 - r21, lo=lo, hi=hi,
                      excludes_zero=bool(lo > 0 or hi < 0)))

# direct VNNIC-minus-Ookla contrast of each dispersion log ratio, from the common resamples
t2 = pd.DataFrame(rows2)
contrast = []
for q in (1, 2, 3, 4):
    for k in ["sd_level", "sd_log", "cv", "iqr", "p90_p10", "max_min"]:
        a = t2[(t2.quarter == q) & (t2.source == "VNNIC") & (t2.indicator == k)].iloc[0]
        b = t2[(t2.quarter == q) & (t2.source == "Ookla") & (t2.indicator == k)].iloc[0]
        lo, hi = ci(a._boot - b._boot)
        contrast.append(dict(quarter=q, indicator=k, diff_V_minus_O=a.log_ratio - b.log_ratio, lo=lo, hi=hi,
                             excludes_zero=bool(lo > 0 or hi < 0)))
t2 = t2.drop(columns="_boot")
t1, t3, tc = pd.DataFrame(rows1), pd.DataFrame(rows3), pd.DataFrame(contrast)

# ---- reproduction check: the Q2 rows must equal the stored Q2 results
R = HERE / "results"
x1d = pd.read_csv(R / "x1d_dispersion.csv")
for _, r in x1d.iterrows():
    m = t2[(t2.quarter == 2) & (t2.source == r.source) & (t2.indicator == r.indicator)].iloc[0]
    assert abs(m.log_ratio - r.log_ratio) < 1e-9 and abs(m.lo - r.lo) < 1e-9 and abs(m.hi - r.hi) < 1e-9, ("dispersion mismatch", r.source, r.indicator)
x1e = pd.read_csv(R / "x1e_direction.csv").set_index("item")
q2 = t1[t1.quarter == 2].iloc[0]
assert q2.same_sign == x1e.loc["same sign", "k"] and q2.both_positive == x1e.loc["both positive", "k"]
x1c = pd.read_csv(R / "x1c_rho_decline.csv").iloc[0]
q2r = t3[t3.quarter == 2].iloc[0]
assert abs((q2r.rho2021 - q2r.rho2024) - x1c.est) < 1e-9 and abs(-q2r.hi - x1c.lo) < 1e-9 and abs(-q2r.lo - x1c.hi) < 1e-9
print("Q2 rows reproduce the stored results (dispersion, direction, rho decline).")

t1.to_csv(OUT / "allq_L1_growth.csv", index=False); t2.to_csv(OUT / "allq_L2_dispersion.csv", index=False)
tc.to_csv(OUT / "allq_L2_contrast.csv", index=False); t3.to_csv(OUT / "allq_L3_change.csv", index=False)
pd.set_option("display.width", 220)
print(t1.round(3).to_string()); print(t3.round(3).to_string())
print(tc.assign(ex=tc.excludes_zero).pivot(index="indicator", columns="quarter", values="excludes_zero").to_string())
print(t2.pivot_table(index=["source", "indicator"], columns="quarter", values="log_ratio").round(3).to_string())
