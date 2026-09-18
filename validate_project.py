from pathlib import Path
import hashlib, json, re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
AGGREGATES = {"0", "1", "13", "28", "43", "49", "56"}
OLD = {
    "run_20260912T174708Z": "8bd7b8035d9ba5c756c0cf03d894c31157eec8866a271640cb151f33b87ed981",
    "run_20260913T013734Z": "c9e340eeaaed54e66c2ad400c329448f2f489685d8f745c40fd9ad8486cccdf9",
    "run_20260913T063540Z": "b07a8e98628079828e4f0f80c5115f18f3464ec5baa7a6691d9cce12a91ce759",
    "run_20260913T064755Z": "ca193009480d833f998f2a91849017a7afc4c81bfd6c6c4d8d20ac0ff3a24cee",
    "run_20260913T070320Z": "a56e1e77ddf8f1ab3bd7125902b1ba2bf0dbfebbc54cae4b5456248888571122",
    "run_20260913T070404Z": "dc711cf71e7c3f551abd8f1009c71e6e99a90ed56b4d2bfca0000f8f2b8ac311",
    "run_20260913T071002Z": "acabcf02894b5001ea4931fb19bd77ec8be56ede82630a2158243cbaed815c20",
    "run_20260913T072504Z": "cfbf9b210260bd5a7d68f6b0a049e1eb46329280b40fefab78dfa06c31e3f45c",
}

def fail(msg): raise RuntimeError(f"VALIDATION FAIL: {msg}")
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def unique(df, keys, n): return len(df) == n and not df.duplicated(keys).any()

def validate_descriptive(run, summary, gates):
    if summary.get("research_gate") != "READY_FOR_MEASUREMENT_VALIDATION" or not summary.get("analysis_panel_created") or not summary.get("descriptive_analysis_run") or summary.get("model_run"): fail("descriptive scope flags inconsistent")
    if summary.get("h2_status") != "REGISTERED_NOT_TESTED" or summary.get("next_stage") != "BOUNDED_OOKLA_VALIDATION_PILOT": fail("H2 or next-stage status changed")
    for gate in ["G0", "DESCRIPTIVE_INPUT", "DESCRIPTIVE_GATE", "DESCRIPTIVE_CLAIM", "DESCRIPTIVE_REPRODUCIBILITY"]:
        if gates.get(gate, {}).get("status") != "PASS": fail(f"descriptive gate failed: {gate}")
    if gates["DESCRIPTIVE_GATE"]["evidence"].get("classification") != "PASS_WITH_LIMITATIONS" or gates["DESCRIPTIVE_CLAIM"]["evidence"].get("bivariate_calculations") != 0: fail("descriptive gate evidence inconsistent")
    panel_path = ROOT / "data/analysis/analysis_panel_2021_2024.parquet"
    if sha(panel_path) != "7711c489b5b6da109fa4050cc04d29f252d6dbade99274ccac015a5824b0454e": fail("authoritative panel changed")
    panel = pd.read_parquet(panel_path)
    if not unique(panel,["province_id_legacy63","year"],252) or panel.groupby("year").province_id_legacy63.nunique().ne(63).any() or panel[["ftth_download_median_apr_dec_mbps","active_firms_per_1000"]].isna().any().any(): fail("panel contract drift")
    addendum=ROOT/"protocol/descriptive_analysis_addendum_20260913.md"; lock=json.loads((ROOT/"protocol/descriptive_analysis_addendum_lock.json").read_text(encoding="utf-8"))
    if sha(addendum) != lock["sha256"] or lock["h2_status"] != "REGISTERED_NOT_TESTED": fail("descriptive addendum lock failed")
    result_paths=list((ROOT/"artifacts/tables").glob("table_*.csv"))+list((ROOT/"artifacts/figures").glob("figure_*.csv"))
    if any(addendum.stat().st_mtime > p.stat().st_mtime for p in result_paths): fail("addendum does not predate result artifacts")
    expected = panel.groupby("year").ftth_download_median_apr_dec_mbps
    t2=pd.read_csv(ROOT/"artifacts/tables/table_02_connectivity_summary_by_year.csv").set_index("year")
    for y,g in expected:
        checks={"N":len(g),"mean":g.mean(),"median":g.median(),"standard_deviation":g.std(ddof=1),"minimum":g.min(),"p10":g.quantile(.1),"p25":g.quantile(.25),"p75":g.quantile(.75),"p90":g.quantile(.9),"maximum":g.max(),"coefficient_of_variation":g.std(ddof=1)/g.mean(),"interquartile_range":g.quantile(.75)-g.quantile(.25)}
        if any(not np.isclose(t2.loc[y,k],v,rtol=0,atol=1e-12) for k,v in checks.items()): fail("connectivity summary does not recompute")
    t3=pd.read_csv(ROOT/"artifacts/tables/table_03_enterprise_summary_by_year.csv").set_index("year")
    for y,g in panel.groupby("year").active_firms_per_1000:
        if not np.isclose(t3.loc[y,"mean"],g.mean(),rtol=0,atol=1e-12): fail("enterprise summary does not recompute")
    bins=json.loads((ROOT/"artifacts/qc/descriptive_map_bins.json").read_text(encoding="utf-8"))
    if len(bins["ftth"])<2 or len(bins["firm_density"])<2: fail("pooled map bins missing")
    import matplotlib.image as mpimg
    for n in ["01_ftth_distribution_by_year","02_ftth_average_province_trend","03_ftth_maps_2021_2024","04_ftth_change_map_2021_2024","05_ftth_rank_mobility","06_firm_density_distribution_by_year","07_firm_density_average_province_trend","08_firm_density_maps_2021_2024","09_firm_density_change_map_2021_2024"]:
        base=ROOT/"artifacts/figures"/f"figure_{n}"
        for suffix in [".png",".svg","_data.csv"]:
            path=Path(str(base)+suffix)
            if not path.exists(): fail(f"figure companion missing: {path.name}")
        if mpimg.imread(Path(str(base)+".png")).ndim != 3: fail("figure dimensions invalid")
    outliers=pd.read_csv(ROOT/"artifacts/qc/descriptive_outlier_review.csv")
    if len(outliers) and set(outliers.retained_excluded_status) != {"RETAINED"}: fail("an outlier was silently excluded")
    spot=pd.read_csv(ROOT/"artifacts/qc/descriptive_spot_checks.csv")
    if spot.province_id_legacy63.nunique()<5 or set(spot.fact_reconciliation)!={"PASS"}: fail("spot checks incomplete")
    claims=pd.read_csv(ROOT/"reports/claim_audit.csv")
    if set(claims[claims.claim_id.str.startswith("D")].claim_level)-{"DESCRIPTIVE"}: fail("claim ceiling exceeded")
    if any((ROOT/"artifacts/models").glob("*")): fail("model artifact exists")
    created="\n".join(summary.get("created_artifacts",[])).lower()
    if any(x in created for x in ["ookla","wbes","pci"]): fail("out-of-scope source processed")
    if gates["DESCRIPTIVE_REPRODUCIBILITY"]["evidence"].get("stable_hashes_match") is not True: fail("stable outputs did not reproduce")
    registry=pd.read_csv(run/"artifact_registry.csv")
    if registry.empty or registry.sha256.str.len().ne(64).any(): fail("descriptive artifact hashes incomplete")
    print("VALIDATOR: PASS_DESCRIPTIVE_READY_FOR_MEASUREMENT_VALIDATION")
    print("RESEARCH_GATE: READY_FOR_MEASUREMENT_VALIDATION")
    print("DESCRIPTIVE_CLASSIFICATION:", json.loads((ROOT/"artifacts/qc/descriptive_classification.json").read_text())["classification"])
    print("OUTLIER_FLAGS:", len(outliers), "SPOT_CHECK_PROVINCES:", spot.province_id_legacy63.nunique())
    print("H2_STATUS: REGISTERED_NOT_TESTED")
    print("CAUSAL_GATE: CLOSED")
    print("RUN:",run.name)
    return 0

def validate_ookla(run,summary,gates):
    if summary.get("research_gate")!="BLOCKED_PENDING_MEASUREMENT_DECISION" or summary.get("measurement_validation_classification")!="MIXED_MEASUREMENT_SUPPORT" or summary.get("next_stage")!="HUMAN_MEASUREMENT_REVIEW": fail("measurement decision status inconsistent")
    if summary.get("h2_status")!="REGISTERED_NOT_TESTED" or summary.get("model_run") or summary.get("ch3_status") not in {"PARTIALLY_CONSTRAINED","REMAINS_UNRESOLVED","HEIGHTENED_CONCERN"}: fail("scope or CH3 status invalid")
    for gate in ["G0","OOKLA_SEMANTICS","OOKLA_2024_PILOT","OOKLA_REPRODUCIBILITY"]:
        if gates.get(gate,{}).get("status")!="PASS": fail(f"Ookla gate failed: {gate}")
    if gates.get("MEASUREMENT_VALIDATION_GATE",{}).get("status")!="WARN": fail("mixed evidence must produce WARN")
    if sha(ROOT/"data/analysis/analysis_panel_2021_2024.parquet")!="7711c489b5b6da109fa4050cc04d29f252d6dbade99274ccac015a5824b0454e": fail("panel changed")
    if sha(ROOT/"artifacts/qc/descriptive_classification.json")!="bbf10becaadf22867f65c11038b2fd02e6e865374b18e53af7a587846b24e8ab" or sha(ROOT/"artifacts/tables/table_04_connectivity_dispersion.csv")!="dacbbef9ba686126bc1c8980c776f683e98b3af29b213dfbcf85f01db89adfd3": fail("descriptive artifacts changed")
    expected={2021:(4335355,218743050,"64e02b523547cf3886d345332b1ef42d1b7fc9070768cf47b154032c8570fd34"),2022:(6598700,332924853,"3bf9c68a7ce66af2e017bd7b39da42d6abe491742e40bd512b96ee39671a2e04"),2023:(6370238,345915057,"3e8ea5fcc570a1030f083f62c45e4ff2065ead83877bc4488c209b9e18a4901d"),2024:(6492072,354398509,"e6b0581e5db260f301ac0e719de235d2279613111f6cc826a13e6aeefacffd5b")}
    pre=json.loads((ROOT/"artifacts/qc/ookla_preflight.json").read_text())
    if pre["authorized_files"]!=4 or pre["discovered_files"]!=4 or pre["expected_rows"]!=23796365: fail("authorized file accounting changed")
    for rec in pre["files"]:
        rows,size,digest=expected[int(rec["year"])]
        if rec["rows"]!=rows or rec["bytes"]!=size or rec["sha256"]!=digest or rec["schema_variant"]!="EXTENDED_LATENCY_V2" or "mobile" in rec["path"].lower() or "\\q2\\" not in rec["path"].lower(): fail("unauthorized or drifted partition")
    if sha(Path(r"D:\Q1_RESEARCH\GIS_DERIVED\CANONICAL_ADM1_63.geojson"))!="c64a07c3fd5d3ca0339a5002983dc76ddd60a0ef88e889522e37ca2408f74400": fail("canonical geometry changed")
    bench=json.loads((ROOT/"artifacts/qc/ookla_2024q2_benchmark.json").read_text())
    if bench["pilot_gate"]!="PASS" or not bench["aggregate_reproducible"] or bench["failed_batches"] or bench["ambiguous"] or bench["peak_rss_bytes"]>4*1024**3: fail("2024 benchmark gate failed")
    coverage=pd.read_csv(ROOT/"artifacts/qc/ookla_coverage_audit.csv")
    if set(coverage.year)!={2021,2022,2023,2024} or coverage.rows_scanned.sum()!=23796365 or coverage.failed_batches.sum()!=0 or coverage.ambiguous.sum()!=0 or coverage.invalid_coordinates.sum()!=0 or coverage.provinces_represented.ne(63).any(): fail("batch accounting or spatial coverage failed")
    audit=pd.read_csv(ROOT/"artifacts/qc/ookla_spatial_assignment_audit.csv")
    if len(audit)<100 or audit.absolute_lon_difference.max()>0.0001 or audit.absolute_lat_difference.max()>0.0001: fail("quadkey centroid audit failed")
    ookla=pd.read_parquet(ROOT/"data/processed/ookla_fixed_q2_adm1_2021_2024.parquet")
    if not unique(ookla,["province_id_legacy63","year"],252) or ookla.groupby("year").province_id_legacy63.nunique().ne(63).any() or ookla.ookla_tile_median_download_mbps.le(0).any(): fail("Ookla aggregate contract failed")
    vq=pd.read_parquet(ROOT/"data/processed/vnnic_q2_validation_2021_2024.parquet")
    if not unique(vq,["province_id_legacy63","year"],252) or set(vq.months_observed)!={3} or set(vq.validation_role)!={"VALIDATION_ONLY"} or {"value","value_raw"}&set(vq.columns): fail("VNNIC validation window failed")
    manifest=pd.read_csv(ROOT/"artifacts/manifests/ookla_validation_partition_manifest.csv")
    if len(manifest)!=4 or set(manifest.status)!={"PASS"} or manifest.checkpoint_sha256.str.len().ne(64).any(): fail("partition checkpoints incomplete")
    decision=json.loads((ROOT/"artifacts/qc/measurement_validation_decision.json").read_text())
    if decision["measurement_validation_classification"]!="MIXED_MEASUREMENT_SUPPORT" or decision["ch3_speed_test_composition"]=="ELIMINATED" or decision["vnnic_descriptive_classification"]!="DESCRIPTIVE_DIVERGENCE_UNCHANGED": fail("measurement classification invalid")
    if gates["OOKLA_REPRODUCIBILITY"]["evidence"].get("stable_hashes_match") is not True: fail("stable Ookla outputs did not reproduce")
    if any((ROOT/"artifacts/models").glob("*")): fail("model artifact exists")
    created="\n".join(summary.get("created_artifacts",[])).lower()
    if any(x in created for x in ["wbes","pci","mobile_tiles"]): fail("out-of-scope input processed")
    registry=pd.read_csv(run/"artifact_registry.csv")
    if registry.empty or registry.sha256.str.len().ne(64).any(): fail("artifact hashes incomplete")
    print("VALIDATOR: PASS_OOKLA_MIXED_REQUIRES_HUMAN_REVIEW")
    print("RESEARCH_GATE: BLOCKED_PENDING_MEASUREMENT_DECISION")
    print("MEASUREMENT_VALIDATION_CLASSIFICATION: MIXED_MEASUREMENT_SUPPORT")
    print("ROWS_SCANNED:",int(coverage.rows_scanned.sum()),"AGGREGATE_ROWS:",len(ookla))
    print("CH3_SPEED_TEST_COMPOSITION:",decision["ch3_speed_test_composition"])
    print("H2_STATUS: REGISTERED_NOT_TESTED")
    print("CAUSAL_GATE: CLOSED")
    print("RUN:",run.name)
    return 0

def validate_measurement_review(run,summary,gates):
    if summary.get("research_gate")!="BLOCKED_EXPOSURE_REDESIGN_REQUIRED" or summary.get("measurement_decision")!="EXPOSURE_REDESIGN_REQUIRED" or summary.get("h2_status")!="NOT_TESTABLE_WITH_CURRENT_EXPOSURE": fail("adjudication status inconsistent")
    if summary.get("model_run") or summary.get("enterprise_outcome_read") is not False or summary.get("causal_gate")!="CLOSED": fail("prohibited outcome/model state")
    if summary.get("ch3_status")!="HEIGHTENED_CONCERN_PENDING_REVIEW" or summary.get("stage_b_status")!="NOT_RUN_STAGE_A_TERMINAL_EXPOSURE_REDESIGN": fail("CH3 or Stage B state invalid")
    for gate in ["G0","MEASUREMENT_REVIEW_INPUT","MEASUREMENT_REVIEW_DECISION","MEASUREMENT_REVIEW_REPRODUCIBILITY"]:
        if gates.get(gate,{}).get("status")!="PASS": fail(f"review gate failed: {gate}")
    evidence=gates["MEASUREMENT_REVIEW_INPUT"]["evidence"]
    if evidence.get("enterprise_outcome_read") is not False or evidence.get("raw_ookla_files_opened")!=0: fail("scope evidence invalid")
    decision=json.loads((ROOT/"artifacts/qc/exposure_adjudication_decision.json").read_text())
    if decision["diagnostic_label"]!="POST_HOC_MEASUREMENT_DIAGNOSTIC" or not decision["preregistered_rank_failure_preserved"] or decision["preregistered_measurement_classification"]!="MIXED_MEASUREMENT_SUPPORT_UNCHANGED": fail("preregistered failure overwritten")
    if decision["measurement_decision"]!="EXPOSURE_REDESIGN_REQUIRED" or not decision["all_change_rank_correlations_negative"] or decision["ch3_speed_test_composition"]!="HEIGHTENED_CONCERN_PENDING_REVIEW" or decision["stage_b_run"] is not False: fail("decision does not follow metrics")
    t12=pd.read_csv(ROOT/"artifacts/tables/table_12_aggregation_agreement.csv")
    if len(t12)!=16 or t12.aggregation_variant.nunique()!=4 or t12.groupby(["aggregation_variant","year"]).size().ne(1).any() or set(t12.N)!={63}: fail("aggregation agreement contract failed")
    if not (t12.groupby("aggregation_variant").change_rank_spearman_2021_2024.first()<0).all(): fail("negative change-rank finding not preserved")
    t13=pd.read_csv(ROOT/"artifacts/tables/table_13_measurement_influence_audit.csv")
    if len(t13)!=1260 or set(t13.influence_disposition)!={"RETAINED"} or t13.excluded_province_id_legacy63.nunique()!=63: fail("leave-one-out audit incomplete")
    t14=pd.read_csv(ROOT/"artifacts/tables/table_14_composition_sensitivity.csv")
    if len(t14)!=24 or t14.aggregation_variant.nunique()!=4 or set(t14.diagnostic_label)!={"POST_HOC_MEASUREMENT_DIAGNOSTIC"}: fail("composition audit incomplete")
    if decision["maximum_absolute_composition_spearman"]<.5: fail("heightened composition concern unsupported")
    if (ROOT/"artifacts/tables/table_15_quarterly_temporal_reliability.csv").exists() or (ROOT/"artifacts/qc/temporal_extension_manifest.csv").exists(): fail("Stage B artifacts exist despite terminal Stage A")
    if any((ROOT/"artifacts/models").glob("*")): fail("model artifact exists")
    created="\n".join(summary.get("created_artifacts",[])).lower()
    if any(x in created for x in ["ookla_raw","fact_nso","analysis_panel_2021_2024.parquet","wbes","pci"]): fail("prohibited source was opened or emitted")
    ledger_lock=json.loads((ROOT/"protocol/human_measurement_review_ledger_lock.json").read_text())
    if sha(ROOT/ledger_lock["ledger_path"])!=ledger_lock["sha256"]: fail("human-review ledger drift")
    if gates["MEASUREMENT_REVIEW_REPRODUCIBILITY"]["evidence"].get("stable_hashes_match") is not True: fail("review outputs did not reproduce")
    registry=pd.read_csv(run/"artifact_registry.csv")
    if registry.empty or registry.sha256.str.len().ne(64).any(): fail("run artifact hashes incomplete")
    print("VALIDATOR: PASS_MEASUREMENT_REVIEW_EXPOSURE_REDESIGN_REQUIRED")
    print("RESEARCH_GATE: BLOCKED_EXPOSURE_REDESIGN_REQUIRED")
    print("MEASUREMENT_DECISION: EXPOSURE_REDESIGN_REQUIRED")
    print("STAGE_B: NOT_RUN")
    print("CH3_SPEED_TEST_COMPOSITION: HEIGHTENED_CONCERN_PENDING_REVIEW")
    print("H2_STATUS: NOT_TESTABLE_WITH_CURRENT_EXPOSURE")
    print("ENTERPRISE_OUTCOME_READ: false MODEL_RUN: false")
    print("RUN:",run.name)
    return 0

def validate_paper_protocol(run,summary,gates):
    if summary.get("research_gate")!="READY_FOR_MEASUREMENT_DIVERGENCE_MANUSCRIPT_DRAFTING" or summary.get("primary_study_path")!="DESCRIPTIVE_MEASUREMENT_DIVERGENCE" or summary.get("paper_protocol_status")!="PASS_LOCKED": fail("paper protocol governance state invalid")
    if summary.get("h2_status")!="NOT_TESTABLE_WITH_CURRENT_EXPOSURE" or summary.get("enterprise_outcome_read") is not False or summary.get("model_run") or summary.get("causal_gate")!="CLOSED": fail("paper scope boundary violated")
    if gates.get("PAPER_PROTOCOL",{}).get("status")!="PASS" or gates.get("PAPER_CLAIM_GATE",{}).get("status")!="PASS": fail("paper protocol gates failed")
    lock=json.loads((ROOT/"protocol/measurement_divergence_paper_protocol_lock.json").read_text())
    if sha(ROOT/lock["protocol_path"])!=lock["protocol_sha256"] or lock["claim_ceiling"]!="DESCRIPTIVE_MEASUREMENT" or lock["enterprise_outcomes_allowed"] or lock["new_raw_ookla_processing_allowed"]: fail("protocol lock invalid")
    audit=json.loads((ROOT/"artifacts/qc/measurement_divergence_protocol_audit.json").read_text())
    if audit["status"]!="PASS" or audit["allowed_table_count"]!=12 or audit["allowed_figure_count"]!=8 or audit["enterprise_artifacts_authorized"] or audit["raw_ookla_files_authorized"] or audit["manuscript_started"]: fail("paper evidence allow-list invalid")
    dc=audit["data_challenge"]
    if dc["feasibility_verdict"]!="FEASIBLE_WITH_LIMITATIONS" or dc["design_support"]!="DESCRIPTIVE_MEASUREMENT_PAPER_ONLY": fail("DATA_CHALLENGE verdict invalid")
    decision=json.loads((ROOT/"artifacts/qc/exposure_adjudication_decision.json").read_text())
    if decision["measurement_decision"]!="EXPOSURE_REDESIGN_REQUIRED" or decision["h2_status"]!="NOT_TESTABLE_WITH_CURRENT_EXPOSURE" or decision["ch3_speed_test_composition"]!="HEIGHTENED_CONCERN_PENDING_REVIEW": fail("measurement adjudication weakened")
    if any((ROOT/"artifacts/models").glob("*")): fail("model artifact exists")
    registry=pd.read_csv(run/"artifact_registry.csv")
    if registry.empty or registry.sha256.str.len().ne(64).any(): fail("protocol artifact registry incomplete")
    print("VALIDATOR: PASS_MEASUREMENT_DIVERGENCE_PROTOCOL_LOCKED")
    print("RESEARCH_GATE: READY_FOR_MEASUREMENT_DIVERGENCE_MANUSCRIPT_DRAFTING")
    print("PRIMARY_STUDY_PATH: DESCRIPTIVE_MEASUREMENT_DIVERGENCE")
    print("H2_RECOVERY_PATH: SEPARATE_PROTOCOL_REQUIRED")
    print("H2_STATUS: NOT_TESTABLE_WITH_CURRENT_EXPOSURE")
    print("MODEL_RUN: false CAUSAL_GATE: CLOSED")
    print("RUN:",run.name)
    return 0

def validate_manuscript(run, summary, gates):
    if summary.get("status") != "PASS_MANUSCRIPT_DRAFT_COMPLETE": fail("manuscript run status invalid")
    if summary.get("research_gate") != "READY_FOR_INTERNAL_SCIENTIFIC_REVIEW": fail("manuscript research gate invalid")
    if (summary.get("manuscript_status"), summary.get("claim_audit"), summary.get("allow_list_compliance"), summary.get("numeric_reconciliation")) != ("DRAFT_COMPLETE", "PASS", "PASS", "PASS"): fail("manuscript completion metadata inconsistent")
    if summary.get("model_run") or summary.get("causal_gate") != "CLOSED" or summary.get("enterprise_outcome_read") is not False: fail("manuscript scope boundary violated")
    if summary.get("h2_status") != "NOT_TESTABLE_WITH_CURRENT_EXPOSURE" or summary.get("next_stage") != "INTERNAL_SCIENTIFIC_REVIEW": fail("manuscript H2 or next-stage state invalid")
    for name in ["MANUSCRIPT_DRAFT", "MANUSCRIPT_CLAIM_AUDIT", "MANUSCRIPT_NUMERIC_RECONCILIATION"]:
        if gates.get(name, {}).get("status") != "PASS": fail(f"manuscript gate failed: {name}")
    lock=json.loads((ROOT/"protocol/measurement_divergence_paper_protocol_lock.json").read_text(encoding="utf-8"))
    if sha(ROOT/lock["protocol_path"]) != lock["protocol_sha256"]: fail("manuscript protocol hash drift")
    manuscript=ROOT/"reports/measurement_divergence_manuscript.md"; appendix=ROOT/"reports/measurement_divergence_appendix.md"
    text=manuscript.read_text(encoding="utf-8")+"\n"+appendix.read_text(encoding="utf-8")
    if re.search(r"\b(enterprise|H2|treatment effect|policy effect|caused|causal effect)\b", text, re.I): fail("prohibited outcome or causal wording in manuscript")
    if re.search(r"\b(regression coefficient|p-value|statistically significant)\b", text, re.I): fail("model language in manuscript")
    validation=json.loads((ROOT/"artifacts/qc/manuscript_validation.json").read_text(encoding="utf-8"))
    if any(validation.get(k) != "PASS" for k in ["claim_audit","allow_list_compliance","numeric_reconciliation"]): fail("manuscript validation artifact failed")
    compliance=json.loads((ROOT/"artifacts/qc/manuscript_allow_list_compliance.json").read_text(encoding="utf-8"))
    if compliance.get("table_count") != 12 or compliance.get("figure_count") != 8 or compliance.get("new_result_calculations") != 0 or compliance.get("enterprise_outcome_references") != 0 or compliance.get("h2_references") != 0: fail("manuscript allow-list audit failed")
    claims=pd.read_csv(ROOT/"artifacts/qc/manuscript_claim_source_crosswalk.csv")
    if claims.empty or not set(claims.claim_level).issubset({"MEASUREMENT","DESCRIPTIVE_MEASUREMENT"}) or claims.status.str.startswith("SUPPORTED").sum()!=len(claims): fail("claim crosswalk failed")
    nums=pd.read_csv(ROOT/"artifacts/qc/manuscript_numeric_reconciliation.csv")
    if nums.empty or set(nums.status)!={"PASS"}: fail("numeric reconciliation failed")
    refs=pd.read_csv(ROOT/"reports/measurement_divergence_references.csv")
    if len(refs)!=3 or set(refs.cited)!={"YES"}: fail("reference list contains uncited entries")
    registry=pd.read_csv(run/"artifact_registry.csv")
    if registry.empty or registry.sha256.str.len().ne(64).any(): fail("manuscript artifact registry incomplete")
    if any((ROOT/"artifacts/models").glob("*")): fail("model artifact exists")
    print("VALIDATOR: PASS_MANUSCRIPT_DRAFT_COMPLETE")
    print("MANUSCRIPT_STATUS: DRAFT_COMPLETE")
    print("CLAIM_AUDIT: PASS")
    print("ALLOW_LIST_COMPLIANCE: PASS")
    print("NUMERIC_RECONCILIATION: PASS")
    print("MODEL_RUN: false CAUSAL_GATE: CLOSED")
    print("NEXT_STAGE: INTERNAL_SCIENTIFIC_REVIEW")
    print("RUN:", run.name)
    return 0

def validate_internal_review(run, summary, gates):
    if summary.get("status") != "PASS_INTERNAL_SCIENTIFIC_REVIEW" or summary.get("research_gate") != "READY_FOR_JOURNAL_STYLE_EDIT": fail("internal review status invalid")
    if summary.get("internal_scientific_review") != "PASS" or summary.get("construct_distinction") != "PASS": fail("internal review gates not passed")
    if summary.get("claim_audit") != "PASS" or summary.get("numeric_reconciliation") != "PASS": fail("claim or numeric review failed")
    if summary.get("model_run") or summary.get("causal_gate") != "CLOSED" or summary.get("h2_status") != "NOT_TESTABLE_WITH_CURRENT_EXPOSURE": fail("review governance state invalid")
    for name in ["INTERNAL_SCIENTIFIC_REVIEW", "INTERNAL_REVIEW_CLAIM_GATE", "INTERNAL_REVIEW_NUMERIC_GATE"]:
        if gates.get(name, {}).get("status") != "PASS": fail(f"review gate failed: {name}")
    decision=json.loads((ROOT/"artifacts/qc/internal_scientific_review_decision.json").read_text(encoding="utf-8"))
    if decision["initial_verdict"] != "REVISE" or decision["critical_open"] or decision["major_open"] or decision["internal_scientific_review"] != "PASS": fail("review decision unresolved")
    original=ROOT/"reports/measurement_divergence_manuscript.md"; archived=ROOT/"reports/archive/measurement_divergence_manuscript_draft_v1_20260913.md"
    if sha(original) != decision["original_draft_sha256"] or sha(archived) != decision["archived_draft_sha256"] or sha(original) != sha(archived): fail("original draft was not preserved")
    revision=ROOT/"reports/measurement_divergence_manuscript_revision_01.md"
    if sha(revision) != decision["revision_sha256"]: fail("revision hash mismatch")
    text=revision.read_text(encoding="utf-8")+(ROOT/"reports/measurement_divergence_appendix_revision_01.md").read_text(encoding="utf-8")
    if re.search(r"\b(enterprise|H2|treatment effect|policy effect|caused|causal effect|regression coefficient|p-value|statistically significant)\b",text,re.I): fail("prohibited wording in reviewed revision")
    for phrase in ["national-direction trend", "connectivity inequality is partly a property", "not driven by a single excluded province", "composition-invariant reading"]:
        if phrase.lower() in text.lower(): fail(f"unresolved review wording: {phrase}")
    matrix=pd.read_csv(ROOT/"artifacts/qc/internal_review_response_matrix.csv")
    if len(matrix)!=8 or (matrix.status=="RESOLVED").sum()!=7 or (matrix.status=="DEFERRED_NONBLOCKING").sum()!=1: fail("response matrix incomplete")
    claims=pd.read_csv(ROOT/"artifacts/qc/internal_review_claim_ledger.csv")
    if len(claims)!=13 or not claims.status.str.startswith("SUPPORTED").all(): fail("review claim ledger incomplete")
    nums=pd.read_csv(ROOT/"artifacts/qc/internal_review_numeric_reconciliation.csv", dtype={"displayed_value": str})
    result_section=text.split("## 4 Results",1)[1].split("## 5 Discussion",1)[0]
    result_prose="\n".join(line for line in result_section.splitlines() if not line.startswith("#"))
    displayed=set(re.findall(r"(?<![\w])-?\d+\.\d+",result_prose))
    if displayed != set(nums.displayed_value.astype(str)) or set(nums.status)!={"PASS"}: fail("numeric reconciliation not exhaustive")
    if any((ROOT/"artifacts/models").glob("*")): fail("model artifact exists")
    print("VALIDATOR: PASS_INTERNAL_SCIENTIFIC_REVIEW")
    print("INTERNAL_SCIENTIFIC_REVIEW: PASS")
    print("CLAIM_CEILING_COMPLIANCE: PASS")
    print("CONSTRUCT_DISTINCTION: PASS")
    print("CAUSAL_LANGUAGE_AUDIT: PASS")
    print("NUMERIC_RECONCILIATION: PASS")
    print("MODEL_RUN: false CAUSAL_GATE: CLOSED")
    print("NEXT_STAGE: JOURNAL_STYLE_EDIT")
    print("RUN:",run.name)
    return 0

def validate_internal_review_final(run,summary,gates):
    if summary.get("research_gate")!="READY_FOR_JOURNAL_STYLE_EDIT" or summary.get("internal_scientific_review")!="PASS" or summary.get("construct_distinction")!="PASS": fail("final internal review state invalid")
    if summary.get("model_run") or summary.get("causal_gate")!="CLOSED" or summary.get("h2_status")!="NOT_TESTABLE_WITH_CURRENT_EXPOSURE": fail("final review governance invalid")
    decision=json.loads((ROOT/"artifacts/qc/internal_scientific_review_final_decision.json").read_text(encoding="utf-8"))
    if decision["revision"]!="02" or decision["major_open"] or decision["internal_scientific_review"]!="PASS": fail("Revision 02 not approved")
    rev1=ROOT/"reports/measurement_divergence_manuscript_revision_01.md"; archive=ROOT/"reports/archive/measurement_divergence_manuscript_revision_01_20260913.md"; rev2=ROOT/"reports/measurement_divergence_manuscript_revision_02.md"
    if sha(rev1)!=sha(archive)!=decision["revision_01_sha256"]: fail("Revision 01 archive mismatch")
    if sha(rev1)!=decision["revision_01_sha256"] or sha(archive)!=decision["revision_01_archive_sha256"] or sha(rev2)!=decision["revision_02_sha256"]: fail("revision identity mismatch")
    text=rev2.read_text(encoding="utf-8"); body=text.split("## References",1)[0]; prose="\n".join(line for line in body.splitlines() if not line.startswith("#")); tokens=set(re.findall(r"(?<![\w])-?\d+(?:\.\d+)?",prose))
    nums=pd.read_csv(ROOT/"artifacts/qc/internal_review_numeric_reconciliation_v2.csv",dtype={"displayed_token":str})
    if tokens!=set(nums.displayed_token) or set(nums.status)!={"PASS"} or not set(nums.classification)<={"EMPIRICAL_OR_METHOD_VALUE","STRUCTURAL_EXEMPTION"}: fail("full numeric-token reconciliation failed")
    if any(x in text.lower() for x in ["connectivity inequality","spatial inequality","national-direction trend"]): fail("construct language remains")
    if re.search(r"\b(enterprise|H2|treatment effect|policy effect|caused|causal effect)\b",text,re.I): fail("prohibited wording in Revision 02")
    matrix=pd.read_csv(ROOT/"artifacts/qc/internal_review_response_matrix_v2.csv")
    if len(matrix)!=2 or set(matrix.status)!={"RESOLVED"}: fail("Revision 02 response matrix incomplete")
    print("VALIDATOR: PASS_INTERNAL_SCIENTIFIC_REVIEW")
    print("REVISION: 02")
    print("INTERNAL_SCIENTIFIC_REVIEW: PASS")
    print("CLAIM_CEILING_COMPLIANCE: PASS")
    print("CONSTRUCT_DISTINCTION: PASS")
    print("CAUSAL_LANGUAGE_AUDIT: PASS")
    print("NUMERIC_RECONCILIATION: PASS")
    print("MODEL_RUN: false CAUSAL_GATE: CLOSED")
    print("NEXT_STAGE: JOURNAL_STYLE_EDIT")
    print("RUN:",run.name)
    return 0

def validate_journal_edit(run,summary,gates):
    if summary.get("status")!="PASS_JOURNAL_STYLE_EDIT" or summary.get("research_gate")!="READY_FOR_LATEX_CONVERSION": fail("journal edit state invalid")
    if summary.get("manuscript_status")!="REVISION_03_JOURNAL_EDIT_PASS" or summary.get("internal_scientific_review")!="PASS": fail("journal manuscript status invalid")
    if summary.get("model_run") or summary.get("causal_gate")!="CLOSED" or summary.get("h2_status")!="NOT_TESTABLE_WITH_CURRENT_EXPOSURE": fail("journal governance invalid")
    for name in ["JOURNAL_STYLE_EDIT","JOURNAL_EDIT_CLAIM_GATE","JOURNAL_EDIT_NUMERIC_GATE"]:
        if gates.get(name,{}).get("status")!="PASS": fail(f"journal gate failed: {name}")
    audit=json.loads((ROOT/"artifacts/qc/journal_style_edit_audit.json").read_text())
    r2=ROOT/"reports/measurement_divergence_manuscript_revision_02.md"; archive=ROOT/"reports/archive/measurement_divergence_manuscript_revision_02_20260913.md"; r3=ROOT/"reports/measurement_divergence_manuscript_revision_03.md"
    if sha(r2)!=sha(archive) or sha(r2)!=audit["source_sha256"] or sha(r3)!=audit["revision_sha256"]: fail("journal version preservation failed")
    def tokens(p):
        body=p.read_text(encoding="utf-8").split("## References",1)[0]; prose="\n".join(x for x in body.splitlines() if not x.startswith("#")); return set(re.findall(r"(?<![\w])-?\d+(?:\.\d+)?",prose))
    if tokens(r2)!=tokens(r3) or audit["numeric_inventory_identity"]!="PASS": fail("journal numeric inventory changed")
    text=r3.read_text(encoding="utf-8")
    if re.search(r"\b(enterprise|H2|treatment effect|policy effect|caused|causal effect|regression coefficient|p-value|statistically significant)\b",text,re.I): fail("prohibited journal wording")
    if any(x in text.lower() for x in ["connectivity inequality","spatial inequality","national-direction trend"]): fail("construct distinction drift")
    if text.count("https://")!=r2.read_text(encoding="utf-8").count("https://"): fail("reference inventory changed")
    print("VALIDATOR: PASS_JOURNAL_STYLE_EDIT")
    print("REVISION: 03")
    print("CLAIM_CEILING_COMPLIANCE: PASS")
    print("CONSTRUCT_DISTINCTION: PASS")
    print("CAUSAL_LANGUAGE_AUDIT: PASS")
    print("NUMERIC_RECONCILIATION: PASS")
    print("VERSION_PRESERVATION: PASS")
    print("MODEL_RUN: false CAUSAL_GATE: CLOSED")
    print("NEXT_STAGE: LATEX_CONVERSION")
    print("RUN:",run.name)
    return 0

def validate_latex(run,summary,gates):
    if summary.get("status")!="PASS_LATEX_CONVERSION" or summary.get("research_gate")!="READY_FOR_TARGET_JOURNAL_SELECTION": fail("LaTeX run state invalid")
    if summary.get("manuscript_status")!="LATEX_JOURNAL_NEUTRAL_PASS" or summary.get("model_run") or summary.get("causal_gate")!="CLOSED": fail("LaTeX governance invalid")
    for name in ["LATEX_CONVERSION","LATEX_RECONCILIATION"]:
        if gates.get(name,{}).get("status")!="PASS": fail(f"LaTeX gate failed: {name}")
    audit=json.loads((ROOT/"artifacts/qc/latex_conversion_audit.json").read_text())
    if any(audit.get(k)!="PASS" for k in ["latex_conversion","content_reconciliation","numeric_reconciliation","table_figure_allowlist","citation_reconciliation","pdf_build"]): fail("LaTeX audit incomplete")
    if audit.get("source_revision")!="REVISION_03" or audit.get("tables")!=12 or audit.get("figures")!=8 or audit.get("citations")!=3: fail("LaTeX allow-list changed")
    source=ROOT/"reports/measurement_divergence_manuscript_revision_03.md"; appendix=ROOT/"reports/measurement_divergence_appendix_revision_03.md"
    main=ROOT/"latex/manuscript.tex"; apptex=ROOT/"latex/appendix.tex"; pdf=ROOT/"latex/manuscript.pdf"
    if sha(source)!=audit["source_sha256"] or sha(appendix)!=audit["appendix_source_sha256"] or sha(main)!=audit["tex_sha256"] or sha(apptex)!=audit["appendix_tex_sha256"] or sha(pdf)!=audit["pdf_sha256"]: fail("LaTeX identity mismatch")
    tex=main.read_text(encoding="utf-8"); app=apptex.read_text(encoding="utf-8")
    if tex.count("\\includegraphics")!=8 or "\\input{appendix.tex}" not in tex or app.count("\\input{tables/table_")!=12: fail("LaTeX assembly incomplete")
    if len(list((ROOT/"latex/tables").glob("table_*.tex")))!=12: fail("LaTeX table inventory mismatch")
    if re.search(r"enterprise|firm_density",(ROOT/"latex/tables/table_07.tex").read_text(encoding="utf-8"),re.I): fail("enterprise rows entered Table 07")
    recon=pd.read_csv(ROOT/"artifacts/qc/latex_content_reconciliation.csv")
    if recon.empty or set(recon.status)!={"PASS"} or not recon.numeric_tokens_preserved.all() or recon.source_file.nunique()!=2: fail("block/numeric reconciliation failed")
    cites=pd.read_csv(ROOT/"artifacts/qc/latex_citation_reconciliation.csv")
    if len(cites)!=3 or set(cites.status)!={"PASS"} or set(cites.latex_key)!={"vnnic","ookla","aws"}: fail("citation reconciliation failed")
    log=(ROOT/"latex/latex_build.log").read_text(encoding="utf-8",errors="replace").lower()
    if "overfull \\hbox" in log or "undefined references" in log or "latex warning" in log: fail("PDF build warnings remain")
    if any((ROOT/"artifacts/models").glob("*")): fail("model artifact exists")
    print("VALIDATOR: PASS_LATEX_CONVERSION")
    print("LATEX_CONVERSION: PASS")
    print("CONTENT_RECONCILIATION: PASS")
    print("NUMERIC_RECONCILIATION: PASS")
    print("TABLE_FIGURE_ALLOWLIST: PASS")
    print("CITATION_RECONCILIATION: PASS")
    print("PDF_BUILD: PASS")
    print("SOURCE_REVISION: REVISION_03")
    print("MODEL_RUN: false CAUSAL_GATE: CLOSED")
    print("NEXT_STAGE: TARGET_JOURNAL_SELECTION")
    print("RUN:",run.name)
    return 0

def main():
    runs = sorted(p for p in (ROOT / "runs").glob("run_*") if (p / "run_summary.json").exists())
    if not runs: fail("no completed run")
    run = runs[-1]
    summary = json.loads((run / "run_summary.json").read_text(encoding="utf-8"))
    gates = json.loads((run / "gate_summary.json").read_text(encoding="utf-8"))["gates"]
    if summary["status"]=="PASS_LATEX_CONVERSION":
        return validate_latex(run,summary,gates)
    if summary["status"]=="PASS_JOURNAL_STYLE_EDIT":
        return validate_journal_edit(run,summary,gates)
    if summary["status"]=="PASS_INTERNAL_SCIENTIFIC_REVIEW" and summary.get("requested_stage")=="internal-review-final":
        return validate_internal_review_final(run,summary,gates)
    if summary["status"]=="PASS_INTERNAL_SCIENTIFIC_REVIEW":
        return validate_internal_review(run,summary,gates)
    if summary["status"]=="PASS_MANUSCRIPT_DRAFT_COMPLETE":
        return validate_manuscript(run,summary,gates)
    if summary["status"]=="PASS_MEASUREMENT_DIVERGENCE_PROTOCOL_LOCKED":
        return validate_paper_protocol(run,summary,gates)
    if summary["status"]=="PASS_MEASUREMENT_REVIEW_ADJUDICATED":
        for name,expected in OLD.items():
            if sha(ROOT/"runs"/name/"run_summary.json")!=expected: fail(f"historical run modified: {name}")
        return validate_measurement_review(run,summary,gates)
    if summary["status"] in {"PASS_OOKLA_MIXED_REQUIRES_HUMAN_REVIEW","PASS_OOKLA_READY_FOR_ASSOCIATIONAL_PROTOCOL_REVIEW"}:
        if summary["causal_gate"]!="CLOSED" or summary["decision_2269_gate"]!="FAIL_PRIMARY_ROUTE": fail("causal closure changed")
        for name,expected in OLD.items():
            if sha(ROOT/"runs"/name/"run_summary.json")!=expected: fail(f"historical run modified: {name}")
        return validate_ookla(run,summary,gates)
    if summary["status"] == "PASS_DESCRIPTIVE_READY_FOR_MEASUREMENT_VALIDATION":
        if summary["causal_gate"] != "CLOSED" or summary["decision_2269_gate"] != "FAIL_PRIMARY_ROUTE": fail("causal closure changed")
        for name, expected in OLD.items():
            if sha(ROOT / "runs" / name / "run_summary.json") != expected: fail(f"historical run modified: {name}")
        return validate_descriptive(run,summary,gates)
    if summary["status"] != "PASS_PANEL_READY_FOR_DESCRIPTIVE" or summary.get("research_gate") != "READY_FOR_DESCRIPTIVE_ANALYSIS": fail("latest status is inconsistent")
    if summary["causal_gate"] != "CLOSED" or summary["decision_2269_gate"] != "FAIL_PRIMARY_ROUTE": fail("causal closure changed")
    if not summary.get("analysis_panel_created") or summary.get("descriptive_analysis_run") or summary.get("model_run"): fail("scope flags inconsistent")
    required = ["G0", "G1", "G2", "G3", "G4", "G5", "G4_EXPOSURE_CONSTRUCTION", "G1_PRIMARY_PROVENANCE", "G2_PRIMARY_SEMANTICS", "G5_PRIMARY_OUTCOME", "G6_PANEL_AND_MERGE", "G7_PANEL_READINESS", "G8_CLAIM", "G9_REPRODUCIBILITY"]
    if any(gates.get(x, {}).get("status") != "PASS" for x in required): fail("one or more current gates are not PASS")
    if gates["G1_PRIMARY_PROVENANCE"]["evidence"].get("classification") != "PASS_WITH_LIMITATIONS": fail("G1 limitation missing")
    sem = gates["G2_PRIMARY_SEMANTICS"]["evidence"]
    if (sem.get("classification"), sem.get("value"), sem.get("entry_intensity")) != ("PASS_WITH_LIMITATIONS", "NOT_USED", "EXPLORATORY_UNAVAILABLE"): fail("semantic metadata contradictory")
    for name, expected in OLD.items():
        if sha(ROOT / "runs" / name / "run_summary.json") != expected: fail(f"historical run modified: {name}")

    lock = json.loads((ROOT / "protocol/protocol_effective_lock.json").read_text(encoding="utf-8"))
    base, amendment = sha(ROOT / lock["base_protocol_path"]), sha(ROOT / lock["amendment_path"])
    effective = hashlib.sha256(f"{base.lower()}|{amendment.lower()}".encode("ascii")).hexdigest()
    if effective != lock["effective_protocol_sha256"]: fail("effective protocol hash mismatch")

    ids = pd.read_csv(ROOT / "artifacts/qc/province_identifier_audit.csv", dtype={"px_geo_code": str})
    if len(ids) != 63 or ids.province_id_legacy63.nunique() != 63 or (ids.match_status != "MATCHED").any() or set(ids.px_geo_code) & AGGREGATES: fail("identifier audit failed")
    monthly = pd.read_parquet(ROOT / "data/processed/fact_vnnic_province_month_primary.parquet")
    annual = pd.read_parquet(ROOT / "data/processed/fact_connectivity_province_year.parquet")
    outcome = pd.read_parquet(ROOT / "data/processed/fact_nso_primary_outcome.parquet")
    panel = pd.read_parquet(ROOT / "data/analysis/analysis_panel_2021_2024.parquet")
    if not unique(monthly, ["province_id_legacy63", "year", "month"], 2268): fail("monthly contract failed")
    if {"value", "value_raw"} & set(monthly.columns): fail("VNNIC value entered analytical data")
    if set(monthly.network.str.lower()) != {"ftth"} or set(monthly.year) != {2021, 2022, 2023, 2024} or set(monthly.month) != set(range(4, 13)): fail("FTTH window changed")
    counts = monthly.groupby(["province_id_legacy63", "year"]).month.agg(["size", "nunique"])
    if len(counts) != 252 or not counts.eq(9).all().all(): fail("nine-month rule failed")
    if (~np.isfinite(monthly.download_mbps) | monthly.download_mbps.le(0)).any(): fail("download support invalid")
    if not unique(annual, ["province_id_legacy63", "year"], 252): fail("annual fact contract failed")
    recomputed = monthly.groupby(["province_id_legacy63", "year"]).download_mbps.median().sort_index()
    observed = annual.set_index(["province_id_legacy63", "year"]).ftth_download_median_apr_dec_mbps.sort_index()
    if not np.allclose(recomputed, observed, rtol=0, atol=1e-12): fail("median reconciliation failed")

    if not unique(outcome, ["province_id_legacy63", "year"], 252) or outcome.groupby("year").province_id_legacy63.nunique().ne(63).any(): fail("NSO fact contract failed")
    if set(outcome.table_code) != {"V05.05"} or outcome.active_firms_per_1000.le(0).any(): fail("NSO values invalid")
    official = pd.read_parquet(ROOT / "data/reference/nso_official_snapshot_20260913/nso_official_snapshot_long.parquet")
    src = official[(official.table_code == "V05.05") & official.year.between(2021, 2024)].copy(); src["px_geo_code"] = src.px_geo_code.astype(str)
    if len(src[src.px_geo_code.isin(AGGREGATES)]) != 28: fail("aggregate exclusion evidence changed")
    src = src[~src.px_geo_code.isin(AGGREGATES)].merge(ids[["px_geo_code", "province_id_legacy63"]], on="px_geo_code", validate="many_to_one")
    check = src.merge(outcome[["province_id_legacy63", "year", "active_firms_per_1000"]], on=["province_id_legacy63", "year"], validate="one_to_one")
    if len(check) != 252 or not np.array_equal(check.official_value.to_numpy(), check.active_firms_per_1000.to_numpy()): fail("official PXWeb values do not reconcile")

    if not unique(panel, ["province_id_legacy63", "year"], 252) or panel.groupby("year").province_id_legacy63.nunique().ne(63).any(): fail("panel skeleton contract failed")
    if any("entry" in c.lower() for c in panel.columns) or panel.isna().any().any(): fail("entry field or missing panel value")
    if set(panel.merge_status_connectivity) != {"both"} or set(panel.merge_status_nso) != {"both"}: fail("unmatched panel row")
    merge = json.loads((ROOT / "artifacts/qc/panel_merge_audit.json").read_text(encoding="utf-8"))
    if len(merge) != 2 or any(x["status"] != "PASS" or x["observed_cardinality"] != "1:1" or x["matched_rows"] != 252 or x["unmatched_left_rows"] or x["unmatched_right_rows"] for x in merge): fail("merge audit failed")
    if gates["G9_REPRODUCIBILITY"]["evidence"].get("stable_value_hashes_match") is not True: fail("reproducibility evidence missing")
    registry = pd.read_csv(run / "artifact_registry.csv")
    if registry.empty or registry.sha256.str.len().ne(64).any(): fail("artifact hashes incomplete")
    if any(any((ROOT / f).glob("*")) for f in ["artifacts/models", "artifacts/figures", "artifacts/tables"]): fail("substantive artifacts created")
    forbidden = re.compile(r"\b(caused|treatment effect|policy effect|impact of decision 2269)\b", re.I)
    if forbidden.search((ROOT / "reports/claim_audit.csv").read_text(encoding="utf-8-sig")): fail("unsupported causal wording")
    for path in [ROOT / "reports/panel_construction_report.md", ROOT / "reports/panel_construction_next_action.md", run / "lineage_edges.csv"]:
        if not path.exists(): fail(f"missing artifact: {path}")
    print("VALIDATOR: PASS_PANEL_READY_FOR_DESCRIPTIVE")
    print("RESEARCH_GATE: READY_FOR_DESCRIPTIVE_ANALYSIS")
    print("ROWS: monthly=2268 annual_connectivity=252 nso=252 panel=252")
    print("MERGES: connectivity=252/252 nso=252/252 losses=0")
    print("CAUSAL_GATE: CLOSED")
    print("RUN:", run.name)
    return 0

if __name__ == "__main__": raise SystemExit(main())
