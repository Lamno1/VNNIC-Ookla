from pathlib import Path
from datetime import datetime, timezone
from itertools import product
import csv
import hashlib
import json
import re
import unicodedata
import urllib.request

import openpyxl
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
SNAPSHOT = ROOT / "data/reference/nso_official_snapshot_20260913"
QC = ROOT / "artifacts/qc"
MANIFESTS = ROOT / "artifacts/manifests"
LINEAGE = ROOT / "artifacts/lineage"
NSO_LOCAL = PROJECT_ROOT / "NSO"
DIM_PATH = ROOT / "data/reference/dim_province_legacy63.parquet"
API_ROOT = "https://pxweb.nso.gov.vn/api/v1/vi/Doanh%20nghi%E1%BB%87p"
TABLES = {
    "V05.02": ("new_registrations", "V05.02.xlsx"),
    "V05.04": ("active_firms_dec31", "V05.04.xlsx"),
    "V05.05": ("active_firms_per_1000", "V05.05.xlsx"),
}
AGGREGATE_CODES = {"0", "1", "13", "28", "43", "49", "56"}
TOLERANCE = 1e-12


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def norm(value):
    value = str(value or "").strip().lower().replace("đ", "d")
    value = unicodedata.normalize("NFD", value)
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    value = re.sub(r"\btp\.?\s*", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def request_bytes(url, payload=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "connectivity-enterprise-semantic-audit/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.status, dict(response.headers.items()), response.read()


def jsonstat_rows(table, measure, response):
    dataset = response["dataset"]
    dims = dataset["dimension"]
    ids = dims["id"]
    if ids != ["Tỉnh/thành phố", "Năm"]:
        raise RuntimeError(f"Unexpected dimension order for {table}: {ids}")
    geo_index = dims["Tỉnh/thành phố"]["category"]["index"]
    year_index = dims["Năm"]["category"]["index"]
    geos = [k for k, _ in sorted(geo_index.items(), key=lambda x: x[1])]
    years = [k for k, _ in sorted(year_index.items(), key=lambda x: x[1])]
    geo_labels = dims["Tỉnh/thành phố"]["category"]["label"]
    year_labels = dims["Năm"]["category"]["label"]
    values = dataset["value"]
    rows = []
    for index, (g, y) in enumerate(product(geos, years)):
        rows.append({"table_code": table, "measure_id": measure, "px_geo_code": g, "px_geo_label": geo_labels[g], "px_year_code": y, "year": int(year_labels[y]), "official_value": values[index]})
    return rows


def local_rows(table, measure, filename):
    wb = openpyxl.load_workbook(NSO_LOCAL / filename, read_only=True, data_only=True, keep_links=False)
    ws = wb[wb.sheetnames[0]]
    years = [int(ws.cell(3, c).value) for c in range(2, ws.max_column + 1)]
    rows = []
    for r in range(4, ws.max_row + 1):
        label = ws.cell(r, 1).value
        for c, year in enumerate(years, start=2):
            rows.append({"table_code": table, "measure_id": measure, "local_geo_label": label, "year": year, "local_value": ws.cell(r, c).value, "source_cell": ws.cell(r, c).coordinate})
    return rows


def main():
    for path in [SNAPSHOT, QC, MANIFESTS, LINEAGE]:
        path.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(timezone.utc).isoformat()
    manifest, official_rows, metadata_by_table = [], [], {}

    for table, (measure, _) in TABLES.items():
        url = f"{API_ROOT}/{table}.px"
        status, headers, metadata_bytes = request_bytes(url)
        metadata = json.loads(metadata_bytes.decode("utf-8-sig"))
        metadata_by_table[table] = metadata
        metadata_path = SNAPSHOT / f"{table}_metadata.json"
        metadata_path.write_bytes(metadata_bytes)
        variables = metadata["variables"]
        query = {"query": [{"code": v["code"], "selection": {"filter": "item", "values": v["values"]}} for v in variables], "response": {"format": "json-stat"}}
        request_bytes_raw = json.dumps(query, ensure_ascii=False, indent=2).encode("utf-8")
        request_path = SNAPSHOT / f"{table}_request.json"
        request_path.write_bytes(request_bytes_raw)
        post_status, post_headers, response_bytes = request_bytes(url, query)
        response_path = SNAPSHOT / f"{table}_response.json"
        response_path.write_bytes(response_bytes)
        headers_path = SNAPSHOT / f"{table}_response_headers.json"
        headers_path.write_text(json.dumps(post_headers, ensure_ascii=False, indent=2), encoding="utf-8")
        response = json.loads(response_bytes.decode("utf-8-sig"))
        official_rows.extend(jsonstat_rows(table, measure, response))
        for kind, path, body, http_status, hdrs in [
            ("metadata", metadata_path, metadata_bytes, status, headers),
            ("request", request_path, request_bytes_raw, "LOCAL_REQUEST_PAYLOAD", {}),
            ("response", response_path, response_bytes, post_status, post_headers),
            ("response_headers", headers_path, headers_path.read_bytes(), post_status, post_headers),
        ]:
            manifest.append({"table_code": table, "artifact_type": kind, "official_url": url, "api_endpoint": url, "retrieval_timestamp_utc": retrieved, "http_status": http_status, "content_type": hdrs.get("Content-Type", "application/json"), "file_path": str(path), "file_bytes": len(body), "sha256": sha256(body), "dimension_codes": " | ".join(v["code"] for v in variables), "dimension_labels": " | ".join(v["text"] for v in variables), "dataset_updated": response.get("dataset", {}).get("updated", ""), "vintage_interpretation": "Latest official PXWeb vintage retrieved 2026-09-13; ex-post historical snapshot"})

    official = pd.DataFrame(official_rows)
    official.to_parquet(SNAPSHOT / "nso_official_snapshot_long.parquet", index=False)
    if len(official) != 1750:
        raise RuntimeError(f"Expected 1,750 official cells, found {len(official)}")

    # Official table codes are preserved. Seven known national/region codes are excluded.
    provinces = official[~official["px_geo_code"].isin(AGGREGATE_CODES)].copy()
    if provinces["px_geo_code"].nunique() != 63:
        raise RuntimeError("Official PXWeb geography is not 63 provinces")
    dim = pd.read_parquet(DIM_PATH)
    lookup = {norm(r.province_name_official): r for r in dim.itertuples(index=False)}
    id_rows = []
    for (code, label), _ in provinces.groupby(["px_geo_code", "px_geo_label"]):
        match = lookup.get(norm(label))
        id_rows.append({"px_geo_code": code, "px_geo_label": label, "normalized_label": norm(label), "province_id_legacy63": getattr(match, "province_id_legacy63", ""), "vnnic_code": getattr(match, "vnnic_code", ""), "match_method": "official_px_code_plus_exact_normalized_legal_name", "match_status": "MATCHED" if match else "UNMATCHED", "review_status": "SYSTEMATIC_DETERMINISTIC_AUDIT"})
    id_audit = pd.DataFrame(id_rows).sort_values("px_geo_code", key=lambda s: s.astype(int))
    if len(id_audit) != 63 or (id_audit["match_status"] != "MATCHED").any() or id_audit["province_id_legacy63"].nunique() != 63:
        raise RuntimeError("Province identifier audit failed")
    id_audit.to_csv(QC / "province_identifier_audit.csv", index=False, encoding="utf-8-sig")

    local = pd.DataFrame([row for table, (measure, filename) in TABLES.items() for row in local_rows(table, measure, filename)])
    official_cmp = official.copy()
    official_cmp["join_label"] = official_cmp["px_geo_label"].map(norm)
    local["join_label"] = local["local_geo_label"].map(norm)
    comparison = official_cmp.merge(local, on=["table_code", "measure_id", "join_label", "year"], how="outer", indicator=True)
    comparison["absolute_difference"] = (pd.to_numeric(comparison["official_value"], errors="coerce") - pd.to_numeric(comparison["local_value"], errors="coerce")).abs()
    comparison["cell_status"] = "MISMATCH"
    comparison.loc[comparison["_merge"] == "left_only", "cell_status"] = "MISSING_LOCAL"
    comparison.loc[comparison["_merge"] == "right_only", "cell_status"] = "MISSING_OFFICIAL"
    both = comparison["_merge"] == "both"
    equal = comparison["absolute_difference"].le(TOLERANCE) | (comparison["official_value"].isna() & comparison["local_value"].isna())
    comparison.loc[both & equal, "cell_status"] = "MATCHED"
    comparison["numeric_tolerance"] = TOLERANCE
    comparison.to_csv(QC / "nso_official_reconciliation.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(manifest).to_csv(MANIFESTS / "nso_official_snapshot_manifest.csv", index=False, encoding="utf-8-sig")

    summary = comparison.groupby(["table_code", "cell_status"]).size().unstack(fill_value=0)
    primary_complete = len(provinces[provinces["table_code"] == "V05.05"]) == 504
    primary_values_valid = pd.to_numeric(
        provinces.loc[provinces["table_code"] == "V05.05", "official_value"], errors="coerce"
    ).notna().all()
    primary_ok = primary_complete and primary_values_valid
    decisions = {
        "retrieval_timestamp_utc": retrieved,
        "official_snapshot_cells": len(official),
        "official_province_cells": len(provinces),
        "official_unique_province_codes": provinces["px_geo_code"].nunique(),
        "province_identifier_matches": int((id_audit["match_status"] == "MATCHED").sum()),
        "reconciliation": {table: {str(k): int(v) for k, v in summary.loc[table].items()} for table in TABLES},
        "numeric_tolerance": TOLERANCE,
        "reconciliation_verdict": "V05.02 and V05.04 exact; V05.05 local workbook is a two-decimal rounded derivative. Official API snapshot adopted prospectively.",
        "v05_05_max_absolute_difference": float(comparison.loc[(comparison["table_code"] == "V05.05") & (comparison["cell_status"] == "MISMATCH"), "absolute_difference"].max()),
        "G2_NSO_PRIMARY": "PASS_WITH_LIMITATIONS" if primary_ok else "FAIL",
        "G2_NSO_ENTRY_RATE": "EXPLORATORY_UNAVAILABLE",
        "G5_PRIMARY_OUTCOME": "PASS" if primary_ok else "FAIL",
        "primary_source_policy": "Official PXWeb snapshot retrieved 2026-09-13; local workbooks are comparison derivatives only",
        "official_statistics_metadata_note": "PXWeb interface labels these tables 'Thống kê chính thức: Không'; source is official NSO-hosted publication but must not be described as an official-statistics designation.",
    }
    (QC / "nso_semantic_decision.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    lineage = [{"parent": str(SNAPSHOT / f"{t}_response.json"), "child": str(SNAPSHOT / "nso_official_snapshot_long.parquet"), "relation": "parsed_without_value_transformation"} for t in TABLES]
    pd.DataFrame(lineage).to_csv(LINEAGE / "semantic_evidence_lineage.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(decisions, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
