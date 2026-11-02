"""X18 build: tile-level assigned Ookla fixed data for Q2 2021-2024 (download average, tests, devices per tile) to compute weighted medians.
Reuses the validated geometry/assignment/decoding functions of build_ookla_quarters.py (imported, not modified). Run after x18_specification.md was hashed."""
import os, sys, time, importlib.util
os.environ.setdefault("OMP_NUM_THREADS", "1")
from pathlib import Path
import numpy as np, pandas as pd, pyarrow.parquet as pq
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "RED_TEAM_DIAGNOSTICS/within_source_reliability/build_ookla_quarters.py"
spec = importlib.util.spec_from_file_location("bq", SRC); bq = importlib.util.module_from_spec(spec); spec.loader.exec_module(bq)
RAW = Path(r"D:\Q1_RESEARCH\VNNIC-Ookla\OOKLA\RAW"); GEO = bq.GEO; OUT = HERE / "data" / "ookla_x18"


def do(job):
    y, q = job
    out = OUT / f"fixed_{y}Q{q}_tiles.parquet"; OUT.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return job, 0.0
    t0 = time.time()
    f = RAW / "fixed" / str(y) / f"Q{q}" / f"{y}-{(q-1)*3+1:02d}-01_performance_fixed_tiles.parquet"
    units, bounds = bq.geometry_index(GEO)
    pf = pq.ParquetFile(f); names = pf.schema_arrow.names; decode = "tile_x" not in names
    cols = (["quadkey"] if decode else ["tile_x", "tile_y"]) + ["avg_d_kbps", "tests", "devices"]
    chunks = []
    for batch in pf.iter_batches(batch_size=bq.BATCH, columns=cols, use_threads=False):
        fr = batch.to_pandas()
        if decode:
            xy = np.array([bq.quad_centroid(str(k)) for k in fr.quadkey]); fr["tile_x"] = xy[:, 0]; fr["tile_y"] = xy[:, 1]
        good = np.isfinite(fr.tile_x) & np.isfinite(fr.tile_y); fr = fr[good]
        cand = fr[fr.tile_x.between(bounds[0], bounds[2]) & fr.tile_y.between(bounds[1], bounds[3])].copy()
        if not len(cand):
            continue
        codes, status = bq.assign(cand[["tile_x", "tile_y"]].to_numpy(), units)
        cand["shapeISO"] = codes; cand["status"] = status
        keep = cand[cand.status == "ASSIGNED_UNIQUE"].copy()
        keep["d"] = keep.avg_d_kbps / 1000.0
        chunks.append(keep[["shapeISO", "d", "tests", "devices"]])
    pd.concat(chunks, ignore_index=True).assign(year=y, quarter=q).to_parquet(out)
    return job, time.time() - t0


if __name__ == "__main__":
    jobs = [(y, 2) for y in (2021, 2022, 2023, 2024)]
    t0 = time.time()
    with ProcessPoolExecutor(4) as ex:
        futs = {ex.submit(do, j): j for j in jobs}
        for f in as_completed(futs):
            print(f.result(), f"{time.time()-t0:.0f}s", flush=True)
    print("ALL DONE", flush=True)
