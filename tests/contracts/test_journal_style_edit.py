import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def tokens(p):
    body=p.read_text(encoding="utf-8").split("## References",1)[0]
    prose="\n".join(x for x in body.splitlines() if not x.startswith("#"))
    return set(re.findall(r"(?<![\w])-?\d+(?:\.\d+)?",prose))

def test_revision_02_preserved():
    r2=ROOT/"reports/measurement_divergence_manuscript_revision_02.md"; a=ROOT/"reports/archive/measurement_divergence_manuscript_revision_02_20260913.md"
    assert sha(r2)==sha(a)

def test_revision_03_preserves_numbers_and_scope():
    r2=ROOT/"reports/measurement_divergence_manuscript_revision_02.md"; r3=ROOT/"reports/measurement_divergence_manuscript_revision_03.md"
    assert tokens(r2)==tokens(r3)
    text=r3.read_text(encoding="utf-8")
    assert all(term in text for term in ["common-direction agreement","cross-province dispersion","rank agreement","change-rank agreement","composition concern"])
    assert not re.search(r"\b(enterprise|H2|treatment effect|policy effect|caused|causal effect)\b",text,re.I)

def test_journal_edit_audit():
    d=json.loads((ROOT/"artifacts/qc/journal_style_edit_audit.json").read_text())
    assert d["status"]=="PASS" and d["revision"]=="03"
    assert d["numeric_inventory_identity"]==d["claim_ceiling_compliance"]==d["version_preservation"]=="PASS"
    assert d["new_analysis"] is False and d["new_references"] is False and d["model_run"] is False
