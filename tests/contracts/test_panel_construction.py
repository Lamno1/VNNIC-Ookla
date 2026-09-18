import hashlib
import json
import numpy as np
import pandas as pd
from connectivity_enterprise.core.paths import WORKING_ROOT

def test_historical_runs_and_effective_protocol_are_immutable():
    expected = {
        "run_20260912T174708Z": "8bd7b8035d9ba5c756c0cf03d894c31157eec8866a271640cb151f33b87ed981",
        "run_20260913T013734Z": "c9e340eeaaed54e66c2ad400c329448f2f489685d8f745c40fd9ad8486cccdf9",
    }
    for run, digest in expected.items():
        assert hashlib.sha256((WORKING_ROOT / "runs" / run / "run_summary.json").read_bytes()).hexdigest() == digest
    lock = json.loads((WORKING_ROOT / "protocol/protocol_effective_lock.json").read_text(encoding="utf-8"))
    base = hashlib.sha256((WORKING_ROOT / lock["base_protocol_path"]).read_bytes()).hexdigest()
    amend = hashlib.sha256((WORKING_ROOT / lock["amendment_path"]).read_bytes()).hexdigest()
    assert hashlib.sha256(f"{base}|{amend}".encode()).hexdigest() == lock["effective_protocol_sha256"]

def test_primary_monthly_fact_obeys_locked_filter_and_no_value():
    df = pd.read_parquet(WORKING_ROOT / "data/processed/fact_vnnic_province_month_primary.parquet")
    assert len(df) == 2268 and not df.duplicated(["province_id_legacy63", "year", "month"]).any()
    assert set(df.network.str.lower()) == {"ftth"} and set(df.month) == set(range(4, 13))
    assert set(df.year) == {2021, 2022, 2023, 2024}
    assert not ({"value", "value_raw"} & set(df.columns))
    assert df.groupby(["province_id_legacy63", "year"]).month.agg(["size", "nunique"]).eq(9).all().all()

def test_annual_connectivity_medians_reconcile():
    month = pd.read_parquet(WORKING_ROOT / "data/processed/fact_vnnic_province_month_primary.parquet")
    annual = pd.read_parquet(WORKING_ROOT / "data/processed/fact_connectivity_province_year.parquet")
    assert len(annual) == 252 and not annual.duplicated(["province_id_legacy63", "year"]).any()
    left = month.groupby(["province_id_legacy63", "year"]).download_mbps.median().sort_index()
    right = annual.set_index(["province_id_legacy63", "year"]).ftth_download_median_apr_dec_mbps.sort_index()
    assert np.allclose(left, right, rtol=0, atol=1e-12)
    assert annual.complete_primary_window.all()

def test_nso_fact_is_exact_official_v0505_only():
    fact = pd.read_parquet(WORKING_ROOT / "data/processed/fact_nso_primary_outcome.parquet")
    assert len(fact) == 252 and set(fact.table_code) == {"V05.05"}
    assert fact.groupby("year").province_id_legacy63.nunique().eq(63).all()
    assert fact.active_firms_per_1000.gt(0).all()
    assert not fact.astype(str).apply(lambda x: x.str.contains("quarantine", case=False).any()).any()

def test_panel_and_merge_audits_are_complete_without_entry_rate():
    panel = pd.read_parquet(WORKING_ROOT / "data/analysis/analysis_panel_2021_2024.parquet")
    assert len(panel) == 252 and not panel.duplicated(["province_id_legacy63", "year"]).any()
    assert panel.groupby("year").province_id_legacy63.nunique().eq(63).all()
    assert panel.exposure_complete.all() and panel.outcome_complete.all()
    assert not any("entry" in c.lower() for c in panel.columns)
    merge = json.loads((WORKING_ROOT / "artifacts/qc/panel_merge_audit.json").read_text(encoding="utf-8"))
    assert len(merge) == 2
    assert all(x["status"] == "PASS" and x["matched_rows"] == 252 and x["unmatched_left_rows"] == 0 and x["unmatched_right_rows"] == 0 for x in merge)

def test_no_model_outputs_exist():
    assert not any((WORKING_ROOT / "artifacts/models").glob("*"))
