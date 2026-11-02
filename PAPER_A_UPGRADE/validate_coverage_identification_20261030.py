"""Independent saved-tile/spatial/bounds/completion validation, no production loader."""
from pathlib import Path
from itertools import combinations_with_replacement,product,permutations
from fractions import Fraction
import hashlib,json,math
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from shapely.geometry import shape
import shapely

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
CACHE=HERE/'data/coverage_tiles_canonical_20261030';OUT=HERE/'coverage_identification_20261030'
checks=0


def equal(a,b,context):
    global checks
    if np.isinf(a) or np.isinf(b):assert a==b,(context,a,b)
    elif np.isnan(a) or np.isnan(b):assert np.isnan(a) and np.isnan(b),(context,a,b)
    else:assert abs(a-b)<=2e-9*max(1,abs(b)),(context,a,b)
    checks+=1


def explicit_bounds(x,n):
    r=n-len(x)
    return np.median(np.r_[x,np.zeros(r)]),np.median(np.r_[x,np.repeat(np.inf,r)])


def main():
    # Independent Shapely predicates and independent base-4 integer ID decoding.
    geo=json.loads((ROOT.parent/'GIS_DERIVED/CANONICAL_ADM1_63.geojson').read_text(encoding='utf-8-sig'))
    codes=np.array([f['properties']['shapeISO'] for f in geo['features']])
    polygons=[shape(f['geometry']) for f in geo['features']]
    assert all(p.is_valid for p in polygons),'Geometry validity needs review before independent predicates'
    tree=shapely.STRtree(polygons);panels={};spatial=[]
    old=pd.concat([pd.read_parquet(ROOT/'RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet'),
                   pd.read_parquet(HERE/'data/ookla_province_quarter_ext.parquet')]).drop_duplicates(['shapeISO','year','quarter'])
    for y in range(2021,2025):
        for q in range(1,5):
            p=CACHE/f'{y}Q{q}.parquet';f=pd.read_parquet(p)
            assert not f.quadkey.duplicated().any()
            quad=np.array([int(k,4) for k in f.quadkey],dtype=np.uint64)
            xx=np.zeros(len(f),dtype=np.uint64);yy=xx.copy()
            for bit in range(16):xx|=((quad>>(2*bit))&1)<<bit;yy|=((quad>>(2*bit+1))&1)<<bit
            lon=(xx+.5)/65536*360-180
            lat=np.degrees(np.arctan(np.sinh(np.pi*(1-2*(yy+.5)/65536))))
            assert np.allclose(lon,f.tile_x,atol=1e-12,rtol=0)
            assert np.allclose(lat,f.tile_y,atol=1e-12,rtol=0)
            points=shapely.points(lon,lat);hits=tree.query(points,predicate='within')
            count=np.bincount(hits[0],minlength=len(f));ind=np.full(len(f),'',dtype=object)
            ind[hits[0]]=codes[hits[1]];ind[count!=1]=''
            mismatch=np.flatnonzero(ind!=f.shapeISO.to_numpy())
            assert len(mismatch)==0,(y,q,'spatial mismatch',len(mismatch),f.iloc[mismatch[:3]].to_dict())
            spatial.append(dict(year=y,quarter=q,tiles=len(f),coordinate_and_geometry_mismatches=0))
            for iso,g in f[f.legacy_shapeISO!=''].groupby('legacy_shapeISO'):
                row=old[(old.year==y)&(old.quarter==q)&(old.shapeISO==iso)].iloc[0]
                equal(g.download_mbps.median(),row.ookla_tile_median_download_mbps,('legacy median',y,q,iso))
                equal(len(g),row.observed_ookla_tiles,('legacy count',y,q,iso))
                equal(g.tests.sum(),row.total_tests,('legacy tests',y,q,iso))
            panels[y,q]={iso:g.set_index('quadkey').download_mbps for iso,g in f[f.shapeISO!=''].groupby('shapeISO')}
    monthly=pd.read_parquet(ROOT/'data/interim/fact_vnnic_province_month.parquet')
    monthly=monthly[monthly.network=='ftth'].copy();monthly['date']=pd.to_datetime(monthly.month)
    monthly['yr']=monthly.date.dt.year;monthly['qtr']=monthly.date.dt.quarter
    v_table=monthly.groupby(['province_id_legacy63','yr','qtr']).download.agg(['median','count'])
    b=pd.read_csv(OUT/'province_bounds.csv');vectors={}
    for r in b.itertuples():
        start=int(r.period[:4]);a=panels[start,r.quarter][r.iso];e=panels[2024,r.quarter][r.iso]
        union=set(a.index)|set(e.index);common=sorted(set(a.index)&set(e.index));n=len(union)
        al,au=explicit_bounds(a.to_numpy(),n);bl,bu=explicit_bounds(e.to_numpy(),n)
        with np.errstate(divide='ignore',invalid='ignore'):
            lower=float(np.log(np.divide(bl,au)));upper=float(np.log(np.divide(bu,al)))
        ca=float(a.loc[common].median());cb=float(e.loc[common].median())
        vals=dict(start_cells=len(a),end_cells=len(e),common_cells=len(common),union_cells=n,
                  entering_cells=len(e)-len(common),exiting_cells=len(a)-len(common),
                  start_observed_fraction=len(a)/n,end_observed_fraction=len(e)/n,cell_jaccard=len(common)/n,
                  available_start_median=a.median(),available_end_median=e.median(),
                  available_log_change=math.log(e.median()/a.median()),available_Mbps_change=e.median()-a.median(),
                  common_start_median=ca,common_end_median=cb,common_log_change=math.log(cb/ca),common_Mbps_change=cb-ca,
                  paired_cell_median_log_change=np.median(np.log(e.loc[common]/a.loc[common])),
                  common_positive_share=(e.loc[common]>a.loc[common]).mean(),
                  start_median_lower=al,start_median_upper=au,end_median_lower=bl,end_median_upper=bu,
                  log_change_lower=lower,log_change_upper=upper,Mbps_change_lower=bl-au,Mbps_change_upper=bu-al)
        va=v_table.loc[(r.province_id,start,r.quarter)];ve=v_table.loc[(r.province_id,2024,r.quarter)]
        assert va['count']>=2 and ve['count']>=2
        vals['VNNIC_log_change']=math.log(ve['median']/va['median'])
        amin=np.median(np.r_[a.to_numpy(),np.repeat(1e-12,n-len(a))]);amax=np.median(np.r_[a.to_numpy(),np.repeat(1e12,n-len(a))])
        emin=np.median(np.r_[e.to_numpy(),np.repeat(1e-12,n-len(e))]);emax=np.median(np.r_[e.to_numpy(),np.repeat(1e12,n-len(e))])
        vals['lower_completion_log']=math.log(emin/amax);vals['upper_completion_log']=math.log(emax/amin)
        for name,v in vals.items():equal(getattr(r,name),v,('province',r.period,r.quarter,r.iso,name))
        vectors[r.period,r.quarter,r.province_id]=(lower,upper)
    for r in b.itertuples():
        others=[v for (period,q,pid),v in vectors.items() if period==r.period and q==r.quarter and pid!=r.province_id]
        lower,upper=vectors[r.period,r.quarter,r.province_id]
        best=1+sum(v[0]>upper for v in others);worst=63-sum(v[1]<lower for v in others)
        equal(r.rank_best,best,('best rank',r.province_id));equal(r.rank_worst,worst,('worst rank',r.province_id))
    pairs=pd.read_csv(OUT/'pairs.csv')
    for r in pairs.itertuples():
        al,au=vectors[r.period,r.quarter,r.province_a];bl,bu=vectors[r.period,r.quarter,r.province_b]
        assert r.a_certainly_ahead==(al>bu) and r.b_certainly_ahead==(bl>au)
        assert r.a_strictly_ahead_possible==(au>bl) and r.b_strictly_ahead_possible==(bu>al)
        assert r.both_strict_orders_possible==((au>bl) and (bu>al))
    members=pd.read_csv(OUT/'membership.csv')
    for r in members.itertuples():
        assert r.guaranteed==(r.rank_worst<=r.k) and r.possible==(r.rank_best<=r.k) and r.never==(r.rank_best>r.k)
    summaries=pd.read_csv(OUT/'summary.csv')
    for r in summaries.itertuples():
        g=b[(b.period==r.period)&(b.quarter==r.quarter)]
        p=pairs[(pairs.period==r.period)&(pairs.quarter==r.quarter)]
        certain=p.a_certainly_ahead|p.b_certainly_ahead
        fields=dict(N=len(g),start_cells=g.start_cells.sum(),end_cells=g.end_cells.sum(),union_cells=g.union_cells.sum(),
                    common_cells=g.common_cells.sum(),median_province_cell_jaccard=g.cell_jaccard.median(),
                    start_median_upper_finite=np.isfinite(g.start_median_upper).sum(),end_median_upper_finite=np.isfinite(g.end_median_upper).sum(),
                    change_interval_finite=(np.isfinite(g.log_change_lower)&np.isfinite(g.log_change_upper)).sum(),
                    no_finite_change_endpoint=(~np.isfinite(g.log_change_lower)&~np.isfinite(g.log_change_upper)).sum(),
                    certain_increase=(g.log_change_lower>0).sum(),certain_decrease=(g.log_change_upper<0).sum(),
                    strict_order_identified_pairs=certain.sum(),unresolved_pairs=(~certain).sum(),
                    both_strict_orders_possible_pairs=p.both_strict_orders_possible.sum(),pairs_total=len(p),
                    finite_completion_witness_failures=((p.a_strictly_ahead_possible&~p.finite_witness_a_ahead).sum()+(p.b_strictly_ahead_possible&~p.finite_witness_b_ahead).sum()),
                    full_rank_range=((g.rank_best==1)&(g.rank_worst==63)).sum(),
                    common_vs_available_change_sign_switches=(np.sign(g.available_log_change)!=np.sign(g.common_log_change)).sum())
        for outname,aname,bname in [('available_vs_common_change_rho','available_log_change','common_log_change'),
                                   ('VNNIC_vs_available_change_rho','VNNIC_log_change','available_log_change'),
                                   ('VNNIC_vs_common_change_rho','VNNIC_log_change','common_log_change')]:
            fields[outname]=np.corrcoef(g[aname].rank(),g[bname].rank())[0,1]
        for k in (5,10,16):fields[f'guaranteed_top{k}']=(g.rank_worst<=k).sum();fields[f'possible_top{k}']=(g.rank_best<=k).sum()
        for name,val in fields.items():equal(getattr(r,name),val,('summary',r.period,r.quarter,name))
    # All witness medians recalculated on ID-indexed union panels, preserving observations.
    witness=pd.read_csv(OUT/'completion_witnesses.csv')
    rounded_checks=[]
    for key,g in witness.groupby(['period','quarter','orientation']):
        actual=[];rounded=[];exact_ratios=[]
        for r in g.sort_values('target_rank').itertuples():
            a=panels[int(r.period[:4]),r.quarter][r.iso];e=panels[2024,r.quarter][r.iso]
            union=sorted(set(a.index)|set(e.index))
            aa=a.reindex(union).fillna(r.fill_start_Mbps);ee=e.reindex(union).fillna(r.fill_end_Mbps)
            assert aa.loc[a.index].equals(a.loc[aa.loc[a.index].index])
            assert np.array_equal(aa.loc[a.index].to_numpy(),a.to_numpy())
            assert np.array_equal(ee.loc[e.index].to_numpy(),e.to_numpy())
            z=math.log(ee.median()/aa.median());actual.append(z)
            equal(z,r.target_log_change,('witness desired',key,r.iso));equal(z,r.realised_log_change,('witness stored',key,r.iso))
            equal(aa.median(),r.completed_start_median,('witness median start',key,r.iso));equal(ee.median(),r.completed_end_median,('witness median end',key,r.iso))
            assert r.start_fill_in_observed_range==(a.min()<=r.fill_start_Mbps<=a.max())
            assert r.end_fill_in_observed_range==(e.min()<=r.fill_end_Mbps<=e.max())
            ar=a.reindex(union).fillna(round(r.fill_start_Mbps*1000)/1000)
            er=e.reindex(union).fillna(round(r.fill_end_Mbps*1000)/1000)
            am=ar.median();em=er.median()
            rounded.append(math.log(em/am))
            exact_ratios.append(Fraction(round(em*2000),round(am*2000)))
        assert np.all(np.diff(actual)<0),key
        assert all(exact_ratios[i]>exact_ratios[i+1] for i in range(62)),('rounded kbps order',key)
        rounded_checks.append(dict(period=key[0],quarter=int(key[1]),orientation=key[2],
                                   strict_order_preserved=True,exact_rational_order_verified=True,
                                   minimum_rank_gap=float(min(-np.diff(rounded)))))
    pd.DataFrame(rounded_checks).to_csv(OUT/'rounded_kbps_witness_checks.csv',index=False)
    # Exhaustive finite-grid tests exercise the production algorithm only here.
    from coverage_identification_20261030 import median_bounds,rank_bounds
    examples=0;completions=0
    for n in range(1,7):
        for m in range(1,n+1):
            for observed in combinations_with_replacement([1.,2.,5.],m):
                lo,hi=median_bounds(observed,n);exlo,exhi=explicit_bounds(np.array(observed),n)
                equal(lo,exlo,('toy lower',n,m,observed));equal(hi,exhi,('toy upper',n,m,observed))
                grid=np.array(list(product([0.,.5,1.,2.,5.,20.],repeat=n-m)))
                x=np.column_stack([np.tile(observed,(len(grid),1)),grid]) if n>m else np.array([observed])
                med=np.median(x,axis=1);assert (med>=lo).all() and (med<=hi).all()
                assert abs(med.min()-lo)<1e-12
                if np.isfinite(hi):assert abs(med.max()-hi)<1e-12
                else:assert np.median(np.r_[observed,np.full(n-m,1e6)])>np.median(np.r_[observed,np.full(n-m,1e3)])
                examples+=1;completions+=len(x)
    toys=[([1.,3.,5.],[2.,4.,6.]),([1.,1.,1.],[3.,3.,3.]),([1.,2.,3.],[2.,3.,4.]),
          ([-np.inf,1.,2.],[np.inf,1.,4.])]
    for lower,upper in toys:
        best,worst=rank_bounds(lower,upper);n=len(lower);lb=np.full(n,n);ub=np.ones(n,dtype=int)
        finiteL=np.where(np.isneginf(lower),-100,lower);finiteU=np.where(np.isposinf(upper),100,upper)
        for vals in product(*zip(finiteL,finiteU)):
            for order in permutations(range(n)):
                if all(vals[order[i]]>=vals[order[i+1]] for i in range(n-1)):
                    ranks=np.empty(n,int)
                    for i,j in enumerate(order):ranks[j]=i+1
                    lb=np.minimum(lb,ranks);ub=np.maximum(ub,ranks)
        assert np.array_equal(best,lb) and np.array_equal(worst,ub),(lower,upper,best,worst,lb,ub)
    report=dict(passed=True,numeric_comparisons=checks,independent_spatial_tiles=sum(r['tiles'] for r in spatial),
                spatial_checks=spatial,bound_examples=examples,finite_grid_completions=completions,
                rank_toy_configurations=len(toys),witness_provinces=len(witness),full_orders_verified=witness.groupby(['period','quarter','orientation']).ngroups,
                rounded_integer_kbps_orders_verified=len(rounded_checks),
                real_data_path_uses_production_helpers=False,not_an_independent_research_team=True,
                validation_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='spatial_checks'},indent=2))


if __name__=='__main__':main()
