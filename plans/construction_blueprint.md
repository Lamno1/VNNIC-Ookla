# Construction Blueprint

Mode: direct; no Git/PR workflow.

## Dependency graph

```text
S00 Preflight -> S01 Inventory -> S02 Semantics
                                  |-> S03 Geography
                                  |-> S04 NSO
                                  |-> S05 VNNIC -> S06 Connectivity features
                                  |-> S09 WBES
                                  `-> S10 Ookla pilot
S03 + S04 + S06 -> S07 Panel -> S08 Descriptive -> S11 Association
All stages -> S12 Reporting -> Adversarial review -> Validator
```

## Cold-start phase briefs

| Step | Inputs | Writes | Depends on | Exit gate | Rollback |
|---|---|---|---|---|---|
| S00 | Four readiness/treatment reports; path allow-list | run metadata, protected-path snapshot | none | G0 | Remove only failed run directory |
| S01 | Explicit allow-listed roots and existing manifests | source inventory and lineage seeds | S00 | G1 per source | Regenerate inventory |
| S02 | Official/local documentation | semantic registry and missing-document requests | S01 | G2 | Retain UNVERIFIED state |
| S03 | Frozen canonical GeoJSON and crosswalk | province dimension | S01 | G3 | Quarantine invalid dimension |
| S04 | NSO V05 workbooks | long measures and outcomes | S02,S03 | G5 | Quarantine ambiguous tables |
| S05 | VNNIC raw/derived and manifests | audited monthly fact | S02,S03 | structural G4 | Rebuild from declared inputs |
| S06 | Audited monthly fact | annual connectivity features | S05 | G4 | Remove derived artifact only |
| S07 | Dimension, connectivity, NSO outcomes | 252-row analysis panel | S03,S04,S06 | G6 | Preserve merge audit, quarantine panel |
| S08 | Passed panel | descriptive tables/figures | S07 | lineage validation | Regenerate deterministically |
| S09 | WBES DTA, questionnaires, implementation report | weighted mechanism appendix | S02 | module gate | Suppress unverified concepts |
| S10 | One manifested fixed Ookla quarter | pilot extract/audit | S02,S03 | pilot gate | Delete only pilot outputs |
| S11 | Frozen specification and passed G1–G7 | associational models | S07,S08 | G7/G8 | Mark NOT RUN on any blocker |
| S12 | All safe modules | reports, claim audit, validator evidence | independent completed steps | G9 | Rebuild from inputs |

Parallel work is allowed only for steps with disjoint outputs. The primary process owns integration and gate decisions.

## Adversarial review checklist

- Challenge semantics, units, timing, geography, merge cardinality, sample stability, outliers, reverse causality, common shocks, measurement composition, administrative vintages, silent exclusion, specification selection, and claim language.
- A critical finding must be fixed or retained explicitly as a blocker.

## Plan mutation protocol

Steps may be split, inserted, reordered, skipped, or abandoned only through an appended record in `protocol/plan_mutations.md`. Each record states the reason, dependencies, affected artifacts, gate effect, and whether rebuild is required.
