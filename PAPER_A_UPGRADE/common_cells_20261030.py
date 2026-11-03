"""Common-cell sensitivity of Ookla provincial speed changes (spec: common_cells_specification_20261030.md)."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import upg_common as U
HERE=Path(__file__).resolve().parent
T=HERE/'data/coverage_tiles_canonical_20261030'
d=U.Data()
def load(y,q):
    f=pd.read_parquet(T/f'{y}Q{q}.parquet',columns=['quadkey','legacy_shapeISO','download_mbps'])
    return f[f.legacy_shapeISO!=''].set_index('quadkey')
rows=[];prov=[]
for y0 in (2021,2023):
  for q in (1,2,3,4):
    a,b=load(y0,q),load(2024,q)
    for iso in sorted(set(a.legacy_shapeISO)|set(b.legacy_shapeISO)):
        A=a[a.legacy_shapeISO==iso].download_mbps;B=b[b.legacy_shapeISO==iso].download_mbps
        com=A.index.intersection(B.index);un=A.index.union(B.index)
        r=dict(start=y0,quarter=q,iso=iso,n_a=len(A),n_b=len(B),n_common=len(com),jaccard=len(com)/len(un),
               avail=np.log(B.median()/A.median()),common=np.nan)
        if len(com)>=10:r['common']=np.log(B[com].median()/A[com].median())
        prov.append(r)
P=pd.DataFrame(prov);P.to_csv(HERE/'results_common_cells_20261030.csv',index=False)
out=[]
for (y0,q),g in P.groupby(['start','quarter']):
    ok=g.dropna(subset=['common'])
    out.append(dict(start=y0,quarter=q,provinces=len(g),computed=len(ok),median_jaccard=g.jaccard.median(),
      min_jaccard=g.jaccard.min(),median_common_share_of_start=(g.n_common/g.n_a).median(),median_common_share_of_end=(g.n_common/g.n_b).median(),
      rho_avail_vs_common=spearmanr(ok.avail,ok.common).statistic,
      mean_abs_diff=(ok.avail-ok.common).abs().mean()))
S=pd.DataFrame(out);S.to_csv(HERE/'results_common_cells_summary_20261030.csv',index=False)
pd.set_option('display.width',250);print(S.round(3).to_string())
