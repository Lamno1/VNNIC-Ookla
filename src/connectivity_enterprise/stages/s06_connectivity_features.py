from pathlib import Path
import json

import numpy as np
import pandas as pd

from ..core.contracts import require_unique, validate_schema_contract
from ..core.paths import WORKING_ROOT, assert_safe_input_path, sources_config


def run(ctx):
    if not ctx["gatebook"].is_pass("G2", "G3", "G4"):
        ctx["gatebook"].set("G4_EXPOSURE_CONSTRUCTION", "FAIL", "Exposure construction requires G2, G3 and G4 structural PASS.")
        return []

    source = assert_safe_input_path(Path(sources_config()["sources"]["vnnic_legacy_panel"]))
    raw = pd.read_csv(source, dtype={"code": str})
    raw["code"] = raw["code"].str.zfill(2)
    dim = pd.read_parquet(WORKING_ROOT / "data/reference/dim_province_legacy63.parquet")
    bridge = dim[["province_id_legacy63", "shapeISO", "vnnic_code"]].copy()
    bridge["vnnic_code"] = bridge["vnnic_code"].astype(str).str.zfill(2)

    selected = raw[
        raw["network"].str.lower().eq("ftth")
        & raw["year"].between(2021, 2024)
        & raw["month"].between(4, 12)
    ].copy()
    selected = selected.merge(bridge, left_on="code", right_on="vnnic_code", how="left", validate="many_to_one", suffixes=("_raw", ""))
    if len(selected) != 2268 or selected["province_id_legacy63"].isna().any():
        raise RuntimeError("FAIL-CLOSED: primary VNNIC selection is not 2,268 mapped rows")
    if "shapeISO_raw" in selected and not selected["shapeISO_raw"].eq(selected["shapeISO"]).all():
        raise RuntimeError("FAIL-CLOSED: VNNIC shapeISO disagrees with canonical dimension")

    monthly = pd.DataFrame({
        "province_id_legacy63": selected["province_id_legacy63"],
        "shapeISO": selected["shapeISO"],
        "vnnic_code": selected["vnnic_code"],
        "year": selected["year"].astype(int),
        "month": selected["month"].astype(int),
        "date": pd.to_datetime(selected["date"]).dt.strftime("%Y-%m-%d"),
        "network": "ftth",
        "download_mbps": pd.to_numeric(selected["download"], errors="coerce"),
        "upload_mbps": pd.to_numeric(selected["upload"], errors="coerce"),
        "ping_ms": pd.to_numeric(selected["ping"], errors="coerce"),
        "jitter_ms": pd.to_numeric(selected["jitter"], errors="coerce"),
        "source_file": selected["source_file"],
        "semantic_status": "PASS_WITH_LIMITATIONS",
        "source_artifact_id": "vnnic_province_month_legacy63_csv",
        "run_id": ctx["run_id"],
        "config_hash": ctx["config_hash"],
    }).sort_values(["province_id_legacy63", "year", "month"]).reset_index(drop=True)
    require_unique(monthly, ["province_id_legacy63", "year", "month"], "primary VNNIC month")
    if set(monthly["month"]) != set(range(4, 13)) or set(monthly["year"]) != {2021, 2022, 2023, 2024}:
        raise RuntimeError("FAIL-CLOSED: primary month/year universe changed")
    if (~np.isfinite(monthly["download_mbps"]) | monthly["download_mbps"].le(0)).any():
        raise RuntimeError("FAIL-CLOSED: invalid primary monthly download")
    validate_schema_contract(monthly, WORKING_ROOT / "config/schemas/fact_vnnic_province_month_primary.json", "fact_vnnic_province_month_primary")
    monthly_path = WORKING_ROOT / "data/processed/fact_vnnic_province_month_primary.parquet"
    monthly.to_parquet(monthly_path, index=False)

    annual = monthly.groupby(["province_id_legacy63", "shapeISO", "year"], as_index=False).agg(
        ftth_download_median_apr_dec_mbps=("download_mbps", "median"),
        ftth_upload_median_apr_dec_mbps=("upload_mbps", "median"),
        ftth_ping_median_apr_dec_ms=("ping_ms", "median"),
        ftth_jitter_median_apr_dec_ms=("jitter_ms", "median"),
        months_observed=("month", "size"),
        distinct_months_observed=("month", "nunique"),
    )
    annual["months_expected"] = 9
    annual["complete_primary_window"] = annual["months_observed"].eq(9) & annual["distinct_months_observed"].eq(9)
    annual["semantic_status"] = "PASS_WITH_LIMITATIONS"
    annual["source_artifact_id"] = "fact_vnnic_province_month_primary"
    annual["run_id"] = ctx["run_id"]
    annual["config_hash"] = ctx["config_hash"]
    annual = annual.sort_values(["province_id_legacy63", "year"]).reset_index(drop=True)
    require_unique(annual, ["province_id_legacy63", "year"], "annual connectivity")
    independent = monthly.groupby(["province_id_legacy63", "year"])["download_mbps"].apply(lambda x: float(np.median(x.to_numpy()))).reset_index(name="independent")
    checked = annual.merge(independent, on=["province_id_legacy63", "year"], validate="one_to_one")
    max_diff = float((checked["ftth_download_median_apr_dec_mbps"] - checked["independent"]).abs().max())
    if len(annual) != 252 or not annual["complete_primary_window"].all() or max_diff > 1e-12:
        raise RuntimeError("FAIL-CLOSED: annual connectivity contract/reconciliation failed")
    validate_schema_contract(annual, WORKING_ROOT / "config/schemas/fact_connectivity_province_year.json", "fact_connectivity_province_year")
    annual_path = WORKING_ROOT / "data/processed/fact_connectivity_province_year.parquet"
    annual.to_parquet(annual_path, index=False)

    evidence = {"monthly_rows": len(monthly), "annual_rows": len(annual), "distinct_months_all_nine": bool(annual["distinct_months_observed"].eq(9).all()), "invalid_download": 0, "median_max_absolute_difference": max_diff, "value_field_present": False, "value_field_use": "NOT_USED"}
    ctx["gatebook"].set("G4_EXPOSURE_CONSTRUCTION", "PASS", "Primary FTTH monthly and annual facts satisfy the locked April-December design.", evidence)
    return [monthly_path, annual_path]
