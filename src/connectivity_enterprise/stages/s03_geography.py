from pathlib import Path
import hashlib
import json
import re
import unicodedata

import pandas as pd

from ..core.contracts import validate_schema_contract
from ..core.paths import WORKING_ROOT, sources_config
from ..core.provenance import sha256_file


CANONICAL_SHA256 = "c64a07c3fd5d3ca0339a5002983dc76ddd60a0ef88e889522e37ca2408f74400"


def norm(value):
    value = str(value or "").strip().lower().replace("đ", "d")
    value = unicodedata.normalize("NFD", value)
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    value = re.sub(r"\btp\.?\s*", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def run(ctx):
    cfg = sources_config()["sources"]
    geo_path = Path(cfg["canonical_geojson"])
    crosswalk_path = Path(cfg["province_crosswalk"])
    manifest_path = Path(cfg["canonical_manifest"])
    validation_path = Path(cfg["canonical_geometry_validation"])

    actual_hash = sha256_file(geo_path)
    if actual_hash != CANONICAL_SHA256:
        raise RuntimeError(f"FAIL-CLOSED: canonical geography hash mismatch: {actual_hash}")

    manifest = pd.read_csv(manifest_path)
    if len(manifest) != 1:
        raise RuntimeError("FAIL-CLOSED: canonical manifest must have exactly one row")
    registry = manifest.iloc[0]
    if registry["canonical_sha256"] != actual_hash or registry["hash_identity"] != "PASS":
        raise RuntimeError("FAIL-CLOSED: canonical manifest identity does not validate")
    if any(registry[x] != "NONE" for x in ["geometry_transformation", "reprojection", "simplification"]):
        raise RuntimeError("FAIL-CLOSED: canonical manifest records a geometry transformation")

    validation_df = pd.read_csv(validation_path)
    validation = dict(zip(validation_df["metric"], validation_df["value"]))
    expected_validation = {
        "features": 63, "unique_shapeID": 63, "unique_shapeISO": 63,
        "unique_shapeName": 63, "missing_geometry": 0, "empty_geometry": 0,
        "valid_geometry": 63, "invalid_geometry": 0,
    }
    if any(int(validation.get(k, -1)) != v for k, v in expected_validation.items()):
        raise RuntimeError("FAIL-CLOSED: canonical geometry validation artifact does not pass")

    with open(geo_path, encoding="utf-8-sig") as f:
        geo = json.load(f)
    features = geo.get("features", [])
    if len(features) != 63:
        raise RuntimeError(f"FAIL-CLOSED: canonical feature count is {len(features)}")

    geo_props = pd.DataFrame([f.get("properties", {}) for f in features])
    for key in ["shapeID", "shapeISO", "shapeName"]:
        if geo_props[key].isna().any() or geo_props[key].nunique() != 63:
            raise RuntimeError(f"FAIL-CLOSED: canonical {key} is not complete/unique")

    geometry_hashes = []
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry or not geometry.get("coordinates"):
            raise RuntimeError("FAIL-CLOSED: missing or empty canonical geometry")
        raw = json.dumps(geometry, sort_keys=True, separators=(",", ":")).encode("utf-8")
        geometry_hashes.append(hashlib.sha256(raw).hexdigest())
    if len(set(geometry_hashes)) != 63:
        raise RuntimeError("FAIL-CLOSED: canonical geometry objects are not unique")

    xw = pd.read_csv(crosswalk_path, dtype={"vnnic_code": str})
    xw["vnnic_code"] = xw["vnnic_code"].str.zfill(2)
    if len(xw) != 63 or set(xw["match_status"]) != {"MATCHED"}:
        raise RuntimeError("FAIL-CLOSED: VNNIC crosswalk is not 63/63 matched")
    if xw["shapeID"].nunique() != 63 or xw["shapeISO"].nunique() != 63:
        raise RuntimeError("FAIL-CLOSED: crosswalk identifiers are not one-to-one")

    check = xw.merge(
        geo_props[["shapeID", "shapeISO", "shapeName"]], on="shapeID",
        how="left", validate="one_to_one", suffixes=("_xw", "_geo"),
    )
    if len(check) != 63 or check["shapeName"].isna().any():
        raise RuntimeError("FAIL-CLOSED: crosswalk/geometry shapeID sets differ")
    if not (check["shapeISO_xw"] == check["shapeISO_geo"]).all():
        raise RuntimeError("FAIL-CLOSED: row-wise crosswalk shapeISO differs from geometry")
    if not all(norm(a) == norm(b) for a, b in zip(check["province_name_canonical"], check["shapeName"])):
        raise RuntimeError("FAIL-CLOSED: row-wise crosswalk names differ from geometry")

    dim = pd.DataFrame({
        "province_id_legacy63": "VN_LEGACY63_" + xw["vnnic_code"],
        "vnnic_code": xw["vnnic_code"],
        "province_name_official": xw["province_name_official"],
        "province_name_canonical": xw["province_name_canonical"],
        "shapeISO": xw["shapeISO"], "shapeID": xw["shapeID"],
        "boundary_vintage": "metadata_boundaryYear_2016",
        "source_artifact": str(geo_path),
    }).sort_values("province_id_legacy63").reset_index(drop=True)
    validate_schema_contract(
        dim, WORKING_ROOT / "config/schemas/dim_province_legacy63.json",
        "dim_province_legacy63",
    )

    out = WORKING_ROOT / "data/reference/dim_province_legacy63.parquet"
    dim.to_parquet(out, index=False)
    audit = WORKING_ROOT / "artifacts/qc/geography_gate.json"
    audit.write_text(json.dumps({
        "status": "PASS", "rows": len(dim),
        "unique_province_id": dim["province_id_legacy63"].nunique(),
        "unique_vnnic_code": dim["vnnic_code"].nunique(),
        "unique_shapeISO": dim["shapeISO"].nunique(),
        "unique_shapeID": dim["shapeID"].nunique(),
        "unmatched": 0, "ambiguous": 0, "canonical_sha256": actual_hash,
        "post_2025_geography_rows": 0,
        "geometry_validation_reused": str(validation_path),
        "unique_geometry_hashes": len(set(geometry_hashes)),
        "rowwise_crosswalk_identity": "PASS",
    }, indent=2), encoding="utf-8")
    ctx["gatebook"].set(
        "G3", "PASS",
        "Legacy-63 geography is deterministic, one-to-one, geometry-validated, and hash-locked.",
        {"dimension": str(out), "audit": str(audit)},
    )
    return [out, audit]
