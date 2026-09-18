import csv
import json

from ..core.paths import WORKING_ROOT


def run(ctx):
    vnnic_decision_path = WORKING_ROOT / "artifacts/qc/vnnic_semantic_decision.json"
    nso_decision_path = WORKING_ROOT / "artifacts/qc/nso_semantic_decision.json"
    vnnic_decision = json.loads(vnnic_decision_path.read_text(encoding="utf-8")) if vnnic_decision_path.exists() else {}
    nso_decision = json.loads(nso_decision_path.read_text(encoding="utf-8")) if nso_decision_path.exists() else {}
    rows = [
        {
            "variable_id": "vnnic_download",
            "source": "VNNIC i-Speed",
            "official_url": "https://ispeed.vn/",
            "definition": "Measured fixed-broadband download speed; public interface labels Download/Upload, Ping and Jitter.",
            "unit": "Mbps for download/upload; ms for ping/jitter",
            "aggregation_semantics": "Public VNNIC material supports monthly locality reporting and median summaries, but the exact local export endpoint, filtering, revision vintage and province-month construction remain unverified.",
            "semantic_status": vnnic_decision.get("G2_VNNIC", "PARTIAL_BLOCKING"),
            "blocking": "NO" if vnnic_decision.get("G2_VNNIC") in {"PASS", "PASS_WITH_LIMITATIONS"} else "YES",
            "request": "Official codebook/API or archived methodology matching the acquired province-month files, including metric aggregation, geographic assignment, filters, revisions, and value field meaning.",
        },
        {
            "variable_id": "active_firms_per_1000",
            "source": "NSO PXWeb V05.05",
            "official_url": "https://pxweb.nso.gov.vn/pxweb/vi/Doanh%20nghi%E1%BB%87p/Doanh%20nghi%E1%BB%87p/V05.05.px/",
            "definition": "Active enterprises at 31 December per 1,000 inhabitants, by province and year.",
            "unit": "enterprises per 1,000 inhabitants",
            "aggregation_semantics": "Table-face definition and years are verified; exact local-workbook acquisition/vintage mapping and detailed enterprise/population universe remain pending.",
            "semantic_status": nso_decision.get("G2_NSO_PRIMARY", "PARTIAL_BLOCKING"),
            "blocking": "NO" if nso_decision.get("G2_NSO_PRIMARY") in {"PASS", "PASS_WITH_LIMITATIONS"} else "YES",
            "request": "Authoritative acquisition record/vintage for the local workbook and detailed metadata defining the enterprise and population universes and revision policy.",
        },
        {
            "variable_id": "new_registrations",
            "source": "NSO PXWeb V05.02",
            "official_url": "https://pxweb.nso.gov.vn/pxweb/vi/Doanh%20nghi%E1%BB%87p/Doanh%20nghi%E1%BB%87p/V05.02.px/",
            "definition": "Newly established enterprises in the year, by province.",
            "unit": "enterprises",
            "aggregation_semantics": "Table-face meaning is verified; compatibility with the V05.04 denominator and local-workbook vintage remains pending.",
            "semantic_status": nso_decision.get("G2_NSO_ENTRY_RATE", "PARTIAL_BLOCKING"),
            "blocking": "NO_PRIMARY_BLOCK" if nso_decision.get("G2_NSO_ENTRY_RATE") == "EXPLORATORY_UNAVAILABLE" else "YES",
            "request": "Official compatibility note for V05.02 numerator versus lagged V05.04 denominator, plus local acquisition/vintage evidence.",
        },
        {
            "variable_id": "active_firms_lag_denominator",
            "source": "NSO PXWeb V05.04",
            "official_url": "https://pxweb.nso.gov.vn/pxweb/vi/Doanh%20nghi%E1%BB%87p/Doanh%20nghi%E1%BB%87p/V05.04.px/",
            "definition": "Active enterprises at 31 December, by province and year.",
            "unit": "enterprises",
            "aggregation_semantics": "Year-end stock is verified at table-face level; compatibility with registrations and local-workbook vintage remains pending.",
            "semantic_status": nso_decision.get("G2_NSO_ENTRY_RATE", "PARTIAL_BLOCKING"),
            "blocking": "NO_PRIMARY_BLOCK" if nso_decision.get("G2_NSO_ENTRY_RATE") == "EXPLORATORY_UNAVAILABLE" else "YES",
            "request": "Official scope/timing compatibility with V05.02 and local acquisition/vintage evidence.",
        },
    ]
    out = WORKING_ROOT / "artifacts/qc/semantic_registry.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    request = WORKING_ROOT / "reports/missing_document_request.md"
    request.write_text(
        "# Residual documentation requests\n\n"
        "Primary semantics have been rescued with limitations using newly retrieved official sources. These residual requests remain material to interpretation.\n\n"
        "1. VNNIC: field-level API codebook covering test/device composition, internal computation and retrospective revision policy. `value` remains NOT_USED.\n"
        "2. NSO entry-intensity proxy: documentation proving V05.02 and lagged V05.04 universe compatibility. Until then it is EXPLORATORY_UNAVAILABLE.\n"
        "3. NSO: detailed denominator-universe note for V05.05 beyond its official table title.\n",
        encoding="utf-8",
    )
    primary_pass = (
        vnnic_decision.get("G2_VNNIC") in {"PASS", "PASS_WITH_LIMITATIONS"}
        and nso_decision.get("G2_NSO_PRIMARY") in {"PASS", "PASS_WITH_LIMITATIONS"}
    )
    ctx["gatebook"].set(
        "G2", "PASS" if primary_pass else "FAIL",
        "Primary VNNIC and NSO semantics are verified with documented limitations; entry-intensity proxy is unavailable."
        if primary_pass else "Primary semantics remain unresolved.",
        {"semantic_registry": str(out), "vnnic_decision": str(vnnic_decision_path), "nso_decision": str(nso_decision_path), "document_request": str(request)},
    )
    outputs = [out, request]
    for evidence_path in [vnnic_decision_path, nso_decision_path]:
        if evidence_path.exists():
            outputs.append(evidence_path)
    return outputs
