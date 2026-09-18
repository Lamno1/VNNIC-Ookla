import json
from pathlib import Path
import numpy as np
import pandas as pd
from connectivity_enterprise.core.paths import WORKING_ROOT

def test_only_authorized_fixed_q2_partitions_are_registered():
    pre=json.loads((WORKING_ROOT/"artifacts/qc/ookla_preflight.json").read_text())
    assert pre["authorized_files"]==pre["discovered_files"]==4
    assert {x["year"] for x in pre["files"]}=={2021,2022,2023,2024}
    assert all("\\fixed\\" in x["path"].lower() and "\\q2\\" in x["path"].lower() and x["schema_variant"]=="EXTENDED_LATENCY_V2" for x in pre["files"])

def test_pilot_and_batch_accounting_pass():
    bench=json.loads((WORKING_ROOT/"artifacts/qc/ookla_2024q2_benchmark.json").read_text())
    assert bench["pilot_gate"]=="PASS" and bench["aggregate_reproducible"] is True
    assert bench["failed_batches"]==bench["ambiguous"]==bench["invalid_coordinates"]==0
    assert bench["peak_rss_bytes"]<=4*1024**3
    cov=pd.read_csv(WORKING_ROOT/"artifacts/qc/ookla_coverage_audit.csv")
    assert cov.rows_scanned.sum()==23796365 and cov.provinces_represented.eq(63).all()
    assert cov.failed_batches.sum()==0

def test_quadkey_assignment_and_aggregate_contract():
    audit=pd.read_csv(WORKING_ROOT/"artifacts/qc/ookla_spatial_assignment_audit.csv")
    assert len(audit)>=100 and audit.absolute_lon_difference.max()<.0001 and audit.absolute_lat_difference.max()<.0001
    out=pd.read_parquet(WORKING_ROOT/"data/processed/ookla_fixed_q2_adm1_2021_2024.parquet")
    assert len(out)==252 and out.groupby("year").province_id_legacy63.nunique().eq(63).all()
    assert out.ookla_tile_median_download_mbps.gt(0).all()

def test_vnnic_q2_is_validation_only_and_unweighted():
    q2=pd.read_parquet(WORKING_ROOT/"data/processed/vnnic_q2_validation_2021_2024.parquet")
    assert len(q2)==252 and set(q2.months_observed)=={3} and set(q2.validation_role)=={"VALIDATION_ONLY"}
    assert not ({"value","value_raw"}&set(q2.columns))

def test_classification_preserves_vnnic_and_ch3_not_eliminated():
    decision=json.loads((WORKING_ROOT/"artifacts/qc/measurement_validation_decision.json").read_text())
    assert decision["measurement_validation_classification"]=="MIXED_MEASUREMENT_SUPPORT"
    assert decision["vnnic_descriptive_classification"]=="DESCRIPTIVE_DIVERGENCE_UNCHANGED"
    assert decision["ch3_speed_test_composition"]!="ELIMINATED"
    assert decision["researcher_defined_thresholds"] is True

def test_partition_checkpoints_and_no_models():
    manifest=pd.read_csv(WORKING_ROOT/"artifacts/manifests/ookla_validation_partition_manifest.csv")
    assert len(manifest)==4 and set(manifest.status)=={"PASS"}
    assert manifest.checkpoint_sha256.str.len().eq(64).all()
    assert not any((WORKING_ROOT/"artifacts/models").glob("*"))
