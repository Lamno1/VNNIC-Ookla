import hashlib
import json
import numpy as np
import pandas as pd
from connectivity_enterprise.core.paths import WORKING_ROOT

def test_authoritative_panel_and_addendum_locks():
    panel=WORKING_ROOT/"data/analysis/analysis_panel_2021_2024.parquet"
    assert hashlib.sha256(panel.read_bytes()).hexdigest()=="7711c489b5b6da109fa4050cc04d29f252d6dbade99274ccac015a5824b0454e"
    lock=json.loads((WORKING_ROOT/"protocol/descriptive_analysis_addendum_lock.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((WORKING_ROOT/lock["addendum_path"]).read_bytes()).hexdigest()==lock["sha256"]
    assert lock["h2_status"]=="REGISTERED_NOT_TESTED"

def test_summary_statistics_recompute():
    panel=pd.read_parquet(WORKING_ROOT/"data/analysis/analysis_panel_2021_2024.parquet")
    table=pd.read_csv(WORKING_ROOT/"artifacts/tables/table_02_connectivity_summary_by_year.csv").set_index("year")
    for year,g in panel.groupby("year"):
        x=g.ftth_download_median_apr_dec_mbps
        assert np.isclose(table.loc[year,"mean"],x.mean(),rtol=0,atol=1e-12)
        assert np.isclose(table.loc[year,"standard_deviation"],x.std(ddof=1),rtol=0,atol=1e-12)
        assert np.isclose(table.loc[year,"p90"],x.quantile(.9),rtol=0,atol=1e-12)

def test_figures_have_png_svg_and_companion_data():
    names=["01_ftth_distribution_by_year","02_ftth_average_province_trend","03_ftth_maps_2021_2024","04_ftth_change_map_2021_2024","05_ftth_rank_mobility","06_firm_density_distribution_by_year","07_firm_density_average_province_trend","08_firm_density_maps_2021_2024","09_firm_density_change_map_2021_2024"]
    for name in names:
        base=WORKING_ROOT/"artifacts/figures"/f"figure_{name}"
        assert base.with_suffix(".png").exists() and base.with_suffix(".svg").exists()
        assert (WORKING_ROOT/"artifacts/figures"/f"figure_{name}_data.csv").exists()

def test_outliers_retained_and_counter_hypotheses_unresolved():
    out=pd.read_csv(WORKING_ROOT/"artifacts/qc/descriptive_outlier_review.csv")
    assert set(out.retained_excluded_status)=={"RETAINED"}
    counter=pd.read_csv(WORKING_ROOT/"protocol/counter_hypotheses.csv")
    assert len(counter)==4
    assert set(counter.loc[counter.alternative_id!="CH3","current_status"])=={"UNRESOLVED"}
    assert counter.loc[counter.alternative_id=="CH3","current_status"].iloc[0] in {"UNRESOLVED","REMAINS_UNRESOLVED","PARTIALLY_CONSTRAINED","HEIGHTENED_CONCERN"}

def test_no_bivariate_or_model_outputs():
    assert not any((WORKING_ROOT/"artifacts/models").glob("*"))
    claims=pd.read_csv(WORKING_ROOT/"reports/claim_audit.csv")
    assert set(claims[claims.claim_id.str.startswith("D")].claim_level)=={"DESCRIPTIVE"}
    decision=json.loads((WORKING_ROOT/"artifacts/qc/descriptive_classification.json").read_text())
    assert decision["causal_interpretation"] is False
