"""Table S34 of the supplement as a CSV: whether the 95 percent interval excludes zero under six block groupings
(contiguous blocks of 8, 10, 12, 15 and 20, and the six administrative regions). Reads results_spatial_block_20261103/intervals_contig.csv."""
import pandas as pd
from paths import HERE

OUT = HERE / "results_spatial_block_20261103"
t = pd.read_csv(OUT / "intervals_contig.csv").set_index("stat")
G = ["contig8", "contig10", "contig12", "contig15", "contig20", "region6"]
KEYS = [k % q for k in ("A_L1_diff_log_ratio_q%d", "A_L3_change_2024_minus_2021_q%d", "A_L4_log_q%d", "B_main_L4_log_q%d") for q in (1, 2, 3, 4)] + \
       ["A_stab_diff_O_minus_V", "B_main_stab_diff_V_minus_O", "B_xAM_stab_diff_V_minus_O"]
rows = []
for k in KEYS:
    r = t.loc[k]
    d = {"statistic": k, "estimate": round(float(r.estimate), 3)}
    for g in G:
        d[g] = "excl" if bool(r[g + "_excl0"]) else "incl"
    d["n_excl"] = sum(bool(r[g + "_excl0"]) for g in G)
    rows.append(d)
df = pd.DataFrame(rows)
df.to_csv(OUT / "table_S34.csv", index=False)
print(df.to_string(index=False))
