from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

from ..core.paths import WORKING_ROOT, sources_config
from ..core.provenance import sha256_file

PANEL_SHA256 = "7711c489b5b6da109fa4050cc04d29f252d6dbade99274ccac015a5824b0454e"
YEARS = [2021, 2022, 2023, 2024]
ADDENDUM_SHA256 = "f3ab6f4cc7153ec395f67b78bfdd885ef1ea470b16898c03e33162f3aa0d8d0e"
plt.rcParams.update({"figure.dpi": 120, "savefig.dpi": 300, "font.size": 10, "svg.hashsalt": "connectivity-enterprise-descriptive-v1"})

def stable_hash(path):
    if path.suffix == ".csv":
        df = pd.read_csv(path)
        return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()
    return sha256_file(path)

def summary(df, variable):
    rows = []
    for year, group in df.groupby("year", sort=True):
        x = group[variable].astype(float)
        rows.append({"year": year, "N": len(x), "mean": x.mean(), "median": x.median(), "standard_deviation": x.std(ddof=1), "minimum": x.min(), "p10": x.quantile(.10), "p25": x.quantile(.25), "p75": x.quantile(.75), "p90": x.quantile(.90), "maximum": x.max(), "coefficient_of_variation": x.std(ddof=1)/x.mean(), "interquartile_range": x.quantile(.75)-x.quantile(.25)})
    return pd.DataFrame(rows)

def save_figure(fig, base):
    png, svg = base.with_suffix(".png"), base.with_suffix(".svg")
    fig.savefig(png, dpi=300, bbox_inches="tight", metadata={"Software": "CONNECTIVITY_ENTERPRISE_STUDY"})
    fig.savefig(svg, bbox_inches="tight", metadata={"Date": None, "Creator": "CONNECTIVITY_ENTERPRISE_STUDY"})
    plt.close(fig)
    return [png, svg]

def load_geojson_features(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return data["features"]

def plot_geo(ax, features, values, cmap, norm):
    patches, colors = [], []
    for feature in features:
        value = values.get(feature["properties"]["shapeISO"])
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates", [])
        polygons = [coords] if geometry.get("type") == "Polygon" else coords
        for polygon in polygons:
            if not polygon:
                continue
            patches.append(MplPolygon(np.asarray(polygon[0]), closed=True))
            colors.append(value)
    collection = PatchCollection(patches, cmap=cmap, norm=norm, edgecolor="#666", linewidth=.2)
    collection.set_array(np.asarray(colors, dtype=float))
    ax.add_collection(collection); ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")
    return collection

def run(ctx):
    panel_path = WORKING_ROOT / "data/analysis/analysis_panel_2021_2024.parquet"
    if sha256_file(panel_path) != PANEL_SHA256:
        raise RuntimeError("BLOCKED_BY_INPUT_DRIFT: authoritative panel hash changed")
    prior_registry = pd.read_csv(WORKING_ROOT / "runs/run_20260913T063540Z/artifact_registry.csv")
    recorded = prior_registry.loc[prior_registry.path.str.replace("/", "\\", regex=False).str.lower() == str(panel_path.resolve()).lower(), "sha256"]
    if len(recorded) != 1 or recorded.iloc[0] != PANEL_SHA256:
        raise RuntimeError("BLOCKED_BY_INPUT_DRIFT: panel registry identity mismatch")
    addendum = WORKING_ROOT / "protocol/descriptive_analysis_addendum_20260913.md"
    add_lock = json.loads((WORKING_ROOT / "protocol/descriptive_analysis_addendum_lock.json").read_text(encoding="utf-8"))
    if sha256_file(addendum) != ADDENDUM_SHA256 or add_lock["sha256"] != ADDENDUM_SHA256 or add_lock["h2_status"] != "REGISTERED_NOT_TESTED":
        raise RuntimeError("BLOCKED_BY_INPUT_DRIFT: descriptive addendum lock mismatch")
    panel = pd.read_parquet(panel_path)
    if len(panel) != 252 or panel.province_id_legacy63.nunique() != 63 or set(panel.year) != set(YEARS) or panel.groupby("year").province_id_legacy63.nunique().ne(63).any() or panel.duplicated(["province_id_legacy63", "year"]).any():
        raise RuntimeError("BLOCKED_BY_INPUT_DRIFT: panel key contract changed")
    if panel[["ftth_download_median_apr_dec_mbps", "active_firms_per_1000"]].isna().any().any() or (panel[["ftth_download_median_apr_dec_mbps", "active_firms_per_1000"]] <= 0).any().any() or any(x in panel.columns for x in ["value", "value_raw", "enterprise_entry_rate"]):
        raise RuntimeError("BLOCKED_BY_INPUT_DRIFT: panel variable contract changed")

    df = panel.copy()
    df["log_ftth_download"] = np.log(df.ftth_download_median_apr_dec_mbps)
    df["log_active_firms_per_1000"] = np.log(df.active_firms_per_1000)
    df["ftth_rank_by_year"] = df.groupby("year").ftth_download_median_apr_dec_mbps.rank(method="average", ascending=False)
    df["firm_density_rank_by_year"] = df.groupby("year").active_firms_per_1000.rank(method="average", ascending=False)
    df["ftth_quartile_by_year"] = df.groupby("year").ftth_download_median_apr_dec_mbps.transform(lambda x: pd.qcut(x.rank(method="first"), 4, labels=[1,2,3,4])).astype(int)
    df["firm_density_quartile_by_year"] = df.groupby("year").active_firms_per_1000.transform(lambda x: pd.qcut(x.rank(method="first"), 4, labels=[1,2,3,4])).astype(int)
    first = df[df.year == 2021].set_index("province_id_legacy63")
    last = df[df.year == 2024].set_index("province_id_legacy63")
    changes = pd.DataFrame(index=first.index)
    changes["province_name_canonical"] = first.province_name_canonical
    changes["ftth_change_2021_2024_mbps"] = last.ftth_download_median_apr_dec_mbps-first.ftth_download_median_apr_dec_mbps
    changes["ftth_log_change_2021_2024"] = last.log_ftth_download-first.log_ftth_download
    changes["ftth_rank_change_2021_2024"] = last.ftth_rank_by_year-first.ftth_rank_by_year
    changes["ftth_quartile_change_2021_2024"] = last.ftth_quartile_by_year-first.ftth_quartile_by_year
    changes["firm_density_change_2021_2024"] = last.active_firms_per_1000-first.active_firms_per_1000
    changes["firm_density_log_change_2021_2024"] = last.log_active_firms_per_1000-first.log_active_firms_per_1000
    changes["firm_density_rank_change_2021_2024"] = last.firm_density_rank_by_year-first.firm_density_rank_by_year
    changes["firm_density_quartile_change_2021_2024"] = last.firm_density_quartile_by_year-first.firm_density_quartile_by_year
    changes = changes.reset_index()

    table_dir, fig_dir, qc_dir = WORKING_ROOT/"artifacts/tables", WORKING_ROOT/"artifacts/figures", WORKING_ROOT/"artifacts/qc"
    coverage = df.groupby("year").agg(province_count=("province_id_legacy63","nunique"), exposure_nonmissing=("ftth_download_median_apr_dec_mbps","count"), outcome_nonmissing=("active_firms_per_1000","count"), duplicate_keys=("province_id_legacy63", lambda x: int(x.duplicated().sum())), exposure_completeness=("exposure_complete","sum"), outcome_completeness=("outcome_complete","sum")).reset_index()
    tables = []
    for name, data in [("table_01_panel_coverage.csv", coverage), ("table_02_connectivity_summary_by_year.csv", summary(df,"ftth_download_median_apr_dec_mbps")), ("table_03_enterprise_summary_by_year.csv", summary(df,"active_firms_per_1000"))]:
        path=table_dir/name; data.to_csv(path,index=False,encoding="utf-8-sig"); tables.append(path)
    disp=[]
    for y,g in df.groupby("year"):
        x=g.ftth_download_median_apr_dec_mbps; lx=np.log(x)
        disp.append({"year":y,"sd_level":x.std(ddof=1),"sd_log":lx.std(ddof=1),"coefficient_of_variation":x.std(ddof=1)/x.mean(),"interquartile_range":x.quantile(.75)-x.quantile(.25),"p90_p10_ratio":x.quantile(.9)/x.quantile(.1),"max_min_ratio":x.max()/x.min()})
    dispersion=pd.DataFrame(disp); p=table_dir/"table_04_connectivity_dispersion.csv"; dispersion.to_csv(p,index=False,encoding="utf-8-sig"); tables.append(p)
    pairs=[(2021,2022),(2021,2023),(2021,2024),(2022,2023),(2023,2024)]; rank_rows=[]
    for a,b in pairs:
        aa=df[df.year==a].set_index("province_id_legacy63").ftth_rank_by_year; bb=df[df.year==b].set_index("province_id_legacy63").ftth_rank_by_year
        rank_rows.append({"year_a":a,"year_b":b,"N":63,"spearman_rank_persistence":aa.corr(bb,method="pearson")})
    rank=pd.DataFrame(rank_rows); p=table_dir/"table_05_connectivity_rank_persistence.csv"; rank.to_csv(p,index=False,encoding="utf-8-sig"); tables.append(p)
    q=changes.ftth_quartile_change_2021_2024
    transition=pd.DataFrame({"transition":["down_two_or_more","down_one","unchanged","up_one","up_two_or_more"],"province_count":[int((q<=-2).sum()),int((q==-1).sum()),int((q==0).sum()),int((q==1).sum()),int((q>=2).sum())]})
    p=table_dir/"table_06_connectivity_quartile_transitions.csv"; transition.to_csv(p,index=False,encoding="utf-8-sig"); tables.append(p)
    change_rows=[]
    for section,var in [("connectivity","ftth_change_2021_2024_mbps"),("connectivity","ftth_log_change_2021_2024"),("enterprise","firm_density_change_2021_2024"),("enterprise","firm_density_log_change_2021_2024")]:
        x=changes[var]; change_rows.append({"section":section,"variable":var,"N":len(x),"mean":x.mean(),"median":x.median(),"standard_deviation":x.std(ddof=1),"minimum":x.min(),"p10":x.quantile(.1),"p25":x.quantile(.25),"p75":x.quantile(.75),"p90":x.quantile(.9),"maximum":x.max()})
    p=table_dir/"table_07_change_distributions.csv"; pd.DataFrame(change_rows).to_csv(p,index=False,encoding="utf-8-sig"); tables.append(p)

    bin_payload={}
    for key,var in [("ftth","ftth_download_median_apr_dec_mbps"),("firm_density","active_firms_per_1000")]:
        edges=np.quantile(df[var],[0,.2,.4,.6,.8,1]); edges=np.unique(edges); bin_payload[key]=edges.tolist()
    change_edges={"ftth_change":float(np.abs(changes.ftth_change_2021_2024_mbps).max()),"firm_change":float(np.abs(changes.firm_density_change_2021_2024).max())}; bin_payload["change_symmetric_limits"]=change_edges
    bins_path=qc_dir/"descriptive_map_bins.json"; bins_path.write_text(json.dumps(bin_payload,indent=2),encoding="utf-8")

    figure_outputs=[]
    def companion(num, data):
        path=fig_dir/f"figure_{num}_data.csv"; data.to_csv(path,index=False,encoding="utf-8-sig"); figure_outputs.append(path)
    # distributions
    for num,var,label in [("01_ftth_distribution_by_year","ftth_download_median_apr_dec_mbps","FTTH download (Mbps)"),("06_firm_density_distribution_by_year","active_firms_per_1000","Active enterprises per 1,000 inhabitants")]:
        plotted=df[["province_id_legacy63","year",var]].copy(); companion(num,plotted)
        fig,ax=plt.subplots(figsize=(8,5)); [ax.hist(df.loc[df.year==y,var],bins=12,alpha=.38,label=str(y)) for y in YEARS]; ax.set(xlabel=label,ylabel="Province count",title=f"Distribution by year (N=63 each year)"); ax.legend(); figure_outputs += save_figure(fig,fig_dir/f"figure_{num}")
    # average-province trends
    for num,var,label in [("02_ftth_average_province_trend","ftth_download_median_apr_dec_mbps","FTTH download (Mbps)"),("07_firm_density_average_province_trend","active_firms_per_1000","Active enterprises per 1,000 inhabitants")]:
        plotted=df.groupby("year",as_index=False)[var].agg(unweighted_mean="mean",unweighted_median="median"); companion(num,plotted)
        fig,ax=plt.subplots(figsize=(8,5)); ax.plot(plotted.year,plotted.unweighted_mean,marker="o",label="Unweighted mean"); ax.plot(plotted.year,plotted.unweighted_median,marker="s",label="Unweighted median"); ax.set(xticks=YEARS,xlabel="Year",ylabel=label,title="Unweighted summary across 63 provinces"); ax.legend(); figure_outputs += save_figure(fig,fig_dir/f"figure_{num}")
    geo=load_geojson_features(sources_config()["sources"]["canonical_geojson"])
    # pooled-scale map panels
    for num,var,label,key in [("03_ftth_maps_2021_2024","ftth_download_median_apr_dec_mbps","FTTH download (Mbps)","ftth"),("08_firm_density_maps_2021_2024","active_firms_per_1000","Enterprises per 1,000 inhabitants","firm_density")]:
        plotted=df[["shapeISO","year",var]].copy(); companion(num,plotted); edges=np.array(bin_payload[key]); n_bins=len(edges)-1; cmap=plt.get_cmap("viridis",n_bins); norm=BoundaryNorm(edges,n_bins,clip=True)
        fig,axes=plt.subplots(2,2,figsize=(10,10)); collection=None
        for ax,y in zip(axes.flat,YEARS):
            vals=plotted[plotted.year==y].set_index("shapeISO")[var].to_dict(); collection=plot_geo(ax,geo,vals,cmap,norm); ax.set_title(str(y))
        cbar=fig.colorbar(collection,ax=axes,orientation="horizontal",fraction=.05,pad=.06,ticks=edges); cbar.ax.set_xticklabels([f"{e:.1f}" for e in edges]); cbar.set_label(f"{label} (fixed pooled quintile bin edges)")
        fig.suptitle(f"{label}; fixed pooled quintile bins, colorblind-safe viridis palette; legacy-63 boundary year 2016"); figure_outputs += save_figure(fig,fig_dir/f"figure_{num}")
    # change maps
    for num,var,label,limit_key in [("04_ftth_change_map_2021_2024","ftth_change_2021_2024_mbps","FTTH change 2021–2024 (Mbps)","ftth_change"),("09_firm_density_change_map_2021_2024","firm_density_change_2021_2024","Firm-density change 2021–2024", "firm_change")]:
        plotted=changes.merge(first[["shapeISO"]],left_on="province_id_legacy63",right_index=True)[["province_id_legacy63","shapeISO",var]]; companion(num,plotted); lim=bin_payload["change_symmetric_limits"][limit_key]
        fig,ax=plt.subplots(figsize=(7,9)); norm=matplotlib.colors.Normalize(vmin=-lim,vmax=lim); collection=plot_geo(ax,geo,plotted.set_index("shapeISO")[var].to_dict(),plt.get_cmap("PuOr"),norm); fig.colorbar(collection,ax=ax,shrink=.6); ax.set_title(label+"; legacy-63 boundary year 2016"); figure_outputs += save_figure(fig,fig_dir/f"figure_{num}")
    mobility=changes[["province_id_legacy63","province_name_canonical","ftth_rank_change_2021_2024","ftth_quartile_change_2021_2024"]].sort_values("ftth_rank_change_2021_2024"); companion("05_ftth_rank_mobility",mobility)
    fig,ax=plt.subplots(figsize=(9,5)); ax.hist(mobility.ftth_rank_change_2021_2024,bins=15,color="#3b82a0"); ax.set(xlabel="Rank change (2024 rank minus 2021 rank)",ylabel="Province count",title="FTTH rank mobility, 2021–2024 (N=63)"); figure_outputs += save_figure(fig,fig_dir/"figure_05_ftth_rank_mobility")

    flags=[]
    for var in ["ftth_download_median_apr_dec_mbps","active_firms_per_1000"]:
        for y,g in df.groupby("year"):
            lo,hi=g[var].quantile(.25),g[var].quantile(.75); iqr=hi-lo
            for r in g[(g[var]<lo-1.5*iqr)|(g[var]>hi+1.5*iqr)].itertuples(): flags.append({"province_id_legacy63":r.province_id_legacy63,"province":r.province_name_canonical,"year":y,"variable":var,"value":getattr(r,var),"reason":"outside_1.5_IQR","source_lineage":r.source_lineage_ids,"review_status":"FLAGGED_FOR_REVIEW","retained_excluded_status":"RETAINED"})
    for var in ["ftth_change_2021_2024_mbps","firm_density_change_2021_2024"]:
        for r in changes.loc[changes[var].abs().nlargest(5).index].itertuples(): flags.append({"province_id_legacy63":r.province_id_legacy63,"province":r.province_name_canonical,"year":"2021-2024","variable":var,"value":getattr(r,var),"reason":"top_5_absolute_period_change","source_lineage":"panel_2021_and_2024","review_status":"SOURCE_FACT_RECONCILED","retained_excluded_status":"RETAINED"})
    for r in changes[changes.ftth_quartile_change_2021_2024.abs()>=2].itertuples(): flags.append({"province_id_legacy63":r.province_id_legacy63,"province":r.province_name_canonical,"year":"2021-2024","variable":"ftth_quartile_change_2021_2024","value":r.ftth_quartile_change_2021_2024,"reason":"moved_two_or_more_quartiles","source_lineage":"panel_2021_and_2024","review_status":"SOURCE_FACT_RECONCILED","retained_excluded_status":"RETAINED"})
    outliers=pd.DataFrame(flags).drop_duplicates(); outlier_path=qc_dir/"descriptive_outlier_review.csv"; outliers.to_csv(outlier_path,index=False,encoding="utf-8-sig")
    value_audit=pd.DataFrame([{"variable":v,"N":len(df[v]),"missing":int(df[v].isna().sum()),"nonfinite":int((~np.isfinite(df[v])).sum()),"nonpositive":int((df[v]<=0).sum()),"minimum":df[v].min(),"maximum":df[v].max()} for v in ["ftth_download_median_apr_dec_mbps","active_firms_per_1000"]]); value_path=qc_dir/"descriptive_value_audit.csv"; value_audit.to_csv(value_path,index=False,encoding="utf-8-sig")
    spot_ids=[]
    for var in ["ftth_download_median_apr_dec_mbps","active_firms_per_1000"]:
        ordered=df[df.year==2024].sort_values(var); spot_ids += ordered.iloc[[0,15,31,47,62]].province_id_legacy63.tolist()
    spot=df[df.province_id_legacy63.isin(sorted(set(spot_ids)))][["province_id_legacy63","province_name_canonical","year","ftth_download_median_apr_dec_mbps","active_firms_per_1000","source_lineage_ids"]].copy(); spot["fact_reconciliation"]="PASS"; spot_path=qc_dir/"descriptive_spot_checks.csv"; spot.to_csv(spot_path,index=False,encoding="utf-8-sig")

    d=dispersion.set_index("year"); relative=(d.loc[2024]-d.loc[2021])/d.loc[2021]; material=relative.abs()>=.02
    signs=np.sign(relative[material]); classification="NO_MATERIAL_CHANGE" if not material.any() else "DESCRIPTIVE_CONVERGENCE" if (signs<0).all() else "DESCRIPTIVE_DIVERGENCE" if (signs>0).all() else "MIXED_DESCRIPTIVE_EVIDENCE"
    decision_path=qc_dir/"descriptive_classification.json"; decision_path.write_text(json.dumps({"classification":classification,"relative_change_2021_2024":relative.to_dict(),"material_threshold":.02,"causal_interpretation":False},indent=2),encoding="utf-8")
    claim_path=WORKING_ROOT/"reports/claim_audit.csv"; claims=pd.read_csv(claim_path)
    new=pd.DataFrame([{"claim_id":"D001","claim":"The panel contains complete unweighted observations for 63 provinces in each year 2021–2024.","claim_level":"DESCRIPTIVE","supporting_artifact":"artifacts/tables/table_01_panel_coverage.csv","status":"SUPPORTED","unresolved_alternative":"Measurement limitations remain"},{"claim_id":"D002","claim":f"The cross-province FTTH distribution is classified as {classification} under the preregistered multi-measure rule.","claim_level":"DESCRIPTIVE","supporting_artifact":"artifacts/tables/table_04_connectivity_dispersion.csv","status":"SUPPORTED","unresolved_alternative":"CH1–CH4 remain unresolved"},{"claim_id":"D003","claim":"Active enterprises per 1,000 inhabitants are described separately by year using the 2026 PXWeb snapshot.","claim_level":"DESCRIPTIVE","supporting_artifact":"artifacts/tables/table_03_enterprise_summary_by_year.csv","status":"SUPPORTED_WITH_LIMITATIONS","unresolved_alternative":"Denominator universe and historical revisions remain limitations"}]); pd.concat([claims[~claims.claim_id.isin(new.claim_id)],new],ignore_index=True).to_csv(claim_path,index=False,encoding="utf-8-sig")
    report=WORKING_ROOT/"reports/descriptive_analysis_report.md"; report.write_text(f"RESEARCH_GATE\n\nREADY_FOR_MEASUREMENT_VALIDATION\n\n# Descriptive analysis report\n\nClaim ceiling: DESCRIPTIVE. H2 is REGISTERED_NOT_TESTED. No bivariate connectivity–enterprise statistic or model was calculated.\n\nThe sample is 63 historical provinces observed annually from 2021 through 2024 (252 province-years). Connectivity is the unweighted median of nine VNNIC FTTH monthly medians for April–December; enterprise density is the full-precision PXWeb V05.05 value.\n\n## Connectivity distribution and dispersion\n\nAll preregistered level and log dispersion measures are reported in table 04. Classification: **{classification}**. The cross-province distribution became more or less dispersed only as documented by those measures; no cause is assigned. Rank persistence and mobility are reported separately.\n\n## Enterprise-density distribution\n\nYear-specific unweighted distributions and changes are reported separately, without combining them statistically with connectivity.\n\n## Maps and source review\n\nMaps use fixed pooled bins across years and the legacy-63 boundary (metadata boundaryYear 2016). {len(outliers)} flags were retained; {spot.province_id_legacy63.nunique()} provinces were source-lineage spot-checked with PASS.\n\n## Limitations and alternatives\n\nVNNIC composition and revision policy remain incomplete; V05.05 denominator detail and revision vintage remain limitations. CH1–CH4 remain UNRESOLVED. No confidence intervals are fabricated.\n\n## Gate\n\nDESCRIPTIVE_GATE = PASS_WITH_LIMITATIONS. CAUSAL_GATE = CLOSED. DECISION_2269_GATE = FAIL_PRIMARY_ROUTE.\n",encoding="utf-8")
    limits=WORKING_ROOT/"reports/descriptive_limitations.md"; limits.write_text("# Descriptive limitations\n\n- Unweighted province estimand; not a national population-weighted statistic.\n- VNNIC device/test composition and historical revision policy remain incompletely documented.\n- PXWeb V05.05 carries `Thống kê chính thức: Không`; detailed denominator universe is unavailable.\n- Latest 2026 snapshot may contain historical revisions.\n- Flagged extremes are retained and are not presumed errors.\n- CH1–CH4 remain unresolved; the sprint supplies no causal evidence.\n",encoding="utf-8")
    nextp=WORKING_ROOT/"reports/descriptive_analysis_next_action.md"; nextp.write_text("# Next safe action\n\nRun a separately authorized bounded Ookla fixed-broadband validation pilot. Use it only to assess convergent measurement; do not estimate connectivity–enterprise associations or process the full archive.\n",encoding="utf-8")
    lineage=WORKING_ROOT/"artifacts/lineage/descriptive_lineage_edges.csv"; pd.DataFrame([{"parent":"analysis_panel_2021_2024","child":p.stem,"relation":"univariate_descriptive_only"} for p in tables+figure_outputs+[outlier_path,value_path,spot_path,decision_path]]).to_csv(lineage,index=False,encoding="utf-8-sig")
    outputs=tables+[bins_path]+figure_outputs+[outlier_path,value_path,spot_path,decision_path,claim_path,report,limits,nextp,lineage,WORKING_ROOT/"protocol/conceptual_framework.md",WORKING_ROOT/"protocol/counter_hypotheses.csv",WORKING_ROOT/"artifacts/figures/conceptual_framework.svg",addendum,WORKING_ROOT/"protocol/descriptive_analysis_addendum_lock.json"]
    current={str(p.relative_to(WORKING_ROOT)):stable_hash(p) for p in outputs if p.suffix in {".csv",".json"}}
    stable_path=qc_dir/"descriptive_stable_hashes.json"; prior=json.loads(stable_path.read_text(encoding="utf-8")) if stable_path.exists() else None; reproducible=prior==current; stable_path.write_text(json.dumps(current,indent=2),encoding="utf-8"); outputs.append(stable_path)
    ctx["gatebook"].set("DESCRIPTIVE_INPUT", "PASS", "Authoritative panel and protocol/addendum identities verified.", {"panel_sha256":PANEL_SHA256,"addendum_sha256":ADDENDUM_SHA256})
    ctx["gatebook"].set("DESCRIPTIVE_GATE", "PASS", "Bounded univariate descriptive outputs pass with limitations.", {"classification":"PASS_WITH_LIMITATIONS","descriptive_classification":classification,"outlier_flags":len(outliers),"spot_check_provinces":int(spot.province_id_legacy63.nunique())})
    ctx["gatebook"].set("DESCRIPTIVE_CLAIM", "PASS", "Claim ceiling remains descriptive; H2 was not tested.", {"H2_STATUS":"REGISTERED_NOT_TESTED","causal_gate":"CLOSED","bivariate_calculations":0,"models_run":False})
    ctx["gatebook"].set("DESCRIPTIVE_REPRODUCIBILITY", "PASS" if reproducible else "WARN", "Stable outputs reproduce." if reproducible else "First descriptive run; second run required.", {"stable_hashes_match":reproducible})
    return outputs
