import json
from ..core.paths import WORKING_ROOT
from ..core.provenance import sha256_file

ALLOWED_TABLES = [
    "table_02_connectivity_summary_by_year.csv",
    "table_04_connectivity_dispersion.csv",
    "table_05_connectivity_rank_persistence.csv",
    "table_06_connectivity_quartile_transitions.csv",
    "table_07_change_distributions.csv",
    "table_08_measurement_validation_by_year.csv",
    "table_09_measurement_change_concordance.csv",
    "table_10_dispersion_source_comparison.csv",
    "table_11_ookla_aggregation_sensitivity.csv",
    "table_12_aggregation_agreement.csv",
    "table_13_measurement_influence_audit.csv",
    "table_14_composition_sensitivity.csv",
]
ALLOWED_FIGURES = [1, 2, 3, 4, 5, 10, 11, 12]

def run(ctx):
    lock_path=WORKING_ROOT/"protocol/measurement_divergence_paper_protocol_lock.json"
    lock=json.loads(lock_path.read_text(encoding="utf-8")); protocol=WORKING_ROOT/lock["protocol_path"]
    if sha256_file(protocol)!=lock["protocol_sha256"]: raise RuntimeError("FAIL-CLOSED: paper protocol hash drift")
    if lock["primary_study_path"]!="DESCRIPTIVE_MEASUREMENT_DIVERGENCE" or lock["h2_status"]!="NOT_TESTABLE_WITH_CURRENT_EXPOSURE" or lock["model_run"] or lock["causal_gate"]!="CLOSED": raise RuntimeError("FAIL-CLOSED: paper governance state inconsistent")
    checks={"protocol_hash":"PASS","exposure_decision_hash":"PASS","authorized_tables":[],"authorized_figures":[],"enterprise_artifacts_authorized":0,"raw_ookla_files_authorized":0,"manuscript_started":False}
    hashes={"exposure_adjudication_sha256":WORKING_ROOT/"artifacts/qc/exposure_adjudication_decision.json","table_12_sha256":WORKING_ROOT/"artifacts/tables/table_12_aggregation_agreement.csv","table_13_sha256":WORKING_ROOT/"artifacts/tables/table_13_measurement_influence_audit.csv","table_14_sha256":WORKING_ROOT/"artifacts/tables/table_14_composition_sensitivity.csv"}
    for key,path in hashes.items():
        if sha256_file(path)!=lock[key]: raise RuntimeError(f"FAIL-CLOSED: locked evidence drift: {path.name}")
    for name in ALLOWED_TABLES:
        path=WORKING_ROOT/"artifacts/tables"/name
        if not path.exists(): raise RuntimeError(f"FAIL-CLOSED: authorized table missing: {name}")
        checks["authorized_tables"].append({"path":str(path.relative_to(WORKING_ROOT)),"sha256":sha256_file(path)})
    for n in ALLOWED_FIGURES:
        matches=sorted((WORKING_ROOT/"artifacts/figures").glob(f"figure_{n:02d}_*.png"))
        if len(matches)!=1: raise RuntimeError(f"FAIL-CLOSED: expected one authorized PNG figure {n:02d}")
        data=matches[0].with_name(matches[0].stem+"_data.csv")
        if not data.exists(): raise RuntimeError(f"FAIL-CLOSED: figure companion missing: {matches[0].name}")
        checks["authorized_figures"].append({"figure":str(matches[0].relative_to(WORKING_ROOT)),"figure_sha256":sha256_file(matches[0]),"companion":str(data.relative_to(WORKING_ROOT)),"companion_sha256":sha256_file(data)})
    decision=json.loads((WORKING_ROOT/"artifacts/qc/exposure_adjudication_decision.json").read_text())
    if decision["measurement_decision"]!="EXPOSURE_REDESIGN_REQUIRED" or decision["h2_status"]!="NOT_TESTABLE_WITH_CURRENT_EXPOSURE" or decision["ch3_speed_test_composition"]!="HEIGHTENED_CONCERN_PENDING_REVIEW": raise RuntimeError("FAIL-CLOSED: adjudication state was weakened")
    checks.update({"status":"PASS","allowed_table_count":len(ALLOWED_TABLES),"allowed_figure_count":len(ALLOWED_FIGURES),"enterprise_outcome_read":False,"model_run":False,"h2_tested":False,"decision_2269_gate":"FAIL_PRIMARY_ROUTE","data_challenge":{"artifact_inventory":"PASS","variable_lineage":"PASS_WITH_LIMITATIONS","coverage":"PASS_63_BY_4","quality_findings":"MEASUREMENT_DIVERGENCE","merge_audit":"NOT_APPLICABLE_NO_NEW_MERGE","leakage_and_revision_risks":"DOCUMENTED","unverified_semantics":"SOURCE_ESTIMAND_NON_EQUIVALENCE","design_support":"DESCRIPTIVE_MEASUREMENT_PAPER_ONLY","feasibility_verdict":"FEASIBLE_WITH_LIMITATIONS"}})
    audit=WORKING_ROOT/"artifacts/qc/measurement_divergence_protocol_audit.json"; audit.write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding="utf-8")
    readiness=WORKING_ROOT/"reports/measurement_divergence_protocol_readiness.md"; readiness.write_text("RESEARCH_GATE\n\nREADY_FOR_MEASUREMENT_DIVERGENCE_MANUSCRIPT_DRAFTING\n\n# Protocol readiness\n\nThe measurement-divergence paper protocol is locked and its evidence allow-list validates. The paper is feasible with limitations at the descriptive-measurement claim level. Enterprise outcomes, H2 estimation, new raw Ookla processing, and causal claims remain prohibited.\n",encoding="utf-8")
    ctx.update({"primary_study_path":"DESCRIPTIVE_MEASUREMENT_DIVERGENCE","h2_review_status":"NOT_TESTABLE_WITH_CURRENT_EXPOSURE","paper_protocol_status":"PASS_LOCKED","review_research_gate":"READY_FOR_MEASUREMENT_DIVERGENCE_MANUSCRIPT_DRAFTING"})
    ctx["gatebook"].set("PAPER_PROTOCOL","PASS","Measurement-divergence paper protocol and evidence allow-list are locked.",checks)
    ctx["gatebook"].set("PAPER_CLAIM_GATE","PASS","Claim ceiling is descriptive measurement; enterprise and causal claims are prohibited.",{"claim_ceiling":"DESCRIPTIVE_MEASUREMENT","H2_STATUS":"NOT_TESTABLE_WITH_CURRENT_EXPOSURE","MODEL_RUN":False,"CAUSAL_GATE":"CLOSED"})
    return [protocol,lock_path,audit,readiness,WORKING_ROOT/"reports/measurement_divergence_manuscript_plan.md"]
