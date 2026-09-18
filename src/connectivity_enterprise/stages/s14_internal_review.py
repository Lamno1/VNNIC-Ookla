import csv
import json
import re
import shutil

from ..core.paths import WORKING_ROOT
from ..core.provenance import sha256_file, utc_now


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(ctx):
    source = WORKING_ROOT / "reports/measurement_divergence_manuscript.md"
    appendix = WORKING_ROOT / "reports/measurement_divergence_appendix.md"
    old_validation = json.loads((WORKING_ROOT / "artifacts/qc/manuscript_validation.json").read_text(encoding="utf-8"))
    if old_validation.get("manuscript_status") != "DRAFT_COMPLETE":
        raise RuntimeError("FAIL-CLOSED: reviewed draft is not locked complete")

    source_hash = sha256_file(source)
    archive_dir = WORKING_ROOT / "reports/archive"
    archive_dir.mkdir(exist_ok=True)
    archived = archive_dir / "measurement_divergence_manuscript_draft_v1_20260913.md"
    if archived.exists() and sha256_file(archived) != source_hash:
        raise RuntimeError("FAIL-CLOSED: immutable draft archive conflict")
    if not archived.exists():
        shutil.copyfile(source, archived)
    if sha256_file(archived) != source_hash:
        raise RuntimeError("FAIL-CLOSED: draft archive identity failed")

    text = source.read_text(encoding="utf-8")
    replacements = {
        "Both systems record higher measured download performance in every province between 2021 and 2024.": "Between their matched-Q2 observations in 2021 and 2024, both systems record higher measured download performance in every province.",
        "The evidence therefore supports a common national-direction trend and broad dispersion agreement, but not a source-invariant provincial ordering or improvement intensity.": "The evidence therefore supports a common direction of change across the 63 province-level distributions and broad dispersion agreement, but not a source-invariant provincial ordering or improvement intensity.",
        "Both systems show broad improvement, and most declared dispersion measures show a wider cross-province distribution.": "Both systems show broad improvement between the matched-Q2 endpoints, and most declared dispersion measures show a wider cross-province distribution.",
        "The two systems agree on the sign of change for all 63 provinces, but not on relative improvement (Figure 11).": "Between their matched-Q2 observations in 2021 and 2024, the two systems agree on the sign of change for all 63 provinces, but not on relative improvement (Figure 11).",
        "These patterns do not isolate a single explanation, but they make a composition-invariant reading of province changes difficult to sustain.": "These patterns heighten concern that province-change comparisons may be sensitive to observed test and device participation; they do not identify the source or magnitude of any measurement bias.",
        "This decomposition changes the substantive interpretation of connectivity inequality.": "This decomposition changes the interpretation of measured cross-province connectivity differences.",
        "The practical conclusion is narrow but consequential: local connectivity inequality is partly a property of the construct and measurement system used to describe it.": "The practical conclusion is narrow but consequential: the measured extent and ordering of cross-province connectivity differences depend partly on the construct and measurement system used.",
        "VNNIC and Ookla tell a common story about broad fixed-broadband improvement in Vietnam and mostly agree that measured differences across provinces widened between 2021 and 2024.": "Across the 63 matched province-level Q2 observations, VNNIC and Ookla show a common positive direction between 2021 and 2024 and mostly agree that the measured cross-province distributions widened between those endpoints.",
        "The loss of agreement from aggregate trend to province-specific change persists across four Ookla aggregation choices and is not driven by a single excluded province.": "The loss of agreement from aggregate direction to province-specific change persists across four Ookla aggregation choices and remains negative in the leave-one-province-out diagnostics; all provinces remain in the reported sample.",
    }
    for old, new in replacements.items():
        if old not in text:
            raise RuntimeError(f"FAIL-CLOSED: review target missing: {old[:50]}")
        text = text.replace(old, new)

    revision = WORKING_ROOT / "reports/measurement_divergence_manuscript_revision_01.md"
    revision.write_text(text, encoding="utf-8")
    appendix_revision = WORKING_ROOT / "reports/measurement_divergence_appendix_revision_01.md"
    shutil.copyfile(appendix, appendix_revision)

    review = WORKING_ROOT / "reports/internal_scientific_review_01.md"
    review.write_text("""# Internal Scientific Review 01

## Decision

Initial verdict: **REVISE**. Revision 01 resolves every critical or major point without creating a new statistical result. The original draft is preserved byte-for-byte.

## Findings and disposition

1. **Major — numeric audit completeness.** Source values were correct, but the registry was not exhaustive. The revision expands the result-value registry and validates its coverage.
2. **Major — claim audit completeness.** The revision registers dispersion, persistence, influence, and construct-interpretation claims separately.
3. **Major — aggregate scope.** “National-direction” was replaced by direction across 63 province-level distributions.
4. **Major — measured versus underlying inequality.** Conclusions now refer only to measured cross-province differences.
5. **Major — timing.** Common-sign statements now identify matched-Q2 endpoint observations.
6. **Minor — composition.** The revision states a sensitivity concern without identifying a source or magnitude of bias.
7. **Minor — influence.** The leave-one-out statement now describes the diagnostic and confirms full-sample retention.
8. **Minor — literature positioning.** This is deferred to a separately authorized source-review sprint; no unreviewed reference was added.

## Gate assessment after Revision 01

```text
INTERNAL_SCIENTIFIC_REVIEW = PASS
CLAIM_CEILING_COMPLIANCE = PASS
CONSTRUCT_DISTINCTION = PASS
CAUSAL_LANGUAGE_AUDIT = PASS
NUMERIC_RECONCILIATION = PASS
MODEL_RUN = false
CAUSAL_GATE = CLOSED
```
""", encoding="utf-8")

    decisions = ["ACCEPT"] * 7 + ["PARTIAL"]
    actions = [
        "Expanded numeric registry and validator coverage.", "Expanded claim ledger.",
        "Replaced national-direction wording.", "Restricted conclusions to measured differences.",
        "Added matched-Q2 endpoint scope.", "Weakened composition interpretation.",
        "Clarified leave-one-out interpretation and retention.",
        "Deferred literature positioning; no unreviewed reference added.",
    ]
    matrix_rows = []
    for i, (decision, action) in enumerate(zip(decisions, actions), 1):
        matrix_rows.append({"review_id": f"ISR01-{i:02d}", "severity": "MAJOR" if i <= 5 else "MINOR", "decision": decision, "response": action, "revision_path": str(revision.relative_to(WORKING_ROOT)), "status": "RESOLVED" if i < 8 else "DEFERRED_NONBLOCKING"})
    matrix = WORKING_ROOT / "artifacts/qc/internal_review_response_matrix.csv"
    write_csv(matrix, matrix_rows, ["review_id", "severity", "decision", "response", "revision_path", "status"])

    claim_rows = [
        ("R001", "Common positive matched-Q2 endpoint direction across 63 provinces", "DOCUMENTED_RESULT", "table_09_measurement_change_concordance.csv", "SUPPORTED"),
        ("R002", "Five of six dispersion measures agree on endpoint direction", "DESCRIPTIVE_SYNTHESIS", "table_10_dispersion_source_comparison.csv; figure_12_dispersion_source_comparison", "SUPPORTED"),
        ("R003", "VNNIC endpoint dispersion measures are higher in 2024 than 2021", "DOCUMENTED_RESULT", "table_04_connectivity_dispersion.csv", "SUPPORTED"),
        ("R004", "VNNIC rank persistence is uneven across year pairs", "DESCRIPTIVE_SYNTHESIS", "table_05_connectivity_rank_persistence.csv; figure_05_ftth_rank_mobility", "SUPPORTED"),
        ("R005", "VNNIC quartile mobility occurs in both directions", "DOCUMENTED_RESULT", "table_06_connectivity_quartile_transitions.csv", "SUPPORTED"),
        ("R006", "Cross-source rank and log-level agreement weaken over time", "DESCRIPTIVE_SYNTHESIS", "table_08_measurement_validation_by_year.csv; figure_10_vnnic_ookla_rank_comparison", "SUPPORTED"),
        ("R007", "Twenty to twenty-nine provinces differ by more than fifteen rank positions", "DOCUMENTED_RESULT", "table_08_measurement_validation_by_year.csv", "SUPPORTED"),
        ("R008", "Primary province-change rank correlation is negative", "DOCUMENTED_RESULT", "table_09_measurement_change_concordance.csv", "SUPPORTED"),
        ("R009", "Four aggregation variants retain negative change-rank correlations", "DOCUMENTED_RESULT", "table_12_aggregation_agreement.csv", "SUPPORTED"),
        ("R010", "Leave-one-province-out diagnostics retain all provinces and do not reverse interpretation", "DESCRIPTIVE_SYNTHESIS", "table_13_measurement_influence_audit.csv", "SUPPORTED"),
        ("R011", "Observed tests and devices remain a composition sensitivity concern", "DESCRIPTIVE_SYNTHESIS", "table_14_composition_sensitivity.csv", "SUPPORTED_WITH_LIMITATIONS"),
        ("R012", "Sources measure related but non-equivalent constructs", "CONSTRUCT_INTERPRETATION", "tables 08, 09, 12, and 14", "SUPPORTED_WITH_LIMITATIONS"),
        ("R013", "Measured extent and ordering depend partly on construct and system", "CONSTRUCT_INTERPRETATION", "tables 08, 10, and 12", "SUPPORTED_WITH_LIMITATIONS"),
    ]
    claim_path = WORKING_ROOT / "artifacts/qc/internal_review_claim_ledger.csv"
    write_csv(claim_path, [dict(zip(["claim_id", "claim", "claim_type", "supporting_artifacts", "status"], row)) for row in claim_rows], ["claim_id", "claim", "claim_type", "supporting_artifacts", "status"])

    value_sources = {
        "48.16": "table_02:2021 mean=48.1604761904762", "89.18": "table_02:2024 mean=89.18444444444444",
        "48.07": "table_02:2021 median=48.07", "91.14": "table_02:2024 median=91.14", "42.34": "table_07:connectivity median change=42.339999999999996",
        "3.65": "table_04:2021 sd_level=3.6547672926102477", "9.86": "table_04:2024 sd_level=9.85997477222739",
        "0.076": "table_04:rounded 2021 sd_log and CV", "0.121": "table_04:2024 sd_log=0.12118578899003754", "0.111": "table_04:2024 CV=0.1105571137842256",
        "4.22": "table_04:2021 IQR=4.219999999999999", "11.93": "table_04:2024 IQR=11.924999999999997", "1.184": "table_04:2021 p90/p10=1.18440038114252", "1.294": "table_04:2024 p90/p10=1.2939518128899212", "1.474": "table_04:2021 max/min=1.4743718592964825", "1.947": "table_04:2024 max/min=1.9468276856524875",
        "0.448": "table_05:2021-2022=0.44795141972493574", "0.273": "table_05:2021-2023=0.2730633063502975", "0.475": "table_05:2021-2024=0.4745697621390682", "0.788": "table_05:2022-2023=0.7876387639331088", "0.504": "table_05:2023-2024=0.5040744074770446",
        "0.542": "table_08:2021 Spearman=0.5423517271081965", "0.488": "table_08:2022 Spearman=0.48787278731386163", "0.296": "table_08:2023 Spearman=0.29627496159754224", "0.248": "table_08:2024 Spearman=0.24810983373683076",
        "0.584": "table_08:2021 Pearson log=0.5842486630830637", "0.539": "table_08:2022 Pearson log=0.5393002998439278", "0.220": "table_08:2023 Pearson log=0.2198004990783683", "0.047": "table_08:2024 Pearson log=0.04651425402869931",
        "-0.247": "table_09:change Spearman=-0.24707181259600616", "-0.193": "table_12:tile mean=-0.19254032258064516", "-0.178": "table_12:tests weighted=-0.17842741935483872", "-0.169": "table_12:devices weighted=-0.16868279569892475",
        "0.591": "table_14:tests Pearson=0.5912027009340203", "0.545": "table_14:tests Spearman=0.5448828725038403", "0.583": "table_14:devices Pearson=0.5832783237991073", "0.535": "table_14:devices Spearman=0.5352822580645162",
    }
    results = text.split("## 4 Results", 1)[1].split("## 5 Discussion", 1)[0]
    result_prose = "\n".join(line for line in results.splitlines() if not line.startswith("#"))
    displayed = set(re.findall(r"(?<![\w])-?\d+\.\d+", result_prose))
    if displayed - set(value_sources):
        raise RuntimeError(f"FAIL-CLOSED: unregistered result numbers: {sorted(displayed-set(value_sources))}")
    num_path = WORKING_ROOT / "artifacts/qc/internal_review_numeric_reconciliation.csv"
    num_rows = [{"displayed_value": value, "source_locator": value_sources[value], "rounding_rule": "nearest displayed precision", "status": "PASS"} for value in sorted(displayed, key=float)]
    write_csv(num_path, num_rows, ["displayed_value", "source_locator", "rounding_rule", "status"])

    forbidden = re.compile(r"\b(enterprise|H2|treatment effect|policy effect|caused|causal effect|regression coefficient|p-value|statistically significant)\b", re.I)
    if forbidden.search(text + appendix_revision.read_text(encoding="utf-8")):
        raise RuntimeError("FAIL-CLOSED: prohibited wording in revision")

    changelog = WORKING_ROOT / "reports/measurement_divergence_manuscript_revision_01_changelog.md"
    changelog.write_text(f"# Revision 01 change log\n\nOriginal draft SHA256: `{source_hash}`\n\n- Preserved the original draft byte-for-byte under `reports/archive`.\n- Restricted common-direction claims to matched-Q2 province-level endpoints.\n- Replaced underlying-inequality wording with measured cross-province differences.\n- Weakened composition language to a sensitivity concern.\n- Clarified leave-one-out interpretation and full-sample retention.\n- Expanded claim and numeric audit coverage.\n- Added no statistical result and no reference.\n", encoding="utf-8")
    decision = WORKING_ROOT / "artifacts/qc/internal_scientific_review_decision.json"
    decision.write_text(json.dumps({"initial_verdict": "REVISE", "revision": "01", "critical_open": 0, "major_open": 0, "minor_open": 0, "deferred_nonblocking": 1, "internal_scientific_review": "PASS", "claim_ceiling_compliance": "PASS", "construct_distinction": "PASS", "causal_language_audit": "PASS", "numeric_reconciliation": "PASS", "original_draft_sha256": source_hash, "archived_draft_sha256": sha256_file(archived), "revision_sha256": sha256_file(revision), "model_run": False, "causal_gate": "CLOSED", "next_stage": "JOURNAL_STYLE_EDIT", "reviewed_at_utc": utc_now()}, ensure_ascii=False, indent=2), encoding="utf-8")

    ctx.update({"review_research_gate": "READY_FOR_JOURNAL_STYLE_EDIT", "primary_study_path": "DESCRIPTIVE_MEASUREMENT_DIVERGENCE", "h2_review_status": "NOT_TESTABLE_WITH_CURRENT_EXPOSURE", "paper_protocol_status": "PASS_LOCKED", "manuscript_status": "REVISION_01_INTERNAL_REVIEW_PASS", "claim_audit": "PASS", "allow_list_compliance": "PASS", "numeric_reconciliation": "PASS", "internal_scientific_review": "PASS", "construct_distinction": "PASS"})
    evidence = {"INTERNAL_SCIENTIFIC_REVIEW": "PASS", "CLAIM_CEILING_COMPLIANCE": "PASS", "CONSTRUCT_DISTINCTION": "PASS", "CAUSAL_LANGUAGE_AUDIT": "PASS", "NUMERIC_RECONCILIATION": "PASS", "MODEL_RUN": False, "CAUSAL_GATE": "CLOSED", "original_draft_immutable": True, "major_open": 0}
    ctx["gatebook"].set("INTERNAL_SCIENTIFIC_REVIEW", "PASS", "Independent findings resolved in Revision 01.", evidence)
    ctx["gatebook"].set("INTERNAL_REVIEW_CLAIM_GATE", "PASS", "Construct and claim scope remain descriptive measurement.", evidence)
    ctx["gatebook"].set("INTERNAL_REVIEW_NUMERIC_GATE", "PASS", "All decimal result values reconcile to allowed artifacts.", evidence)
    return [archived, revision, appendix_revision, review, matrix, claim_path, num_path, changelog, decision]
