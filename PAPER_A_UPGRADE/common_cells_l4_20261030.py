"""Cross-source L4 with common-cell Ookla change (spec item 4)."""
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import upg_common as U
d=U.Data(); P=pd.read_csv('results_common_cells_20261030.csv')
iso2pid={v:k for k,v in d.iso.items()}
R=[]
for y0 in (2021,2023):
  for q in (1,2,3,4):
    g=P[(P.start==y0)&(P.quarter==q)].copy(); g['pid']=g.iso.map(iso2pid); g=g.set_index('pid').reindex(d.pids)
    v=np.log(np.asarray(d.V(2024,q),float)/np.asarray(d.V(y0,q),float))
    R.append(dict(start=y0,quarter=q,rho_avail=spearmanr(v,g.avail).statistic,rho_common=spearmanr(v,g.common).statistic))
    print(y0,q,'avail',round(spearmanr(v,g.avail).statistic,3),'common',round(spearmanr(v,g.common).statistic,3))

pd.DataFrame(R).to_csv('results_common_cells_l4_20261030.csv',index=False)
