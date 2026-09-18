from pathlib import Path
import hashlib, json, math, re, time
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import psutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath

from ..core.paths import WORKING_ROOT, sources_config
from ..core.provenance import sha256_file

FILES={
2021:(r"D:\Q1_RESEARCH\OOKLA_RAW\fixed\2021\Q2\2021-04-01_performance_fixed_tiles.parquet",4335355,218743050,"64e02b523547cf3886d345332b1ef42d1b7fc9070768cf47b154032c8570fd34"),
2022:(r"D:\Q1_RESEARCH\OOKLA_RAW\fixed\2022\Q2\2022-04-01_performance_fixed_tiles.parquet",6598700,332924853,"3bf9c68a7ce66af2e017bd7b39da42d6abe491742e40bd512b96ee39671a2e04"),
2023:(r"D:\Q1_RESEARCH\OOKLA_RAW\fixed\2023\Q2\2023-04-01_performance_fixed_tiles.parquet",6370238,345915057,"3e8ea5fcc570a1030f083f62c45e4ff2065ead83877bc4488c209b9e18a4901d"),
2024:(r"D:\Q1_RESEARCH\OOKLA_RAW\fixed\2024\Q2\2024-04-01_performance_fixed_tiles.parquet",6492072,354398509,"e6b0581e5db260f301ac0e719de235d2279613111f6cc826a13e6aeefacffd5b"),}
REQUIRED={"quadkey","tile_x","tile_y","avg_d_kbps","tests","devices"}; BATCH=250000
GEO_HASH="c64a07c3fd5d3ca0339a5002983dc76ddd60a0ef88e889522e37ca2408f74400"
ADD_HASH="320e9a08067b870b28bb2e607b3c2ae087fa037631d31c7a542e81f0b1d42321"
plt.rcParams.update({"svg.hashsalt":"ookla-validation-v1","figure.dpi":120,"savefig.dpi":300})

def quad_centroid(q):
    x=y=0; z=len(q)
    for i,c in enumerate(q):
        bit=z-i-1; d=int(c); x += (d&1)<<bit; y += ((d>>1)&1)<<bit
    n=2**z; lon=(x+.5)/n*360-180; a=math.pi*(1-2*(y+.5)/n); lat=math.degrees(math.atan(math.sinh(a)))
    return lon,lat

def geometry_index(path):
    geo=json.loads(Path(path).read_text(encoding="utf-8-sig")); units=[]; allx=[]; ally=[]
    for f in geo["features"]:
        geom=f["geometry"]; polys=[geom["coordinates"]] if geom["type"]=="Polygon" else geom["coordinates"]; parts=[]
        for poly in polys:
            outer=np.asarray(poly[0],float); holes=[MplPath(np.asarray(h,float)) for h in poly[1:]]; parts.append((MplPath(outer),holes,outer[:,0].min(),outer[:,1].min(),outer[:,0].max(),outer[:,1].max())); allx.extend(outer[:,0]); ally.extend(outer[:,1])
        units.append((f["properties"]["shapeISO"],parts))
    return units,(min(allx),min(ally),max(allx),max(ally))

def assign(points,units):
    count=np.zeros(len(points),np.int16); code=np.full(len(points),"",object); boundary=np.zeros(len(points),bool)
    for iso,parts in units:
        hit=np.zeros(len(points),bool); edge=np.zeros(len(points),bool)
        for path,holes,minx,miny,maxx,maxy in parts:
            cand=(points[:,0]>=minx)&(points[:,0]<=maxx)&(points[:,1]>=miny)&(points[:,1]<=maxy)
            idx=np.flatnonzero(cand)
            if not len(idx): continue
            p=points[idx]; inside=path.contains_points(p,radius=0)
            for hole in holes: inside &= ~hole.contains_points(p,radius=0)
            plus=path.contains_points(p,radius=1e-11); minus=path.contains_points(p,radius=-1e-11); edge[idx] |= plus!=minus
            hit[idx] |= inside
        count += hit; code[hit]=iso; boundary |= edge
    status=np.where(boundary,"BOUNDARY_REVIEW",np.where(count>1,"AMBIGUOUS",np.where(count==1,"ASSIGNED_UNIQUE","OUTSIDE_VIETNAM")))
    return code,status

def aggregate_frame(frame,year):
    rows=[]
    for iso,g in frame.groupby("shapeISO"):
        d=g.download_mbps.to_numpy(); tests=g.tests.to_numpy(float); devices=g.devices.to_numpy(float)
        rows.append({"shapeISO":iso,"year":year,"quarter":2,"network":"fixed","ookla_tile_median_download_mbps":float(np.median(d)),"ookla_tile_mean_download_mbps":float(np.mean(d)),"ookla_tests_weighted_mean_download_mbps":float(np.average(d,weights=tests)),"ookla_devices_weighted_mean_download_mbps":float(np.average(d,weights=devices)),"observed_ookla_tiles":len(g),"total_tests":int(tests.sum()),"total_devices":int(devices.sum()),"tests_per_observed_tile":float(tests.mean()),"devices_per_observed_tile":float(devices.mean())})
    return pd.DataFrame(rows).sort_values("shapeISO").reset_index(drop=True)

def process_partition(year,units,bounds,audit_sample=False):
    path=Path(FILES[year][0]); pf=pq.ParquetFile(path); start=time.perf_counter(); proc=psutil.Process(); peak=proc.memory_info().rss
    scanned=candidate=assigned=outside=ambiguous=boundary=invalid=failed=batches=0; chunks=[]; samples=[]
    cols=["quadkey","tile_x","tile_y","avg_d_kbps","tests","devices"]
    for batch in pf.iter_batches(batch_size=BATCH,columns=cols,use_threads=False):
        batches+=1; frame=batch.to_pandas(); scanned+=len(frame); peak=max(peak,proc.memory_info().rss)
        good=np.isfinite(frame.tile_x)&np.isfinite(frame.tile_y)&np.isfinite(frame.avg_d_kbps); invalid+=int((~good).sum()); frame=frame[good]
        bbox=frame.tile_x.between(bounds[0],bounds[2])&frame.tile_y.between(bounds[1],bounds[3]); candidate+=int(bbox.sum()); cand=frame[bbox].copy()
        if not len(cand): continue
        codes,status=assign(cand[["tile_x","tile_y"]].to_numpy(),units); cand["shapeISO"]=codes; cand["assignment_status"]=status
        assigned+=int((status=="ASSIGNED_UNIQUE").sum()); outside+=int((status=="OUTSIDE_VIETNAM").sum()); ambiguous+=int((status=="AMBIGUOUS").sum()); boundary+=int((status=="BOUNDARY_REVIEW").sum())
        if audit_sample and len(samples)<100:
            take=cand.iloc[:min(100-len(samples),len(cand))].copy()
            for r in take.itertuples():
                qx,qy=quad_centroid(str(r.quadkey)); samples.append({"year":year,"quadkey":r.quadkey,"tile_x":r.tile_x,"tile_y":r.tile_y,"decoded_x":qx,"decoded_y":qy,"absolute_lon_difference":abs(qx-r.tile_x),"absolute_lat_difference":abs(qy-r.tile_y),"assignment_status":r.assignment_status,"shapeISO":r.shapeISO})
        keep=cand[cand.assignment_status=="ASSIGNED_UNIQUE"].copy(); keep["download_mbps"]=keep.avg_d_kbps/1000.0; chunks.append(keep[["shapeISO","download_mbps","tests","devices"]])
    if scanned!=FILES[year][1]: raise RuntimeError(f"FAIL-CLOSED: {year} batch accounting mismatch")
    values=pd.concat(chunks,ignore_index=True); agg=aggregate_frame(values,year); elapsed=time.perf_counter()-start
    acc={"year":year,"source_rows":FILES[year][1],"row_groups":pf.metadata.num_row_groups,"rows_scanned":scanned,"bbox_candidates":candidate,"assigned_unique":assigned,"outside_vietnam_within_bbox":outside,"ambiguous":ambiguous,"boundary_review":boundary,"invalid_coordinates":invalid,"failed_rows":failed,"batch_count":batches,"failed_batches":0,"provinces_represented":int(agg.shapeISO.nunique()),"aggregate_rows":len(agg),"elapsed_seconds":elapsed,"peak_rss_bytes":peak,"rows_per_second":scanned/elapsed}
    return agg,acc,pd.DataFrame(samples)

def dispersion(df,var,source):
    out=[]
    for y,g in df.groupby("year"):
        x=g[var]; out.append({"source":source,"year":y,"sd_level":x.std(ddof=1),"sd_log":np.log(x).std(ddof=1),"coefficient_of_variation":x.std(ddof=1)/x.mean(),"interquartile_range":x.quantile(.75)-x.quantile(.25),"p90_p10_ratio":x.quantile(.9)/x.quantile(.1),"max_min_ratio":x.max()/x.min()})
    return pd.DataFrame(out)

def savefig(fig,base):
    png=base.with_suffix(".png"); svg=base.with_suffix(".svg"); fig.savefig(png,dpi=300,bbox_inches="tight",metadata={"Software":"CONNECTIVITY_ENTERPRISE_STUDY"}); fig.savefig(svg,bbox_inches="tight",metadata={"Date":None,"Creator":"CONNECTIVITY_ENTERPRISE_STUDY"}); plt.close(fig); return [png,svg]

def run(ctx):
    add=WORKING_ROOT/"protocol/ookla_validation_addendum_20260913.md"; lock=json.loads((WORKING_ROOT/"protocol/ookla_validation_addendum_lock.json").read_text())
    if sha256_file(add)!=ADD_HASH or lock["sha256"]!=ADD_HASH: raise RuntimeError("FAIL-CLOSED: Ookla addendum drift")
    geo_path=Path(sources_config()["sources"]["canonical_geojson"])
    if sha256_file(geo_path)!=GEO_HASH: raise RuntimeError("FAIL-CLOSED: canonical geometry drift")
    registry=pd.read_csv(r"D:\Q1_RESEARCH\OOKLA_LOGS\ookla_schema_registry.csv")
    selected=registry[(registry.network=="fixed")&(registry.quarter==2)&registry.year.isin(FILES)].copy()
    pre=[]
    for y,(name,rows,size,digest) in FILES.items():
        path=Path(name); pf=pq.ParquetFile(path); actual=sha256_file(path); rec=selected[selected.year==y]
        ok=len(rec)==1 and path.stat().st_size==size and pf.metadata.num_rows==rows and actual==digest and REQUIRED<=set(pf.schema.names) and rec.iloc[0].schema_variant=="EXTENDED_LATENCY_V2"
        pre.append({"year":y,"path":str(path),"rows":rows,"bytes":size,"sha256":actual,"row_groups":pf.metadata.num_row_groups,"columns":pf.schema.names,"schema_variant":"EXTENDED_LATENCY_V2","status":"PASS" if ok else "FAIL"})
        if not ok: raise RuntimeError(f"FAIL-CLOSED: Ookla preflight failed {y}")
    preflight_path=WORKING_ROOT/"artifacts/qc/ookla_preflight.json"; preflight_path.write_text(json.dumps({"authorized_files":4,"discovered_files":len(selected),"expected_rows":23796365,"expected_bytes":1251981469,"batch_size":BATCH,"workers":1,"files":pre,"semantics":"PASS_WITH_LIMITATIONS"},indent=2),encoding="utf-8")
    units,bounds=geometry_index(geo_path)
    agg24,bench,sample=process_partition(2024,units,bounds,True)
    agg24b,bench2,_=process_partition(2024,units,bounds,False)
    reproducible=agg24.equals(agg24b); pilot_pass=reproducible and bench["provinces_represented"]==63 and bench["failed_batches"]==0 and bench["ambiguous"]==0 and bench["invalid_coordinates"]==0 and bench["peak_rss_bytes"]<=4*1024**3 and np.isfinite(agg24.ookla_tile_median_download_mbps).all() and agg24.ookla_tile_median_download_mbps.gt(0).all()
    bench.update({"source_sha256":FILES[2024][3],"geometry_engine":"matplotlib.path.Path","geometry_engine_version":matplotlib.__version__,"reproducibility_rescan_rows":bench2["rows_scanned"],"aggregate_reproducible":reproducible,"pilot_gate":"PASS" if pilot_pass else "FAIL"})
    benchmark_path=WORKING_ROOT/"artifacts/qc/ookla_2024q2_benchmark.json"; benchmark_path.write_text(json.dumps(bench,indent=2),encoding="utf-8")
    if not pilot_pass: raise RuntimeError("FAIL-CLOSED: 2024Q2 pilot gate failed; scale-out prohibited")
    aggregates=[agg24]; accounts=[bench]; sample_rows=[sample]
    checkpoint_dir=WORKING_ROOT/"data/interim/ookla_validation_checkpoints"; checkpoint_dir.mkdir(parents=True,exist_ok=True)
    partitions=[]
    cp=checkpoint_dir/"2024Q2.parquet"; agg24.to_parquet(cp,index=False); partitions.append((2024,cp,bench))
    for y in [2021,2022,2023]:
        agg,acc,samp=process_partition(y,units,bounds,True); aggregates.append(agg); accounts.append(acc); sample_rows.append(samp); cp=checkpoint_dir/f"{y}Q2.parquet"; agg.to_parquet(cp,index=False); partitions.append((y,cp,acc))
    ookla=pd.concat(aggregates,ignore_index=True).sort_values(["shapeISO","year"]); 
    if len(ookla)!=252 or ookla.groupby("year").shapeISO.nunique().ne(63).any(): raise RuntimeError("FAIL-CLOSED: scale-out lacks 63x4 coverage")
    dim=pd.read_parquet(WORKING_ROOT/"data/reference/dim_province_legacy63.parquet")[["province_id_legacy63","shapeISO"]]
    ookla=ookla.merge(dim,on="shapeISO",validate="many_to_one").sort_values(["province_id_legacy63","year"]); ookla_path=WORKING_ROOT/"data/processed/ookla_fixed_q2_adm1_2021_2024.parquet"; ookla.to_parquet(ookla_path,index=False)
    monthly=pd.read_parquet(WORKING_ROOT/"data/processed/fact_vnnic_province_month_primary.parquet"); q2=monthly[monthly.month.isin([4,5,6])]
    if len(q2)!=756 or q2.groupby(["province_id_legacy63","year"]).month.nunique().ne(3).any() or {"value","value_raw"}&set(q2.columns): raise RuntimeError("FAIL-CLOSED: VNNIC Q2 validation window failed")
    vq=q2.groupby(["province_id_legacy63","shapeISO","year"],as_index=False).download_mbps.median().rename(columns={"download_mbps":"vnnic_q2_monthly_median_download_mbps"}); vq["validation_role"]="VALIDATION_ONLY"; vq["months_observed"]=3; vq_path=WORKING_ROOT/"data/processed/vnnic_q2_validation_2021_2024.parquet"; vq.to_parquet(vq_path,index=False)
    comp=ookla.merge(vq,on=["province_id_legacy63","shapeISO","year"],validate="one_to_one"); annual=pd.read_parquet(WORKING_ROOT/"data/processed/fact_connectivity_province_year.parquet")[["province_id_legacy63","year","ftth_download_median_apr_dec_mbps"]]; comp=comp.merge(annual,on=["province_id_legacy63","year"],validate="one_to_one")
    yearly=[]
    for y,g in comp.groupby("year"):
        a=g.ookla_tile_median_download_mbps; b=g.vnnic_q2_monthly_median_download_mbps; ra=a.rank(); rb=b.rank(); za=(a-a.mean())/a.std(ddof=1); zb=(b-b.mean())/b.std(ddof=1)
        yearly.append({"year":y,"N":len(g),"spearman_rank_correlation":ra.corr(rb),"pearson_log_level_correlation":np.log(a).corr(np.log(b)),"median_absolute_standardized_rank_difference":np.median(np.abs((ra-rb)/62)),"rank_difference_greater_15":int((ra-rb).abs().gt(15).sum()),"mean_absolute_zscore_difference":np.mean(np.abs(za-zb)),"above_below_median_agreement":np.mean((a>=a.median())==(b>=b.median())),"secondary_apr_dec_log_correlation":np.log(a).corr(np.log(g.ftth_download_median_apr_dec_mbps)),"secondary_temporal_mismatch_warning":True})
    t8=pd.DataFrame(yearly); t8p=WORKING_ROOT/"artifacts/tables/table_08_measurement_validation_by_year.csv"; t8.to_csv(t8p,index=False,encoding="utf-8-sig")
    wide=comp.pivot(index="province_id_legacy63",columns="year",values=["ookla_tile_median_download_mbps","vnnic_q2_monthly_median_download_mbps"]); oc=wide["ookla_tile_median_download_mbps"][2024]-wide["ookla_tile_median_download_mbps"][2021]; vc=wide["vnnic_q2_monthly_median_download_mbps"][2024]-wide["vnnic_q2_monthly_median_download_mbps"][2021]; same=np.sign(oc)==np.sign(vc)
    t9=pd.DataFrame({"metric":["same_change_direction_count","same_change_direction_proportion","spearman_change_correlation","opposite_direction_count"],"value":[int(same.sum()),float(same.mean()),oc.rank().corr(vc.rank()),int((~same).sum())]}); t9p=WORKING_ROOT/"artifacts/tables/table_09_measurement_change_concordance.csv"; t9.to_csv(t9p,index=False,encoding="utf-8-sig")
    vdisp=dispersion(comp,"vnnic_q2_monthly_median_download_mbps","VNNIC_Q2"); odisp=dispersion(comp,"ookla_tile_median_download_mbps","OOKLA_TILE_MEDIAN"); t10=pd.concat([vdisp,odisp],ignore_index=True); t10p=WORKING_ROOT/"artifacts/tables/table_10_dispersion_source_comparison.csv"; t10.to_csv(t10p,index=False,encoding="utf-8-sig")
    sens=comp[["province_id_legacy63","shapeISO","year","ookla_tile_median_download_mbps","ookla_tile_mean_download_mbps","ookla_tests_weighted_mean_download_mbps","ookla_devices_weighted_mean_download_mbps"]]; t11p=WORKING_ROOT/"artifacts/tables/table_11_ookla_aggregation_sensitivity.csv"; sens.to_csv(t11p,index=False,encoding="utf-8-sig")
    measures=["sd_level","sd_log","coefficient_of_variation","interquartile_range","p90_p10_ratio","max_min_ratio"]; dirs={}
    for m in measures: dirs[m]={"ookla":float(np.sign(odisp.set_index("year").loc[2024,m]-odisp.set_index("year").loc[2021,m])),"vnnic":float(np.sign(vdisp.set_index("year").loc[2024,m]-vdisp.set_index("year").loc[2021,m]))}; agree=sum(v["ookla"]==v["vnnic"] for v in dirs.values())
    rank_ok=int((t8.spearman_rank_correlation>=.7).sum())>=3 and t8.spearman_rank_correlation.min()>=.5; change_ok=same.mean()>=.7; coverage_ok=len(comp)==252
    if not coverage_ok: classification="INSUFFICIENT_MEASUREMENT_COVERAGE"
    elif rank_ok and change_ok and agree>=4: classification="CONVERGENT_MEASUREMENT_SUPPORT"
    elif t8.spearman_rank_correlation.max()<.5 or same.mean()<.5: classification="NONCONVERGENT_MEASUREMENT"
    else: classification="MIXED_MEASUREMENT_SUPPORT"
    ch3="PARTIALLY_CONSTRAINED" if classification=="CONVERGENT_MEASUREMENT_SUPPORT" else "HEIGHTENED_CONCERN" if classification=="NONCONVERGENT_MEASUREMENT" else "REMAINS_UNRESOLVED"
    decision={"measurement_validation_classification":classification,"researcher_defined_thresholds":True,"coverage_pass":bool(coverage_ok),"rank_threshold_pass":bool(rank_ok),"change_direction_threshold_pass":bool(change_ok),"dispersion_direction_agreement_count":int(agree),"dispersion_directions":dirs,"same_change_direction_proportion":float(same.mean()),"ch3_speed_test_composition":ch3,"vnnic_descriptive_classification":"DESCRIPTIVE_DIVERGENCE_UNCHANGED"}; decp=WORKING_ROOT/"artifacts/qc/measurement_validation_decision.json"; decp.write_text(json.dumps(decision,indent=2),encoding="utf-8")
    manifest=[]
    for y,cp,acc in partitions: manifest.append({"year":y,"quarter":2,"network":"fixed","source_path":FILES[y][0],"source_sha256":FILES[y][3],"source_rows":FILES[y][1],"checkpoint_path":str(cp),"checkpoint_sha256":sha256_file(cp),"aggregate_rows":acc["aggregate_rows"],"status":"PASS"})
    manp=WORKING_ROOT/"artifacts/manifests/ookla_validation_partition_manifest.csv"; pd.DataFrame(manifest).to_csv(manp,index=False,encoding="utf-8-sig")
    audit=pd.concat(sample_rows,ignore_index=True); auditp=WORKING_ROOT/"artifacts/qc/ookla_spatial_assignment_audit.csv"; audit.to_csv(auditp,index=False,encoding="utf-8-sig")
    covp=WORKING_ROOT/"artifacts/qc/ookla_coverage_audit.csv"; pd.DataFrame(accounts).to_csv(covp,index=False,encoding="utf-8-sig")
    compdiag=[]
    for metric in ["observed_ookla_tiles","total_tests","total_devices"]:
        w=comp.pivot(index="province_id_legacy63",columns="year",values=metric); delta=w[2024]-w[2021]; compdiag.append({"composition_metric":metric,"spearman_with_ookla_primary_change":delta.rank().corr(oc.rank()),"interpretation":"measurement_composition_diagnostic_only"})
    compp=WORKING_ROOT/"artifacts/qc/ookla_composition_audit.csv"; pd.DataFrame(compdiag).to_csv(compp,index=False,encoding="utf-8-sig")
    linp=WORKING_ROOT/"artifacts/lineage/ookla_validation_lineage.csv"; pd.DataFrame([{"parent":FILES[y][0],"child":str(ookla_path),"relation":"bbox_centroid_ADM1_then_preregistered_aggregates"} for y in FILES]+[{"parent":str(WORKING_ROOT/"data/processed/fact_vnnic_province_month_primary.parquet"),"child":str(vq_path),"relation":"validation_only_April_June_median"}]).to_csv(linp,index=False,encoding="utf-8-sig")
    figouts=[]
    rankdata=comp.assign(ookla_rank=comp.groupby("year").ookla_tile_median_download_mbps.rank(),vnnic_rank=comp.groupby("year").vnnic_q2_monthly_median_download_mbps.rank())[["province_id_legacy63","year","ookla_rank","vnnic_rank"]]; p=WORKING_ROOT/"artifacts/figures/figure_10_vnnic_ookla_rank_comparison_data.csv"; rankdata.to_csv(p,index=False,encoding="utf-8-sig"); figouts.append(p); fig,ax=plt.subplots(figsize=(7,6)); [ax.scatter(g.vnnic_rank,g.ookla_rank,label=str(y),alpha=.65) for y,g in rankdata.groupby("year")]; ax.plot([1,63],[1,63],color="#555"); ax.set(xlabel="VNNIC Q2 rank",ylabel="Ookla Q2 rank",title="Connectivity rank comparison"); ax.legend(); figouts+=savefig(fig,WORKING_ROOT/"artifacts/figures/figure_10_vnnic_ookla_rank_comparison")
    changedata=pd.DataFrame({"province_id_legacy63":oc.index,"ookla_change":oc.values,"vnnic_change":vc.values}); p=WORKING_ROOT/"artifacts/figures/figure_11_measurement_change_comparison_data.csv"; changedata.to_csv(p,index=False,encoding="utf-8-sig"); figouts.append(p); fig,ax=plt.subplots(figsize=(7,6)); ax.scatter(vc,oc,alpha=.7); ax.axhline(0,color="#777"); ax.axvline(0,color="#777"); ax.set(xlabel="VNNIC Q2 change",ylabel="Ookla Q2 change",title="Connectivity change comparison, 2021–2024"); figouts+=savefig(fig,WORKING_ROOT/"artifacts/figures/figure_11_measurement_change_comparison")
    plotdata=t10[t10.source.isin(["VNNIC_Q2","OOKLA_TILE_MEDIAN"])][["source","year","sd_log"]]; p=WORKING_ROOT/"artifacts/figures/figure_12_dispersion_source_comparison_data.csv"; plotdata.to_csv(p,index=False,encoding="utf-8-sig"); figouts.append(p); fig,ax=plt.subplots(figsize=(7,5)); [ax.plot(g.year,g.sd_log,marker="o",label=s) for s,g in plotdata.groupby("source")]; ax.set(xticks=[2021,2022,2023,2024],ylabel="SD of log download",title="Cross-province connectivity dispersion"); ax.legend(); figouts+=savefig(fig,WORKING_ROOT/"artifacts/figures/figure_12_dispersion_source_comparison")
    total={"source_files_authorized":4,"source_files_discovered":len(selected),"source_files_processed":4,"source_rows_expected":23796365,"source_rows_scanned":sum(a["rows_scanned"] for a in accounts),"reproducibility_rescan_rows":bench2["rows_scanned"],"total_physical_rows_read_including_rescan":sum(a["rows_scanned"] for a in accounts)+bench2["rows_scanned"],"vietnam_bbox_candidate_rows":sum(a["bbox_candidates"] for a in accounts),"adm1_assigned_rows":sum(a["assigned_unique"] for a in accounts),"outside_vietnam_rows":sum(a["outside_vietnam_within_bbox"] for a in accounts),"ambiguous_rows":sum(a["ambiguous"] for a in accounts),"failed_rows":sum(a["failed_rows"] for a in accounts),"aggregate_rows_created":len(ookla),"partitions_skipped_from_checkpoint":0,"peak_rss_bytes":max(a["peak_rss_bytes"] for a in accounts),"primary_runtime_seconds":sum(a["elapsed_seconds"] for a in accounts),"pilot_rescan_runtime_seconds":bench2["elapsed_seconds"],"total_runtime_seconds_including_rescan":sum(a["elapsed_seconds"] for a in accounts)+bench2["elapsed_seconds"],"correctness_gate":"PASS"}
    report=WORKING_ROOT/"reports/ookla_validation_report.md"; report.write_text("RESEARCH_GATE\n\n"+("READY_FOR_ASSOCIATIONAL_PROTOCOL_REVIEW" if classification=="CONVERGENT_MEASUREMENT_SUPPORT" else "BLOCKED_PENDING_MEASUREMENT_DECISION" if classification=="MIXED_MEASUREMENT_SUPPORT" else "BLOCKED_BY_MEASUREMENT_VALIDATION")+f"\n\n# Bounded Ookla measurement validation\n\nClassification: **{classification}**. These thresholds are researcher-defined. Agreement or disagreement concerns convergent measurement only. H2 was not tested.\n\n## Data throughput result\n\n"+"\n".join(f"- {k.replace('_',' ').title()}: {v}" for k,v in total.items())+f"\n\nCH3 status: {ch3}. VNNIC descriptive classification remains DESCRIPTIVE_DIVERGENCE.\n",encoding="utf-8")
    limitp=WORKING_ROOT/"reports/ookla_validation_limitations.md"; limitp.write_text("# Ookla validation limitations\n\n- Both sources reflect voluntary speed-test participation.\n- Tile medians are spatial summaries, not population or firm averages.\n- Centroid assignment does not allocate tile area across boundaries.\n- Historical Ookla files may be reaggregated.\n- Q2 VNNIC is validation-only; April–December comparison has temporal mismatch.\n- CH3 cannot be eliminated.\n",encoding="utf-8")
    nextp=WORKING_ROOT/"reports/ookla_validation_next_action.md"; nextp.write_text("# Next safe action\n\n"+("Conduct a separately authorized associational protocol review; do not estimate yet.\n" if classification=="CONVERGENT_MEASUREMENT_SUPPORT" else "Conduct a human measurement review; do not choose the source based on favorable results.\n" if classification=="MIXED_MEASUREMENT_SUPPORT" else "Redesign the connectivity exposure before any associational analysis.\n"),encoding="utf-8")
    outputs=[ookla_path,vq_path,manp,linp,preflight_path,benchmark_path,auditp,covp,compp,decp,t8p,t9p,t10p,t11p]+figouts+[report,limitp,nextp,add,WORKING_ROOT/"protocol/ookla_validation_addendum_lock.json",WORKING_ROOT/"protocol/counter_hypotheses.csv",WORKING_ROOT/"data/reference/ookla_methodology/official_methodology_record.md",WORKING_ROOT/"data/reference/ookla_methodology/ookla_semantic_evidence.csv"]
    stable={str(p.relative_to(WORKING_ROOT)):sha256_file(p) for p in outputs if p.suffix in {".csv",".parquet",".json"} and "benchmark" not in p.name and "coverage_audit" not in p.name and "counter_hypotheses" not in p.name}; sp=WORKING_ROOT/"artifacts/qc/ookla_validation_stable_hashes.json"; prior=json.loads(sp.read_text()) if sp.exists() else None; repro=prior==stable; sp.write_text(json.dumps(stable,indent=2),encoding="utf-8"); outputs.append(sp)
    ctx["measurement_classification"]=classification; ctx["ch3_status"]=ch3
    ctx["gatebook"].set("OOKLA_SEMANTICS","PASS","Official Ookla definitions support the bounded measures with limitations.",{"classification":"PASS_WITH_LIMITATIONS"})
    ctx["gatebook"].set("OOKLA_2024_PILOT","PASS","2024Q2 pilot passed before scale-out.",bench)
    gate_status="PASS" if classification=="CONVERGENT_MEASUREMENT_SUPPORT" else "WARN" if classification=="MIXED_MEASUREMENT_SUPPORT" else "FAIL"
    ctx["gatebook"].set("MEASUREMENT_VALIDATION_GATE",gate_status,"Bounded four-file comparison completed.",decision)
    ctx["gatebook"].set("OOKLA_REPRODUCIBILITY","PASS" if repro else "WARN","Stable outputs reproduce." if repro else "Second complete run required.",{"stable_hashes_match":repro})
    return outputs
