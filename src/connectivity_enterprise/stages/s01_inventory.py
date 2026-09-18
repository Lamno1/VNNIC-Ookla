from pathlib import Path
import csv

from ..core.paths import (
    WORKING_ROOT,
    sources_config,
    is_credential_like,
    assert_safe_input_path,
)
from ..core.provenance import sha256_file, utc_now


SOURCE_META = {
    "nso": ("National Statistics Office of Vietnam", "province-year workbooks", "QUARANTINED_NOT_USED"),
    "pci": ("Provincial Competitiveness Index", "annual province workbooks", "AUXILIARY_PENDING_AUDIT"),
    "gis_derived": ("geoBoundaries", "fixed legacy-63 reference", "VERIFIED"),
    "vnnic_raw": ("VNNIC i-Speed", "province-month", "PASS_WITH_LIMITATIONS"),
    "vnnic_derived": ("VNNIC i-Speed", "derived province-month", "PASS_WITH_LIMITATIONS"),
    "ookla_raw": ("Ookla Open Data", "tile-quarter-network", "VERIFIED_INTEGRITY"),
    "wbes_raw": ("World Bank Enterprise Surveys", "firm-wave", "VERIFIED_EXTRACTION"),
    "wbes_raw_nested": ("World Bank Enterprise Surveys", "firm-wave/documentation", "VERIFIED_EXTRACTION"),
    "treatment": ("Vietnam government/VTF", "locality evidence", "FAIL_PRIMARY_ROUTE"),
}


def run(ctx):
    cfg = sources_config()
    rows = []
    for source_id, value in sorted(cfg["protected_roots"].items()):
        path = Path(value)
        files = [p for p in path.rglob("*") if p.is_file() and not is_credential_like(p)]
        institution, unit, status = SOURCE_META.get(
            source_id, ("derived/audit", "artifact", "REFERENCE")
        )
        rows.append({
            "source_id": source_id,
            "local_path": str(path.resolve()),
            "source_institution": institution,
            "official_url": "",
            "file_count": len(files),
            "total_bytes": sum(p.stat().st_size for p in files),
            "source_vintage": "",
            "geography": "Vietnam / varies by source",
            "temporal_coverage": "",
            "unit_of_observation": unit,
            "format": "mixed",
            "status": status,
            "limitations": "See readiness report and limitations register.",
            "inventory_time_utc": utc_now(),
        })

    out = WORKING_ROOT / "artifacts/manifests/source_inventory.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    inputs = []
    for source_id, path_text in sorted(cfg["sources"].items()):
        path = assert_safe_input_path(path_text)
        inputs.append({
            "source_artifact_id": source_id,
            "path": str(path.resolve()),
            "exists": path.exists(),
            "file_size": path.stat().st_size if path.exists() else "",
            "sha256": sha256_file(path) if path.exists() and path.stat().st_size < 100_000_000 else "REUSE_EXTERNAL_MANIFEST",
        })
    declared = WORKING_ROOT / "artifacts/manifests/declared_inputs.csv"
    with open(declared, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(inputs[0]))
        writer.writeheader()
        writer.writerows(inputs)

    semantic_ready = all(
        (WORKING_ROOT / rel).exists()
        for rel in [
            "artifacts/qc/nso_semantic_decision.json",
            "artifacts/qc/vnnic_semantic_decision.json",
            "protocol/protocol_effective_lock.json",
        ]
    )
    ctx["gatebook"].set(
        "G1",
        "PASS" if semantic_ready else "WARN",
        (
            "Primary NSO PXWeb and VNNIC endpoint provenance pass with documented limitations; "
            "local NSO workbook candidates remain quarantined and unused."
            if semantic_ready else
            "Primary semantic/provenance decisions are not yet complete."
        ),
        {
            "classification": "PASS_WITH_LIMITATIONS" if semantic_ready else "PENDING",
            "source_inventory": str(out),
            "declared_inputs": str(declared),
            "local_nso_candidates": "QUARANTINED_NOT_USED",
        },
    )
    return [out, declared]
