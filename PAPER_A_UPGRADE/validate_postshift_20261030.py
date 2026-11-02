"""Second implementation of the post-shift analyses (main 2023-2024 and the variant without April-May 2024).
Reads the saved input tables directly with pandas and scipy; does not use Data, corr_rows, sp, sp_boot or ci from upg_common.
Compares every point estimate and the percentile intervals of the headline quantities with the saved result files."""
from pathlib import Path
import itertools, json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
B, SEED, N_EXPECTED = 5000, 20261010, 63

v = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet"); v = v[v.network == "ftth"].copy()
v["month"] = pd.to_datetime(v.month); v["year"] = v.month.dt.year; v["mon"] = v.month.dt.month
q = pd.concat([pd.read_parquet(ROOT / "RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet"),
               pd.read_parquet(HERE / "data/ookla_province_quarter_ext.parquet")]).drop_duplicates(["shapeISO", "year", "quarter"], keep="first")
lookup = pd.read_parquet(ROOT / "data/processed/vnnic_q2_validation_2021_2024.parquet")[["province_id_legacy63", "shapeISO"]].drop_duplicates()
q = q.merge(lookup, on="shapeISO", validate="many_to_one")
pids = sorted(lookup.province_id_legacy63.unique()); assert len(pids) == N_EXPECTED


def vq(y, qq, months=None):
    mm = months if months is not None else [3 * (qq - 1) + k for k in (1, 2, 3)]
    s = v[(v.year == y) & (v.mon.isin(mm))].groupby("province_id_legacy63").download.agg(["median", "count"])
    s = s[s["count"] >= (1 if len(mm) == 1 else 2)]
    return s["median"].reindex(pids).values.astype(float)


def vyear(y, months):
    s = v[(v.year == y) & (v.mon.isin(months))].groupby("province_id_legacy63").download.agg(["median", "count"])
    s = s[s["count"] >= 9]
    return s["median"].reindex(pids).values.astype(float)


def oq(y, qq):
    s = q[(q.year == y) & (q.quarter == qq)].set_index("province_id_legacy63").ookla_tile_median_download_mbps
    return s.reindex(pids).values.astype(float)


def oyear(y):
    a = np.vstack([oq(y, k) for k in (1, 2, 3, 4)]); ok = np.isfinite(a).sum(0) >= 3
    return np.where(ok, np.nanmedian(a, axis=0), np.nan)


rng_idx = np.random.default_rng(SEED).integers(0, N_EXPECTED, (B, N_EXPECTED))  # same resampling design, own correlation code


def boot_rho(x, y):
    out = np.empty(B)
    for b in range(B):
        i = rng_idx[b]; out[b] = spearmanr(x[i], y[i]).statistic
    return out


def build(variant):
    Vs, Os = {}, {}
    for w in (1, 2, 3, 4):
        for y in (2023, 2024):
            months = [6] if (variant and w == 2 and y == 2024) else None
            Vs[(y, w)] = vq(y, w, months); Os[(y, w)] = oq(y, w)
    for y in (2023, 2024):
        months = [1, 2, 3, 6, 7, 8, 9, 10, 11, 12] if (variant and y == 2024) else list(range(1, 13))
        Vs[(y, "year")] = vyear(y, months); Os[(y, "year")] = oyear(y)
    for a in (*Vs.values(), *Os.values()):
        assert np.isfinite(a).all() and len(a) == N_EXPECTED
    return Vs, Os


def compare(variant, folder):
    Vs, Os = build(variant); n_checks = 0
    L1 = pd.read_csv(folder / "L1.csv"); L3 = pd.read_csv(folder / "L3.csv"); L4 = pd.read_csv(folder / "L4.csv"); ST = pd.read_csv(folder / "stability.csv")
    L1["window"] = L1.window.astype(str); L3["window"] = L3.window.astype(str); L4["window"] = L4.window.astype(str)
    chg = {"VNNIC": {}, "Ookla": {}}
    for w in ("1", "2", "3", "4", "year"):
        wk = int(w) if w != "year" else "year"
        V0, V1, O0, O1 = Vs[(2023, wk)], Vs[(2024, wk)], Os[(2023, wk)], Os[(2024, wk)]
        r = L1[L1.window == w].iloc[0]
        gv, go = np.median(V1) / np.median(V0), np.median(O1) / np.median(O0)
        assert abs(r.V_ratio - gv) < 1e-12 and abs(r.O_ratio - go) < 1e-12 and abs(r.diff_log_ratio - (np.log(gv) - np.log(go))) < 1e-12; n_checks += 3
        assert r.ookla_larger_growth_n == int(((O1 / O0) > (V1 / V0)).sum()); assert r.both_positive == int(((V1 > V0) & (O1 > O0)).sum()); n_checks += 2
        r3 = L3[L3.window == w].iloc[0]
        assert abs(r3.rho_2023 - spearmanr(V0, O0).statistic) < 1e-12 and abs(r3.rho_2024 - spearmanr(V1, O1).statistic) < 1e-12; n_checks += 2
        for scale, (xv, xo) in (("log", (np.log(V1 / V0), np.log(O1 / O0))), ("Mbps", (V1 - V0, O1 - O0))):
            r4 = L4[(L4.window == w) & (L4.scale == scale)].iloc[0]
            assert abs(r4.rho - spearmanr(xv, xo).statistic) < 1e-12; n_checks += 1
        if w != "year":
            chg["VNNIC"][int(w)] = np.log(V1 / V0); chg["Ookla"][int(w)] = np.log(O1 / O0)
    means = {}
    for src in ("VNNIC", "Ookla"):
        vals = []
        for a, b in itertools.combinations((1, 2, 3, 4), 2):
            rho = spearmanr(chg[src][a], chg[src][b]).statistic; vals.append(rho)
            assert abs(ST[(ST.source == src) & (ST.pair == f"Q{a}-Q{b}")].rho.iloc[0] - rho) < 1e-12; n_checks += 1
        means[src] = float(np.mean(vals)); assert abs(ST[(ST.source == src) & (ST.pair == "mean of six")].rho.iloc[0] - means[src]) < 1e-12; n_checks += 1
    assert abs(ST[ST.source == "V-O"].rho.iloc[0] - (means["VNNIC"] - means["Ookla"])) < 1e-12; n_checks += 1
    # independent bootstrap of the headline intervals (spearmanr per resample, own percentile call)
    pct = lambda a: (float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5)))
    for w in ("1", "2", "3", "4"):
        r4 = L4[(L4.window == w) & (L4.scale == "log")].iloc[0]
        lo, hi = pct(boot_rho(chg["VNNIC"][int(w)], chg["Ookla"][int(w)]))
        assert abs(lo - r4.lo) < 1e-9 and abs(hi - r4.hi) < 1e-9, ("L4 interval", w, lo, hi, r4.lo, r4.hi); n_checks += 2
    bm = {}
    for src in ("VNNIC", "Ookla"):
        bm[src] = np.mean([boot_rho(chg[src][a], chg[src][b]) for a, b in itertools.combinations((1, 2, 3, 4), 2)], axis=0)
    lo, hi = pct(bm["VNNIC"] - bm["Ookla"]); r = ST[ST.source == "V-O"].iloc[0]
    assert abs(lo - r.lo) < 1e-9 and abs(hi - r.hi) < 1e-9, ("stability difference interval", lo, hi, r.lo, r.hi); n_checks += 2
    for src in ("VNNIC", "Ookla"):
        lo, hi = pct(bm[src]); r = ST[(ST.source == src) & (ST.pair == "mean of six")].iloc[0]
        assert abs(lo - r.lo) < 1e-9 and abs(hi - r.hi) < 1e-9; n_checks += 2
    return n_checks


res = {"main": compare(False, HERE / "results_postshift_20261030"), "variant_without_aprmay_2024": compare(True, HERE / "results_postshift_exclAprMay_20261030")}
res["passed"] = True; res["scope"] = "point estimates for L1, L3, L4 and stability, and bootstrap intervals for L4 and stability, reproduced with an independent implementation; L2 and the L1/L3 intervals were not re-derived"
res["not_independent_team"] = True
json.dump(res, open(HERE / "results_postshift_20261030" / "validation.json", "w"), indent=1)
print(json.dumps(res, indent=1))
