import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]

def test_latex_inventory_and_appendix():
    main=(ROOT/"latex/manuscript.tex").read_text(encoding="utf-8")
    appendix=(ROOT/"latex/appendix.tex").read_text(encoding="utf-8")
    assert main.count("\\includegraphics")==8
    assert "\\input{appendix.tex}" in main
    assert appendix.count("\\input{tables/table_")==12
    assert len(list((ROOT/"latex/tables").glob("table_*.tex")))==12

def test_latex_reconciliation_evidence():
    d=json.loads((ROOT/"artifacts/qc/latex_conversion_audit.json").read_text())
    assert d["source_revision"]=="REVISION_03"
    assert d["tables"]==12 and d["figures"]==8 and d["citations"]==3
    assert all(d[k]=="PASS" for k in ["latex_conversion","content_reconciliation","numeric_reconciliation","table_figure_allowlist","citation_reconciliation","pdf_build"])
    r=pd.read_csv(ROOT/"artifacts/qc/latex_content_reconciliation.csv")
    assert not r.empty and r.status.eq("PASS").all() and r.numeric_tokens_preserved.all() and r.source_file.nunique()==2

def test_latex_scope_and_build_log():
    table7=(ROOT/"latex/tables/table_07.tex").read_text(encoding="utf-8").lower()
    assert "enterprise" not in table7 and "firm_density" not in table7
    log=(ROOT/"latex/latex_build.log").read_text(encoding="utf-8",errors="replace").lower()
    assert "overfull \\hbox" not in log and "undefined references" not in log and "latex warning" not in log
    assert (ROOT/"latex/manuscript.pdf").stat().st_size>0
