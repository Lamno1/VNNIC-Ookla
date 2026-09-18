from pathlib import Path
import csv
import hashlib
import json
import re
from datetime import datetime, timezone

import pyarrow.parquet as pq


ROOT = Path(r"D:\Q1_RESEARCH")
OOKLA_ROOT = ROOT / "OOKLA_RAW"
SOURCE_MANIFEST = OOKLA_ROOT / "SHA256_manifest.csv"
LOG_DIR = ROOT / "OOKLA_LOGS"

LOG_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY = LOG_DIR / "ookla_schema_registry.csv"
SUMMARY = LOG_DIR / "ookla_schema_registry_summary.txt"

NETWORKS = ("fixed", "mobile")
EXPECTED_QUARTERS = [
    (year, quarter)
    for year in range(2019, 2027)
    for quarter in range(1, 5)
    if (year, quarter) <= (2026, 1)
]

CORE_SCHEMA = [
    ("quadkey", "string"),
    ("tile", "string"),
    ("avg_d_kbps", "int64"),
    ("avg_u_kbps", "int64"),
    ("avg_lat_ms", "int64"),
    ("tests", "int64"),
    ("devices", "int64"),
]

EXTENDED_SCHEMA = [
    ("quadkey", "string"),
    ("tile", "string"),
    ("tile_x", "double"),
    ("tile_y", "double"),
    ("avg_d_kbps", "int64"),
    ("avg_u_kbps", "int64"),
    ("avg_lat_ms", "int64"),
    ("avg_lat_down_ms", "int32"),
    ("avg_lat_up_ms", "int32"),
    ("tests", "int64"),
    ("devices", "int64"),
]

ALLOWED_SCHEMAS = {
    tuple(CORE_SCHEMA): "CORE_V1",
    tuple(EXTENDED_SCHEMA): "EXTENDED_LATENCY_V2",
}


def sha256_file(path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def schema_signature(fields):
    raw = json.dumps(
        fields,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


if not SOURCE_MANIFEST.exists():
    raise FileNotFoundError(
        f"FAIL-CLOSED: SHA256 manifest not found: {SOURCE_MANIFEST}"
    )

parquet_files = sorted(OOKLA_ROOT.rglob("*.parquet"))

if len(parquet_files) != 58:
    raise RuntimeError(
        "FAIL-CLOSED: expected exactly 58 Parquet files under "
        f"{OOKLA_ROOT}, found {len(parquet_files)}."
    )

with open(SOURCE_MANIFEST, encoding="utf-8-sig", newline="") as f:
    manifest_rows = list(csv.DictReader(f))

if len(manifest_rows) != 58:
    raise RuntimeError(
        "FAIL-CLOSED: expected 58 SHA256 manifest rows, "
        f"found {len(manifest_rows)}."
    )

manifest_by_path = {}

for row in manifest_rows:
    path = str(Path(row["Path"]).resolve()).lower()
    if path in manifest_by_path:
        raise RuntimeError(
            f"FAIL-CLOSED: duplicate manifest path: {row['Path']}"
        )
    manifest_by_path[path] = row["Hash"].lower()

timestamp = datetime.now(timezone.utc).isoformat()
rows = []
observed_quarters = {network: set() for network in NETWORKS}

path_pattern = re.compile(
    r"^(fixed|mobile)\\(\d{4})\\Q([1-4])\\"
    r"(\d{4})-(01|04|07|10)-01_performance_(fixed|mobile)_tiles\.parquet$",
    re.IGNORECASE,
)

print("=" * 72)
print("OOKLA 58-FILE SCHEMA REGISTRY")
print("=" * 72)
print("Input root     :", OOKLA_ROOT)
print("Parquet files  :", len(parquet_files))
print("Manifest rows  :", len(manifest_rows))
print()

for source_path in parquet_files:
    relative_path = str(source_path.relative_to(OOKLA_ROOT))
    match = path_pattern.match(relative_path)

    if match is None:
        raise RuntimeError(
            f"FAIL-CLOSED: unexpected Ookla path layout: {relative_path}"
        )

    network = match.group(1).lower()
    year = int(match.group(2))
    quarter = int(match.group(3))
    filename_year = int(match.group(4))
    filename_month = int(match.group(5))
    filename_network = match.group(6).lower()

    expected_month = 1 + (quarter - 1) * 3

    if filename_year != year or filename_month != expected_month:
        raise RuntimeError(
            f"FAIL-CLOSED: path/filename period mismatch: {relative_path}"
        )

    if filename_network != network:
        raise RuntimeError(
            f"FAIL-CLOSED: path/filename network mismatch: {relative_path}"
        )

    resolved_key = str(source_path.resolve()).lower()

    if resolved_key not in manifest_by_path:
        raise RuntimeError(
            f"FAIL-CLOSED: file absent from SHA256 manifest: {source_path}"
        )

    actual_sha256 = sha256_file(source_path)
    expected_sha256 = manifest_by_path[resolved_key]

    if actual_sha256.lower() != expected_sha256:
        raise RuntimeError(
            "FAIL-CLOSED: SHA256 mismatch.\n"
            f"File     : {source_path}\n"
            f"Manifest : {expected_sha256}\n"
            f"Actual   : {actual_sha256}"
        )

    try:
        parquet = pq.ParquetFile(source_path)
        metadata = parquet.metadata
        arrow_schema = parquet.schema_arrow
    except Exception as exc:
        raise RuntimeError(
            f"FAIL-CLOSED: unreadable Parquet file: {source_path}\n{exc}"
        ) from exc

    fields = [
        (field.name, str(field.type))
        for field in arrow_schema
    ]

    schema_key = tuple(fields)

    if schema_key not in ALLOWED_SCHEMAS:
        raise RuntimeError(
            "FAIL-CLOSED: unclassified third schema variant.\n"
            f"File   : {source_path}\n"
            f"Schema : {fields}"
        )

    variant = ALLOWED_SCHEMAS[schema_key]
    names = [name for name, _ in fields]

    rows.append({
        "network": network,
        "year": year,
        "quarter": quarter,
        "source_path": str(source_path),
        "filename": source_path.name,
        "sha256": actual_sha256,
        "file_bytes": source_path.stat().st_size,
        "row_count": metadata.num_rows,
        "column_count": len(fields),
        "column_names": " | ".join(names),
        "has_tile_x": "YES" if "tile_x" in names else "NO",
        "has_tile_y": "YES" if "tile_y" in names else "NO",
        "has_avg_lat_down_ms": (
            "YES" if "avg_lat_down_ms" in names else "NO"
        ),
        "has_avg_lat_up_ms": (
            "YES" if "avg_lat_up_ms" in names else "NO"
        ),
        "schema_signature": schema_signature(fields),
        "schema_variant": variant,
        "readability": "PASS",
        "manifest_hash_identity": "PASS",
        "registry_timestamp_utc": timestamp,
    })

    observed_quarters[network].add((year, quarter))


for network in NETWORKS:
    network_rows = [r for r in rows if r["network"] == network]

    if len(network_rows) != 29:
        raise RuntimeError(
            f"FAIL-CLOSED: expected 29 {network} files, "
            f"found {len(network_rows)}."
        )

    observed = observed_quarters[network]
    expected = set(EXPECTED_QUARTERS)

    if observed != expected:
        raise RuntimeError(
            f"FAIL-CLOSED: {network} quarter coverage mismatch.\n"
            f"Missing: {sorted(expected - observed)}\n"
            f"Extra  : {sorted(observed - expected)}"
        )

registered_paths = {str(Path(r["source_path"]).resolve()).lower() for r in rows}
manifest_paths = set(manifest_by_path)

if registered_paths != manifest_paths:
    raise RuntimeError(
        "FAIL-CLOSED: Parquet files and SHA256 manifest paths differ.\n"
        f"Only files    : {sorted(registered_paths - manifest_paths)}\n"
        f"Only manifest : {sorted(manifest_paths - registered_paths)}"
    )

fieldnames = list(rows[0].keys())

with open(REGISTRY, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda r: (
        r["network"], r["year"], r["quarter"]
    )))

variant_counts = {}
for row in rows:
    key = (row["schema_variant"], row["network"])
    variant_counts[key] = variant_counts.get(key, 0) + 1

total_rows = sum(r["row_count"] for r in rows)

lines = []
lines.append("OOKLA 58-FILE SCHEMA REGISTRY AUDIT")
lines.append("=" * 68)
lines.append(f"Input root: {OOKLA_ROOT}")
lines.append(f"Parquet files: {len(rows)}")
lines.append(f"Fixed files: {sum(r['network'] == 'fixed' for r in rows)}")
lines.append(f"Mobile files: {sum(r['network'] == 'mobile' for r in rows)}")
lines.append("Quarter coverage: 2019Q1 through 2026Q1")
lines.append(f"Readable files: {sum(r['readability'] == 'PASS' for r in rows)}/58")
lines.append(
    "Manifest SHA256 identity: "
    f"{sum(r['manifest_hash_identity'] == 'PASS' for r in rows)}/58"
)
lines.append(f"Total source rows: {total_rows}")
lines.append("")
lines.append("SCHEMA VARIANTS:")

for variant in ("CORE_V1", "EXTENDED_LATENCY_V2"):
    total = sum(
        r["schema_variant"] == variant
        for r in rows
    )
    fixed = variant_counts.get((variant, "fixed"), 0)
    mobile = variant_counts.get((variant, "mobile"), 0)
    signatures = sorted({
        r["schema_signature"]
        for r in rows
        if r["schema_variant"] == variant
    })
    lines.append(
        f"{variant}: {total} files "
        f"(fixed={fixed}, mobile={mobile})"
    )
    lines.append(f"  schema_signature: {signatures[0]}")

lines.append("")
lines.append("SEMANTIC POLICY:")
lines.append("- schema_variant records file structure only.")
lines.append("- It does not assert a measurement-regime change.")
lines.append("- Absent extended latency fields are structural NA downstream.")
lines.append("- avg_lat_ms is the common latency field across all files.")
lines.append("")
lines.append(f"Registry: {REGISTRY}")
lines.append("")
lines.append("OOKLA SCHEMA REGISTRY GATE: PASS")

SUMMARY.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
