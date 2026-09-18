import hashlib
import json
from connectivity_enterprise.core.paths import WORKING_ROOT

def test_paper_protocol_is_hash_locked():
    lock=json.loads((WORKING_ROOT/"protocol/measurement_divergence_paper_protocol_lock.json").read_text())
    assert hashlib.sha256((WORKING_ROOT/lock["protocol_path"]).read_bytes()).hexdigest()==lock["protocol_sha256"]
    assert lock["primary_study_path"]=="DESCRIPTIVE_MEASUREMENT_DIVERGENCE"
    assert lock["claim_ceiling"]=="DESCRIPTIVE_MEASUREMENT"

def test_paper_protocol_excludes_enterprise_and_models():
    lock=json.loads((WORKING_ROOT/"protocol/measurement_divergence_paper_protocol_lock.json").read_text())
    audit=json.loads((WORKING_ROOT/"artifacts/qc/measurement_divergence_protocol_audit.json").read_text())
    assert lock["enterprise_outcomes_allowed"] is False and lock["new_raw_ookla_processing_allowed"] is False
    assert audit["enterprise_artifacts_authorized"]==audit["raw_ookla_files_authorized"]==0
    assert audit["manuscript_started"] is False
    assert not any((WORKING_ROOT/"artifacts/models").glob("*"))

def test_data_challenge_supports_only_descriptive_measurement_paper():
    audit=json.loads((WORKING_ROOT/"artifacts/qc/measurement_divergence_protocol_audit.json").read_text())
    dc=audit["data_challenge"]
    assert dc["feasibility_verdict"]=="FEASIBLE_WITH_LIMITATIONS"
    assert dc["design_support"]=="DESCRIPTIVE_MEASUREMENT_PAPER_ONLY"
    assert dc["quality_findings"]=="MEASUREMENT_DIVERGENCE"
