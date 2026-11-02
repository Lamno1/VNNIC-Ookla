"""Standalone scientific figures from saved, validated outputs."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'PAPER_A_UPGRADE/decision_stability_20261030'
OUT=ROOT/'reports/decision_stability_20261030'
W=['Q1','Q2','Q3','Q4','H1','H2','Year']
PERIODS=['2021-2024','2023-2024']


def main():
    OUT.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42,'ps.fonttype':42})
    c=pd.read_csv(DATA/'comparisons.csv')
    c=c[(c.panel=='base')&(c.metric=='log')&(c.axis=='source')&(c.k==10)]
    c.to_csv(OUT/'primary_source_comparisons.csv',index=False)
    fig,axs=plt.subplots(1,2,figsize=(9.4,5.1),layout='constrained')
    ag=pd.read_csv(DATA/'aggregation_comparisons.csv')
    ag=ag[(ag.metric=='log')&(ag.source=='VNNIC')&(ag.k==10)&(ag.panel_a=='base')&(ag.panel_b=='monthly_mean')]
    for ax,(data,index,title) in zip(axs,[(c,'window_a','(a) VNNIC versus Ookla'),
                                        (ag,'window','(b) VNNIC: median versus mean months')]):
        a=data.pivot(index=index,columns='period',values='common_top_mass').reindex(index=W,columns=PERIODS).to_numpy()
        vmax=10;im=ax.imshow(a,vmin=0,vmax=vmax,cmap='YlGnBu',aspect='auto')
        ax.set_xticks([0,1],PERIODS);ax.set_yticks(range(7),W)
        ax.set_title(title,fontsize=11,pad=12)
        for i in range(7):
            for j in range(2):ax.text(j,i,f'{a[i,j]:.0f}',ha='center',va='center',color='white' if a[i,j]>(vmax*.65) else '#182229',fontsize=12)
        fig.colorbar(im,ax=ax,shrink=.75,pad=.03)
    fig.supxlabel('Common provinces in two top-10 lists; log speed improvement; N = 63.\nPanel (a) reference: independent uniform lists share 1.59 provinces (8.41 replacements) on average.\nThis reference is not a calibrated null for the observed rankings. Panel (b) changes only monthly aggregation.',fontsize=8)
    fig.savefig(OUT/'decision_stability_summary.pdf',bbox_inches='tight')
    fig.savefig(OUT/'decision_stability_summary.png',dpi=180,bbox_inches='tight');plt.close(fig)
    r=pd.read_csv(DATA/'rankings.csv');r=r[(r.panel=='base')&(r.metric=='log')]
    for period in PERIODS:
        t=r[r.period==period].copy();t['column']=t.source+' '+t.window
        ids=sorted(t.province_id.unique());cols=[s+' '+w for s in ['VNNIC','Ookla'] for w in W]
        ranks=t.pivot(index='province_id',columns='column',values='rank').loc[ids,cols]
        weights=t.pivot(index='province_id',columns='column',values='top10').loc[ids,cols]
        names=t.drop_duplicates('province_id').set_index('province_id').loc[ids,'province_name']
        fig,ax=plt.subplots(figsize=(10.6,14),layout='constrained')
        im=ax.imshow(ranks.to_numpy(),aspect='auto',cmap='viridis_r',vmin=1,vmax=63)
        ax.set_yticks(range(len(ids)),names,fontsize=8)
        ax.set_xticks(range(14),W+W,fontsize=9);ax.xaxis.tick_top()
        ax.tick_params(axis='both',length=0)
        ax.axvline(6.5,color='white',linewidth=3)
        ax.text(3,1.025,'VNNIC',ha='center',transform=ax.get_xaxis_transform(),fontsize=11)
        ax.text(10,1.025,'Ookla',ha='center',transform=ax.get_xaxis_transform(),fontsize=11)
        yy,xx=np.where(weights.to_numpy()>0)
        ax.scatter(xx,yy,marker='s',s=43,facecolors='none',edgecolors='#111111',linewidths=.7)
        ax.set_title(f'Provincial log-speed improvement ranks, {period}',pad=47,fontsize=13)
        cb=fig.colorbar(im,ax=ax,shrink=.45,pad=.025,ticks=[1,10,20,30,40,50,63])
        cb.set_label('Descending rank (1 = largest observed improvement)')
        fig.supxlabel('Outlined cells belong to the top 10. Every province and all 14 rankings are shown.\nWindow changes alter the temporal target; ranks measure neither accuracy nor investment need.',fontsize=9)
        name=f'province_rankings_{period.replace("-","_")}'
        fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight')
        fig.savefig(OUT/(name+'.png'),dpi=150,bbox_inches='tight');plt.close(fig)
    print('Saved three figures as PDF and PNG in',OUT)


if __name__=='__main__':main()
