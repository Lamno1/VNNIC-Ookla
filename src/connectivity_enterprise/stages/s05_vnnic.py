from pathlib import Path
import json

import numpy as np
import pandas as pd

from ..core.contracts import validate_schema_contract
from ..core.paths import WORKING_ROOT, assert_safe_input_path, sources_config


def run(ctx):
    cfg = sources_config()["sources"]
    source = assert_safe_input_path(Path(cfg["vnnic_legacy_panel"]))
    dim_path = WORKING_ROOT / "data/reference/dim_province_legacy63.parquet"
    if not dim_path.exists():
        raise RuntimeError("FAIL-CLOSED: geography dimension is missing")

    raw = pd.read_csv(source, dtype={"code": str, "vnnic_code": str})
    raw["code"] = raw["code"].str.zfill(2)
    raw["vnnic_code"] = raw["vnnic_code"].str.zfill(2)
    raw["network"] = raw["network"].str.lower()
    raw_date = pd.to_datetime(raw["date"], errors="coerce")
    if raw_date.isna().any():
        raise RuntimeError("FAIL-CLOSED: invalid VNNIC dates")
    if not ((raw_date.dt.year == raw["year"]) & (raw_date.dt.month == raw["month"])).all():
        raise RuntimeError("FAIL-CLOSED: date disagrees with year/month")
    if len(raw) != 7360:
        raise RuntimeError(f"FAIL-CLOSED: expected 7,360 legacy rows, found {len(raw)}")
    if set(raw["network"].unique()) != {"ftth", "mobile"}:
        raise RuntimeError(f"FAIL-CLOSED: unexpected network universe: {sorted(raw['network'].unique())}")
    duplicate_rows = int(raw.duplicated(["network", "year", "month", "code"], keep=False).sum())
    if duplicate_rows:
        raise RuntimeError(f"FAIL-CLOSED: {duplicate_rows} duplicate source key rows")

    dim = pd.read_parquet(dim_path)
    link = dim[["vnnic_code", "province_id_legacy63", "province_name_canonical", "shapeISO", "shapeID"]]
    checked = raw.merge(link, left_on="code", right_on="vnnic_code", how="left", validate="many_to_one", suffixes=("_raw", "_dim"))
    if checked["province_id_legacy63"].isna().any():
        raise RuntimeError("FAIL-CLOSED: VNNIC code outside canonical dimension")
    for col in ["shapeID", "shapeISO", "province_name_canonical"]:
        if not checked[f"{col}_raw"].fillna("").eq(checked[f"{col}_dim"].fillna("")).all():
            raise RuntimeError(f"FAIL-CLOSED: rowwise {col} disagrees with canonical dimension")

    fact = pd.DataFrame({
        "network": checked["network"],
        "province_id_legacy63": checked["province_id_legacy63"],
        "month": raw_date.dt.strftime("%Y-%m-01"),
        "year": checked["year"].astype(int),
        "download": pd.to_numeric(checked["download"], errors="coerce"),
        "upload": pd.to_numeric(checked["upload"], errors="coerce"),
        "ping": pd.to_numeric(checked["ping"], errors="coerce"),
        "jitter": pd.to_numeric(checked["jitter"], errors="coerce"),
        "value_raw": pd.to_numeric(checked["value"], errors="coerce"),
        "source_file": checked["source_file"],
        "semantic_status": "PASS_WITH_LIMITATIONS",
        "coverage_flag": "OBSERVED",
    })
    validate_schema_contract(fact, WORKING_ROOT / "config/schemas/fact_vnnic_province_month.json", "fact_vnnic_province_month")
    fact = fact.sort_values(["network", "province_id_legacy63", "month"]).reset_index(drop=True)
    out = WORKING_ROOT / "data/interim/fact_vnnic_province_month.parquet"
    fact.to_parquet(out, index=False)

    months = pd.date_range("2019-12-01", "2025-06-01", freq="MS").strftime("%Y-%m-01")
    expected = pd.MultiIndex.from_product(
        [["ftth", "mobile"], sorted(dim["province_id_legacy63"]), months],
        names=["network", "province_id_legacy63", "month"],
    ).to_frame(index=False)
    actual_keys = fact[["network", "province_id_legacy63", "month"]]
    unexpected = actual_keys.merge(expected, how="left", indicator=True)
    unexpected = unexpected[unexpected["_merge"] == "left_only"]
    missing = expected.merge(actual_keys, how="left", indicator=True)
    missing = missing[missing["_merge"] == "left_only"].drop(columns="_merge")
    if len(unexpected):
        raise RuntimeError(f"FAIL-CLOSED: {len(unexpected)} VNNIC keys outside expected legacy grid")
    if len(missing) != 1082:
        raise RuntimeError(f"FAIL-CLOSED: expected 1,082 absent legacy cells, found {len(missing)}")
    missing_path = WORKING_ROOT / "artifacts/qc/vnnic_expected_grid_missing.csv"
    missing.to_csv(missing_path, index=False, encoding="utf-8-sig")

    primary = fact[(fact["network"] == "ftth") & fact["year"].between(2021, 2024) & pd.to_datetime(fact["month"]).dt.month.between(4, 12)].copy()
    finite_download = np.isfinite(primary["download"])
    positive_download = primary["download"] > 0
    nonnull_counts = primary.assign(valid_download=finite_download & positive_download).groupby(["province_id_legacy63", "year"])["valid_download"].sum()
    row_counts = primary.groupby(["province_id_legacy63", "year"]).size()
    complete_cells = int(((row_counts == 9) & (nonnull_counts == 9)).sum())

    qc = {
        "source_rows": len(raw), "duplicate_source_key_rows": duplicate_rows,
        "province_count": fact["province_id_legacy63"].nunique(),
        "legacy_expected_cells": len(expected), "legacy_observed_cells": len(fact),
        "legacy_missing_expected_cells": len(missing), "unexpected_legacy_cells": len(unexpected),
        "primary_ftth_rows": len(primary), "primary_province_year_cells": len(row_counts),
        "complete_nine_month_valid_download_cells": complete_cells,
        "primary_download_null_or_nonfinite": int((~finite_download).sum()),
        "primary_download_nonpositive": int((~positive_download).sum()),
        "primary_expected_rows": 2268, "semantic_status": "PASS_WITH_LIMITATIONS",
    }
    qc_path = WORKING_ROOT / "artifacts/qc/vnnic_structural_audit.json"
    qc_path.write_text(json.dumps(qc, indent=2), encoding="utf-8")
    passed = len(primary) == 2268 and len(row_counts) == 252 and complete_cells == 252
    ctx["gatebook"].set(
        "G4", "PASS" if passed else "FAIL",
        "Primary FTTH April-December structural and non-null coverage passes; metric semantics remain governed by G2."
        if passed else "Primary FTTH April-December coverage/value contract failed.", qc,
    )
    return [out, missing_path, qc_path]
