"""Description of the block resampling actually used (Supplementary Note S8): how many provinces enter a replicate when 12 blocks of
unequal size are drawn with replacement and equal probability. Uses the saved block assignment and the same seed and draw rule as
spatial_block_contiguous_20261103.py (rng = default_rng(SEED); integers(0, k, (B, k)))."""
import json
import numpy as np, pandas as pd
from upg_common import B, SEED
from paths import HERE

OUT = HERE / "results_spatial_block_20261103"
b = pd.read_csv(OUT / "block_assignments_contig.csv")
lab = b["contig12"].to_numpy()
K = int(lab.max()) + 1
members = [np.where(lab == j)[0] for j in range(K)]
sizes = np.array([len(m) for m in members])
draws = np.random.default_rng(SEED).integers(0, K, (B, K))
n_rep = sizes[draws].sum(1)                                                  # provinces per replicate, counted with repeats
n_distinct_blocks = np.array([len(set(r)) for r in draws])
n_distinct_prov = np.array([len(np.unique(np.concatenate([members[j] for j in set(r)]))) for r in draws])
big = int(np.argmax(sizes))
res = dict(
    B=int(B), seed=int(SEED), blocks=K, block_sizes=sorted(sizes.tolist()),
    provinces_per_replicate=dict(min=int(n_rep.min()), p2_5=float(np.percentile(n_rep, 2.5)), median=float(np.median(n_rep)), mean=float(n_rep.mean()),
                                 p97_5=float(np.percentile(n_rep, 97.5)), max=int(n_rep.max())),
    distinct_provinces_per_replicate=dict(min=int(n_distinct_prov.min()), mean=float(n_distinct_prov.mean()), max=int(n_distinct_prov.max())),
    distinct_blocks_per_replicate=dict(min=int(n_distinct_blocks.min()), mean=float(n_distinct_blocks.mean()), max=int(n_distinct_blocks.max())),
    share_replicates_with_a_repeated_block=float(np.mean(n_distinct_blocks < K)),
    largest_block=dict(size=int(sizes[big]), share_absent=float(np.mean((draws == big).sum(1) == 0)), share_drawn_twice_or_more=float(np.mean((draws == big).sum(1) >= 2))),
)
(OUT / "resampling_facts.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
