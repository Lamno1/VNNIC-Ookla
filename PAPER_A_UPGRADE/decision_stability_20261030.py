"""Exploratory fixed-design audit; see decision_stability_specification_20261030.md."""
from pathlib import Path
from itertools import combinations
import hashlib
import importlib.metadata
import json
import math
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr, kendalltau
from upg_common import Data, ROOT, HERE

OUT = HERE / 'decision_stability_20261030'
WINDOWS = {'Q1': [1, 2, 3], 'Q2': [4, 5, 6], 'Q3': [7, 8, 9],
           'Q4': [10, 11, 12], 'H1': list(range(1, 7)),
           'H2': list(range(7, 13)), 'Year': list(range(1, 13))}
SUBSETS = {'all7': list(WINDOWS), 'quarters': ['Q1', 'Q2', 'Q3', 'Q4'],
           'no_Q2_support': ['Q1', 'Q3', 'Q4', 'H2']}
PANELS = {'base': ('median', False), 'monthly_mean': ('mean', False),
          'complete_median': ('median', True), 'complete_mean': ('mean', True)}
KS = (5, 10, 16)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def membership(values, k):
    """Fractional boundary ties, exactly k membership mass, no arbitrary ID ordering."""
    values = np.asarray(values, float)
    assert np.isfinite(values).all() and 0 < k < len(values)
    boundary = np.sort(values)[-k]
    above, tied = values > boundary, values == boundary
    weight = above.astype(float)
    weight[tied] = (k - above.sum()) / tied.sum()
    assert abs(weight.sum() - k) < 1e-12
    return weight, int(tied.sum())


def compare(a, b, k):
    ra, rb = rankdata(-a), rankdata(-b)
    wa, ta = membership(a, k); wb, tb = membership(b, k)
    mass = float(np.minimum(wa, wb).sum())
    i, j = np.triu_indices(len(a), 1)
    sa, sb = np.sign(a[i] - a[j]), np.sign(b[i] - b[j])
    eligible = (sa != 0) & (sb != 0)
    flips = int(((sa != sb) & eligible).sum())
    return dict(N=len(a), k=k, spearman=float(spearmanr(a, b).statistic),
                kendall_tau_b=float(kendalltau(a, b).statistic),
                mean_rank_displacement=float(np.abs(ra-rb).mean()),
                max_rank_displacement=float(np.abs(ra-rb).max()),
                common_top_mass=mass, retention=mass/k, replacements=k-mass,
                jaccard=mass/(2*k-mass), pairs_total=len(i),
                jointly_untied_pairs=int(eligible.sum()), pair_inversions=flips,
                inversion_fraction=flips/eligible.sum(),
                tied_in_either_pairs=int((~eligible).sum()),
                boundary_ties_a=ta, boundary_ties_b=tb)


def audit_inputs():
    paths = [ROOT/'data/interim/fact_vnnic_province_month.parquet',
             ROOT/'RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet',
             HERE/'data/ookla_province_quarter_ext.parquet',
             ROOT/'data/processed/vnnic_q2_validation_2021_2024.parquet',
             ROOT/'data/processed/ookla_fixed_q2_adm1_2021_2024.parquet',
             ROOT/'data/analysis/analysis_panel_2021_2024.parquet',
             ROOT/'data/reference/dim_province_legacy63.parquet',
             HERE/'upg_common.py', Path(__file__),
             HERE/'decision_stability_specification_20261030.md']
    m = pd.read_parquet(paths[0]); m = m[m.network == 'ftth']
    assert not m.duplicated(['province_id_legacy63', 'month']).any()
    a, b = [pd.read_parquet(p) for p in paths[1:3]]
    for x in (a, b): assert not x.duplicated(['shapeISO', 'year', 'quarter']).any()
    same = a.merge(b, on=['shapeISO', 'year', 'quarter'], suffixes=('_a', '_b'))
    for c in ['ookla_tile_median_download_mbps', 'observed_ookla_tiles', 'total_tests']:
        assert np.array_equal(same[c+'_a'], same[c+'_b'])
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}, len(same)


def main():
    OUT.mkdir(exist_ok=True)
    hashes, overlap = audit_inputs(); d = Data(with_ext=True)
    names = pd.read_parquet(ROOT/'data/reference/dim_province_legacy63.parquet')
    names = names.set_index('province_id_legacy63').province_name_official.to_dict()
    arrays = {}; cells = []
    for panel, (agg, complete) in PANELS.items():
        for y in (2021, 2023, 2024):
            for w, months in WINDOWS.items():
                x = d.M.reindex([pd.Timestamp(y, m, 1) for m in months])
                count = x.notna().sum().to_numpy()
                minimum = len(months) if complete else {3: 2, 6: 5, 12: 9}[len(months)]
                v = (x.median().to_numpy() if agg == 'median' else
                     np.array([math.fsum(col.dropna().tolist())/col.notna().sum()
                               for _, col in x.items()]))
                v = np.where(count >= minimum, v, np.nan)
                quarters = sorted({(m-1)//3+1 for m in months})
                o = np.median(np.stack([d.O[(y, q)] for q in quarters]), axis=0)
                assert np.isfinite(o).all()
                arrays[panel, y, w] = (v, o)
                for n, pid in enumerate(d.pids):
                    cells.append(dict(panel=panel, year=y, window=w, province_id=pid,
                                      iso=d.iso[pid], province_name=names[pid],
                                      months=int(count[n]), required_months=minimum,
                                      quarters=len(quarters), V=v[n], O=o[n]))
    pd.DataFrame(cells).to_csv(OUT/'source_panel.csv', index=False)

    rankings=[]; comps=[]; details=[]; group_counts=[]; pair_rows=[]; coverage=[]; aggregate_comps=[]
    cache={}
    for start in (2021, 2023):
        period=f'{start}-2024'
        for panel in PANELS:
            mask = np.logical_and.reduce([np.isfinite(a) for y in (start, 2024)
                                          for w in WINDOWS for a in arrays[panel, y, w]])
            ids=np.array(d.pids)[mask]; n=len(ids); assert n >= 60
            for pid, keep in zip(d.pids, mask):
                coverage.append(dict(period=period, panel=panel, province_id=pid, included=bool(keep)))
            for metric in ('log', 'Mbps'):
                values={}
                for source, j in [('VNNIC', 0), ('Ookla', 1)]:
                    for w in WINDOWS:
                        a=arrays[panel, start, w][j][mask]; b=arrays[panel, 2024, w][j][mask]
                        z=np.log(b/a) if metric=='log' else b-a
                        assert np.isfinite(z).all()
                        values[source, w]=z; cache[period, panel, metric, source, w]=(ids,z)
                        rr=rankdata(-z)
                        weights={k: membership(z,k) for k in KS}
                        for i, pid in enumerate(ids):
                            row=dict(period=period,panel=panel,metric=metric,source=source,window=w,
                                     N=n,province_id=pid,iso=d.iso[pid],province_name=names[pid],
                                     start_value=a[i],end_value=b[i],change=z[i],rank=rr[i])
                            for k in KS:row[f'top{k}']=weights[k][0][i]
                            rankings.append(row)
                base=dict(period=period,panel=panel,metric=metric)
                for w in WINDOWS:
                    for k in KS:
                        comps.append(dict(**base,axis='source',source_a='VNNIC',source_b='Ookla',
                                          window_a=w,window_b=w,**compare(values['VNNIC',w],values['Ookla',w],k)))
                for source in ('VNNIC','Ookla'):
                    for wa,wb in combinations(WINDOWS,2):
                        for k in KS:
                            comps.append(dict(**base,axis='window',source_a=source,source_b=source,
                                              window_a=wa,window_b=wb,**compare(values[source,wa],values[source,wb],k)))
                for subset, windows in SUBSETS.items():
                    for source in ('VNNIC','Ookla','both'):
                        keys=[(s,w) for s in ('VNNIC','Ookla') if source in (s,'both') for w in windows]
                        all_ranks=np.stack([rankdata(-values[key]) for key in keys])
                        for k in KS:
                            all_members=np.stack([membership(values[key],k)[0] for key in keys])
                            freqs=all_members.mean(axis=0)
                            group_counts.append(dict(**base,subset=subset,source=source,k=k,N=n,
                                                     scenarios=len(keys),always=int((freqs==1).sum()),
                                                     ever=int((freqs>0).sum()),never=int((freqs==0).sum()),
                                                     sometimes=int(((freqs>0)&(freqs<1)).sum())))
                            for i,pid in enumerate(ids):
                                details.append(dict(**base,subset=subset,source=source,k=k,N=n,
                                                    scenarios=len(keys),province_id=pid,iso=d.iso[pid],province_name=names[pid],
                                                    rank_min=all_ranks[:,i].min(),rank_max=all_ranks[:,i].max(),
                                                    rank_range=np.ptp(all_ranks[:,i]),rank_median=np.median(all_ranks[:,i]),
                                                    membership_sum=all_members[:,i].sum(),scenario_frequency=freqs[i]))
                    # Localise all pairwise directions across both sources, for each subset.
                    keys=[(s,w) for s in ('VNNIC','Ookla') for w in windows]
                    i,j=np.triu_indices(n,1)
                    signs=np.stack([np.sign(values[key][i]-values[key][j]) for key in keys])
                    pos=(signs>0).sum(axis=0);neg=(signs<0).sum(axis=0);ties=(signs==0).sum(axis=0)
                    for q in range(len(i)):
                        pair_rows.append(dict(**base,subset=subset,province_a=ids[i[q]],province_b=ids[j[q]],
                                              positive=int(pos[q]),negative=int(neg[q]),ties=int(ties[q]),
                                              scenarios=len(keys),both_directions=bool(pos[q]>0 and neg[q]>0)))
        # Matched aggregation comparisons restrict BOTH panels to common provinces.
        for metric in ('log','Mbps'):
            for a_panel,b_panel in [('base','monthly_mean'),('complete_median','complete_mean'),('base','complete_median')]:
                for source in ('VNNIC','Ookla'):
                    for w in WINDOWS:
                        ai,a=cache[period,a_panel,metric,source,w];bi,b=cache[period,b_panel,metric,source,w]
                        common=sorted(set(ai)&set(bi));a=pd.Series(a,index=ai).loc[common].to_numpy();b=pd.Series(b,index=bi).loc[common].to_numpy()
                        for k in KS:
                            aggregate_comps.append(dict(period=period,metric=metric,source=source,window=w,
                                                        panel_a=a_panel,panel_b=b_panel,**compare(a,b,k)))

    tables={'rankings':rankings,'comparisons':comps,'province_scenarios':details,
            'selection_summary':group_counts,'pair_directions':pair_rows,'coverage':coverage,
            'aggregation_comparisons':aggregate_comps}
    for name,rows in tables.items(): pd.DataFrame(rows).to_csv(OUT/f'{name}.csv',index=False)
    c=pd.DataFrame(comps)
    summary=c.groupby(['period','panel','metric','axis','source_a','k'],sort=False).agg(
        comparisons=('retention','size'),retention_min=('retention','min'),retention_median=('retention','median'),
        retention_max=('retention','max'),rho_min=('spearman','min'),rho_median=('spearman','median'),rho_max=('spearman','max'),
        inversions_min=('inversion_fraction','min'),inversions_median=('inversion_fraction','median'),
        inversions_max=('inversion_fraction','max'),rank_displacement_mean=('mean_rank_displacement','mean')).reset_index()
    summary.to_csv(OUT/'comparison_summary.csv',index=False)
    # Reconcile with published saved L4 values, not merely internal sums.
    h=pd.read_csv(HERE/'results_halfyear_20261030/L4.csv')
    post=pd.read_csv(HERE/'results_postshift_20261030/L4.csv')
    reconciled=0
    for half in ('H1','H2'):
        for metric in ('log','Mbps'):
            obs=c[(c.period=='2021-2024')&(c.panel=='base')&(c.metric==metric)&(c.axis=='source')&(c.window_a==half)&(c.k==10)].iloc[0].spearman
            expected=h[(h.rule=='min5')&(h.half==half)&(h.scale==metric)].iloc[0].rho
            assert abs(obs-expected)<1e-12;reconciled+=1
    for w,old in [('Q1','1'),('Q2','2'),('Q3','3'),('Q4','4'),('Year','year')]:
        for metric in ('log','Mbps'):
            obs=c[(c.period=='2023-2024')&(c.panel=='base')&(c.metric==metric)&(c.axis=='source')&(c.window_a==w)&(c.k==10)].iloc[0].spearman
            expected=post[(post.window.astype(str)==old)&(post.scale==metric)].iloc[0].rho
            assert abs(obs-expected)<1e-12;reconciled+=1
    report=dict(mode='EXPLORATORY_FIXED_DESIGN_DESCRIPTIVE',input_hashes=hashes,
                duplicate_ookla_overlap_rows_verified=overlap,
                design=dict(periods=['2021-2024','2023-2024'],windows=list(WINDOWS),panels=PANELS,
                            metrics=['log','Mbps'],selection_sizes=KS,subsets=SUBSETS),
                row_counts={k:len(v) for k,v in tables.items()},prior_result_reconciliations=reconciled,
                packages={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','pyarrow']},
                no_inferential_tests=True,no_independent_measurement_validation=True)
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(summary[(summary.panel=='base')&(summary.metric=='log')&(summary.k==10)].to_string(index=False))
    print('Saved complete results; prior L4 point estimates reconciled:',reconciled)


if __name__=='__main__': main()
