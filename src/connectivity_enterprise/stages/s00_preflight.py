from pathlib import Path
import importlib.metadata
import hashlib
import json
import os
import platform
import shutil
import sys

from ..core.paths import (
    WORKING_ROOT,
    sources_config,
    is_credential_like,
    assert_safe_input_path,
)
from ..core.provenance import sha256_file, utc_now


def run(ctx):
    cfg = sources_config()
    root = Path(cfg["project_root"]).resolve()
    working = Path(cfg["working_root"]).resolve()

    if root != Path(r"D:\Q1_RESEARCH").resolve():
        raise RuntimeError(f"FAIL-CLOSED: unexpected project root: {root}")
    if working != WORKING_ROOT.resolve():
        raise RuntimeError(f"FAIL-CLOSED: unexpected working root: {working}")

    protected = {k: Path(v).resolve() for k, v in cfg["protected_roots"].items()}
    missing = [str(p) for p in protected.values() if not p.exists()]
    if missing:
        raise RuntimeError(f"FAIL-CLOSED: missing protected roots: {missing}")
    for path in protected.values():
        try:
            working.relative_to(path)
            raise RuntimeError(
                f"FAIL-CLOSED: output root is nested in protected root: {path}"
            )
        except ValueError:
            pass

    for source_id, source_path in cfg["sources"].items():
        safe = assert_safe_input_path(source_path)
        if not safe.exists():
            raise RuntimeError(
                f"FAIL-CLOSED: required declared input missing: {source_id} = {safe}"
            )

    lock_path = WORKING_ROOT / "protocol/protocol_lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    protocol_path = WORKING_ROOT / lock["protocol_path"]
    actual_protocol_hash = sha256_file(protocol_path)
    if actual_protocol_hash != lock["sha256"]:
        raise RuntimeError(
            "FAIL-CLOSED: frozen protocol hash differs from protocol lock; "
            "record an amendment before continuing."
        )

    effective_path = WORKING_ROOT / "protocol/protocol_effective_lock.json"
    effective = json.loads(effective_path.read_text(encoding="utf-8"))
    amendment_path = WORKING_ROOT / effective["amendment_path"]
    base_hash = sha256_file(WORKING_ROOT / effective["base_protocol_path"])
    amendment_hash = sha256_file(amendment_path)
    composite = hashlib.sha256(
        f"{base_hash.lower()}|{amendment_hash.lower()}".encode("ascii")
    ).hexdigest()
    if (
        base_hash != effective["base_protocol_sha256"]
        or amendment_hash != effective["amendment_sha256"]
        or composite != effective["effective_protocol_sha256"]
    ):
        raise RuntimeError("FAIL-CLOSED: effective protocol lock is inconsistent")
    ctx["effective_protocol_hash"] = composite

    treatment_gate_path = assert_safe_input_path(cfg["sources"]["treatment_gate"])
    readiness_summary_path = assert_safe_input_path(cfg["sources"]["readiness_summary"])
    treatment_gate = json.loads(treatment_gate_path.read_text(encoding="utf-8"))
    readiness = json.loads(readiness_summary_path.read_text(encoding="utf-8"))
    if treatment_gate.get("gate_status") != "FAIL_PRIMARY_ROUTE":
        raise RuntimeError("FAIL-CLOSED: treatment gate is not FAIL_PRIMARY_ROUTE")
    if treatment_gate.get("econometrics_run") is not False:
        raise RuntimeError("FAIL-CLOSED: treatment report unexpectedly records econometrics")
    if treatment_gate.get("timing", {}).get("earliest_verified_treatment") is not None:
        raise RuntimeError("FAIL-CLOSED: treatment timing contradicts locked protocol")
    challenge = readiness.get("data_challenge", {})
    if challenge.get("feasibility_verdict") != "NOT_FEASIBLE":
        raise RuntimeError("FAIL-CLOSED: readiness verdict contradicts locked causal closure")

    run_dir = ctx["run_dir"]
    snapshot_dir = run_dir / "config_snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted((WORKING_ROOT / "config").rglob("*")):
        if path.is_file():
            target = snapshot_dir / path.relative_to(WORKING_ROOT / "config")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)

    inventory = []
    for name, path in protected.items():
        files = [
            p for p in path.rglob("*")
            if p.is_file() and not is_credential_like(p)
        ]
        inventory.append({
            "root_id": name,
            "path": str(path),
            "file_count": len(files),
            "total_bytes": sum(p.stat().st_size for p in files),
        })

    packages = {}
    for name in ["pandas", "pyarrow", "openpyxl", "PyYAML", "statsmodels", "matplotlib", "scipy"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None

    treatment_evidence = {
        "treatment_gate_status": treatment_gate["gate_status"],
        "verified_actual_treatment_village_count": treatment_gate["geographic_coverage"]["verified_actual_treatment_village_count"],
        "earliest_verified_treatment": treatment_gate["timing"]["earliest_verified_treatment"],
        "latest_verified_treatment": treatment_gate["timing"]["latest_verified_treatment"],
        "econometrics_run": treatment_gate["econometrics_run"],
        "outcome_data_merged": treatment_gate["outcome_data_merged"],
        "ookla_processed": treatment_gate["ookla_processed"],
        "readiness_causal_verdict": challenge["feasibility_verdict"],
        "readiness_descriptive_verdict": challenge["descriptive_pivot_verdict"],
        "source_hashes": {
            source_id: sha256_file(assert_safe_input_path(cfg["sources"][source_id]))
            for source_id in [
                "readiness_report", "readiness_summary",
                "treatment_report", "treatment_gate",
            ]
        },
    }
    treatment_evidence_path = run_dir / "treatment_readiness_evidence.json"
    treatment_evidence_path.write_text(
        json.dumps(treatment_evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    environment = {
        "run_id": ctx["run_id"],
        "created_at_utc": utc_now(),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "processor_count": os.cpu_count(),
        "git_workflow": False,
        "packages": packages,
        "protocol_sha256": actual_protocol_hash,
        "effective_protocol_sha256": composite,
        "parquet_engine": "pyarrow" if packages.get("pyarrow") else None,
        "credential_files_accessed": False,
        "protected_roots": inventory,
    }
    out = run_dir / "environment.json"
    out.write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")

    ctx["gatebook"].set(
        "G0",
        "PASS",
        "Output root is separate; all allow-listed roots exist; direct mode; credential exclusions active.",
        {
            "environment": str(out),
            "treatment_readiness_evidence": str(treatment_evidence_path),
            "credential_files_accessed": False,
        },
    )
    return [out, treatment_evidence_path]
