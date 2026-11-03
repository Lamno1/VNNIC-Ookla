from pathlib import Path
import os
import pandas as pd

ROOT = Path(os.environ.get("VNNIC_OOKLA_ROOT", Path(__file__).resolve().parents[2])).resolve()

PANEL = ROOT / "VNNIC_DERIVED" / "vnnic_province_month_raw.csv"
XWALK = ROOT / "GIS_DERIVED" / "vnnic_adm1_crosswalk_63.csv"

OUT_DIR = ROOT / "VNNIC_DERIVED"
LOG_DIR = ROOT / "VNNIC_LOGS"

OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

OUT_PANEL = OUT_DIR / "vnnic_province_month_legacy63.csv"
OUT_COVERAGE = OUT_DIR / "vnnic_legacy63_coverage.csv"
OUT_MISSING = OUT_DIR / "vnnic_legacy63_missing_cells.csv"
OUT_SUMMARY = LOG_DIR / "vnnic_legacy63_audit_summary.txt"

# ---------------------------------------------------------
# Load
# ---------------------------------------------------------

df = pd.read_csv(PANEL, dtype={"code": str})
xw = pd.read_csv(XWALK, dtype={"vnnic_code": str})

df["code"] = df["code"].str.zfill(2)
xw["vnnic_code"] = xw["vnnic_code"].str.zfill(2)

# Legacy 63-province regime only
legacy = df[
    (df["year"] < 2025) |
    ((df["year"] == 2025) & (df["month"] <= 6))
].copy()

# ---------------------------------------------------------
# Attach crosswalk
# ---------------------------------------------------------

m = legacy.merge(
    xw,
    how="left",
    left_on="code",
    right_on="vnnic_code",
    validate="many_to_one"
)

# Basic merge audit
unmatched = m["shapeID"].isna().sum()

# Unique panel key check
dup_key = m.duplicated(
    subset=["network", "year", "month", "code"],
    keep=False
)

# ---------------------------------------------------------
# Save attached panel
# ---------------------------------------------------------

m = m.sort_values(
    ["network", "year", "month", "code"]
)

m.to_csv(
    OUT_PANEL,
    index=False,
    encoding="utf-8-sig"
)

# ---------------------------------------------------------
# Coverage by network-month
# ---------------------------------------------------------

coverage = (
    m.groupby(
        ["network", "year", "month"],
        as_index=False
    )
    .agg(
        observed_provinces=("code", "nunique"),
        rows=("code", "size"),
        total_value=("value", "sum"),
    )
)

coverage["missing_provinces"] = 63 - coverage["observed_provinces"]
coverage["coverage_rate"] = coverage["observed_provinces"] / 63

coverage = coverage.sort_values(
    ["network", "year", "month"]
)

coverage.to_csv(
    OUT_COVERAGE,
    index=False,
    encoding="utf-8-sig"
)

# ---------------------------------------------------------
# Explicit missing province-month cells
# ---------------------------------------------------------

all_codes = sorted(xw["vnnic_code"].unique())

missing_rows = []

for network in sorted(m["network"].unique()):

    sub = coverage[coverage["network"] == network]

    for _, r in sub.iterrows():

        yy = int(r["year"])
        mm = int(r["month"])

        present = set(
            m[
                (m["network"] == network) &
                (m["year"] == yy) &
                (m["month"] == mm)
            ]["code"]
        )

        missing_codes = [
            c for c in all_codes
            if c not in present
        ]

        for c in missing_codes:
            xrow = xw[xw["vnnic_code"] == c].iloc[0]

            missing_rows.append({
                "network": network,
                "year": yy,
                "month": mm,
                "vnnic_code": c,
                "province_name_official":
                    xrow["province_name_official"],
                "province_name_canonical":
                    xrow["province_name_canonical"],
                "shapeISO": xrow["shapeISO"],
                "shapeID": xrow["shapeID"]
            })

missing = pd.DataFrame(missing_rows)

missing.to_csv(
    OUT_MISSING,
    index=False,
    encoding="utf-8-sig"
)

# ---------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------

lines = []

lines.append("VNNIC LEGACY 63-PROVINCE PANEL AUDIT")
lines.append("=" * 60)

lines.append(f"Rows in legacy panel: {len(m)}")
lines.append(f"Crosswalk unmatched rows: {unmatched}")
lines.append(f"Duplicate panel-key rows: {dup_key.sum()}")

for network in sorted(m["network"].unique()):

    c = coverage[coverage["network"] == network].copy()

    full = c[c["observed_provinces"] == 63]
    incomplete = c[c["observed_provinces"] < 63]

    lines.append("")
    lines.append(f"[{network.upper()}]")
    lines.append(f"Months observed: {len(c)}")
    lines.append(f"Full 63/63 months: {len(full)}")
    lines.append(f"Incomplete months: {len(incomplete)}")
    lines.append(
        f"Minimum provinces in a month: "
        f"{c['observed_provinces'].min()}"
    )
    lines.append(
        f"Mean coverage rate: "
        f"{c['coverage_rate'].mean():.4f}"
    )

    if len(full) > 0:
        first_full = full.iloc[0]
        last_full = full.iloc[-1]

        lines.append(
            "First full month: "
            f"{int(first_full['year']):04d}-"
            f"{int(first_full['month']):02d}"
        )
        lines.append(
            "Last full month: "
            f"{int(last_full['year']):04d}-"
            f"{int(last_full['month']):02d}"
        )

    # Longest continuous 63/63 run
    c["date"] = pd.to_datetime(
        dict(
            year=c["year"],
            month=c["month"],
            day=1
        )
    )

    c = c.sort_values("date").copy()

    best_start = None
    best_end = None
    best_len = 0

    current_start = None
    current_end = None
    current_len = 0

    for _, row in c.iterrows():

        d = row["date"]
        is_full = row["observed_provinces"] == 63

        if is_full:

            if (
                current_end is not None
                and d == current_end + pd.offsets.MonthBegin(1)
            ):
                current_len += 1
            else:
                current_start = d
                current_len = 1

            current_end = d

            if current_len > best_len:
                best_len = current_len
                best_start = current_start
                best_end = current_end
        else:
            current_start = None
            current_end = None
            current_len = 0

    lines.append(
        f"Longest continuous 63/63 run: {best_len} months"
    )

    if best_start is not None:
        lines.append(
            f"Run period: {best_start:%Y-%m} to {best_end:%Y-%m}"
        )

OUT_SUMMARY.write_text(
    "\n".join(lines),
    encoding="utf-8"
)

print("\n".join(lines))

print("\nOutputs:")
print(OUT_PANEL)
print(OUT_COVERAGE)
print(OUT_MISSING)
print(OUT_SUMMARY)
