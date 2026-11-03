"""Shared loaders and statistics for PAPER_A_UPGRADE (upgrade_specification.md, hashed 2026-10-09 12:15)."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
B, SEED, PSEED, NPERM = 5000, 20261010, 20261011, 10000
_IDX = {}


def make_idx(n):
    if n not in _IDX:
        _IDX[n] = np.random.default_rng(SEED).integers(0, n, (B, n))
    return _IDX[n]


def rk(a):
    return stats.rankdata(a, axis=-1)


def corr_rows(a, b):
    a = a - a.mean(-1, keepdims=True)
    b = b - b.mean(-1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (a * b).sum(-1) / np.sqrt((a * a).sum(-1) * (b * b).sum(-1))


def sp(x, y):
    return float(corr_rows(rk(np.asarray(x, float)), rk(np.asarray(y, float))))


def pe(x, y):
    return float(corr_rows(np.asarray(x, float), np.asarray(y, float)))


def sp_boot(x, y, idx=None):
    x = np.asarray(x, float); y = np.asarray(y, float)
    idx = make_idx(len(x)) if idx is None else idx
    return corr_rows(rk(x[idx]), rk(y[idx]))


def pe_boot(x, y, idx=None):
    x = np.asarray(x, float); y = np.asarray(y, float)
    idx = make_idx(len(x)) if idx is None else idx
    return corr_rows(x[idx], y[idx])


def perm_p(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float); n = len(x)
    rx, ry = rk(x), rk(y); obs = float(corr_rows(rx, ry))
    rng = np.random.default_rng(PSEED)
    perms = rng.permuted(np.tile(np.arange(n), (NPERM, 1)), axis=1)
    s = corr_rows(rx[None, :], ry[perms])
    return (1 + int((np.abs(s) >= abs(obs) - 1e-12).sum())) / (NPERM + 1)


def ci(v):
    v = np.asarray(v, float)
    return float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))


def holm(ps):
    ps = np.asarray(ps, float); order = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0.0
    for k, i in enumerate(order):
        run = max(run, (m - k) * ps[i]); adj[i] = min(1.0, run)
    return adj


def clopper_pearson(k, n, a=0.05):
    lo = 0.0 if k == 0 else stats.beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else stats.beta.ppf(1 - a / 2, k + 1, n - k)
    return float(lo), float(hi)


def md(df, floatfmt=3):
    cols = list(df.columns)
    def f(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else f"{v:.{floatfmt}f}"
        return str(v)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(f(r[c]) for c in cols) + " |")
    return "\n".join(lines)


class Data:
    """Province-ordered arrays. pids fixed to the frozen 63 provinces."""

    def __init__(self, with_ext=False):
        self.vq = pd.read_parquet(ROOT / "data/processed/vnnic_q2_validation_2021_2024.parquet")
        self.fq = pd.read_parquet(ROOT / "data/processed/ookla_fixed_q2_adm1_2021_2024.parquet")
        self.pids = sorted(self.vq.province_id_legacy63.unique())
        self.iso = dict(zip(self.vq.province_id_legacy63, self.vq.shapeISO))
        self.n = len(self.pids)
        # frozen Q2 arrays
        v = self.vq.set_index(["province_id_legacy63", "year"])
        f = self.fq.set_index(["province_id_legacy63", "year"])
        self.vq2 = {y: np.array([v.loc[(p, y), "vnnic_q2_monthly_median_download_mbps"] for p in self.pids], float) for y in range(2021, 2025)}
        self.fq2 = {}
        for col in ["ookla_tile_median_download_mbps", "ookla_tile_mean_download_mbps", "ookla_tests_weighted_mean_download_mbps",
                    "ookla_devices_weighted_mean_download_mbps", "observed_ookla_tiles", "total_tests", "total_devices"]:
            self.fq2[col] = {y: np.array([f.loc[(p, y), col] for p in self.pids], float) for y in range(2021, 2025)}
        # VNNIC monthly
        d = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet")
        d = d[d.network == "ftth"].copy(); d["month"] = pd.to_datetime(d["month"])
        self.M = d.pivot_table(index="month", columns="province_id_legacy63", values="download", aggfunc="first").reindex(columns=self.pids)
        # Ookla quarterly
        parts = [pd.read_parquet(ROOT / "RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet")]
        ext = HERE / "data" / "ookla_province_quarter_ext.parquet"
        if with_ext and ext.exists():
            parts.append(pd.read_parquet(ext))
        oq = pd.concat(parts, ignore_index=True).drop_duplicates(["shapeISO", "year", "quarter"], keep="first")
        self.oq = oq
        inv = {v_: k for k, v_ in self.iso.items()}
        oq = oq.assign(pid=oq.shapeISO.map(inv))
        self.O = {}; self.OT = {}; self.OTL = {}
        for (y, q), g in oq.groupby(["year", "quarter"]):
            s = g.set_index("pid")
            self.O[(y, q)] = np.array([s.ookla_tile_median_download_mbps.get(p, np.nan) for p in self.pids], float)
            self.OT[(y, q)] = np.array([s.total_tests.get(p, np.nan) for p in self.pids], float)
            self.OTL[(y, q)] = np.array([s.observed_ookla_tiles.get(p, np.nan) for p in self.pids], float)
        # analysis panel Apr-Dec
        ap = pd.read_parquet(ROOT / "data/analysis/analysis_panel_2021_2024.parquet").set_index(["province_id_legacy63", "year"])
        self.vaprdec = {y: np.array([ap.loc[(p, y), "ftth_download_median_apr_dec_mbps"] for p in self.pids], float) for y in range(2021, 2025)}

    def V(self, y, q):
        m = [pd.Timestamp(y, 3 * (q - 1) + k, 1) for k in (1, 2, 3)]
        sub = self.M.reindex(m)
        ok = sub.notna().sum() >= 2
        return np.where(ok.values, sub.median().values, np.nan).astype(float)

    def Vyear(self, y):
        sub = self.M.reindex([pd.Timestamp(y, k, 1) for k in range(1, 13)])
        ok = sub.notna().sum() >= 9
        return np.where(ok.values, sub.median().values, np.nan).astype(float)

    def Oyear(self, y):
        arr = np.vstack([self.O[(y, q)] for q in (1, 2, 3, 4)])
        ok = np.isfinite(arr).sum(0) >= 3
        return np.where(ok, np.nanmedian(arr, axis=0), np.nan)
