# Vietnam Connectivity and Enterprise Dynamism Study

Reproducible measurement, descriptive, and associational research pipeline for Vietnam's fixed legacy-63 provinces, 2021–2024.

Current claim ceiling: `ASSOCIATIONAL`.

```text
CAUSAL_GATE = CLOSED
DECISION_2269_GATE = FAIL_PRIMARY_ROUTE
```

## Safety

All existing source roots under `D:\Q1_RESEARCH` are read-only. Every generated file is written under this project directory. Credential-like files are excluded and must never be opened, copied, hashed, logged, or released.

## Run

From `D:\Q1_RESEARCH`:

```powershell
python CONNECTIVITY_ENTERPRISE_STUDY\run_pipeline.py --stage all
python CONNECTIVITY_ENTERPRISE_STUDY\validate_project.py
```

The audit pipeline currently returns exit code 2 by design and records `BLOCKED_BY_SEMANTICS`. The validator must return `PASS_FAIL_CLOSED_COMPLETION`.

At the current checkpoint, `--stage all` performs safe structural stages and records semantic blockers. It does not run models or full Ookla processing. The Ookla pilot will require the explicit `--stage ookla-pilot` option once implemented and gated.

## Frozen protocol

The authoritative protocol is `protocol/research_protocol.md`. Its initial frozen SHA256 is recorded in `protocol/protocol_lock.json`. Any change requires an entry in `protocol/plan_mutations.md`.

## Current expected state

- G0 security: expected PASS.
- G1 provenance: expected WARN until NSO/VNNIC primary provenance is complete.
- G2 semantics: expected FAIL until authoritative definitions and units are verified.
- G3 legacy-63 geography: expected PASS.
- G4 primary FTTH structural coverage: tested independently of semantic admissibility.
- Model construction: blocked while G2 is not PASS.
