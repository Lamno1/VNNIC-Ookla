import csv
import hashlib
import json
import time
import urllib.request
import urllib.error
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(os.environ.get("VNNIC_OOKLA_ROOT", Path(__file__).resolve().parents[2])).resolve()
RAW = ROOT / "VNNIC_RAW"
LOGS = ROOT / "VNNIC_LOGS"

START_YEAR = 2019
START_MONTH = 12

# Current endpoint observed through Aug-2026.
END_YEAR = 2026
END_MONTH = 8

NETWORKS = ["ftth", "mobile"]

BASE_URL = (
    "https://internetatlas.vnnic.vn/i-speed/"
    "{network}/overview-place-map"
    "?year={year}&month={month}&isp=ALL&cityId=-1"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/151 Safari/537.36"
)

LOGS.mkdir(parents=True, exist_ok=True)

for network in NETWORKS:
    (RAW / network).mkdir(parents=True, exist_ok=True)


def month_iterator(start_year, start_month, end_year, end_month):
    year = start_year
    month = start_month

    while (year, month) <= (end_year, end_month):
        yield year, month

        month += 1
        if month == 13:
            month = 1
            year += 1


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://internetatlas.vnnic.vn/",
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
        status = response.status
        content_type = response.headers.get("Content-Type", "")

    return status, content_type, body


download_log = []
manifest = []

for network in NETWORKS:

    for year, month in month_iterator(
        START_YEAR, START_MONTH, END_YEAR, END_MONTH
    ):

        url = BASE_URL.format(
            network=network,
            year=year,
            month=month
        )

        filename = f"vnnic_{network}_{year}_{month:02d}.json"
        filepath = RAW / network / filename

        print(f"[{network.upper()}] {year}-{month:02d}")

        downloaded_at = datetime.now(timezone.utc).isoformat()

        try:
            status, content_type, body = fetch(url)

            # Preserve exact raw response bytes.
            filepath.write_bytes(body)

            file_hash = sha256_bytes(body)

            parse_ok = False
            record_count = None
            duplicate_codes = None
            top_level_type = None

            try:
                obj = json.loads(body.decode("utf-8-sig"))
                parse_ok = True
                top_level_type = type(obj).__name__

                if isinstance(obj, list):
                    record_count = len(obj)

                    codes = [
                        str(x.get("code"))
                        for x in obj
                        if isinstance(x, dict) and x.get("code") is not None
                    ]

                    duplicate_codes = len(codes) - len(set(codes))

            except Exception:
                pass

            size_bytes = len(body)

            manifest.append({
                "network": network,
                "year": year,
                "month": month,
                "filename": filename,
                "relative_path": str(filepath.relative_to(ROOT)),
                "size_bytes": size_bytes,
                "sha256": file_hash,
            })

            download_log.append({
                "network": network,
                "year": year,
                "month": month,
                "url": url,
                "downloaded_at_utc": downloaded_at,
                "http_status": status,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "sha256": file_hash,
                "json_parse_ok": parse_ok,
                "top_level_type": top_level_type,
                "record_count": record_count,
                "duplicate_codes": duplicate_codes,
                "error": "",
            })

            print(
                f"   status={status} "
                f"records={record_count} "
                f"parse={parse_ok}"
            )

        except urllib.error.HTTPError as e:

            download_log.append({
                "network": network,
                "year": year,
                "month": month,
                "url": url,
                "downloaded_at_utc": downloaded_at,
                "http_status": e.code,
                "content_type": "",
                "size_bytes": "",
                "sha256": "",
                "json_parse_ok": False,
                "top_level_type": "",
                "record_count": "",
                "duplicate_codes": "",
                "error": f"HTTPError: {e}",
            })

            print(f"   HTTP ERROR: {e}")

        except Exception as e:

            download_log.append({
                "network": network,
                "year": year,
                "month": month,
                "url": url,
                "downloaded_at_utc": downloaded_at,
                "http_status": "",
                "content_type": "",
                "size_bytes": "",
                "sha256": "",
                "json_parse_ok": False,
                "top_level_type": "",
                "record_count": "",
                "duplicate_codes": "",
                "error": repr(e),
            })

            print(f"   ERROR: {e}")

        # Be polite to public server.
        time.sleep(1.0)


log_path = LOGS / "download_log.csv"

log_fields = [
    "network",
    "year",
    "month",
    "url",
    "downloaded_at_utc",
    "http_status",
    "content_type",
    "size_bytes",
    "sha256",
    "json_parse_ok",
    "top_level_type",
    "record_count",
    "duplicate_codes",
    "error",
]

with log_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=log_fields)
    writer.writeheader()
    writer.writerows(download_log)


manifest_path = RAW / "SHA256_manifest.csv"

manifest_fields = [
    "network",
    "year",
    "month",
    "filename",
    "relative_path",
    "size_bytes",
    "sha256",
]

with manifest_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=manifest_fields)
    writer.writeheader()
    writer.writerows(manifest)


print()
print("=" * 60)
print("DOWNLOAD FINISHED")
print(f"Raw data : {RAW}")
print(f"Log      : {log_path}")
print(f"Manifest : {manifest_path}")
print("=" * 60)
