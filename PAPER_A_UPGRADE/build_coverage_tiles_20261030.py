"""Retain stable cell IDs in a new cache; never change frozen builders or outputs."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib,importlib.util,json,math,time,shutil
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;WORKSPACE=ROOT.parent
RAW=WORKSPACE/'VNNIC-Ookla/OOKLA/RAW/fixed'
GEO=WORKSPACE/'GIS_DERIVED/CANONICAL_ADM1_63.geojson'
HELPER=ROOT/'RED_TEAM_DIAGNOSTICS/within_source_reliability/build_ookla_quarters.py'
OUT=HERE/'data/coverage_tiles_canonical_20261030'


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def prefix(x,y,z=4):
    return ''.join(str(((x>>b)&1)+2*((y>>b)&1)) for b in range(z-1,-1,-1))


def one(job):
    y,q=job;t0=time.perf_counter();OUT.mkdir(exist_ok=True)
    raw=RAW/str(y)/f'Q{q}'/f'{y}-{(q-1)*3+1:02d}-01_performance_fixed_tiles.parquet'
    out=OUT/f'{y}Q{q}.parquet';meta=out.with_suffix('.json')
    fingerprints={'raw':sha(raw),'geometry':sha(GEO),'builder':sha(Path(__file__)),'spatial_helper':sha(HELPER)}
    if out.exists() and meta.exists():
        saved=json.loads(meta.read_text(encoding='utf-8'))
        if saved['input_hashes']==fingerprints and saved['output_sha256']==sha(out):
            return dict(year=y,quarter=q,status='CACHE_HASH_VERIFIED',rows=saved['assigned'],seconds=round(time.perf_counter()-t0,2))
        # Code-only changes trigger real reconstruction, preserving the previous
        # new-cache artifacts. Changes to raw data/geography/helper still fail.
        assert all(saved['input_hashes'][k]==fingerprints[k] for k in ['raw','geometry','spatial_helper']),f'Input fingerprint changed: {out}'
        prior=OUT/'superseded'/saved['output_sha256'][:16];prior.mkdir(parents=True,exist_ok=True)
        shutil.copy2(out,prior/out.name);shutil.copy2(meta,prior/meta.name)
    spec=importlib.util.spec_from_file_location('coverage_geometry',HELPER)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    units,bounds=helper.geometry_index(GEO)
    # Conservative zoom-4 envelope for the raw quarter lacking centroid columns.
    def tx(lon):return int(math.floor((lon+180)/360*16))
    def ty(lat):return int(math.floor((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*16))
    prefixes={prefix(x,z) for x in range(tx(bounds[0]),tx(bounds[2])+1)
              for z in range(ty(bounds[3]),ty(bounds[1])+1)}
    f=pq.ParquetFile(raw);decode='tile_x' not in f.schema_arrow.names
    cols=['quadkey','avg_d_kbps','tests','devices']+([] if decode else ['tile_x','tile_y'])
    chunks=[];scanned=0;candidate=0;status_counts={};invalid=0;coord_checks=0;offset_max=0.0;switches=0
    for batch in f.iter_batches(batch_size=200000,columns=cols,use_threads=False):
        frame=batch.to_pandas();scanned+=len(frame)
        if decode:
            frame=frame[frame.quadkey.str.slice(0,4).isin(prefixes)].copy()
            if frame.empty:continue
            xy=np.array([helper.quad_centroid(k) for k in frame.quadkey])
            frame['tile_x']=xy[:,0];frame['tile_y']=xy[:,1]
        frame=frame[frame.tile_x.between(bounds[0]-0.0001,bounds[2]+0.0001)&frame.tile_y.between(bounds[1]-0.0001,bounds[3]+0.0001)].copy()
        if frame.empty:continue
        candidate+=len(frame)
        legacy_codes,legacy_status=helper.assign(frame[['tile_x','tile_y']].to_numpy(),units)
        xy=np.array([helper.quad_centroid(k) for k in frame.quadkey])
        offsets=np.abs(xy-frame[['tile_x','tile_y']].to_numpy())
        offset_max=max(offset_max,float(offsets.max()))
        # Four-decimal rounded polygon-centroid coordinates also differ slightly
        # from the Mercator cell centre because the latitude transform is curved.
        assert float(offsets.max())<=0.000051,(job,'Raw coordinate discrepancy',float(offsets.max()))
        frame['tile_x']=xy[:,0];frame['tile_y']=xy[:,1]
        codes,status=helper.assign(xy,units)
        for key,count in pd.Series(status).value_counts().items():status_counts[key]=status_counts.get(key,0)+int(count)
        frame['shapeISO']=np.where(status=='ASSIGNED_UNIQUE',codes,'')
        frame['legacy_shapeISO']=np.where(legacy_status=='ASSIGNED_UNIQUE',legacy_codes,'')
        switches+=int((frame.shapeISO!=frame.legacy_shapeISO).sum())
        frame=frame[(frame.shapeISO!='')|(frame.legacy_shapeISO!='')].copy()
        if frame.empty:continue
        assert frame.quadkey.str.fullmatch('[0-3]{16}').all(),'Unexpected tile ID/zoom'
        valid=np.isfinite(frame.avg_d_kbps)&(frame.avg_d_kbps>0)&(frame.tests>=1)&(frame.devices>=1)
        invalid+=int((~valid).sum());frame=frame[valid].copy()
        check=frame.iloc[::max(1,len(frame)//50)]
        xy=np.array([helper.quad_centroid(k) for k in check.quadkey])
        assert np.array_equal(xy,check[['tile_x','tile_y']].to_numpy())
        coord_checks+=len(check)
        frame['download_mbps']=frame.avg_d_kbps/1000
        chunks.append(frame[['quadkey','shapeISO','legacy_shapeISO','tile_x','tile_y','download_mbps','tests','devices']])
    result=pd.concat(chunks,ignore_index=True).sort_values('quadkey').reset_index(drop=True)
    assert not result.quadkey.duplicated().any(),'Duplicate tile IDs, no silent deduplication'
    assert result[result.shapeISO!=''].shapeISO.nunique()==63
    # Read-only reconciliation against the saved quarter summary.
    old=pd.read_parquet(ROOT/'RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet')
    ext=pd.read_parquet(HERE/'data/ookla_province_quarter_ext.parquet')
    old=pd.concat([old,ext]).drop_duplicates(['shapeISO','year','quarter'])
    old=old[(old.year==y)&(old.quarter==q)].set_index('shapeISO')
    maximum=0
    for iso,g in result[result.legacy_shapeISO!=''].groupby('legacy_shapeISO'):
        expected=old.loc[iso]
        deviation=abs(g.download_mbps.median()-expected.ookla_tile_median_download_mbps)
        assert deviation<1e-12,(job,iso,'median',deviation)
        assert len(g)==expected.observed_ookla_tiles,(job,iso,'tile count',len(g),expected.observed_ookla_tiles)
        assert int(g.tests.sum())==int(expected.total_tests),(job,iso,'tests')
        maximum=max(maximum,deviation)
    result.to_parquet(out,index=False)
    metadata=dict(year=y,quarter=q,input_hashes=fingerprints,raw_file=str(raw),
                  rows_scanned=scanned,envelope_candidates=candidate,status_counts=status_counts,
                  invalid_assigned_excluded=invalid,assigned=int((result.shapeISO!='').sum()),stored_rows=len(result),provinces=63,
                  canonical_vs_legacy_assignment_differences=switches,raw_coordinate_max_offset=offset_max,
                  decoded=decode,conservative_prefixes=sorted(prefixes) if decode else [],
                  centroid_checks=coord_checks,quarter_median_max_deviation=maximum,
                  output_sha256=sha(out),seconds=time.perf_counter()-t0)
    meta.write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    return dict(year=y,quarter=q,status='BUILT_AND_RECONCILED',rows=len(result),seconds=round(time.perf_counter()-t0,2))


def main():
    OUT.mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(one,(y,q)) for y in range(2021,2025) for q in range(1,5)]
        for future in as_completed(futures):print(json.dumps(future.result()),flush=True)


if __name__=='__main__':main()
