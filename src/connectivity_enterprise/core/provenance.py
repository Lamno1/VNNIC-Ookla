from pathlib import Path
import csv
import hashlib
import json
from datetime import datetime, timezone

import pandas as pd

from .paths import WORKING_ROOT, assert_output_path


def sha256_file(path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def combined_hash(paths):
    records = []
    for path in sorted(Path(p).resolve() for p in paths):
        records.append((str(path), sha256_file(path)))
    return sha256_text(json.dumps(records, separators=(",", ":")))


def dataframe_schema_fingerprint(df):
    schema = [(str(c), str(df[c].dtype)) for c in df.columns]
    return sha256_text(json.dumps(schema, separators=(",", ":")))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def artifact_record(path, artifact_id, stage, run_id, parent_ids, config_hash, code_path=None):
    path = Path(path)
    row_count = ""
    column_count = ""
    schema_fingerprint = ""
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
        row_count = len(df)
        column_count = len(df.columns)
        schema_fingerprint = dataframe_schema_fingerprint(df)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        row_count = len(df)
        column_count = len(df.columns)
        schema_fingerprint = dataframe_schema_fingerprint(df)
    return {
        "artifact_id": artifact_id,
        "path": str(path.resolve()),
        "stage": stage,
        "run_id": run_id,
        "file_size": path.stat().st_size,
        "sha256": sha256_file(path),
        "row_count": row_count,
        "column_count": column_count,
        "schema_fingerprint": schema_fingerprint,
        "config_hash": config_hash,
        "code_hash": sha256_file(code_path) if code_path else "",
        "parent_artifact_ids": " | ".join(parent_ids),
        "creation_time": utc_now(),
        "validation_status": "PASS",
    }


def write_artifact_registry(records):
    path = assert_output_path(WORKING_ROOT / "artifacts/manifests/artifact_registry.csv")
    ordered = sorted(records, key=lambda r: r["artifact_id"])
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(ordered[0].keys()))
        writer.writeheader()
        writer.writerows(ordered)
    return path
