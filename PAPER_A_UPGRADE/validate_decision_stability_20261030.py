"""Second saved-input calculation, without Data or production analysis helpers."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/'decision_stability_20261030'
checked=0
def same(actual,expected,context):
    global checked
    assert np.isfinite(actual) and np.isfinite(expected), context
    assert abs(float(actual)-float(expected)) <= 2e-11*max(1,abs(float(expected))), (context,actual,expected)
    checked+=1


def weights(x,k):
    # Average ranks are independently used for ranking, but top membership is
    # derived from number strictly better and number exactly equal per observation.
    return np.array([max(0,min(1,(k-int((x>value).sum()))/int((x==value).sum()))) for value in x])


def expected_comparison(a,b,k):
    ra=pd.Series(a).rank(ascending=False).to_numpy()
    rb=pd.Series(b).rank(ascending=False).to_numpy()
    wa,wb=weights(a,k),weights(b,k)
    common=(wa+wb-np.abs(wa-wb)).sum()/2
    # Count all ordered pairs rather than reusing production upper triangle code.
    da=np.sign(a[:,None]-a[None,:]);db=np.sign(b[:,None]-b[None,:])
    ta=int((da==0).sum()-len(a))//2;tb=int((db==0).sum()-len(b))//2
    tied_either=int(((da==0)|(db==0)).sum()-len(a))//2
    discord=int(((da!=db)&(da!=0)&(db!=0)).sum())//2
    total=len(a)*(len(a)-1)//2;eligible=total-tied_either
    concord=eligible-discord
    return dict(N=len(a),k=k,spearman=np.corrcoef(ra,rb)[0,1],
                kendall_tau_b=(concord-discord)/math.sqrt((total-ta)*(total-tb)),
                mean_rank_displacement=np.abs(ra-rb).mean(),max_rank_displacement=np.abs(ra-rb).max(),
                common_top_mass=common,retention=common/k,replacements=k-common,
                jaccard=common/(2*k-common),pairs_total=total,jointly_untied_pairs=eligible,
                pair_inversions=discord,inversion_fraction=discord/eligible,tied_in_either_pairs=tied_either,
                boundary_ties_a=int((a==sorted(a,reverse=True)[k-1]).sum()),
                boundary_ties_b=int((b==sorted(b,reverse=True)[k-1]).sum()))


def main():
    # Input rows deliberately shuffled; grouping and keys must remove row-order dependence.
    raw=pd.read_parquet(ROOT/'data/interim/fact_vnnic_province_month.parquet').sample(frac=1,random_state=713)
    raw=raw[raw.network.eq('ftth')].copy();raw['month']=pd.to_datetime(raw.month)
    raw['yr']=raw.month.dt.year;raw['mo']=raw.month.dt.month
    assert not raw.duplicated(['province_id_legacy63','month']).any()
    mapping=pd.read_parquet(ROOT/'data/reference/dim_province_legacy63.parquet')
    lookup=mapping.set_index('shapeISO').province_id_legacy63.to_dict()
    qa=pd.read_parquet(ROOT/'RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet')
    qb=pd.read_parquet(HERE/'data/ookla_province_quarter_ext.parquet')
    q=pd.concat([qa,qb],ignore_index=True).drop_duplicates(['shapeISO','year','quarter'])
    q=q.sample(frac=1,random_state=523).copy();q['pid']=q.shapeISO.map(lookup)
    windows={'Q1':(1,3),'Q2':(4,6),'Q3':(7,9),'Q4':(10,12),'H1':(1,6),'H2':(7,12),'Year':(1,12)}
    panels={'base':('median',False),'monthly_mean':('mean',False),
            'complete_median':('median',True),'complete_mean':('mean',True)}
    source=pd.read_csv(OUT/'source_panel.csv')
    independent={}
    for (panel,year,w),g in source.groupby(['panel','year','window']):
        lo,hi=windows[w];agg,complete=panels[panel]
        t=raw[raw.yr.eq(year)&raw.mo.between(lo,hi)]
        grouped=t.groupby('province_id_legacy63').download
        means=grouped.median() if agg=='median' else grouped.agg(lambda s: math.fsum(s.tolist())/s.count())
        count=grouped.count()
        needed=(hi-lo+1) if complete else {3:2,6:5,12:9}[hi-lo+1]
        selected=q[q.year.eq(year)&q.quarter.between((lo-1)//3+1,(hi-1)//3+1)]
        og=selected.groupby('pid').ookla_tile_median_download_mbps.agg(['count','median'])
        for r in g.itertuples():
            pid=r.province_id
            same(r.months,count[pid],('months',panel,year,w,pid))
            same(r.required_months,needed,('required',panel,year,w,pid))
            same(r.quarters,og.loc[pid,'count'],('quarters',panel,year,w,pid))
            v=means[pid] if count[pid]>=needed else np.nan;o=og.loc[pid,'median']
            if np.isnan(v): assert np.isnan(r.V)
            else:same(r.V,v,('V',panel,year,w,pid))
            same(r.O,o,('O',panel,year,w,pid))
            independent[panel,int(year),w,pid]=(v,o)

    ranks=pd.read_csv(OUT/'rankings.csv');vectors={};ids_by={}
    for (period,panel,metric,source_name,w),g in ranks.groupby(['period','panel','metric','source','window']):
        start=int(period[:4]);ids=sorted(mapping.province_id_legacy63)
        eligible=[pid for pid in ids if all(np.isfinite(independent[panel,y,ww,pid]).all()
                    for y in (start,2024) for ww in windows)]
        assert set(g.province_id)==set(eligible)
        g=g.set_index('province_id').loc[eligible]
        j=0 if source_name=='VNNIC' else 1
        a=np.array([independent[panel,start,w,p][j] for p in eligible])
        b=np.array([independent[panel,2024,w,p][j] for p in eligible])
        z=np.array([math.log(end/start_) for start_,end in zip(a,b)]) if metric=='log' else b-a
        rr=pd.Series(z).rank(ascending=False).to_numpy()
        top={k:weights(z,k) for k in (5,10,16)}
        for i,r in enumerate(g.itertuples()):
            for name,value in [('start_value',a[i]),('end_value',b[i]),('change',z[i]),('rank',rr[i]),('N',len(eligible))]:
                same(getattr(r,name),value,('rank',period,panel,metric,source_name,w,r.Index,name))
            for k in top:same(getattr(r,f'top{k}'),top[k][i],('membership',r.Index,k))
        key=(period,panel,metric,source_name,w);vectors[key]=z;ids_by[key]=eligible

    c=pd.read_csv(OUT/'comparisons.csv')
    for r in c.itertuples():
        a=vectors[r.period,r.panel,r.metric,r.source_a,r.window_a]
        b=vectors[r.period,r.panel,r.metric,r.source_b,r.window_b]
        for name,value in expected_comparison(a,b,r.k).items():same(getattr(r,name),value,('comparison',r.Index,name))
    ac=pd.read_csv(OUT/'aggregation_comparisons.csv')
    for r in ac.itertuples():
        ka=(r.period,r.panel_a,r.metric,r.source,r.window);kb=(r.period,r.panel_b,r.metric,r.source,r.window)
        common=sorted(set(ids_by[ka])&set(ids_by[kb]))
        a=pd.Series(vectors[ka],index=ids_by[ka]).loc[common].to_numpy()
        b=pd.Series(vectors[kb],index=ids_by[kb]).loc[common].to_numpy()
        for name,value in expected_comparison(a,b,r.k).items():same(getattr(r,name),value,('aggregation',r.Index,name))
    subsets={'all7':list(windows),'quarters':['Q1','Q2','Q3','Q4'],'no_Q2_support':['Q1','Q3','Q4','H2']}
    ps=pd.read_csv(OUT/'province_scenarios.csv');ss=pd.read_csv(OUT/'selection_summary.csv')
    for key,g in ps.groupby(['period','panel','metric','subset','source','k']):
        period,panel,metric,subset,source,k=key
        keys=[(period,panel,metric,s,w) for s in ['VNNIC','Ookla'] if source in (s,'both') for w in subsets[subset]]
        ids=ids_by[keys[0]]
        rr=np.stack([pd.Series(vectors[kk]).rank(ascending=False).to_numpy() for kk in keys])
        ww=np.stack([weights(vectors[kk],k) for kk in keys]);g=g.set_index('province_id').loc[ids]
        for i,r in enumerate(g.itertuples()):
            for name,value in [('rank_min',rr[:,i].min()),('rank_max',rr[:,i].max()),
                               ('rank_range',rr[:,i].max()-rr[:,i].min()),('rank_median',np.median(rr[:,i])),
                               ('membership_sum',ww[:,i].sum()),('scenario_frequency',ww[:,i].mean()),('scenarios',len(keys))]:
                same(getattr(r,name),value,('province summary',r.Index,name))
        row=ss[(ss.period==period)&(ss.panel==panel)&(ss.metric==metric)&(ss.subset==subset)&(ss.source==source)&(ss.k==k)]
        assert len(row)==1;r=row.iloc[0];f=ww.mean(axis=0)
        for name,val in [('always',(f==1).sum()),('ever',(f>0).sum()),('never',(f==0).sum()),('sometimes',((f>0)&(f<1)).sum())]:same(r[name],val,('selection summary',key,name))
    pairs=pd.read_csv(OUT/'pair_directions.csv')
    for key,g in pairs.groupby(['period','panel','metric','subset']):
        period,panel,metric,subset=key;keys=[(period,panel,metric,s,w) for s in ['VNNIC','Ookla'] for w in subsets[subset]]
        ids=ids_by[keys[0]];index={p:i for i,p in enumerate(ids)}
        for r in g.itertuples():
            diff=[vectors[kk][index[r.province_a]]-vectors[kk][index[r.province_b]] for kk in keys]
            p=sum(x>0 for x in diff);n=sum(x<0 for x in diff);t=sum(x==0 for x in diff)
            for name,val in [('positive',p),('negative',n),('ties',t),('scenarios',len(keys))]:same(getattr(r,name),val,('pair',r.Index,name))
            assert r.both_directions==(p>0 and n>0)
    # Synthetic production checks: ties, identity, reversal and monotonic transform.
    # Only this isolated section imports production helpers, never the data checks above.
    from decision_stability_20261030 import membership,compare
    tests=0
    for a,b,k in [(np.array([5.,4,4,4,1,0]),np.array([0.,4,4,4,1,5]),2),
                  (np.arange(6.),np.arange(6.),3),(np.arange(6.),-np.arange(6.),3),
                  (np.arange(6.),np.exp(np.arange(6.)),3)]:
        for name,value in expected_comparison(a,b,k).items():same(compare(a,b,k)[name],value,('synthetic',tests,name))
        perm=np.array([3,0,5,1,4,2]);wa,_=membership(a,k);wp,_=membership(a[perm],k)
        assert np.allclose(wa[perm],wp);tests+=1
    report=dict(passed=True,numeric_comparisons=checked,synthetic_cases=tests,
                shuffled_input_rows=True,full_saved_input_reaggregation=True,
                scope='All source cells, rankings, memberships, comparisons, province summaries and pair directions; no Data/production helpers in real-data path.',
                not_independent_team=True,validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
