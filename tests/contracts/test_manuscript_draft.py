import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def test_manuscript_and_appendix_respect_scope():
    paths=[ROOT/"reports/measurement_divergence_manuscript.md",ROOT/"reports/measurement_divergence_appendix.md"]
    assert all(p.exists() for p in paths)
    text="\n".join(p.read_text(encoding="utf-8") for p in paths)
    assert not re.search(r"\b(enterprise|H2|treatment effect|policy effect|caused|causal effect)\b",text,re.I)
    assert "## Abstract" in text and "## 7 Conclusion" in text and "## References" in text


def test_claim_and_numeric_audits_pass():
    claims=pd.read_csv(ROOT/"artifacts/qc/manuscript_claim_source_crosswalk.csv")
    numbers=pd.read_csv(ROOT/"artifacts/qc/manuscript_numeric_reconciliation.csv")
    assert len(claims)>=7 and claims.status.str.startswith("SUPPORTED").all()
    assert set(claims.claim_level)<= {"MEASUREMENT","DESCRIPTIVE_MEASUREMENT"}
    assert len(numbers)>=16 and set(numbers.status)=={"PASS"}


def test_allow_list_and_references_are_closed():
    audit=json.loads((ROOT/"artifacts/qc/manuscript_allow_list_compliance.json").read_text(encoding="utf-8"))
    assert audit["status"]=="PASS" and audit["table_count"]==12 and audit["figure_count"]==8
    assert audit["new_result_calculations"]==0 and audit["enterprise_outcome_references"]==0
    refs=pd.read_csv(ROOT/"reports/measurement_divergence_references.csv")
    assert len(refs)==3 and set(refs.cited)=={"YES"}


def test_manuscript_gate_artifact():
    v=json.loads((ROOT/"artifacts/qc/manuscript_validation.json").read_text(encoding="utf-8"))
    assert v["manuscript_status"]=="DRAFT_COMPLETE"
    assert v["claim_audit"]==v["allow_list_compliance"]==v["numeric_reconciliation"]=="PASS"
    assert v["model_run"] is False and v["causal_gate"]=="CLOSED"
