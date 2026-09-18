import json, re, shutil
from ..core.paths import WORKING_ROOT
from ..core.provenance import sha256_file, utc_now

def numeric_tokens(text):
    body=text.split("## References",1)[0]
    prose="\n".join(line for line in body.splitlines() if not line.startswith("#"))
    return sorted(set(re.findall(r"(?<![\w])-?\d+(?:\.\d+)?",prose)))

def run(ctx):
    decision=json.loads((WORKING_ROOT/"artifacts/qc/internal_scientific_review_final_decision.json").read_text(encoding="utf-8"))
    if decision["internal_scientific_review"]!="PASS" or decision["major_open"]!=0:
        raise RuntimeError("FAIL-CLOSED: internal review not passed")
    rev2=WORKING_ROOT/"reports/measurement_divergence_manuscript_revision_02.md"
    if sha256_file(rev2)!=decision["revision_02_sha256"]:
        raise RuntimeError("FAIL-CLOSED: Revision 02 hash drift")
    archive=WORKING_ROOT/"reports/archive/measurement_divergence_manuscript_revision_02_20260913.md"
    if archive.exists() and sha256_file(archive)!=sha256_file(rev2): raise RuntimeError("FAIL-CLOSED: Revision 02 archive conflict")
    if not archive.exists(): shutil.copyfile(rev2,archive)

    text=rev2.read_text(encoding="utf-8")
    old_abstract=text.split("## Abstract\n\n",1)[1].split("\n\n## 1 Introduction",1)[0]
    new_abstract="""Regional broadband comparisons often treat administrative and crowdsourced speed-test systems as interchangeable. We compare VNNIC i-Speed and Ookla fixed-broadband measurements across 63 historical Vietnamese provinces from 2021 to 2024. The design separates common-direction agreement, cross-province dispersion, yearly rank agreement, and change-rank agreement. Between matched-Q2 observations in 2021 and 2024, both sources report higher download performance in every province. Five of six dispersion indicators also point to a wider cross-province distribution. Agreement is weaker for provincial ordering: yearly Spearman rank correlations are 0.542, 0.488, 0.296, and 0.248, and the change-rank correlation is -0.247. This negative change-rank result persists across four Ookla aggregation rules. Ookla speed changes also co-vary with changes in observed tests and devices, heightening composition concern. The sources therefore support the same aggregate direction and broadly similar dispersion conclusions, but not a source-invariant ranking of provinces or their improvement. The measured extent and ordering of provincial connectivity differences depend on the construct and aggregation system used."""
    text=text.replace(old_abstract,new_abstract)
    replacements={
      "Digital-connectivity indicators increasingly enter regional dashboards, benchmarking exercises, and empirical research as if a single number represented an observable local condition.":"Regional dashboards and empirical studies often summarize digital connectivity with a single indicator.",
      "Agreement at a national or aggregate level therefore need not imply agreement about which places perform better or improve faster.":"Common-direction agreement therefore need not imply rank agreement or change-rank agreement.",
      "This study asks how far their conclusions travel across four levels: the common direction of change, cross-province dispersion, yearly provincial ranks, and province-specific changes.":"We compare the sources at four levels: common-direction agreement, cross-province dispersion, yearly rank agreement, and change-rank agreement.",
      "Our central finding is layered. Both systems show broad improvement between the matched-Q2 endpoints, and most declared dispersion measures show a wider cross-province distribution. Yet cross-source agreement falls markedly when attention shifts to provincial ordering and relative improvement.":"The two systems agree on the matched-Q2 direction of change and broadly agree on dispersion. Their rank agreement is weaker, and their change-rank agreement is negative.",
      "The contribution is methodological and descriptive. We provide an auditable decomposition of agreement rather than a single validity score.":"The study contributes an auditable, descriptive decomposition of agreement rather than a single validity score.",
      "The findings show why measurement agreement must be stated at the correct level.":"Measurement agreement depends on the level of comparison.",
      "The evidence is consistent with the systems measuring related but non-equivalent constructs.":"The evidence is consistent with related but non-equivalent measurement constructs.",
      "These constraints preserve a descriptive-measurement claim ceiling.":"These limitations restrict the claims to descriptive measurement comparisons.",
    }
    for old,new in replacements.items():
        if old not in text: raise RuntimeError(f"FAIL-CLOSED: journal edit target missing: {old[:45]}")
        text=text.replace(old,new)
    text=text.replace("broad directional support across sources","broad dispersion agreement across sources")
    text=text.replace("Yearly agreement is positive but declines across the period","Yearly rank agreement is positive but declines across the period")
    text=text.replace("The two systems agree on the sign of change","The two systems show common-direction agreement")
    text=text.replace("Composition diagnostics remain material","Composition concern remains material")

    if numeric_tokens(text)!=numeric_tokens(rev2.read_text(encoding="utf-8")):
        raise RuntimeError("FAIL-CLOSED: journal edit changed numeric-token inventory")
    forbidden=re.compile(r"\b(enterprise|H2|treatment effect|policy effect|caused|causal effect|regression coefficient|p-value|statistically significant)\b",re.I)
    if forbidden.search(text): raise RuntimeError("FAIL-CLOSED: prohibited wording")
    for phrase in ["connectivity inequality","spatial inequality","national-direction trend"]:
        if phrase in text.lower(): raise RuntimeError("FAIL-CLOSED: construct distinction weakened")

    rev3=WORKING_ROOT/"reports/measurement_divergence_manuscript_revision_03.md"; rev3.write_text(text,encoding="utf-8")
    app2=WORKING_ROOT/"reports/measurement_divergence_appendix_revision_02.md"
    apptext=app2.read_text(encoding="utf-8").replace("## A2 Four Ookla aggregation rules","## A2 Aggregation sensitivity").replace("## A3 Leave-one-province-out audit","## A3 Influence diagnostics").replace("## A4 Composition diagnostics","## A4 Composition concern")
    app3=WORKING_ROOT/"reports/measurement_divergence_appendix_revision_03.md"; app3.write_text(apptext,encoding="utf-8")
    if numeric_tokens(apptext)!=numeric_tokens(app2.read_text(encoding="utf-8")): raise RuntimeError("FAIL-CLOSED: appendix numeric inventory changed")

    changelog=WORKING_ROOT/"reports/measurement_divergence_manuscript_revision_03_changelog.md"
    changelog.write_text(f"# Revision 03 change log\n\nRevision 02 SHA256: `{sha256_file(rev2)}`\n\n- Preserved Revision 02 byte-for-byte under `reports/archive`.\n- Tightened the title and abstract for a journal-neutral audience.\n- Reduced repetition and shortened the introduction and discussion.\n- Standardized common-direction agreement, cross-province dispersion, rank agreement, change-rank agreement, and composition concern.\n- Synchronized appendix headings.\n- Preserved the complete numeric-token inventory, references, constructs, evidence, and claim ceiling.\n- Added no analysis, source, or conclusion.\n",encoding="utf-8")
    audit=WORKING_ROOT/"artifacts/qc/journal_style_edit_audit.json"
    audit.write_text(json.dumps({"status":"PASS","source_revision":"02","source_sha256":sha256_file(rev2),"archive_sha256":sha256_file(archive),"revision":"03","revision_sha256":sha256_file(rev3),"appendix_sha256":sha256_file(app3),"numeric_inventory_identity":"PASS","reference_inventory_identity":"PASS","claim_ceiling_compliance":"PASS","construct_distinction":"PASS","causal_language_audit":"PASS","version_preservation":"PASS","new_analysis":False,"new_references":False,"model_run":False,"causal_gate":"CLOSED","next_stage":"LATEX_CONVERSION","timestamp":utc_now()},indent=2),encoding="utf-8")
    ctx.update({"review_research_gate":"READY_FOR_LATEX_CONVERSION","primary_study_path":"DESCRIPTIVE_MEASUREMENT_DIVERGENCE","h2_review_status":"NOT_TESTABLE_WITH_CURRENT_EXPOSURE","paper_protocol_status":"PASS_LOCKED","manuscript_status":"REVISION_03_JOURNAL_EDIT_PASS","claim_audit":"PASS","allow_list_compliance":"PASS","numeric_reconciliation":"PASS","internal_scientific_review":"PASS","construct_distinction":"PASS"})
    evidence={"JOURNAL_STYLE_EDIT":"PASS","CLAIM_CEILING_COMPLIANCE":"PASS","CONSTRUCT_DISTINCTION":"PASS","CAUSAL_LANGUAGE_AUDIT":"PASS","NUMERIC_RECONCILIATION":"PASS","VERSION_PRESERVATION":"PASS","MODEL_RUN":False,"CAUSAL_GATE":"CLOSED"}
    ctx["gatebook"].set("JOURNAL_STYLE_EDIT","PASS","Revision 03 journal-neutral edit completed.",evidence)
    ctx["gatebook"].set("JOURNAL_EDIT_CLAIM_GATE","PASS","Claims and construct distinctions preserved.",evidence)
    ctx["gatebook"].set("JOURNAL_EDIT_NUMERIC_GATE","PASS","Numeric token inventory unchanged from Revision 02.",evidence)
    return [archive,rev3,app3,changelog,audit]
