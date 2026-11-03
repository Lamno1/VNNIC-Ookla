"""Coverage simulation for the two block rules of reports/spatial_block_bootstrap_20261103/SPEC.md, section 5.
Reuses the matched evaluation of reports/reviewer_checks_20261023 (spatial_pilot.py engine and spatial_main.py, unchanged; same six
configurations, 2,000 datasets, 1,999 draws, same root seed) and replaces only the fixed province groups:
  engine key 6  -> six administrative regions (region_mapping_6.csv)
  engine key 12 -> Ward neighbour blocks, k = 12 (block_assignments.csv)
  engine key 8  -> duplicate of the Ward blocks (ignored in the report)
Province order in the engine is sorted shapeISO; groups are mapped by shapeISO."""
import sys
from pathlib import Path
import numpy as np, pandas as pd

RC = Path(r"D:\Q1_RESEARCH\CONNECTIVITY_ENTERPRISE_STUDY\reports\reviewer_checks_20261023")
BL = Path(r"D:\Q1_RESEARCH\CONNECTIVITY_ENTERPRISE_STUDY\PAPER_A_UPGRADE\results_spatial_block_20261103\block_assignments.csv")
sys.path.insert(0, str(RC))
import spatial_pilot as s
import spatial_main as m

_orig_geometry = s.geometry


def geometry():
    graphs, groups, multipliers, meta = _orig_geometry()
    iso = meta["iso_order"]
    ba = pd.read_csv(BL, encoding="utf-8-sig").set_index("shapeISO")
    ward = ba.loc[iso, "neigh12"].to_numpy(); reg = ba.loc[iso, "region6"].to_numpy()
    wg = [np.flatnonzero(ward == k) for k in sorted(set(ward))]
    rg = [np.flatnonzero(reg == k) for k in sorted(set(reg))]
    assert len(wg) == 12 and len(rg) == 6 and sum(map(len, wg)) == 63 and sum(map(len, rg)) == 63
    groups = {6: rg, 8: wg, 12: wg}
    meta["cluster_sizes"] = {"region6": [len(g) for g in rg], "ward12": [len(g) for g in wg]}
    meta["note"] = "keys 6 = region6, 12 = ward12, 8 = duplicate of ward12"
    return graphs, groups, multipliers, meta


s.geometry = geometry

if __name__ == "__main__":
    import multiprocessing as mp
    mp.freeze_support()
    sys.argv = [sys.argv[0], "--set", "matched", "--tag", "blocks_20261103"]
    m.main()
