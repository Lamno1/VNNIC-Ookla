import json
import pandas as pd
from connectivity_enterprise.core.paths import WORKING_ROOT

def test_stage_a_preserves_preregistered_failure_and_blocks_h2():
    d=json.loads((WORKING_ROOT/"artifacts/qc/exposure_adjudication_decision.json").read_text())
    assert d["diagnostic_label"]=="POST_HOC_MEASUREMENT_DIAGNOSTIC"
    assert d["preregistered_measurement_classification"]=="MIXED_MEASUREMENT_SUPPORT_UNCHANGED"
    assert d["preregistered_rank_failure_preserved"] is True
    assert d["measurement_decision"]=="EXPOSURE_REDESIGN_REQUIRED"
    assert d["h2_status"]=="NOT_TESTABLE_WITH_CURRENT_EXPOSURE"

def test_all_aggregation_variants_are_reported_without_selection():
    t=pd.read_csv(WORKING_ROOT/"artifacts/tables/table_12_aggregation_agreement.csv")
    assert len(t)==16 and t.aggregation_variant.nunique()==4
    assert t.groupby(["aggregation_variant","year"]).size().eq(1).all()
    assert set(t.N)=={63}
    assert (t.groupby("aggregation_variant").change_rank_spearman_2021_2024.first()<0).all()

def test_leave_one_out_retains_every_province():
    t=pd.read_csv(WORKING_ROOT/"artifacts/tables/table_13_measurement_influence_audit.csv")
    assert len(t)==1260 and t.excluded_province_id_legacy63.nunique()==63
    assert set(t.influence_disposition)=={"RETAINED"}

def test_composition_concern_is_heightened_not_resolved():
    t=pd.read_csv(WORKING_ROOT/"artifacts/tables/table_14_composition_sensitivity.csv")
    d=json.loads((WORKING_ROOT/"artifacts/qc/exposure_adjudication_decision.json").read_text())
    assert len(t)==24 and t.aggregation_variant.nunique()==4
    assert d["maximum_absolute_composition_spearman"]>=.5
    assert d["ch3_speed_test_composition"]=="HEIGHTENED_CONCERN_PENDING_REVIEW"

def test_stage_b_and_models_are_not_run():
    d=json.loads((WORKING_ROOT/"artifacts/qc/exposure_adjudication_decision.json").read_text())
    assert d["stage_b_run"] is False
    assert d["stage_b_status"]=="NOT_RUN_STAGE_A_TERMINAL_EXPOSURE_REDESIGN"
    assert not (WORKING_ROOT/"artifacts/tables/table_15_quarterly_temporal_reliability.csv").exists()
    assert not any((WORKING_ROOT/"artifacts/models").glob("*"))
    assert d["enterprise_outcome_read"] is False
