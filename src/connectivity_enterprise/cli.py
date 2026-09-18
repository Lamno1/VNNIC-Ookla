from pathlib import Path
import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone

from .core.gates import GateBook
from .core.logging import configure_logging
from .core.paths import WORKING_ROOT
from .core.provenance import artifact_record, combined_hash, utc_now
from .stages import s00_preflight, s01_inventory, s02_semantics, s03_geography, s04_nso, s05_vnnic, s06_connectivity_features, s07_panel, s08_descriptive, s10_ookla_pilot, s11_measurement_review, s12_paper_protocol, s13_manuscript, s14_internal_review, s15_internal_review_final, s16_journal_edit, s17_latex_conversion


STAGES = {
    "preflight": [s00_preflight],
    "inventory": [s00_preflight, s01_inventory],
    "semantics": [s00_preflight, s01_inventory, s02_semantics],
    "geography": [s00_preflight, s01_inventory, s03_geography],
    "vnnic": [s00_preflight, s01_inventory, s02_semantics, s03_geography, s05_vnnic, s06_connectivity_features],
    "nso": [s00_preflight, s01_inventory, s02_semantics, s03_geography, s04_nso],
    "semantic-rescue": [s00_preflight, s01_inventory, s02_semantics, s03_geography, s04_nso, s05_vnnic],
    "panel": [s00_preflight, s01_inventory, s02_semantics, s03_geography, s04_nso, s05_vnnic, s06_connectivity_features, s07_panel],
    "descriptive": [s00_preflight, s08_descriptive],
    "ookla-pilot": [s00_preflight, s10_ookla_pilot],
    "measurement-review": [s00_preflight, s11_measurement_review],
    "paper-protocol": [s00_preflight, s12_paper_protocol],
    "manuscript": [s00_preflight, s13_manuscript],
    "internal-review": [s00_preflight, s14_internal_review],
    "internal-review-final": [s00_preflight, s15_internal_review_final],
    "journal-edit": [s00_preflight, s16_journal_edit],
    "latex": [s00_preflight, s17_latex_conversion],
    "all": [s00_preflight, s01_inventory, s02_semantics, s03_geography, s04_nso, s05_vnnic, s06_connectivity_features],
}


def make_run_id():
    return "run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=sorted(STAGES), default="all")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)

    run_id = args.run_id or make_run_id()
    if re.fullmatch(r"[A-Za-z0-9_-]+", run_id) is None:
        parser.error("--run-id may contain only letters, digits, underscore, and hyphen")
    runs_root = (WORKING_ROOT / "runs").resolve()
    run_dir = (runs_root / run_id).resolve()
    try:
        run_dir.relative_to(runs_root)
    except ValueError:
        parser.error("--run-id resolves outside the runs directory")
    lock_path = WORKING_ROOT / ".pipeline.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(lock_fd, f"{os.getpid()} {run_id}".encode("utf-8"))
        os.close(lock_fd)
    except FileExistsError:
        raise RuntimeError(f"FAIL-CLOSED: another pipeline run may be active: {lock_path}")
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "logs").mkdir()

    logger = configure_logging(run_dir / "logs/pipeline.log")
    config_files = [p for p in (WORKING_ROOT / "config").rglob("*") if p.is_file()]
    ctx = {
        "run_id": run_id,
        "run_dir": run_dir,
        "config_hash": combined_hash(config_files),
    }
    ctx["gatebook"] = GateBook(run_id, run_dir / "gate_summary.json")

    created = []
    registry_records = []
    lineage_rows = []
    previous_stage_ids = []
    status = "PASS"
    error = None
    try:
        for module in STAGES[args.stage]:
            logger.info("START %s", module.__name__)
            outputs = module.run(ctx)
            stage_ids = []
            for index, output in enumerate(outputs, start=1):
                output = Path(output).resolve()
                artifact_id = f"{module.__name__.split('.')[-1]}_{index:02d}_{output.stem}"
                record = artifact_record(
                    output, artifact_id, module.__name__.split(".")[-1], run_id,
                    previous_stage_ids, ctx["config_hash"], Path(module.__file__),
                )
                registry_records.append(record)
                stage_ids.append(artifact_id)
                for parent_id in previous_stage_ids:
                    lineage_rows.append({"parent_artifact_id": parent_id, "child_artifact_id": artifact_id, "run_id": run_id})
                created.append(str(output))
            previous_stage_ids = stage_ids
            logger.info("DONE %s", module.__name__)
    except Exception as exc:
        status = "FAIL"
        error = repr(exc)
        logger.exception("Pipeline failed")
    if error is None:
        failed = {
            name: gate
            for name, gate in ctx["gatebook"].gates.items()
            if gate["status"] == "FAIL"
        }
        if failed:
            if args.stage == "ookla-pilot" and ctx.get("measurement_classification") in {"NONCONVERGENT_MEASUREMENT", "INSUFFICIENT_MEASUREMENT_COVERAGE"}:
                status = "PASS_FAIL_CLOSED_MEASUREMENT_VALIDATION"
            elif "G2" in failed:
                status = "BLOCKED_BY_SEMANTICS"
            else:
                status = "BLOCKED_BY_FAILED_GATE"
        elif args.stage == "semantic-rescue":
            status = "PASS_SEMANTIC_RESCUE_READY_FOR_PANEL"
        elif args.stage == "panel":
            if ctx["gatebook"].gates.get("G9_REPRODUCIBILITY", {}).get("status") == "PASS":
                status = "PASS_PANEL_READY_FOR_DESCRIPTIVE"
            else:
                status = "PANEL_BUILT_REQUIRES_REPRODUCIBILITY_RERUN"
        elif args.stage == "descriptive":
            if ctx["gatebook"].gates.get("DESCRIPTIVE_REPRODUCIBILITY", {}).get("status") == "PASS":
                status = "PASS_DESCRIPTIVE_READY_FOR_MEASUREMENT_VALIDATION"
            else:
                status = "DESCRIPTIVE_BUILT_REQUIRES_REPRODUCIBILITY_RERUN"
        elif args.stage == "ookla-pilot":
            classification = ctx.get("measurement_classification")
            reproduced = ctx["gatebook"].gates.get("OOKLA_REPRODUCIBILITY", {}).get("status") == "PASS"
            if classification == "CONVERGENT_MEASUREMENT_SUPPORT" and reproduced:
                status = "PASS_OOKLA_READY_FOR_ASSOCIATIONAL_PROTOCOL_REVIEW"
            elif classification == "MIXED_MEASUREMENT_SUPPORT" and reproduced:
                status = "PASS_OOKLA_MIXED_REQUIRES_HUMAN_REVIEW"
            else:
                status = "OOKLA_BUILT_REQUIRES_REPRODUCIBILITY_RERUN"
        elif args.stage == "measurement-review":
            if ctx["gatebook"].gates.get("MEASUREMENT_REVIEW_REPRODUCIBILITY", {}).get("status") == "PASS":
                status = "PASS_MEASUREMENT_REVIEW_ADJUDICATED"
            else:
                status = "MEASUREMENT_REVIEW_REQUIRES_REPRODUCIBILITY_RERUN"
        elif args.stage == "paper-protocol":
            status = "PASS_MEASUREMENT_DIVERGENCE_PROTOCOL_LOCKED"
        elif args.stage == "manuscript":
            status = "PASS_MANUSCRIPT_DRAFT_COMPLETE"
        elif args.stage == "internal-review":
            status = "PASS_INTERNAL_SCIENTIFIC_REVIEW"
        elif args.stage == "internal-review-final":
            status = "PASS_INTERNAL_SCIENTIFIC_REVIEW"
        elif args.stage == "journal-edit":
            status = "PASS_JOURNAL_STYLE_EDIT"
        elif args.stage == "latex":
            status = "PASS_LATEX_CONVERSION"

    registry_path = run_dir / "artifact_registry.csv"
    if registry_records:
        with open(registry_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(registry_records[0]))
            writer.writeheader()
            writer.writerows(registry_records)
    lineage_path = run_dir / "lineage_edges.csv"
    with open(lineage_path, "w", newline="", encoding="utf-8-sig") as f:
        fields = ["parent_artifact_id", "child_artifact_id", "run_id"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(lineage_rows)

    summary = {
        "run_id": run_id,
        "requested_stage": args.stage,
        "status": status,
        "error": error,
        "config_hash": ctx["config_hash"],
        "created_artifacts": created,
        "artifact_registry": str(registry_path),
        "lineage_edges": str(lineage_path),
        "causal_gate": "CLOSED",
        "decision_2269_gate": "FAIL_PRIMARY_ROUTE",
        "research_gate": (
            "READY_FOR_DESCRIPTIVE_ANALYSIS" if status == "PASS_PANEL_READY_FOR_DESCRIPTIVE"
            else ctx.get("review_research_gate") if args.stage in {"measurement-review", "paper-protocol", "manuscript", "internal-review", "internal-review-final", "journal-edit", "latex"} and ctx.get("review_research_gate")
            else "READY_FOR_ASSOCIATIONAL_PROTOCOL_REVIEW" if status == "PASS_OOKLA_READY_FOR_ASSOCIATIONAL_PROTOCOL_REVIEW"
            else "BLOCKED_PENDING_MEASUREMENT_DECISION" if status == "PASS_OOKLA_MIXED_REQUIRES_HUMAN_REVIEW"
            else "MEASUREMENT_REPRODUCIBILITY_CHECK_PENDING" if status == "OOKLA_BUILT_REQUIRES_REPRODUCIBILITY_RERUN"
            else "READY_FOR_MEASUREMENT_VALIDATION" if status == "PASS_DESCRIPTIVE_READY_FOR_MEASUREMENT_VALIDATION"
            else "DESCRIPTIVE_REPRODUCIBILITY_CHECK_PENDING" if status == "DESCRIPTIVE_BUILT_REQUIRES_REPRODUCIBILITY_RERUN"
            else "READY_FOR_PANEL_CONSTRUCTION" if status == "PASS_SEMANTIC_RESCUE_READY_FOR_PANEL"
            else "PANEL_REPRODUCIBILITY_CHECK_PENDING" if status == "PANEL_BUILT_REQUIRES_REPRODUCIBILITY_RERUN"
            else "BLOCKED_BY_PANEL_CONSTRUCTION" if args.stage == "panel" and status == "FAIL"
            else "BLOCKED_BY_SEMANTICS"
        ),
        "analysis_panel_created": args.stage in {"descriptive", "ookla-pilot", "measurement-review", "paper-protocol", "manuscript", "internal-review", "internal-review-final", "journal-edit", "latex"} or status in {"PASS_PANEL_READY_FOR_DESCRIPTIVE", "PANEL_BUILT_REQUIRES_REPRODUCIBILITY_RERUN"},
        "descriptive_analysis_run": args.stage in {"descriptive", "ookla-pilot", "measurement-review", "paper-protocol", "manuscript", "internal-review", "internal-review-final", "journal-edit", "latex"},
        "model_run": False,
        "h2_status": ctx.get("h2_review_status") if args.stage in {"measurement-review", "paper-protocol", "manuscript", "internal-review", "internal-review-final", "journal-edit", "latex"} else "REGISTERED_NOT_TESTED" if args.stage in {"descriptive", "ookla-pilot"} else None,
        "next_stage": (
            "BOUNDED_OOKLA_VALIDATION_PILOT" if status == "PASS_DESCRIPTIVE_READY_FOR_MEASUREMENT_VALIDATION"
            else "ASSOCIATIONAL_PROTOCOL_REVIEW" if status == "PASS_OOKLA_READY_FOR_ASSOCIATIONAL_PROTOCOL_REVIEW"
            else "HUMAN_MEASUREMENT_REVIEW" if status == "PASS_OOKLA_MIXED_REQUIRES_HUMAN_REVIEW"
            else "EXPOSURE_REDESIGN" if status == "PASS_FAIL_CLOSED_MEASUREMENT_VALIDATION"
            else "INTERNAL_SCIENTIFIC_REVIEW" if status == "PASS_MANUSCRIPT_DRAFT_COMPLETE"
            else "JOURNAL_STYLE_EDIT" if status == "PASS_INTERNAL_SCIENTIFIC_REVIEW"
            else "LATEX_CONVERSION" if status == "PASS_JOURNAL_STYLE_EDIT"
            else "TARGET_JOURNAL_SELECTION" if status == "PASS_LATEX_CONVERSION"
            else None
        ),
        "measurement_validation_classification": ctx.get("measurement_classification"),
        "ch3_status": ctx.get("ch3_status"),
        "measurement_decision": ctx.get("measurement_decision"),
        "stage_b_status": ctx.get("stage_b_status"),
        "enterprise_outcome_read": False if args.stage in {"measurement-review", "paper-protocol", "manuscript", "internal-review", "internal-review-final", "journal-edit", "latex"} else None,
        "primary_study_path": ctx.get("primary_study_path"),
        "paper_protocol_status": ctx.get("paper_protocol_status"),
        "manuscript_status": ctx.get("manuscript_status"),
        "claim_audit": ctx.get("claim_audit"),
        "allow_list_compliance": ctx.get("allow_list_compliance"),
        "numeric_reconciliation": ctx.get("numeric_reconciliation"),
        "internal_scientific_review": ctx.get("internal_scientific_review"),
        "construct_distinction": ctx.get("construct_distinction"),
        "completed_at_utc": utc_now(),
    }
    (run_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
    return 0 if status in {"PASS", "PASS_SEMANTIC_RESCUE_READY_FOR_PANEL", "PASS_PANEL_READY_FOR_DESCRIPTIVE", "PANEL_BUILT_REQUIRES_REPRODUCIBILITY_RERUN", "PASS_DESCRIPTIVE_READY_FOR_MEASUREMENT_VALIDATION", "DESCRIPTIVE_BUILT_REQUIRES_REPRODUCIBILITY_RERUN", "PASS_OOKLA_READY_FOR_ASSOCIATIONAL_PROTOCOL_REVIEW", "PASS_OOKLA_MIXED_REQUIRES_HUMAN_REVIEW", "OOKLA_BUILT_REQUIRES_REPRODUCIBILITY_RERUN", "PASS_FAIL_CLOSED_MEASUREMENT_VALIDATION", "PASS_MEASUREMENT_REVIEW_ADJUDICATED", "MEASUREMENT_REVIEW_REQUIRES_REPRODUCIBILITY_RERUN", "PASS_MEASUREMENT_DIVERGENCE_PROTOCOL_LOCKED", "PASS_MANUSCRIPT_DRAFT_COMPLETE", "PASS_INTERNAL_SCIENTIFIC_REVIEW", "PASS_JOURNAL_STYLE_EDIT", "PASS_LATEX_CONVERSION"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
