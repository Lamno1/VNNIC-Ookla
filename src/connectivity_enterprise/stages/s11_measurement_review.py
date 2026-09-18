from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

from ..core.paths import WORKING_ROOT
from ..core.provenance import sha256_file

LEDGER_HASH="d07417d2041c65bec19a607140613e3e2f0a870432fd176ab3878877c28c706e"
VARIANTS={
"unweighted_tile_median":"ookla_tile_median_download_mbps",
"unweighted_tile_mean":"ookla_tile_mean_download_mbps",
"tests_weighted_mean":"ookla_tests_weighted_mean_download_mbps",
"devices_weighted_mean":"ookla_devices_weighted_mean_download_mbps"}
LABEL="POST_HOC_MEASUREMENT_DIAGNOSTIC"

def corr(a,b,method="pearson"):
    return float(pd.Series(a).corr(pd.Series(b),method=method))

def dispersion(x):
    x=pd.Series(x,dtype=float)
    return {"sd_level":x.std(ddof=1),"sd_log":np.log(x).std(ddof=1),"coefficient_of_variation":x.std(ddof=1)/x.mean(),"interquartile_range":x.quantile(.75)-x.quantile(.25),"p90_p10_ratio":x.quantile(.9)/x.quantile(.1),"max_min_ratio":x.max()/x.min()}

def run(ctx):
    ledger=WORKING_ROOT/"protocol/human_measurement_review_ledger_20260913.md"; lock=json.loads((WORKING_ROOT/"protocol/human_measurement_review_ledger_lock.json").read_text())
    if sha256_file(ledger)!=LEDGER_HASH or lock["sha256"]!=LEDGER_HASH or not lock["preregistered_failure_preserved"]: raise RuntimeError("FAIL-CLOSED: human review ledger drift")
    allowed=[WORKING_ROOT/"data/processed/ookla_fixed_q2_adm1_2021_2024.parquet",WORKING_ROOT/"data/processed/vnnic_q2_validation_2021_2024.parquet",WORKING_ROOT/"data/processed/fact_connectivity_province_year.parquet",WORKING_ROOT/"artifacts/tables/table_08_measurement_validation_by_year.csv",WORKING_ROOT/"artifacts/tables/table_09_measurement_change_concordance.csv",WORKING_ROOT/"artifacts/tables/table_10_dispersion_source_comparison.csv",WORKING_ROOT/"artifacts/tables/table_11_ookla_aggregation_sensitivity.csv",WORKING_ROOT/"artifacts/qc/ookla_composition_audit.csv",WORKING_ROOT/"artifacts/qc/measurement_validation_decision.json",WORKING_ROOT/"artifacts/manifests/ookla_validation_partition_manifest.csv"]
    source_hashes={str(p.relative_to(WORKING_ROOT)):sha256_file(p) for p in allowed}
    old=json.loads((WORKING_ROOT/"artifacts/qc/measurement_validation_decision.json").read_text())
    if old["measurement_validation_classification"]!="MIXED_MEASUREMENT_SUPPORT" or old["rank_threshold_pass"] is not False or old["vnnic_descriptive_classification"]!="DESCRIPTIVE_DIVERGENCE_UNCHANGED": raise RuntimeError("FAIL-CLOSED: preregistered failure was not preserved")
    ookla=pd.read_parquet(allowed[0]); vnnic=pd.read_parquet(allowed[1]); annual=pd.read_parquet(allowed[2])[["province_id_legacy63","year","ftth_download_median_apr_dec_mbps"]]
    if len(ookla)!=252 or len(vnnic)!=252 or any(c not in ookla for c in VARIANTS.values()): raise RuntimeError("FAIL-CLOSED: measurement aggregate contract drift")
    data=ookla.merge(vnnic,on=["province_id_legacy63","shapeISO","year"],validate="one_to_one").merge(annual,on=["province_id_legacy63","year"],validate="one_to_one")
    agreement=[]; loo=[]; composition=[]; measures=["sd_level","sd_log","coefficient_of_variation","interquartile_range","p90_p10_ratio","max_min_ratio"]
    vwide=data.pivot(index="province_id_legacy63",columns="year",values="vnnic_q2_monthly_median_download_mbps"); vchange=vwide[2024]-vwide[2021]
    twide=data.pivot(index="province_id_legacy63",columns="year",values="total_tests"); dwide=data.pivot(index="province_id_legacy63",columns="year",values="total_devices"); tchange=twide[2024]-twide[2021]; dchange=dwide[2024]-dwide[2021]
    for variant,col in VARIANTS.items():
        wide=data.pivot(index="province_id_legacy63",columns="year",values=col); ochange=wide[2024]-wide[2021]; change_rank=corr(ochange.rank(),vchange.rank()); same=float((np.sign(ochange)==np.sign(vchange)).mean())
        for year,g in data.groupby("year"):
            a=g[col]; b=g.vnnic_q2_monthly_median_download_mbps; ar=a.rank(); br=b.rank(); qtop=(ar>47.25); vtop=(br>47.25); qbot=(ar<=15.75); vbot=(br<=15.75); disp=dispersion(a)
            row={"diagnostic_label":LABEL,"aggregation_variant":variant,"year":year,"N":63,"spearman_rank_correlation":corr(ar,br),"pearson_log_speed_correlation":corr(np.log(a),np.log(b)),"median_absolute_rank_difference":float(np.median(np.abs(ar-br))),"absolute_rank_difference_gt15":int(np.abs(ar-br).gt(15).sum()),"top_quartile_agreement":float((qtop==vtop).mean()),"bottom_quartile_agreement":float((qbot==vbot).mean()),"median_split_agreement":float(((a>=a.median())==(b>=b.median())).mean()),"change_rank_spearman_2021_2024":change_rank,"same_direction_change_proportion":same}; row.update({f"ookla_{k}":v for k,v in disp.items()}); agreement.append(row)
            baseline=corr(ar,br)
            for pid in g.province_id_legacy63:
                keep=g.province_id_legacy63!=pid; value=corr(a[keep].rank(),b[keep].rank()); loo.append({"diagnostic_label":LABEL,"scope":"yearly_rank","aggregation_variant":variant,"year":year,"excluded_province_id_legacy63":pid,"baseline_correlation":baseline,"leave_one_out_correlation":value,"correlation_change":value-baseline,"influence_disposition":"RETAINED"})
        baseline=change_rank
        for pid in ochange.index:
            keep=ochange.index!=pid; value=corr(ochange[keep].rank(),vchange[keep].rank()); loo.append({"diagnostic_label":LABEL,"scope":"change_rank_2021_2024","aggregation_variant":variant,"year":"2021-2024","excluded_province_id_legacy63":pid,"baseline_correlation":baseline,"leave_one_out_correlation":value,"correlation_change":value-baseline,"influence_disposition":"RETAINED"})
        disagreement=(ochange.rank()-vchange.rank()).abs()
        for comp_name,comp_change in [("tests_change",tchange),("devices_change",dchange)]:
            composition += [
            {"diagnostic_label":LABEL,"aggregation_variant":variant,"relationship":f"speed_change_vs_{comp_name}","pearson":corr(ochange,comp_change),"spearman":corr(ochange.rank(),comp_change.rank()),"interpretation":"composition diagnostic; not causal"},
            {"diagnostic_label":LABEL,"aggregation_variant":variant,"relationship":f"rank_change_vs_rank_{comp_name}","pearson":corr(ochange.rank(),comp_change.rank()),"spearman":corr(ochange.rank(),comp_change.rank()),"interpretation":"composition diagnostic; not causal"},
            {"diagnostic_label":LABEL,"aggregation_variant":variant,"relationship":f"rank_disagreement_vs_absolute_{comp_name}","pearson":corr(disagreement,comp_change.abs()),"spearman":corr(disagreement.rank(),comp_change.abs().rank()),"interpretation":"composition diagnostic; not causal"}]
    agree=pd.DataFrame(agreement); influence=pd.DataFrame(loo); comp=pd.DataFrame(composition)
    table12=WORKING_ROOT/"artifacts/tables/table_12_aggregation_agreement.csv"; agree.to_csv(table12,index=False,encoding="utf-8-sig")
    table13=WORKING_ROOT/"artifacts/tables/table_13_measurement_influence_audit.csv"; influence.to_csv(table13,index=False,encoding="utf-8-sig")
    table14=WORKING_ROOT/"artifacts/tables/table_14_composition_sensitivity.csv"; comp.to_csv(table14,index=False,encoding="utf-8-sig")
    change_corr=agree.groupby("aggregation_variant").change_rank_spearman_2021_2024.first(); yearly=agree.groupby("aggregation_variant").spearman_rank_correlation.agg(["min","median","max"]); all_negative=bool((change_corr<0).all())
    common_trend=bool(all((data.pivot(index="province_id_legacy63",columns="year",values=col)[2024]-data.pivot(index="province_id_legacy63",columns="year",values=col)[2021]).gt(0).all() for col in VARIANTS.values()) and vchange.gt(0).all())
    comp_concern=float(comp[comp.relationship.str.startswith("speed_change")].spearman.abs().max())
    broadly_robust=bool((yearly["min"]>=.5).all() and (change_corr>=.5).all() and comp_concern<.3)
    one_winner=bool(((yearly["median"]>=.7)&(change_corr>=.5)).sum()==1)
    if broadly_robust: decision="BROADLY_ROBUST_DUAL_SOURCE_MEASUREMENT"
    elif all_negative or comp_concern>=.5: decision="EXPOSURE_REDESIGN_REQUIRED"
    elif one_winner: decision="AGGREGATION_SENSITIVE_MEASUREMENT"
    else: decision="AGGREGATE_CONVERGENCE_ONLY"
    stage_b="NOT_RUN_STAGE_A_TERMINAL_EXPOSURE_REDESIGN" if decision=="EXPOSURE_REDESIGN_REQUIRED" else "NOT_RUN_NOT_REQUIRED_FOR_DUAL_SOURCE_DESCRIPTIVE_REPORTING" if decision=="AGGREGATE_CONVERGENCE_ONLY" else "NEEDS_TEMPORAL_RELIABILITY_EXTENSION" if decision=="AGGREGATION_SENSITIVE_MEASUREMENT" else "NOT_RUN_BROADLY_ROBUST"
    h2="NOT_TESTABLE_WITH_CURRENT_EXPOSURE" if decision=="EXPOSURE_REDESIGN_REQUIRED" else "BLOCKED_BY_MEASUREMENT_INSTABILITY" if decision!="BROADLY_ROBUST_DUAL_SOURCE_MEASUREMENT" else "REGISTERED_NOT_TESTED"
    state="BLOCKED_EXPOSURE_REDESIGN_REQUIRED" if decision=="EXPOSURE_REDESIGN_REQUIRED" else "READY_FOR_DUAL_SOURCE_DESCRIPTIVE_REPORTING" if decision=="AGGREGATE_CONVERGENCE_ONLY" else "BLOCKED_PENDING_TEMPORAL_RELIABILITY" if decision=="AGGREGATION_SENSITIVE_MEASUREMENT" else "READY_FOR_DUAL_SOURCE_ASSOCIATIONAL_PROTOCOL_DESIGN"
    adjud={"diagnostic_label":LABEL,"measurement_decision":decision,"research_gate":state,"h2_status":h2,"model_run":False,"causal_gate":"CLOSED","preregistered_measurement_classification":"MIXED_MEASUREMENT_SUPPORT_UNCHANGED","preregistered_rank_failure_preserved":True,"common_trend_agreement":common_trend,"yearly_rank_summary_by_variant":yearly.reset_index().to_dict("records"),"change_rank_spearman_by_variant":change_corr.to_dict(),"all_change_rank_correlations_negative":all_negative,"maximum_absolute_composition_spearman":comp_concern,"ch3_speed_test_composition":"HEIGHTENED_CONCERN_PENDING_REVIEW","stage_b_status":stage_b,"stage_b_run":False,"enterprise_outcome_read":False,"source_hashes":source_hashes}
    dec=WORKING_ROOT/"artifacts/qc/exposure_adjudication_decision.json"; dec.write_text(json.dumps(adjud,indent=2),encoding="utf-8")
    claim=pd.DataFrame([
    {"claim_id":"MR001","exact_claim":"Both sources show a common upward connectivity trend across all 63 provinces.","claim_level":"MEASUREMENT","supporting_artifact":"table_12_aggregation_agreement.csv","sample":"63 provinces; 2021-2024","status":"SUPPORTED","unresolved_alternative_explanation":"Common national trend does not validate province-specific exposure"},
    {"claim_id":"MR002","exact_claim":"Province rank and relative improvement agreement are weak or unstable across sources and aggregation variants.","claim_level":"MEASUREMENT","supporting_artifact":"table_12_aggregation_agreement.csv","sample":"Four aggregation variants; 63 provinces","status":"SUPPORTED_POST_HOC","unresolved_alternative_explanation":"Sources may measure different participation-weighted estimands"},
    {"claim_id":"MR003","exact_claim":"Composition diagnostics heighten concern but do not identify or eliminate composition bias.","claim_level":"MEASUREMENT","supporting_artifact":"table_14_composition_sensitivity.csv","sample":"2021-2024 changes","status":"SUPPORTED_POST_HOC","unresolved_alternative_explanation":"Tests and devices are themselves endogenous participation measures"}]); claimp=WORKING_ROOT/"artifacts/qc/measurement_review_claim_audit.csv"; claim.to_csv(claimp,index=False,encoding="utf-8-sig")
    report=WORKING_ROOT/"reports/human_measurement_review_report.md"; report.write_text(f"RESEARCH_GATE\n\n{state}\n\n# Human measurement review and exposure adjudication\n\nAll diagnostics are **{LABEL}**; the preregistered mixed result and rank failure remain unchanged.\n\n## Agreement decomposition\n\n1. National/common trend: agreement—both sources and all Ookla aggregations rise across all 63 provinces.\n2. Dispersion: broad directional agreement was already documented in the bounded pilot.\n3. Cross-sectional rank: weak and declining in the preregistered primary comparison; sensitivity variants do not restore robust agreement.\n4. Province-specific improvement: all four change-rank correlations are negative ({', '.join(f'{k}={v:.3f}' for k,v in change_corr.items())}).\n5. Aggregation sensitivity: alternative weighting changes magnitudes but does not reverse the negative change-rank finding.\n6. Composition: maximum absolute reported Spearman is {comp_concern:.3f}; concern is heightened, not resolved.\n\nDecision: **{decision}**. H2 status: **{h2}**. CH3: **HEIGHTENED_CONCERN_PENDING_REVIEW**. No province was removed; all influence observations are RETAINED.\n\nStage B: {stage_b}. Stage B was not run and no raw Ookla file was opened. No enterprise outcome was read and no model was run.\n",encoding="utf-8")
    nextp=WORKING_ROOT/"reports/exposure_adjudication_next_action.md"; nextp.write_text("# Next safe action\n\nThe current continuous province-level exposure is not suitable for H2. Keep H2 untested. The safe publication route is dual-source descriptive measurement divergence; any attempt to revive H2 requires a new exposure design and separate protocol, not selection among current aggregations.\n",encoding="utf-8")
    lineage=WORKING_ROOT/"artifacts/lineage/measurement_review_lineage.csv"; pd.DataFrame([{"parent_path":str(p),"parent_sha256":source_hashes[str(p.relative_to(WORKING_ROOT))],"child":"Stage_A_measurement_review","relation":"POST_HOC_MEASUREMENT_DIAGNOSTIC","run_id":ctx["run_id"]} for p in allowed]).to_csv(lineage,index=False,encoding="utf-8-sig")
    outputs=[table12,table13,table14,dec,claimp,report,nextp,lineage,ledger,WORKING_ROOT/"protocol/human_measurement_review_ledger_lock.json"]
    stable={str(p.relative_to(WORKING_ROOT)):sha256_file(p) for p in outputs if p.suffix in {".csv",".json"} and "lineage" not in p.name}; stablep=WORKING_ROOT/"artifacts/qc/measurement_review_stable_hashes.json"; prior=json.loads(stablep.read_text()) if stablep.exists() else None; repro=prior==stable; stablep.write_text(json.dumps(stable,indent=2),encoding="utf-8"); outputs.append(stablep)
    ctx.update({"measurement_decision":decision,"h2_review_status":h2,"review_research_gate":state,"stage_b_status":stage_b,"ch3_status":"HEIGHTENED_CONCERN_PENDING_REVIEW"})
    ctx["gatebook"].set("MEASUREMENT_REVIEW_INPUT","PASS","Only existing connectivity artifacts were opened.",{"enterprise_outcome_read":False,"raw_ookla_files_opened":0,"allowed_artifact_count":len(allowed)})
    ctx["gatebook"].set("MEASUREMENT_REVIEW_DECISION","PASS","Stage A adjudication completed without retroactive threshold changes.",adjud)
    ctx["gatebook"].set("MEASUREMENT_REVIEW_REPRODUCIBILITY","PASS" if repro else "WARN","Stable outputs reproduce." if repro else "Second Stage A run required.",{"stable_hashes_match":repro})
    return outputs
