"""Second aggregation path: direct tables and scipy, not Data or analysis helpers."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;OUT=HERE/'results_halfyear_20261030'
v=pd.read_parquet(ROOT/'data/interim/fact_vnnic_province_month.parquet');v=v[(v.network=='ftth')].copy()
v['year']=pd.to_datetime(v.month).dt.year;v['half']=(pd.to_datetime(v.month).dt.month>6).astype(int)+1
q=pd.concat([pd.read_parquet(ROOT/'RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet'),pd.read_parquet(HERE/'data/ookla_province_quarter_ext.parquet')]).drop_duplicates(['shapeISO','year','quarter'])
q=q[q.year.between(2021,2024)].copy();q['half']=(q.quarter>2).astype(int)+1
lookup=pd.read_parquet(ROOT/'data/processed/vnnic_q2_validation_2021_2024.parquet')[['province_id_legacy63','shapeISO']].drop_duplicates()
q=q.merge(lookup,on='shapeISO',validate='many_to_one')
checks=0
for rule,nmonths in [('min5',5),('strict6',6)]:
    a=v[v.year.between(2021,2024)].groupby(['province_id_legacy63','year','half']).download.agg(['median','count']).reset_index()
    a=a[a['count']>=nmonths].rename(columns={'median':'V'})
    b=q.groupby(['province_id_legacy63','year','half']).ookla_tile_median_download_mbps.agg(['mean','count']).reset_index()
    b=b[b['count']==2].rename(columns={'mean':'O'})
    panel=a.merge(b,on=['province_id_legacy63','year','half'],validate='one_to_one')
    saved=pd.read_csv(OUT/'province_halfyear.csv').rename(columns={'province_id':'province_id_legacy63'});saved=saved[saved.rule==rule].copy();saved['half']=saved.half.str[1:].astype(int)
    merged=panel.merge(saved,on=['province_id_legacy63','year','half'],suffixes=('_direct','_saved'),validate='one_to_one')
    assert len(merged)==saved[['V','O']].dropna().shape[0]
    for c in ['V','O']:
        assert np.allclose(merged[c+'_direct'],merged[c+'_saved'],atol=1e-12,rtol=1e-14)
        checks+=len(merged)
    l3=pd.read_csv(OUT/'L3.csv');l4=pd.read_csv(OUT/'L4.csv');l1=pd.read_csv(OUT/'L1.csv');l2=pd.read_csv(OUT/'L2.csv')
    for y in range(2021,2025):
        for h in (1,2):
            t=panel[(panel.year==y)&(panel.half==h)]
            wanted=spearmanr(t.V,t.O).statistic
            r=l3[(l3.rule==rule)&(l3.half==f'H{h}')&(l3.year==str(y))].iloc[0]
            assert abs(wanted-r.rho)<1e-14;checks+=1
    for h in (1,2):
        t=panel[(panel.half==h)&(panel.year==2021)].merge(panel[(panel.half==h)&(panel.year==2024)],on='province_id_legacy63',suffixes=('_21','_24'))
        r=l1[(l1.rule==rule)&(l1.half==f'H{h}')].iloc[0]
        assert abs(r.V_ratio-t.V_24.median()/t.V_21.median())<1e-14
        assert abs(r.O_ratio-t.O_24.median()/t.O_21.median())<1e-14;checks+=2
        for scale in ['log','Mbps']:
            x=np.log(t.V_24/t.V_21) if scale=='log' else t.V_24-t.V_21
            y=np.log(t.O_24/t.O_21) if scale=='log' else t.O_24-t.O_21
            wanted=spearmanr(x,y).statistic
            r=l4[(l4.rule==rule)&(l4.half==f'H{h}')&(l4.scale==scale)].iloc[0]
            assert abs(wanted-r.rho)<1e-14;checks+=1
        def dispersion(series):
            return {'sd_level':series.std(ddof=1),'sd_log':np.log(series).std(ddof=1),'cv':series.std(ddof=1)/series.mean(),
                    'iqr':series.quantile(.75)-series.quantile(.25),'p90_p10':series.quantile(.9)/series.quantile(.1),'max_min':series.max()/series.min()}
        stats={}
        for source,c in [('VNNIC','V'),('Ookla','O')]:
            before=dispersion(t[c+'_21']);after=dispersion(t[c+'_24'])
            stats[source]={k:np.log(after[k]/before[k]) for k in before}
            for k,wanted in stats[source].items():
                r=l2[(l2.rule==rule)&(l2.half==f'H{h}')&(l2.source==source)&(l2.indicator==k)].iloc[0]
                assert abs(wanted-r.estimate)<1e-13;checks+=1
        for k in stats['VNNIC']:
            wanted=stats['VNNIC'][k]-stats['Ookla'][k]
            r=l2[(l2.rule==rule)&(l2.half==f'H{h}')&(l2.source=='VNNIC minus Ookla')&(l2.indicator==k)].iloc[0]
            assert abs(wanted-r.estimate)<1e-13;checks+=1
coverage=pd.read_csv(OUT/'coverage.csv');missing=coverage[~coverage.included]
result={'second_path_numeric_comparisons':checks,'passed':True,'scope':'Direct saved input reaggregation and point estimates; bootstrap engine has 12 explicit scipy checks in analysis report.',
        'excluded_cells':missing.to_dict('records'),'not_independent_team':True}
(OUT/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
