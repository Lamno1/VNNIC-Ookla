import hashlib,json,re
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def test_revision_01_preserved_and_revision_02_scoped():
    d=json.loads((ROOT/"artifacts/qc/internal_scientific_review_final_decision.json").read_text())
    r1=ROOT/"reports/measurement_divergence_manuscript_revision_01.md"; a=ROOT/"reports/archive/measurement_divergence_manuscript_revision_01_20260913.md"; r2=ROOT/"reports/measurement_divergence_manuscript_revision_02.md"
    assert sha(r1)==sha(a)==d["revision_01_sha256"]
    assert sha(r2)==d["revision_02_sha256"]
    text=r2.read_text(encoding="utf-8").lower()
    assert "connectivity inequality" not in text and "spatial inequality" not in text

def test_all_numeric_tokens_accounted_for():
    text=(ROOT/"reports/measurement_divergence_manuscript_revision_02.md").read_text(encoding="utf-8").split("## References",1)[0]
    prose="\n".join(line for line in text.splitlines() if not line.startswith("#"))
    tokens=set(re.findall(r"(?<![\w])-?\d+(?:\.\d+)?",prose))
    registry=pd.read_csv(ROOT/"artifacts/qc/internal_review_numeric_reconciliation_v2.csv",dtype={"displayed_token":str})
    assert tokens==set(registry.displayed_token) and set(registry.status)=={"PASS"}

def test_final_review_gate():
    d=json.loads((ROOT/"artifacts/qc/internal_scientific_review_final_decision.json").read_text())
    assert d["internal_scientific_review"]==d["construct_distinction"]==d["numeric_reconciliation"]=="PASS"
    assert d["major_open"]==0 and d["model_run"] is False and d["causal_gate"]=="CLOSED"
