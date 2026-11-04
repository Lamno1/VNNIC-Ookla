"""X9 build: Ookla fixed and mobile tiles -> province x quarter (download, upload, latency medians, tiles, tests, devices), 2021Q1-2025Q2.
Reuses the validated geometry/assignment/decoding functions of build_ookla_quarters.py (imported, not modified). Run after x9_replication_specification.md was hashed."""
from paths import RAW_OOKLA
import os, sys, time, importlib.util
os.environ.setdefault("OMP_NUM_THREADS", "1")
from pathlib import Path
import numpy as np, pandas as pd, pyarrow.parquet as pq
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "RED_TEAM_DIAGNOSTICS/within_source_reliability/build_ookla_quarters.py"
spec = importlib.util.spec_from_file_location("bq", SRC); bq = importlib.util.module_from_spec(spec); spec.loader.exec_module(bq)
RAW = RAW_OOKLA; GEO = bq.GEO; OUT = HERE / "data" / "ookla_x9"


def do(job):
    kind, y, q = job
    out = OUT / kind / f"{y}Q{q}.parquet"; out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return job, 0.0
    t0 = time.time()
    f = RAW / kind / str(y) / f"Q{q}" / f"{y}-{(q-1)*3+1:02d}-01_performance_{kind}_tiles.parquet"
    units, bounds = bq.geometry_index(GEO)
    pf = pq.ParquetFile(f); names = pf.schema_arrow.names; decode = "tile_x" not in names
    cols = (["quadkey"] if decode else ["tile_x", "tile_y"]) + ["avg_d_kbps", "avg_u_kbps", "avg_lat_ms", "tests", "devices"]
    chunks = []; scanned = 0
    for batch in pf.iter_batches(batch_size=bq.BATCH, columns=cols, use_threads=False):
        fr = batch.to_pandas(); scanned += len(fr)
        if decode:
            xy = np.array([bq.quad_centroid(str(k)) for k in fr.quadkey]); fr["tile_x"] = xy[:, 0]; fr["tile_y"] = xy[:, 1]
        good = np.isfinite(fr.tile_x) & np.isfinite(fr.tile_y); fr = fr[good]
        cand = fr[fr.tile_x.between(bounds[0], bounds[2]) & fr.tile_y.between(bounds[1], bounds[3])].copy()
        if not len(cand):
            continue
        codes, status = bq.assign(cand[["tile_x", "tile_y"]].to_numpy(), units)
        cand["shapeISO"] = codes; cand["status"] = status
        keep = cand[cand.status == "ASSIGNED_UNIQUE"].copy()
        keep["d"] = keep.avg_d_kbps / 1000.0; keep["u"] = keep.avg_u_kbps / 1000.0; keep["lat"] = keep.avg_lat_ms
        chunks.append(keep[["shapeISO", "d", "u", "lat", "tests", "devices"]])
    vals = pd.concat(chunks, ignore_index=True); rows = []
    for iso, g in vals.groupby("shapeISO"):
        rows.append(dict(shapeISO=iso, year=y, quarter=q, kind=kind, dl_median=float(np.median(g.d)), ul_median=float(np.nanmedian(g.u)), lat_median=float(np.nanmedian(g.lat)),
                         observed_tiles=len(g), total_tests=int(g.tests.sum()), total_devices=int(g.devices.sum()), rows_scanned=scanned))
    pd.DataFrame(rows).to_parquet(out)
    return job, time.time() - t0


if __name__ == "__main__":
    jobs = [(k, y, q) for k in ("fixed", "mobile") for y in (2021, 2022, 2023, 2024, 2025) for q in (1, 2, 3, 4) if (y, q) <= (2025, 2)]
    t0 = time.time()
    with ProcessPoolExecutor(4) as ex:
        futs = {ex.submit(do, j): j for j in jobs}
        for f in as_completed(futs):
            print(f.result(), f"{time.time()-t0:.0f}s", flush=True)
    parts = [pd.read_parquet(p) for p in sorted(OUT.glob("*/*.parquet"))]
    pd.concat(parts, ignore_index=True).to_parquet(HERE / "data" / "ookla_x9_province_quarter.parquet")
    print("ALL DONE", flush=True)
