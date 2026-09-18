from pathlib import Path
import json


def require_columns(df, required, artifact_name):
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise RuntimeError(
            f"FAIL-CLOSED: {artifact_name} missing columns: {missing}"
        )


def require_unique(df, keys, artifact_name):
    duplicate_rows = int(df.duplicated(keys, keep=False).sum())
    if duplicate_rows:
        raise RuntimeError(
            f"FAIL-CLOSED: {artifact_name} has {duplicate_rows} rows "
            f"on duplicate key {keys}"
        )


def require_row_count(df, expected, artifact_name):
    if len(df) != expected:
        raise RuntimeError(
            f"FAIL-CLOSED: {artifact_name} expected {expected} rows, "
            f"found {len(df)}"
        )


def validate_schema_contract(df, contract_path, artifact_name):
    with open(Path(contract_path), encoding="utf-8") as f:
        contract = json.load(f)
    require_columns(df, contract.get("required_columns", []), artifact_name)
    if contract.get("primary_key"):
        require_unique(df, contract["primary_key"], artifact_name)
    if contract.get("expected_rows") is not None:
        require_row_count(df, contract["expected_rows"], artifact_name)
    return contract
