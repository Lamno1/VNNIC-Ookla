"""Summaries of the two coverage simulations (engine output summary.csv): pooled coverage by number of blocks (Table S35)
and coverage by configuration for the province, six-region and 12-block bootstraps (first run).
Usage: python summarize_coverage_20261103.py [k_run_tag] [first_run_tag]"""
import sys
import numpy as np, pandas as pd
from paths import ENGINE, HERE

OUT = HERE / "results_spatial_block_20261103"
tag_k = sys.argv[1] if len(sys.argv) > 1 else "blocks_k_20261103"
tag_1 = sys.argv[2] if len(sys.argv) > 2 else "blocks_20261103"
OUTCOMES = ["delta", "L4_log_Q2"]

s = pd.read_csv(ENGINE / "spatial_main_runs" / tag_k / "summary.csv")
s = s[s.outcome.isin(OUTCOMES)]
g = s.groupby(["outcome", "method"]).coverage.agg(pooled="mean", lo="min", hi="max").reset_index()
g["mcse_pooled_approx"] = np.sqrt(0.9 * 0.1 / (2000 * 6))
g.to_csv(OUT / "coverage_by_k_pooled.csv", index=False)
print(g.round(3).to_string())

f = pd.read_csv(ENGINE / "spatial_main_runs" / tag_1 / "summary.csv")
f = f[f.outcome.isin(OUTCOMES)].copy()
f["cfg"] = f.configuration.str.extract(r"matched_(g\d)_.*_([A-Za-z]+)$").apply(lambda r: "%s_%s" % (r[0], r[1]), axis=1)
f["method"] = f.method.replace({"kmeans6": "region6", "kmeans12": "ward12"})
p = f[f.method.isin(["province", "region6", "ward12"])].pivot_table(index=["outcome", "cfg"], columns="method", values="coverage").reset_index()
p.to_csv(OUT / "coverage_summary_blocks_vs_province.csv", index=False)
print(p.round(3).to_string())
