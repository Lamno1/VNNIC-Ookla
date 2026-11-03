"""Finite-union median/change/rank bounds; no sampling inference or imputation."""
from pathlib import Path
import hashlib,json,math,importlib.metadata
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from upg_common import Data

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
CACHE=HERE/'data/coverage_tiles_canonical_20261030'
OUT=HERE/'coverage_identification_20261030'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def median_bounds(observed,n):
    x=np.sort(np.asarray(observed,float));m=len(x);r=n-m
    assert 0<m<=n and np.isfinite(x).all() and (x>0).all()
    central=[(n+1)//2,n//2+1]
    lower=[0.0 if k<=r else x[k-r-1] for k in central]
    upper=[x[k-1] if k<=m else np.inf for k in central]
    return sum(lower)/2,sum(upper)/2


def change_bounds(aL,aU,bL,bU):
    lo=-np.inf if bL==0 or np.isinf(aU) else math.log(bL)-math.log(aU)
    hi=np.inf if aL==0 or np.isinf(bU) else math.log(bU)-math.log(aL)
    return lo,hi,bL-aU,bU-aL


def rank_bounds(lower,upper):
    lo=np.array(lower);hi=np.array(upper);n=len(lo)
    best=np.array([1+int((lo[np.arange(n)!=i]>hi[i]).sum()) for i in range(n)])
    worst=np.array([n-int((hi[np.arange(n)!=i]<lo[i]).sum()) for i in range(n)])
    assert ((best>=1)&(best<=worst)&(worst<=n)).all()
    return best,worst


def main():
    OUT.mkdir(exist_ok=True);d=Data(with_ext=True)
    mapping=pd.read_parquet(ROOT/'data/reference/dim_province_legacy63.parquet').set_index('shapeISO')
    quarters={};hashes={};geo_checks=[]
    for y in (2021,2023,2024):
        for q in range(1,5):
            p=CACHE/f'{y}Q{q}.parquet';meta=p.with_suffix('.json')
            info=json.loads(meta.read_text(encoding='utf-8'))
            assert sha(p)==info['output_sha256']
            assert info['input_hashes']['builder']==sha(HERE/'build_coverage_tiles_20261030.py')
            f=pd.read_parquet(p);f=f[f.shapeISO!=''].copy()
            assert not f.quadkey.duplicated().any()
            quarters[y,q]={iso:g.set_index('quadkey') for iso,g in f.groupby('shapeISO')}
            hashes[str(p.relative_to(ROOT))]=sha(p);hashes[str(meta.relative_to(ROOT))]=sha(meta)
            geo_checks.append(dict(year=y,quarter=q,canonical_tiles=len(f),
                                   coordinate_assignment_differences=info['canonical_vs_legacy_assignment_differences']))
    rows=[]
    for start in (2021,2023):
        for q in range(1,5):
            for iso in sorted(mapping.index):
                a=quarters[start,q][iso];b=quarters[2024,q][iso]
                union=a.index.union(b.index);common=a.index.intersection(b.index)
                av=a.download_mbps.to_numpy();bv=b.download_mbps.to_numpy()
                aL,aU=median_bounds(av,len(union));bL,bU=median_bounds(bv,len(union))
                lo,hi,mlo,mhi=change_bounds(aL,aU,bL,bU)
                am,bm=float(np.median(av)),float(np.median(bv));observed_log=math.log(bm/am)
                assert lo<=observed_log<=hi
                ac=a.loc[common,'download_mbps'].to_numpy();bc=b.loc[common,'download_mbps'].to_numpy()
                ca=float(np.median(ac)) if len(common) else np.nan;cb=float(np.median(bc)) if len(common) else np.nan
                paired=np.log(bc/ac) if len(common) else np.array([])
                # Finite completions near both bound directions; no upper speed
                # ceiling is added to the model by using this numerical witness.
                eps=1e-12;large=1e12
                amin=float(np.median(np.r_[av,np.full(len(union)-len(av),eps)]))
                amax=float(np.median(np.r_[av,np.full(len(union)-len(av),large)]))
                bmin=float(np.median(np.r_[bv,np.full(len(union)-len(bv),eps)]))
                bmax=float(np.median(np.r_[bv,np.full(len(union)-len(bv),large)]))
                wlo=math.log(bmin/amax);whi=math.log(bmax/amin)
                pid=mapping.loc[iso,'province_id_legacy63'];j=d.pids.index(pid)
                v_start=d.V(start,q)[j];v_end=d.V(2024,q)[j]
                rows.append(dict(period=f'{start}-2024',quarter=q,iso=iso,province_id=pid,
                     province_name=mapping.loc[iso,'province_name_official'],
                     start_cells=len(a),end_cells=len(b),common_cells=len(common),union_cells=len(union),
                     entering_cells=len(b)-len(common),exiting_cells=len(a)-len(common),
                     start_observed_fraction=len(a)/len(union),end_observed_fraction=len(b)/len(union),
                     cell_jaccard=len(common)/len(union),available_start_median=am,available_end_median=bm,
                     available_log_change=observed_log,available_Mbps_change=bm-am,
                     common_start_median=ca,common_end_median=cb,
                     common_log_change=math.log(cb/ca) if len(common) else np.nan,
                     common_Mbps_change=cb-ca,paired_cell_median_log_change=float(np.median(paired)) if len(common) else np.nan,
                     common_positive_share=float((paired>0).mean()) if len(common) else np.nan,
                     start_median_lower=aL,start_median_upper=aU,end_median_lower=bL,end_median_upper=bU,
                     log_change_lower=lo,log_change_upper=hi,Mbps_change_lower=mlo,Mbps_change_upper=mhi,
                     lower_completion_log=wlo,upper_completion_log=whi,
                     VNNIC_log_change=math.log(v_end/v_start)))
    df=pd.DataFrame(rows);pairs=[];summary=[];members=[]
    for (period,q),g in df.groupby(['period','quarter'],sort=False):
        pos=g.index.to_numpy();n=len(g);assert n==63
        best,worst=rank_bounds(g.log_change_lower.to_numpy(),g.log_change_upper.to_numpy())
        df.loc[pos,'rank_best']=best;df.loc[pos,'rank_worst']=worst
        for k in (5,10,16):
            for i,r in enumerate(g.itertuples()):
                members.append(dict(period=period,quarter=q,province_id=r.province_id,iso=r.iso,
                                    province_name=r.province_name,k=k,rank_best=int(best[i]),rank_worst=int(worst[i]),
                                    guaranteed=bool(worst[i]<=k),possible=bool(best[i]<=k),never=bool(best[i]>k)))
        determined=both=unresolved=witness_failures=0
        gg=list(g.itertuples())
        for i in range(n):
            for j in range(i+1,n):
                a,b=gg[i],gg[j]
                certain_a=a.log_change_lower>b.log_change_upper
                certain_b=b.log_change_lower>a.log_change_upper
                possible_a=a.log_change_upper>b.log_change_lower
                possible_b=b.log_change_upper>a.log_change_lower
                wa=a.upper_completion_log>b.lower_completion_log
                wb=b.upper_completion_log>a.lower_completion_log
                if certain_a or certain_b:determined+=1
                else:unresolved+=1
                if possible_a and possible_b:both+=1
                witness_failures+=int(possible_a and not wa)+int(possible_b and not wb)
                pairs.append(dict(period=period,quarter=q,province_a=a.province_id,province_b=b.province_id,
                                  a_certainly_ahead=certain_a,b_certainly_ahead=certain_b,
                                  a_strictly_ahead_possible=possible_a,b_strictly_ahead_possible=possible_b,
                                  both_strict_orders_possible=possible_a and possible_b,
                                  finite_witness_a_ahead=wa,finite_witness_b_ahead=wb))
        finite=np.isfinite(g.log_change_lower)&np.isfinite(g.log_change_upper)
        row=dict(period=period,quarter=q,N=n,start_cells=int(g.start_cells.sum()),end_cells=int(g.end_cells.sum()),
                 union_cells=int(g.union_cells.sum()),common_cells=int(g.common_cells.sum()),
                 median_province_cell_jaccard=float(g.cell_jaccard.median()),
                 start_median_upper_finite=int(np.isfinite(g.start_median_upper).sum()),
                 end_median_upper_finite=int(np.isfinite(g.end_median_upper).sum()),
                 change_interval_finite=int(finite.sum()),
                 no_finite_change_endpoint=int((~np.isfinite(g.log_change_lower)&~np.isfinite(g.log_change_upper)).sum()),
                 certain_increase=int((g.log_change_lower>0).sum()),certain_decrease=int((g.log_change_upper<0).sum()),
                 strict_order_identified_pairs=determined,unresolved_pairs=unresolved,
                 both_strict_orders_possible_pairs=both,pairs_total=n*(n-1)//2,
                 finite_completion_witness_failures=witness_failures,
                 full_rank_range=int(((best==1)&(worst==n)).sum()),
                 available_vs_common_change_rho=float(spearmanr(g.available_log_change,g.common_log_change).statistic),
                 VNNIC_vs_available_change_rho=float(spearmanr(g.VNNIC_log_change,g.available_log_change).statistic),
                 VNNIC_vs_common_change_rho=float(spearmanr(g.VNNIC_log_change,g.common_log_change).statistic),
                 common_vs_available_change_sign_switches=int((np.sign(g.available_log_change)!=np.sign(g.common_log_change)).sum()))
        for k in (5,10,16):row[f'guaranteed_top{k}']=int((worst<=k).sum());row[f'possible_top{k}']=int((best<=k).sum())
        summary.append(row)
    df[['rank_best','rank_worst']]=df[['rank_best','rank_worst']].astype(int)
    for name,table in [('province_bounds',df),('pairs',pd.DataFrame(pairs)),
                       ('membership',pd.DataFrame(members)),('summary',pd.DataFrame(summary)),
                       ('geometry_changes',pd.DataFrame(geo_checks))]:table.to_csv(OUT/f'{name}.csv',index=False)
    for p in [HERE/'coverage_identification_specification_20261030.md',Path(__file__),
              HERE/'build_coverage_tiles_20261030.py',ROOT/'data/reference/dim_province_legacy63.parquet',
              ROOT/'data/interim/fact_vnnic_province_month.parquet',HERE/'upg_common.py',
              ROOT/'data/processed/vnnic_q2_validation_2021_2024.parquet',
              ROOT/'data/processed/ookla_fixed_q2_adm1_2021_2024.parquet',
              ROOT/'data/analysis/analysis_panel_2021_2024.parquet',
              ROOT/'RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet',
              HERE/'data/ookla_province_quarter_ext.parquet']:
        hashes[str(p.relative_to(ROOT))]=sha(p)
    report=dict(status='EXPLORATORY_FINITE_SUPPORT_PARTIAL_IDENTIFICATION',input_hashes=hashes,
                configurations=8,provinces_each=63,rows=len(df),
                no_MAR_no_imputation_no_speed_ceiling=True,identification_intervals_not_confidence_intervals=True,
                target='Hypothetical completed tile-quarter mean-speed medians on endpoint-union support, not residents or all territory.',
                packages={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','shapely','pyarrow']})
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    fields=['period','quarter','median_province_cell_jaccard','change_interval_finite',
            'strict_order_identified_pairs','full_rank_range','guaranteed_top10','possible_top10','available_vs_common_change_rho']
    print(pd.DataFrame(summary)[fields].to_string(index=False))


if __name__=='__main__':main()
