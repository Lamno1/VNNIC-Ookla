from pathlib import Path
import hashlib
import json

import pandas as pd

from connectivity_enterprise.core.paths import WORKING_ROOT


def test_pxweb_payloads_and_response_hashes():
    snapshot = WORKING_ROOT / "data/reference/nso_official_snapshot_20260913"
    manifest = pd.read_csv(WORKING_ROOT / "artifacts/manifests/nso_official_snapshot_manifest.csv")
    for table in ["V05.02", "V05.04", "V05.05"]:
        payload = json.loads((snapshot / f"{table}_request.json").read_text(encoding="utf-8"))
        assert payload["response"]["format"] == "json-stat"
        assert [q["code"] for q in payload["query"]] == ["Tỉnh/thành phố", "Năm"]
    for row in manifest.itertuples(index=False):
        assert hashlib.sha256(Path(row.file_path).read_bytes()).hexdigest() == row.sha256


def test_nso_reconciliation_and_identifier_contract():
    recon = pd.read_csv(WORKING_ROOT / "artifacts/qc/nso_official_reconciliation.csv")
    assert len(recon) == 1750
    counts = recon.groupby(["table_code", "cell_status"]).size()
    assert counts[("V05.02", "MATCHED")] == 630
    assert counts[("V05.04", "MATCHED")] == 560
    assert counts[("V05.05", "MATCHED")] == 100
    assert counts[("V05.05", "MISMATCH")] == 460
    ids = pd.read_csv(WORKING_ROOT / "artifacts/qc/province_identifier_audit.csv")
    assert len(ids) == 63
    assert ids["province_id_legacy63"].nunique() == 63
    assert set(ids["match_status"]) == {"MATCHED"}


def test_semantic_decisions_remain_locked_for_panel():
    nso = json.loads((WORKING_ROOT / "artifacts/qc/nso_semantic_decision.json").read_text(encoding="utf-8"))
    vnnic = json.loads((WORKING_ROOT / "artifacts/qc/vnnic_semantic_decision.json").read_text(encoding="utf-8"))
    assert nso["G2_NSO_PRIMARY"] == "PASS_WITH_LIMITATIONS"
    assert nso["G2_NSO_ENTRY_RATE"] == "EXPLORATORY_UNAVAILABLE"
    assert vnnic["value"] == "NOT_USED"
    assert (WORKING_ROOT / "protocol/protocol_effective_lock.json").exists()
    assert not any((WORKING_ROOT / "artifacts/models").glob("*"))
