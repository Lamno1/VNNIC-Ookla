"""Exploratory H1/H2 L1-L4; see halfyear_specification_20261030.md."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata
from upg_common import Data, make_idx, sp, sp_boot, ci, ROOT, HERE

OUT=HERE/'results_halfyear_20261030'


def indicators(a):
    q=np.percentile(a,[10,25,75,90],axis=-1)
    return dict(sd_level=a.std(axis=-1,ddof=1),sd_log=np.log(a).std(axis=-1,ddof=1),
                cv=a.std(axis=-1,ddof=1)/a.mean(axis=-1),iqr=q[2]-q[1],
                p90_p10=q[3]/q[0],max_min=a.max(axis=-1)/a.min(axis=-1))


def interval(a):
    assert np.isfinite(a).all(),'Undefined bootstrap replicate'
    return ci(a)


def audit_inputs():
    paths=[ROOT/'data/interim/fact_vnnic_province_month.parquet',
           ROOT/'RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet',
           HERE/'data/ookla_province_quarter_ext.parquet',
           ROOT/'data/processed/vnnic_q2_validation_2021_2024.parquet',
           ROOT/'data/processed/ookla_fixed_q2_adm1_2021_2024.parquet',
           ROOT/'data/analysis/analysis_panel_2021_2024.parquet',
           HERE/'upg_common.py',Path(__file__),HERE/'halfyear_specification_20261030.md']
    monthly=pd.read_parquet(paths[0]);monthly=monthly[monthly.network=='ftth']
    assert not monthly.duplicated(['province_id_legacy63','month']).any()
    quarterly=[pd.read_parquet(p) for p in paths[1:3]]
    for q in quarterly: assert not q.duplicated(['shapeISO','year','quarter']).any()
    merged=quarterly[0].merge(quarterly[1],on=['shapeISO','year','quarter'],suffixes=('_a','_b'))
    for c in ['ookla_tile_median_download_mbps','total_tests','observed_ookla_tiles']:
        assert np.allclose(merged[c+'_a'],merged[c+'_b'],rtol=0,atol=0,equal_nan=True),c
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},len(merged)


def main():
    start=time.perf_counter();OUT.mkdir(exist_ok=True)
    hashes,overlap=audit_inputs();d=Data(with_ext=True)
    assert d.n==63
    for y in range(2021,2025):
        assert np.allclose(d.V(y,2),d.vq2[y],rtol=0,atol=1e-12)
        assert np.allclose(d.O[(y,2)],d.fq2['ookla_tile_median_download_mbps'][y],rtol=0,atol=1e-12)
    arrays={};coverage=[];panel=[]
    for rule,minimum in [('min5',5),('strict6',6)]:
        for y in range(2021,2025):
            for h in (1,2):
                months=[pd.Timestamp(y,m,1) for m in range(1+6*(h-1),7+6*(h-1))]
                values=d.M.reindex(months);counts=values.notna().sum().values
                v=values.median().values;v=np.where(counts>=minimum,v,np.nan)
                q=[2*h-1,2*h];oarr=np.vstack([d.O[(y,k)] for k in q])
                oc=np.isfinite(oarr).sum(axis=0);o=np.where(oc==2,np.median(oarr,axis=0),np.nan)
                arrays[(rule,y,h)]=(v,o)
                for j,p in enumerate(d.pids):
                    coverage.append(dict(rule=rule,year=y,half=f'H{h}',province_id=p,iso=d.iso[p],months=int(counts[j]),quarters=int(oc[j]),included=bool(np.isfinite(v[j]) and np.isfinite(o[j]))))
                    panel.append(dict(rule=rule,year=y,half=f'H{h}',province_id=p,V=v[j],O=o[j]))

    l1=[];l2=[];l3=[];l4=[];stability=[]
    for rule in ['min5','strict6']:
        for h in (1,2):
            vals=[*arrays[(rule,2021,h)],*arrays[(rule,2024,h)]]
            mask=np.logical_and.reduce([np.isfinite(a) for a in vals]);n=int(mask.sum());assert n>=3
            v21,o21,v24,o24=[a[mask] for a in vals];idx=make_idx(n)
            gv=np.median(v24)/np.median(v21);go=np.median(o24)/np.median(o21)
            bv=np.median(v24[idx],axis=1)/np.median(v21[idx],axis=1)
            bo=np.median(o24[idx],axis=1)/np.median(o21[idx],axis=1)
            l1.append(dict(rule=rule,half=f'H{h}',N=n,V_ratio=gv,V_lo=interval(bv)[0],V_hi=interval(bv)[1],O_ratio=go,O_lo=interval(bo)[0],O_hi=interval(bo)[1],diff_log_ratio=np.log(gv/go),diff_lo=interval(np.log(bv/bo))[0],diff_hi=interval(np.log(bv/bo))[1],both_positive=int(((v24>v21)&(o24>o21)).sum()),same_sign=int((np.sign(v24-v21)==np.sign(o24-o21)).sum()),ookla_larger_growth_n=int(((o24/o21)>(v24/v21)).sum())))
            point_v={};point_o={};boot_v={};boot_o={}
            for source,a,b in [('VNNIC',v21,v24),('Ookla',o21,o24)]:
                p1,p2=indicators(a),indicators(b);b1,b2=indicators(a[idx]),indicators(b[idx])
                for k in p1:
                    logratio=float(np.log(p2[k]/p1[k]));boot=np.log(b2[k]/b1[k])
                    if source=='VNNIC':point_v[k]=logratio;boot_v[k]=boot
                    else:point_o[k]=logratio;boot_o[k]=boot
                    lo,hi=interval(boot)
                    l2.append(dict(rule=rule,half=f'H{h}',N=n,source=source,indicator=k,estimate=logratio,lo=lo,hi=hi))
            for k in point_v:
                lo,hi=interval(boot_v[k]-boot_o[k]);l2.append(dict(rule=rule,half=f'H{h}',N=n,source='VNNIC minus Ookla',indicator=k,estimate=point_v[k]-point_o[k],lo=lo,hi=hi))
            delta=sp(v24,o24)-sp(v21,o21);lo,hi=interval(sp_boot(v24,o24,idx)-sp_boot(v21,o21,idx))
            l3.append(dict(rule=rule,half=f'H{h}',year='2024 minus 2021',N=n,rho=delta,lo=lo,hi=hi))
            for scale,a,b in [('log',np.log(v24/v21),np.log(o24/o21)),('Mbps',v24-v21,o24-o21)]:
                lo,hi=interval(sp_boot(a,b,idx));l4.append(dict(rule=rule,half=f'H{h}',scale=scale,N=n,rho=sp(a,b),lo=lo,hi=hi))
        for y in range(2021,2025):
            for h in (1,2):
                a,b=arrays[(rule,y,h)];mask=np.isfinite(a)&np.isfinite(b);a,b=a[mask],b[mask]
                lo,hi=interval(sp_boot(a,b));l3.append(dict(rule=rule,half=f'H{h}',year=str(y),N=len(a),rho=sp(a,b),lo=lo,hi=hi))
            for source,j in [('VNNIC',0),('Ookla',1)]:
                a=arrays[(rule,y,1)][j];b=arrays[(rule,y,2)][j];mask=np.isfinite(a)&np.isfinite(b)
                stability.append(dict(rule=rule,kind='within_year_H1_H2',year=str(y),source=source,N=int(mask.sum()),rho=sp(a[mask],b[mask])))
        for source,j in [('VNNIC',0),('Ookla',1)]:
            vectors=[arrays[(rule,y,h)][j] for h in (1,2) for y in (2021,2024)]
            mask=np.logical_and.reduce([np.isfinite(v) for v in vectors]);a,b,c,e=[v[mask] for v in vectors]
            stability.append(dict(rule=rule,kind='log_change_H1_H2',year='2021-2024',source=source,N=int(mask.sum()),rho=sp(np.log(b/a),np.log(e/c))))

    for name,rows in [('coverage',coverage),('province_halfyear',panel),('L1',l1),('L2',l2),('L3',l3),('L4',l4),('stability',stability)]:
        pd.DataFrame(rows).to_csv(OUT/f'{name}.csv',index=False)
    # Compare selected estimates to scipy using explicit repeated bootstrap samples.
    a,b=arrays[('min5',2024,1)];mask=np.isfinite(a)&np.isfinite(b);a,b=a[mask],b[mask]
    i=make_idx(len(a))[:12];fast=sp_boot(a,b,i)
    assert max(abs(fast[j]-spearmanr(a[row],b[row]).statistic) for j,row in enumerate(i))<1e-14
    report=dict(specification='halfyear_specification_20261030.md',mode='EXPLORATORY_SAVED_SUMMARY_REAGGREGATION',
                B=5000,seed=20261010,input_hashes=hashes,province_order=d.pids,iso_order=[d.iso[p] for p in d.pids],
                overlap_rows_verified=overlap,Q2_loaded_values_match=True,scipy_repeat_checks=12,
                packages={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','pyarrow']},
                invalid_replicates=0,elapsed_seconds=time.perf_counter()-start,
                limitations=['Nominal province-bootstrap intervals, not spatially validated.', 'Ookla half-year is midpoint of two province-quarter tile medians, not pooled half-year tiles.', 'H1/2021 spans pre-launch and launch months; no exclusions on that basis.'])
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(pd.DataFrame(l1).to_string(index=False));print(pd.DataFrame(l3).to_string(index=False));print(pd.DataFrame(l4).to_string(index=False));print(json.dumps({k:v for k,v in report.items() if k!='input_hashes'},indent=2))


if __name__=='__main__':main()
