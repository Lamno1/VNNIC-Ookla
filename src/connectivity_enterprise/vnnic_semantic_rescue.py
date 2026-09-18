from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import re
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
OUT = ROOT / "data/reference/vnnic_semantics"
DOCS = OUT / "source_documents"
EXAMPLES = OUT / "request_examples"
QC = ROOT / "artifacts/qc"
ENTRYMANIFEST = PROJECT_ROOT / "VNNIC_LOGS/download_log.csv"
ENTRYRAW = PROJECT_ROOT / "VNNIC_RAW/ftth/vnnic_ftth_2021_04.json"
URLS = {
    "official_interface": "https://internetatlas.vnnic.vn/i-speed",
    "official_interface_js": "https://internetatlas.vnnic.vn/themes/js/pages/statistic/i-speed-new.js",
    "endpoint_example": "https://internetatlas.vnnic.vn/i-speed/ftth/overview-place-map?year=2021&month=4&isp=ALL&cityId=-1",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def retrieve(url):
    req = urllib.request.Request(url, headers={"User-Agent": "connectivity-enterprise-semantic-audit/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.status, dict(response.headers.items()), response.read()


def main():
    for path in [OUT, DOCS, EXAMPLES, QC]:
        path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    evidence = []
    saved = {}
    for evidence_id, url in URLS.items():
        status, headers, body = retrieve(url)
        suffix = ".json" if evidence_id == "endpoint_example" else (".js" if evidence_id.endswith("js") else ".html")
        path = (EXAMPLES if evidence_id == "endpoint_example" else DOCS) / f"{evidence_id}{suffix}"
        path.write_bytes(body)
        saved[evidence_id] = path
        evidence.append({"evidence_id": evidence_id, "official_url": url, "retrieval_timestamp_utc": timestamp, "http_status": status, "content_type": headers.get("Content-Type", ""), "file_path": str(path), "file_bytes": len(body), "sha256": digest(body), "supports": "official endpoint/interface evidence"})

    page = saved["official_interface"].read_text(encoding="utf-8-sig")
    js = saved["official_interface_js"].read_text(encoding="utf-8-sig")
    endpoint = json.loads(saved["endpoint_example"].read_text(encoding="utf-8-sig"))
    page_compact = re.sub(r"\s+", " ", page)
    required_page_phrases = ["Download", "Mbps", "Ping", "Jitter", "ms", "tối thiểu 30 mẫu/tháng"]
    if not all(phrase in page_compact for phrase in required_page_phrases):
        raise RuntimeError("Official interface no longer contains required unit/sample evidence")
    if "số liệu được tính theo phương pháp trung vị" not in js:
        raise RuntimeError("Official JavaScript no longer identifies median method")
    if "overview-place-map" not in js or "isp=" not in js or "cityId=" not in js:
        raise RuntimeError("Official JavaScript endpoint binding changed")
    if not isinstance(endpoint, list) or not endpoint:
        raise RuntimeError("Endpoint example is not a non-empty list")
    observed_fields = sorted({key for row in endpoint for key in row})
    required_fields = {"code", "download", "upload", "ping", "jitter", "value"}
    if not required_fields.issubset(observed_fields):
        raise RuntimeError(f"Endpoint schema missing fields: {required_fields - set(observed_fields)}")

    schema = {"endpoint_template": "https://internetatlas.vnnic.vn/i-speed/{network}/overview-place-map?year={year}&month={month}&isp=ALL&cityId=-1", "request_parameters": {"network": "ftth or mobile path component", "year": "calendar year", "month": "calendar month", "isp": "ALL means all enterprises in official interface", "cityId": "-1 means all provinces in official interface"}, "observed_fields": observed_fields, "example_record_count": len(endpoint), "schema_note": "Field presence and interface binding verified; internal computation code not published."}
    (OUT / "endpoint_schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    classifications = [
        ("download", "VERIFIED_WITH_LIMITATIONS", "Internet download performance", "Mbps", "Official interface labels; official JS states median method; province-month endpoint parameters bind year/month and province codes.", "Test/device composition and retrospective revision policy are not documented."),
        ("upload", "VERIFIED_WITH_LIMITATIONS", "Internet upload performance", "Mbps", "Official interface labels and median-method credit.", "Secondary measure; same composition/revision limitations."),
        ("ping", "VERIFIED_WITH_LIMITATIONS", "Latency/ping", "ms", "Official interface labels and median-method credit.", "Secondary measure; exact protocol not documented."),
        ("jitter", "VERIFIED_WITH_LIMITATIONS", "Latency variation/jitter", "ms", "Official interface labels and median-method credit.", "Secondary measure; exact protocol not documented."),
        ("value", "NOT_USED", "Unverified endpoint count-like field", "UNVERIFIED", "Present in endpoint and raw data.", "No authoritative field definition located in bounded search; never used as weight."),
    ]
    fieldnames = ["field", "semantic_status", "meaning", "unit", "authoritative_support", "limitation"]
    with open(OUT / "vnnic_semantic_evidence.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        writer.writerows(classifications)
    with open(OUT / "retrieval_manifest.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(evidence[0]))
        writer.writeheader(); writer.writerows(evidence)

    decision = {
        "G2_VNNIC": "PASS_WITH_LIMITATIONS",
        "primary_field": "download",
        "substantive_meaning": "province-month median fixed-broadband download performance in Mbps as published by the official VNNIC Internet Atlas endpoint",
        "endpoint_officiality": "VERIFIED",
        "unit": "VERIFIED_Mbps",
        "aggregation": "VERIFIED_MEDIAN",
        "entity_time": "VERIFIED_WITH_LIMITATIONS",
        "minimum_sample_publication_rule": "VERIFIED_MINIMUM_30_SAMPLES_PER_MONTH",
        "isp_filter": "VERIFIED_ALL",
        "measurement_population": "VERIFIED_WITH_LIMITATIONS_iSPEED_MEASUREMENT_SAMPLES",
        "test_device_handling": "UNVERIFIED",
        "historical_revision_policy": "UNVERIFIED_RISK_RECORDED",
        "value": "NOT_USED",
        "bounded_search_result": "Official interface and its production JavaScript located; no authoritative field-level API codebook or revision-policy document located.",
        "existing_download_log_sha256": file_digest(ENTRYMANIFEST),
        "existing_example_raw_sha256": file_digest(ENTRYRAW),
        "decision_rationale": "Remaining uncertainty affects sampling/composition and revision risk, but not the substantive interpretation of download as official province-month median fixed-broadband Mbps. Annual unweighted medians remain interpretable as summaries of the published monthly series, with explicit limitations.",
    }
    (QC / "vnnic_semantic_decision.json").write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "vnnic_semantic_decision.md").write_text(
        "# VNNIC semantic decision\n\nG2_VNNIC = PASS_WITH_LIMITATIONS\n\n"
        "The official Internet Atlas interface labels download/upload in Mbps and ping/jitter in ms; its production JavaScript states that displayed data use the median method and binds the audited endpoint to network, year, month, ISP and province selections. The interface publishes only localities with at least 30 samples per month.\n\n"
        "Limitations: test/device composition, internal calculation implementation and retrospective revision policy are not documented. `value` is NOT_USED. These limitations must accompany every result and prohibit interpreting the measure as population coverage or treatment.\n",
        encoding="utf-8",
    )
    lineage_path = ROOT / "artifacts/lineage/semantic_evidence_lineage.csv"
    lineage_path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if lineage_path.exists():
        with open(lineage_path, encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
    existing = [row for row in existing if not str(row.get("relation", "")).startswith("supports_vnnic")]
    existing.extend([
        {"parent": str(saved["official_interface"]), "child": str(QC / "vnnic_semantic_decision.json"), "relation": "supports_vnnic_labels_units_and_minimum_sample_rule"},
        {"parent": str(saved["official_interface_js"]), "child": str(QC / "vnnic_semantic_decision.json"), "relation": "supports_vnnic_median_method_and_endpoint_binding"},
        {"parent": str(saved["endpoint_example"]), "child": str(QC / "vnnic_semantic_decision.json"), "relation": "supports_vnnic_endpoint_schema"},
    ])
    with open(lineage_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["parent", "child", "relation"])
        writer.writeheader(); writer.writerows(existing)
    print(json.dumps(decision, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
