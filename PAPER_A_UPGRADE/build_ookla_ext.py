"""Aggregate Ookla fixed-broadband tiles to province x quarter (2021Q1-2024Q4), reusing the tile-to-province
point-in-polygon logic of the frozen Q2 pilot (s10_ookla_pilot.py) and the same canonical geometry.
Extension build for PAPER_A_UPGRADE (X7); run after upgrade_specification.md was hashed. 2024Q2 is rebuilt as a code-path check."""
import os, sys, json, time
os.environ.setdefault("OMP_NUM_THREADS", "1")
import math
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from matplotlib.path import Path as MplPath
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = Path(__file__).resolve().parent
RAW = Path(r"D:\Q1_RESEARCH\VNNIC-Ookla\OOKLA\RAW\fixed")
GEO = r"D:\Q1_RESEARCH\GIS_DERIVED\CANONICAL_ADM1_63.geojson"
OUTD = HERE / "data" / "ookla_quarter_parts_ext"
OUTD.mkdir(parents=True, exist_ok=True)
BATCH = 250000


def geometry_index(path):
    geo = json.loads(Path(path).read_text(encoding="utf-8-sig")); units = []; allx = []; ally = []
    for f in geo["features"]:
        geom = f["geometry"]; polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]; parts = []
        for poly in polys:
            outer = np.asarray(poly[0], float); holes = [MplPath(np.asarray(h, float)) for h in poly[1:]]
            parts.append((MplPath(outer), holes, outer[:, 0].min(), outer[:, 1].min(), outer[:, 0].max(), outer[:, 1].max()))
            allx.extend(outer[:, 0]); ally.extend(outer[:, 1])
        units.append((f["properties"]["shapeISO"], parts))
    return units, (min(allx), min(ally), max(allx), max(ally))


def assign(points, units):
    count = np.zeros(len(points), np.int16); code = np.full(len(points), "", object); boundary = np.zeros(len(points), bool)
    for iso, parts in units:
        hit = np.zeros(len(points), bool); edge = np.zeros(len(points), bool)
        for path, holes, minx, miny, maxx, maxy in parts:
            cand = (points[:, 0] >= minx) & (points[:, 0] <= maxx) & (points[:, 1] >= miny) & (points[:, 1] <= maxy)
            idx = np.flatnonzero(cand)
            if not len(idx):
                continue
            p = points[idx]; inside = path.contains_points(p, radius=0)
            for hole in holes:
                inside &= ~hole.contains_points(p, radius=0)
            plus = path.contains_points(p, radius=1e-11); minus = path.contains_points(p, radius=-1e-11); edge[idx] |= plus != minus
            hit[idx] |= inside
        count += hit; code[hit] = iso; boundary |= edge
    status = np.where(boundary, "BOUNDARY_REVIEW", np.where(count > 1, "AMBIGUOUS", np.where(count == 1, "ASSIGNED_UNIQUE", "OUTSIDE_VIETNAM")))
    return code, status


def quad_centroid(q):  # same decoding as frozen pilot (s10_ookla_pilot.quad_centroid)
    x = y = 0; z = len(q)
    for i, c in enumerate(q):
        bit = z - i - 1; d = int(c); x += (d & 1) << bit; y += ((d >> 1) & 1) << bit
    n = 2 ** z; lon = (x + .5) / n * 360 - 180; a = math.pi * (1 - 2 * (y + .5) / n); lat = math.degrees(math.atan(math.sinh(a)))
    return lon, lat


def do_quarter(args):
    year, q = args[0], args[1]
    force_decoded = len(args) > 2 and args[2] == "decoded"
    out = (OUTD.parent / "ookla_decoded_check" / f"{year}Q{q}_decoded.parquet") if force_decoded else OUTD / f"{year}Q{q}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return str(out), 0
    t0 = time.time()
    f = RAW / str(year) / f"Q{q}" / f"{year}-{(q-1)*3+1:02d}-01_performance_fixed_tiles.parquet"
    units, bounds = geometry_index(GEO)
    pf = pq.ParquetFile(f); chunks = []; scanned = 0
    decode = force_decoded or ("tile_x" not in pf.schema_arrow.names)
    cols = ["quadkey", "avg_d_kbps", "tests", "devices"] if decode else ["tile_x", "tile_y", "avg_d_kbps", "tests", "devices"]
    for batch in pf.iter_batches(batch_size=BATCH, columns=cols, use_threads=False):
        fr = batch.to_pandas(); scanned += len(fr)
        if decode:
            xy = np.array([quad_centroid(str(k)) for k in fr.quadkey]); fr["tile_x"] = xy[:, 0]; fr["tile_y"] = xy[:, 1]
        good = np.isfinite(fr.tile_x) & np.isfinite(fr.tile_y) & np.isfinite(fr.avg_d_kbps); fr = fr[good]
        bbox = fr.tile_x.between(bounds[0], bounds[2]) & fr.tile_y.between(bounds[1], bounds[3])
        cand = fr[bbox].copy()
        if not len(cand):
            continue
        codes, status = assign(cand[["tile_x", "tile_y"]].to_numpy(), units)
        cand["shapeISO"] = codes; cand["status"] = status
        keep = cand[cand.status == "ASSIGNED_UNIQUE"].copy(); keep["download_mbps"] = keep.avg_d_kbps / 1000.0
        chunks.append(keep[["shapeISO", "download_mbps", "tests", "devices"]])
    vals = pd.concat(chunks, ignore_index=True)
    rows = []
    for iso, g in vals.groupby("shapeISO"):
        rows.append(dict(shapeISO=iso, year=year, quarter=q, ookla_tile_median_download_mbps=float(np.median(g.download_mbps.to_numpy())),
                         observed_ookla_tiles=len(g), total_tests=int(g.tests.sum()), rows_scanned=scanned))
    pd.DataFrame(rows).to_parquet(out)
    return str(out), time.time() - t0


if __name__ == "__main__":
    jobs = [(y, q) for y in (2019, 2020, 2025) for q in (1, 2, 3, 4)] + [(2026, 1), (2024, 2)]
    t0 = time.time()
    with ProcessPoolExecutor(4) as ex:
        futs = {ex.submit(do_quarter, j): j for j in jobs}
        for f in as_completed(futs):
            print(futs[f], f.result(), f"{time.time()-t0:.0f}s total", flush=True)
    parts = [pd.read_parquet(p) for p in sorted(OUTD.glob("*.parquet"))]
    pd.concat(parts, ignore_index=True).to_parquet(HERE / "data" / "ookla_province_quarter_ext.parquet")
    print("ALL DONE", flush=True)
