import json
import re
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]

def test_original_draft_is_immutable():
    d=json.loads((ROOT/"artifacts/qc/internal_scientific_review_decision.json").read_text(encoding="utf-8"))
    import hashlib
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    original=ROOT/"reports/measurement_divergence_manuscript.md"
    archived=ROOT/"reports/archive/measurement_divergence_manuscript_draft_v1_20260913.md"
    assert sha(original)==sha(archived)==d["original_draft_sha256"]

def test_response_matrix_and_claim_ledger():
    matrix=pd.read_csv(ROOT/"artifacts/qc/internal_review_response_matrix.csv")
    claims=pd.read_csv(ROOT/"artifacts/qc/internal_review_claim_ledger.csv")
    assert len(matrix)==8 and (matrix.status=="RESOLVED").sum()==7
    assert len(claims)==13 and claims.status.str.startswith("SUPPORTED").all()

def test_revision_scope_and_numeric_inventory():
    text=(ROOT/"reports/measurement_divergence_manuscript_revision_01.md").read_text(encoding="utf-8")
    assert not re.search(r"\b(enterprise|H2|treatment effect|policy effect|caused|causal effect)\b",text,re.I)
    assert "matched-Q2" in text and "measured extent and ordering" in text
    nums=pd.read_csv(ROOT/"artifacts/qc/internal_review_numeric_reconciliation.csv",dtype={"displayed_value":str})
    result=text.split("## 4 Results",1)[1].split("## 5 Discussion",1)[0]
    prose="\n".join(line for line in result.splitlines() if not line.startswith("#"))
    assert set(re.findall(r"(?<![\w])-?\d+\.\d+",prose))==set(nums.displayed_value.astype(str))

def test_internal_review_decision_passes():
    d=json.loads((ROOT/"artifacts/qc/internal_scientific_review_decision.json").read_text(encoding="utf-8"))
    assert d["initial_verdict"]=="REVISE" and d["internal_scientific_review"]=="PASS"
    assert d["critical_open"]==d["major_open"]==0
    assert d["model_run"] is False and d["causal_gate"]=="CLOSED"
