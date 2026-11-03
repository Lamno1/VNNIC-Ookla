from pathlib import Path
import math,json,hashlib
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
DATA=HERE/'coverage_identification_20261030'
CACHE=HERE/'data/coverage_tiles_canonical_20261030'


def constant_fill_for_median(observed,n,target):
    x=np.sort(np.asarray(observed,float));r=n-len(x);ks=[(n+1)//2,n//2+1]
    def value(c):
        left=int(np.searchsorted(x,c,side='left'))
        return sum(x[k-1] if k<=left else c if k<=left+r else x[k-r-1] for k in ks)/2
    if r==0:
        assert abs(np.median(x)-target)<1e-10
        return 0.0
    lo=0.0;hi=max(float(x[-1]),target,1.0)*2
    while value(hi)<target:hi*=2;assert hi<1e100
    assert value(lo)<=target<=value(hi)
    for _ in range(100):
        mid=(lo+hi)/2
        if value(mid)<target:lo=mid
        else:hi=mid
    fill=(lo+hi)/2
    completed=np.r_[x,np.full(r,fill)]
    assert abs(float(np.median(completed))-target)<1e-9*max(1,target)
    return fill


def main():
    b=pd.read_csv(DATA/'province_bounds.csv');rows=[];summary=[]
    arrays={}
    for y in [2021,2023,2024]:
        for q in range(1,5):
            f=pd.read_parquet(CACHE/f'{y}Q{q}.parquet');f=f[f.shapeISO!='']
            arrays[y,q]={s:g.set_index('quadkey').download_mbps for s,g in f.groupby('shapeISO')}
    for (period,q),g in b.groupby(['period','quarter']):
        start=int(period[:4]);g=g.sort_values(['available_log_change','province_id'],ascending=[False,True])
        lo=float(g.log_change_lower.max());hi=float(g.log_change_upper.min())
        assert np.isfinite(lo) and np.isfinite(hi) and hi>lo
        for orientation,order in [('available_order',g),('reverse_available_order',g.iloc[::-1])]:
            local=[]
            for rank,r in enumerate(order.itertuples(),1):
                target=lo+(hi-lo)*(64-rank)/64;factor=math.exp(target)
                al=max(r.start_median_lower,r.end_median_lower/factor)
                au=min(r.start_median_upper,r.end_median_upper/factor)
                assert au>al and au>0
                target_a=(al+au)/2 if np.isfinite(au) else max(al+1,r.available_start_median)
                target_b=target_a*factor
                a=arrays[start,q][r.iso].to_numpy();e=arrays[2024,q][r.iso].to_numpy();n=r.union_cells
                fill_a=constant_fill_for_median(a,n,target_a);fill_b=constant_fill_for_median(e,n,target_b)
                completed_a=np.r_[a,np.full(n-len(a),fill_a)]
                completed_b=np.r_[e,np.full(n-len(e),fill_b)]
                assert np.array_equal(completed_a[:len(a)],a) and np.array_equal(completed_b[:len(e)],e)
                ma=float(np.median(completed_a));mb=float(np.median(completed_b));actual=math.log(mb/ma)
                assert abs(actual-target)<1e-10
                row=dict(period=period,quarter=q,orientation=orientation,province_id=r.province_id,iso=r.iso,
                         target_rank=rank,target_log_change=target,realised_log_change=actual,
                         start_observed=len(a),end_observed=len(e),union_cells=n,
                         missing_start=n-len(a),missing_end=n-len(e),fill_start_Mbps=fill_a,fill_end_Mbps=fill_b,
                         completed_start_median=ma,completed_end_median=mb,
                         start_fill_in_observed_range=bool(a.min()<=fill_a<=a.max()),
                         end_fill_in_observed_range=bool(e.min()<=fill_b<=e.max()))
                local.append(row);rows.append(row)
            assert np.all(np.diff([r['realised_log_change'] for r in local])<0)
            summary.append(dict(period=period,quarter=q,orientation=orientation,
                       shared_log_lower=lo,shared_log_upper=hi,shared_growth_lower=math.exp(lo),shared_growth_upper=math.exp(hi),
                       shared_width=hi-lo,minimum_rank_gap=min(-np.diff([r['realised_log_change'] for r in local])),
                       min_fill_Mbps=min(min(r['fill_start_Mbps'],r['fill_end_Mbps']) for r in local),
                       max_fill_Mbps=max(max(r['fill_start_Mbps'],r['fill_end_Mbps']) for r in local),
                       all_missing_fills_within_local_observed_range=all(r['start_fill_in_observed_range'] and r['end_fill_in_observed_range'] for r in local),
                       observed_values_preserved=True,full_order_verified=True))
    pd.DataFrame(rows).to_csv(DATA/'completion_witnesses.csv',index=False)
    pd.DataFrame(summary).to_csv(DATA/'completion_summary.csv',index=False)
    report=dict(status='CONSTRUCTED_TWO_COMPLETE_OPPOSITE_ORDERS_PER_CONFIGURATION',configurations=8,
                completed_rankings=16,province_completions=len(rows),
                arbitrary_permutation_claim='Derived from shared-open-interval proof, not enumeration.',
                not_a_claim_of_joint_completion_across_all_eight_configurations=True,
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                plan_sha256=hashlib.sha256((HERE/'coverage_completion_witness_plan_20261030.md').read_bytes()).hexdigest())
    (DATA/'completion_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(pd.DataFrame(summary).to_string(index=False))


if __name__=='__main__':main()
