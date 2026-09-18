import hashlib
import json

import numpy as np
import pandas as pd

from ..core.contracts import require_unique, validate_schema_contract
from ..core.paths import WORKING_ROOT


AGGREGATE_CODES = {"0", "1", "13", "28", "43", "49", "56"}
TOLERANCE = 1e-12


def stable_frame_hash(df):
    cols = [c for c in df.columns if c not in {"run_id", "config_hash"}]
    ordered = df[cols].sort_values(cols[:2]).reset_index(drop=True)
    return hashlib.sha256(pd.util.hash_pandas_object(ordered, index=False).values.tobytes()).hexdigest()


def merge_audit(left, right, keys, left_id, right_id, output, indicator):
    left_dup = int(left.duplicated(keys, keep=False).sum())
    right_dup = int(right.duplicated(keys, keep=False).sum())
    if left_dup or right_dup:
        raise RuntimeError(f"FAIL-CLOSED: non-1:1 merge {left_id} <- {right_id}")
    right_check = right.merge(left[keys], on=keys, how="left", indicator=True)
    record = {
        "left_artifact": left_id, "right_artifact": right_id,
        "declared_cardinality": "1:1", "observed_cardinality": "1:1",
        "left_rows_before": len(left), "right_rows": len(right), "output_rows": len(output),
        "duplicate_left_key_rows": left_dup, "duplicate_right_key_rows": right_dup,
        "matched_rows": int(output[indicator].eq("both").sum()),
        "unmatched_left_rows": int(output[indicator].eq("left_only").sum()),
        "unmatched_right_rows": int(right_check["_merge"].eq("left_only").sum()),
        "row_expansion": max(0, len(output) - len(left)), "row_contraction": max(0, len(left) - len(output)),
        "match_rate_by_year": json.dumps(output.groupby("year")[indicator].apply(lambda x: float(x.eq("both").mean())).to_dict(), sort_keys=True),
        "match_rate_by_province": json.dumps(output.groupby("province_id_legacy63")[indicator].apply(lambda x: float(x.eq("both").mean())).to_dict(), sort_keys=True),
        "temporal_overlap": "2021-2024",
    }
    record["status"] = "PASS" if record["matched_rows"] == len(left) == len(output) and record["unmatched_right_rows"] == 0 else "FAIL"
    return record


def run(ctx):
    required = ["G2", "G3", "G4", "G5", "G4_EXPOSURE_CONSTRUCTION"]
    if not ctx["gatebook"].is_pass(*required):
        ctx["gatebook"].set("G6_PANEL_AND_MERGE", "FAIL", f"Panel requires PASS: {required}")
        return []

    effective_lock = json.loads((WORKING_ROOT / "protocol/protocol_effective_lock.json").read_text(encoding="utf-8"))
    effective_hash = effective_lock["effective_protocol_sha256"]
    dim = pd.read_parquet(WORKING_ROOT / "data/reference/dim_province_legacy63.parquet")
    connectivity = pd.read_parquet(WORKING_ROOT / "data/processed/fact_connectivity_province_year.parquet")
    official_path = WORKING_ROOT / "data/reference/nso_official_snapshot_20260913/nso_official_snapshot_long.parquet"
    official = pd.read_parquet(official_path)
    ids = pd.read_csv(WORKING_ROOT / "artifacts/qc/province_identifier_audit.csv", dtype={"px_geo_code": str, "vnnic_code": str})
    ids["px_geo_code"] = ids["px_geo_code"].astype(str)
    if len(ids) != 63 or set(ids["match_status"]) != {"MATCHED"} or set(ids["px_geo_code"]) & AGGREGATE_CODES:
        raise RuntimeError("FAIL-CLOSED: official PX identifier mapping is invalid")

    nso = official[(official["table_code"] == "V05.05") & official["year"].between(2021, 2024)].copy()
    nso["px_geo_code"] = nso["px_geo_code"].astype(str)
    if len(nso[nso["px_geo_code"].isin(AGGREGATE_CODES)]) != 28:
        raise RuntimeError("FAIL-CLOSED: explicit aggregate exclusion count changed")
    nso = nso[~nso["px_geo_code"].isin(AGGREGATE_CODES)]
    nso = nso.merge(ids[["px_geo_code", "province_id_legacy63"]], on="px_geo_code", how="left", validate="many_to_one")
    nso = nso.merge(dim[["province_id_legacy63", "shapeISO"]], on="province_id_legacy63", how="left", validate="many_to_one")
    retrieval = json.loads((WORKING_ROOT / "artifacts/qc/nso_semantic_decision.json").read_text(encoding="utf-8"))["retrieval_timestamp_utc"][:10]
    outcome = pd.DataFrame({
        "province_id_legacy63": nso["province_id_legacy63"], "pxweb_geo_code": nso["px_geo_code"], "shapeISO": nso["shapeISO"],
        "year": nso["year"].astype(int), "active_firms_per_1000": pd.to_numeric(nso["official_value"], errors="coerce"),
        "unit": "enterprises per 1,000 inhabitants", "table_code": "V05.05",
        "source_snapshot_id": "nso_pxweb_V05.05_retrieved_20260913", "source_retrieval_date": retrieval,
        "semantic_status": "PASS_WITH_LIMITATIONS",
        "denominator_universe_limitation": "Detailed population and enterprise universe metadata are not present in the PXWeb API response.",
        "official_statistics_designation": "Không (PXWeb label: Thống kê chính thức)",
        "run_id": ctx["run_id"], "config_hash": ctx["config_hash"],
    }).sort_values(["province_id_legacy63", "year"]).reset_index(drop=True)
    require_unique(outcome, ["province_id_legacy63", "year"], "NSO primary outcome")
    if len(outcome) != 252 or outcome.groupby("year")["province_id_legacy63"].nunique().ne(63).any():
        raise RuntimeError("FAIL-CLOSED: NSO outcome is not 63 x 4")
    if (~np.isfinite(outcome["active_firms_per_1000"]) | outcome["active_firms_per_1000"].le(0)).any():
        raise RuntimeError("FAIL-CLOSED: invalid NSO primary values")
    validate_schema_contract(outcome, WORKING_ROOT / "config/schemas/fact_nso_primary_outcome.json", "fact_nso_primary_outcome")
    outcome_path = WORKING_ROOT / "data/processed/fact_nso_primary_outcome.parquet"

    skeleton = pd.MultiIndex.from_product([sorted(dim["province_id_legacy63"]), [2021, 2022, 2023, 2024]], names=["province_id_legacy63", "year"]).to_frame(index=False)
    skeleton = skeleton.merge(dim[["province_id_legacy63", "shapeISO", "province_name_canonical"]], on="province_id_legacy63", validate="many_to_one")
    require_unique(skeleton, ["province_id_legacy63", "year"], "panel skeleton")
    with_conn = skeleton.merge(connectivity.drop(columns=["shapeISO", "run_id", "config_hash"]), on=["province_id_legacy63", "year"], how="left", validate="one_to_one", indicator="merge_status_connectivity")
    audit_conn = merge_audit(skeleton, connectivity, ["province_id_legacy63", "year"], "skeleton_legacy63_2021_2024", "fact_connectivity_province_year", with_conn, "merge_status_connectivity")
    merged = with_conn.merge(outcome.drop(columns=["shapeISO", "run_id", "config_hash"]), on=["province_id_legacy63", "year"], how="left", validate="one_to_one", indicator="merge_status_nso")
    audit_nso = merge_audit(with_conn, outcome, ["province_id_legacy63", "year"], "skeleton_plus_connectivity", "fact_nso_primary_outcome", merged, "merge_status_nso")
    if audit_conn["status"] != "PASS" or audit_nso["status"] != "PASS":
        raise RuntimeError("FAIL-CLOSED: panel merge audit failed")

    panel = pd.DataFrame({
        "province_id_legacy63": merged["province_id_legacy63"], "shapeISO": merged["shapeISO"], "province_name_canonical": merged["province_name_canonical"], "year": merged["year"],
        "ftth_download_median_apr_dec_mbps": merged["ftth_download_median_apr_dec_mbps"], "ftth_upload_median_apr_dec_mbps": merged["ftth_upload_median_apr_dec_mbps"],
        "ftth_ping_median_apr_dec_ms": merged["ftth_ping_median_apr_dec_ms"], "ftth_jitter_median_apr_dec_ms": merged["ftth_jitter_median_apr_dec_ms"],
        "active_firms_per_1000": merged["active_firms_per_1000"], "exposure_complete": merged["complete_primary_window"].fillna(False), "outcome_complete": merged["active_firms_per_1000"].notna(),
        "merge_status_connectivity": merged["merge_status_connectivity"].astype(str), "merge_status_nso": merged["merge_status_nso"].astype(str),
        "vnnic_semantic_status": "PASS_WITH_LIMITATIONS", "nso_semantic_status": "PASS_WITH_LIMITATIONS",
        "source_lineage_ids": "fact_vnnic_province_month_primary | nso_pxweb_V05.05_retrieved_20260913",
        "run_id": ctx["run_id"], "config_hash": ctx["config_hash"], "effective_protocol_hash": effective_hash,
    }).sort_values(["province_id_legacy63", "year"]).reset_index(drop=True)
    validate_schema_contract(panel, WORKING_ROOT / "config/schemas/analysis_panel_2021_2024.json", "analysis_panel_2021_2024")
    if not panel["exposure_complete"].all() or not panel["outcome_complete"].all() or any("entry" in c.lower() for c in panel.columns):
        raise RuntimeError("FAIL-CLOSED: completeness or entry-field contract failed")

    panel_path = WORKING_ROOT / "data/analysis/analysis_panel_2021_2024.parquet"
    prior = {label: stable_frame_hash(pd.read_parquet(path)) for label, path in [("outcome", outcome_path), ("panel", panel_path)] if path.exists()}
    outcome.to_parquet(outcome_path, index=False)
    panel.to_parquet(panel_path, index=False)
    audit_mirror_path = WORKING_ROOT / "data/analysis/analysis_panel_2021_2024_audit.csv"
    panel[["province_id_legacy63", "shapeISO", "province_name_canonical", "year", "ftth_download_median_apr_dec_mbps", "active_firms_per_1000", "exposure_complete", "outcome_complete", "merge_status_connectivity", "merge_status_nso"]].to_csv(audit_mirror_path, index=False, encoding="utf-8-sig")

    merge_rows = [audit_conn, audit_nso]
    merge_csv = WORKING_ROOT / "artifacts/qc/panel_merge_audit.csv"; pd.DataFrame(merge_rows).to_csv(merge_csv, index=False, encoding="utf-8-sig")
    merge_json = WORKING_ROOT / "artifacts/qc/panel_merge_audit.json"; merge_json.write_text(json.dumps(merge_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    missing_path = WORKING_ROOT / "artifacts/qc/panel_missingness.csv"; pd.DataFrame({"variable": panel.columns, "missing_count": panel.isna().sum().values, "missing_rate": panel.isna().mean().values}).to_csv(missing_path, index=False, encoding="utf-8-sig")
    key_audit = {"skeleton_rows": len(skeleton), "panel_rows": len(panel), "panel_duplicate_key_rows": int(panel.duplicated(["province_id_legacy63", "year"], keep=False).sum()), "province_count_by_year": {str(k): int(v) for k, v in panel.groupby("year")["province_id_legacy63"].nunique().items()}, "connectivity_matched": audit_conn["matched_rows"], "nso_matched": audit_nso["matched_rows"], "entry_rate_field_present": False}
    key_path = WORKING_ROOT / "artifacts/qc/panel_key_audit.json"; key_path.write_text(json.dumps(key_audit, indent=2), encoding="utf-8")
    stats = {}
    for col in ["ftth_download_median_apr_dec_mbps", "ftth_upload_median_apr_dec_mbps", "ftth_ping_median_apr_dec_ms", "ftth_jitter_median_apr_dec_ms", "active_firms_per_1000"]:
        x = panel[col]; within = panel.groupby("province_id_legacy63")[col].std(ddof=1)
        stats[col] = {"min": float(x.min()), "q25": float(x.quantile(.25)), "median": float(x.median()), "q75": float(x.quantile(.75)), "max": float(x.max()), "within_province_sd_mean": float(within.mean()), "between_province_sd": float(panel.groupby("province_id_legacy63")[col].mean().std(ddof=1)), "zero_within_variation_provinces": int(panel.groupby("province_id_legacy63")[col].nunique().eq(1).sum())}
    value_path = WORKING_ROOT / "artifacts/qc/panel_value_audit.json"; value_path.write_text(json.dumps({"variables": stats, "lagged_model_potential_observations": 189, "correlations_calculated": False, "models_run": False}, indent=2), encoding="utf-8")
    lineage_path = WORKING_ROOT / "artifacts/lineage/panel_lineage_edges.csv"
    pd.DataFrame([
        {"parent": "vnnic_province_month_legacy63_csv", "child": "fact_vnnic_province_month_primary", "relation": "locked_filter_no_value_weight"},
        {"parent": "fact_vnnic_province_month_primary", "child": "fact_connectivity_province_year", "relation": "unweighted_median_april_december"},
        {"parent": "nso_official_snapshot_long", "child": "fact_nso_primary_outcome", "relation": "V05.05_2021_2024_explicit_code_filter"},
        {"parent": "dim_province_legacy63", "child": "analysis_panel_2021_2024", "relation": "explicit_63_by_4_skeleton"},
        {"parent": "fact_connectivity_province_year", "child": "analysis_panel_2021_2024", "relation": "one_to_one_left_merge"},
        {"parent": "fact_nso_primary_outcome", "child": "analysis_panel_2021_2024", "relation": "one_to_one_left_merge"},
    ]).to_csv(lineage_path, index=False, encoding="utf-8-sig")

    ctx["gatebook"].set("G1_PRIMARY_PROVENANCE", "PASS", "Primary provenance passes with documented limitations.", {"classification": "PASS_WITH_LIMITATIONS", "local_nso_candidates": "QUARANTINED_NOT_USED"})
    ctx["gatebook"].set("G2_PRIMARY_SEMANTICS", "PASS", "Primary semantics pass with documented limitations.", {"classification": "PASS_WITH_LIMITATIONS", "value": "NOT_USED", "entry_intensity": "EXPLORATORY_UNAVAILABLE"})
    ctx["gatebook"].set("G5_PRIMARY_OUTCOME", "PASS", "Official PXWeb snapshot is the sole primary-outcome source.", {"rows": 252, "source": str(official_path), "quarantine_used": False})
    ctx["gatebook"].set("G6_PANEL_AND_MERGE", "PASS", "Explicit 252-row skeleton retained through two 1:1 complete merges.", key_audit)
    ctx["gatebook"].set("G7_PANEL_READINESS", "PASS", "Panel is ready for descriptive analysis with limitations.", {"classification": "PASS_WITH_LIMITATIONS", "lagged_model_potential_observations": 189})
    ctx["gatebook"].set("G8_CLAIM", "PASS", "No descriptive-result, model or causal claim was produced.", {"descriptive_run": False, "model_run": False, "causal_gate": "CLOSED"})
    reproducible = bool(prior) and prior.get("outcome") == stable_frame_hash(outcome) and prior.get("panel") == stable_frame_hash(panel)
    ctx["gatebook"].set("G9_REPRODUCIBILITY", "PASS" if reproducible else "WARN", "Core values/schema reproduce across runs." if reproducible else "First construction run; rerun required.", {"comparison_tolerance": TOLERANCE, "stable_value_hashes_match": reproducible})
    report_path = WORKING_ROOT / "reports/panel_construction_report.md"
    report_path.write_text(
        "\n".join([
            "RESEARCH_GATE", "",
            "READY_FOR_DESCRIPTIVE_ANALYSIS" if reproducible else "PANEL_REPRODUCIBILITY_CHECK_PENDING",
            "", "# Panel construction", "",
            "- Monthly FTTH fact: 2,268 rows (63 provinces × 4 years × 9 months).",
            "- Annual connectivity fact: 252 unique province-year rows.",
            "- Official PXWeb V05.05 outcome fact: 252 unique province-year rows.",
            "- Analysis skeleton and final panel: 252 rows; both joins 1:1 and 252/252 matched.",
            "- Primary exposure and outcome complete: 252/252.",
            "- Entry-intensity proxy: EXPLORATORY_UNAVAILABLE and absent from the panel.",
            "- VNNIC value: NOT_USED.",
            "- Descriptive analysis: not run. Models: not run. Ookla: not processed.",
            "- Causal gate: CLOSED. Decision 2269 gate: FAIL_PRIMARY_ROUTE.",
            f"- Run: {ctx['run_id']}",
            f"- Effective protocol hash: {effective_hash}",
            f"- Reproducibility check: {'PASS' if reproducible else 'PENDING SECOND RUN'}",
        ]) + "\n", encoding="utf-8"
    )
    next_path = WORKING_ROOT / "reports/panel_construction_next_action.md"
    next_path.write_text(
        "# Next safe action\n\nRun the separately authorized descriptive-analysis sprint only after "
        "the panel validator reports PASS_PANEL_READY_FOR_DESCRIPTIVE. Do not estimate models, "
        "process Ookla, or reopen the Decision 2269 route in that step.\n",
        encoding="utf-8",
    )
    return [
        outcome_path, panel_path, audit_mirror_path, merge_json, merge_csv,
        missing_path, key_path, value_path, lineage_path, report_path, next_path,
        WORKING_ROOT / "protocol/decision_log.md",
        WORKING_ROOT / "protocol/limitations_register.md",
        WORKING_ROOT / "reports/reproducibility_report.md",
    ]
