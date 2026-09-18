from pathlib import Path
import csv, hashlib, json, re

ROOT=Path(__file__).resolve().parent
R03=ROOT/"reports/measurement_divergence_manuscript_revision_03.md"
R04=ROOT/"reports/measurement_divergence_manuscript_revision_04.md"
MATRIX=ROOT/"artifacts/qc/external_review_response_matrix_revision_04.csv"
OUT=ROOT/"artifacts/qc/internal_scientific_review_revision_04.json"

a=R03.read_text(encoding="utf-8")
b=R04.read_text(encoding="utf-8")
body=b.split("## References",1)[0]
refs=b.split("## References",1)[1]
locked=["0.542","0.488","0.296","0.248","-0.247","-0.193","-0.178","-0.169","0.591","0.545","0.583","0.535","48.07","91.14"]
forbidden=[r"\bcaused\b",r"\btreatment effect\b",r"\bpolicy effect\b",r"\bproved?\b"]
matrix=list(csv.DictReader(MATRIX.open(encoding="utf-8-sig")))
checks={
 "revision03_hash_preserved":hashlib.sha256(R03.read_bytes()).hexdigest()=="1492d8119d7e3d007f6b7f59ae4b1c8c073ecf9eb386ef99837cacf33a00bfd0",
 "related_work_present":"## 2 Related Work and Measurement Framework" in b,
 "construct_distinction_present":"not necessarily represent the same population, spatial support, or statistical estimand" in b,
 "ground_truth_boundary_present":"cannot partition observed disagreement into true local change and source-specific error" in b,
 "spatial_assignment_documented":"AMBIGUOUS" not in body and "ambiguous or boundary points were quarantined" in body,
 "locked_numbers_preserved":all(x in body for x in locked),
 "reference_count_20":len(re.findall(r"^\d+\.",refs,re.M))==20,
 "academic_reference_count_at_least_15":len(re.findall(r"^(?:[4-9]|1\d|20)\.",refs,re.M))>=17,
 "doi_count_at_least_15":len(re.findall(r"doi:10\.",refs,re.I))>=15,
 "response_matrix_complete":len(matrix)==14 and all(r["decision"] for r in matrix),
 "new_analysis_not_claimed":not any(x in body.lower() for x in ["partial correlation was","bootstrap confidence interval","we estimated a regression"]),
 "causal_language_clean":not any(re.search(p,body,re.I) for p in forbidden),
}
decision="PASS" if all(checks.values()) else "REVISE"
result={"internal_scientific_review_revision_04":decision,"checks":checks,"response_rows":len(matrix),"model_run":False,"causal_gate":"CLOSED","latex_conversion_authorized":decision=="PASS"}
OUT.write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
raise SystemExit(0 if decision=="PASS" else 1)
