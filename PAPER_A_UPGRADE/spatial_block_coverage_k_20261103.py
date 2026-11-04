"""Coverage by number of blocks (AMENDMENT_3.md, C2). Same engine, configurations, datasets and draws as
spatial_block_coverage_20261103.py; only the list of groupings changes:
  engine key 6  -> six administrative regions (region_mapping_6.csv)
  engine keys 8, 10, 12, 15, 20 -> contiguous Ward blocks with that many blocks (block_assignments_contig.csv)
The engine function run_dataset is rebuilt from its own source with the list of keys replaced."""
import sys, inspect
from pathlib import Path
import numpy as np, pandas as pd

from paths import ENGINE as RC, HERE
RES = HERE / "results_spatial_block_20261103"
sys.path.insert(0, str(RC))
import spatial_pilot as s
import spatial_main as m

KEYS = (6, 8, 10, 12, 15, 20)
_orig_geometry = s.geometry
_src = inspect.getsource(s.run_dataset)
assert "(6, 8, 12)" in _src
exec(_src.replace("(6, 8, 12)", repr(KEYS)), s.__dict__)   # redefines s.run_dataset with the new list of groupings


def geometry():
    graphs, groups, multipliers, meta = _orig_geometry()
    iso = meta["iso_order"]
    ba = pd.read_csv(RES / "block_assignments.csv", encoding="utf-8-sig").set_index("shapeISO")
    bc = pd.read_csv(RES / "block_assignments_contig.csv", encoding="utf-8-sig").set_index("shapeISO")
    new = {}
    reg = ba.loc[iso, "region6"].to_numpy()
    new[6] = [np.flatnonzero(reg == k) for k in sorted(set(reg))]
    for k in (8, 10, 12, 15, 20):
        lab = bc.loc[iso, f"contig{k}"].to_numpy()
        new[k] = [np.flatnonzero(lab == c) for c in sorted(set(lab))]
        assert len(new[k]) == k and sum(map(len, new[k])) == 63
    assert len(new[6]) == 6
    meta["cluster_sizes"] = {str(k): [len(g) for g in v] for k, v in new.items()}
    meta["note"] = "keys 6 = region6; 8, 10, 12, 15, 20 = contiguous Ward blocks"
    return graphs, new, multipliers, meta


s.geometry = geometry

if __name__ == "__main__":
    import multiprocessing as mp
    mp.freeze_support()
    extra = sys.argv[1:]
    sys.argv = [sys.argv[0], "--set", "matched"] + ([] if "--tag" in extra else ["--tag", "blocks_k_20261103"]) + extra
    m.main()
