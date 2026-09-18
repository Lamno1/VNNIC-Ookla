# VNNIC-Ookla Repository

Data-acquisition and analysis code supporting *"Common Direction, Divergent Rankings: A Multi-Level Comparison of VNNIC and Ookla Broadband Measurements in Vietnam, 2021–2024."* This repository backs the manuscript's Data Availability statement: the primary analytical dataset and analysis scripts referenced there live under `src/connectivity_enterprise/`, and the scripts that acquire the two raw sources live under `OOKLA/` and `VNNIC/`.

Current claim ceiling: `ASSOCIATIONAL`.

```text
CAUSAL_GATE = CLOSED
DECISION_2269_GATE = FAIL_PRIMARY_ROUTE
```

## Repository structure

```
VNNIC-Ookla/
├── OOKLA/
│   └── CODE/       # Ookla schema-registration script
├── VNNIC/
│   └── CODE/       # VNNIC download and crosswalk/audit scripts
└── src/connectivity_enterprise/
    └── stages/     # Descriptive analysis, cross-source validation, figures/tables
```

`OOKLA/LOGS/`, `OOKLA/RAW/`, `VNNIC/LOGS/`, `VNNIC/RAW/`, and `VNNIC/DERIVED/` are produced locally by running the scripts below and are not tracked in Git (see `.gitignore`).

## Data acquisition (`OOKLA/`, `VNNIC/`)

Actual raw and derived data files are not pushed to this repository, due to GitHub storage limits and the sensitivity of some source data. They are reproduced locally with the following scripts:

### Step 1: Download raw VNNIC data
```bash
python VNNIC/CODE/download_vnnic.py
```
Connects to the public VNNIC Internet Atlas API, downloads the raw monthly series (2019–2026), and writes it to `VNNIC/RAW/` with a log in `VNNIC/LOGS/`.

### Step 2: Build the VNNIC derived panel
```bash
python VNNIC/CODE/attach_crosswalk_audit_panel.py
```
Attaches the province crosswalk and runs consistency/audit checks, writing the cleaned panel to `VNNIC/DERIVED/`.

### Step 3: Register the Ookla schema
```bash
python OOKLA/CODE/build_ookla_schema_registry.py
```
Builds the schema registry used to validate the Ookla Open Data quarterly tile files referenced by the analysis pipeline.

## Analysis pipeline (`src/connectivity_enterprise/`)

This is the code that produces the paper's reported statistics, tables, and figures: dispersion measures (Table 1/4), cross-source Spearman rank and change-rank correlations with 95% confidence intervals (Tables 4/6/7, Figures 4–6), robustness diagnostics (leave-one-province-out, aggregation sensitivity), and all VNNIC/Ookla comparison figures.

### Safety

All existing source roots under `D:\Q1_RESEARCH` are read-only. Every generated file is written under this project directory. Credential-like files are excluded and must never be opened, copied, hashed, logged, or released.

### Run

From `D:\Q1_RESEARCH`:

```powershell
python CONNECTIVITY_ENTERPRISE_STUDY\run_pipeline.py --stage all
python CONNECTIVITY_ENTERPRISE_STUDY\validate_project.py
```

At the current checkpoint, `--stage all` performs the safe structural and descriptive stages and records semantic blockers; it does not run models. The bounded Ookla validation pilot (Spearman rank/change-rank correlations against VNNIC) runs under the explicit `--stage ookla-pilot` option.

### Frozen protocol

The authoritative protocol is `protocol/research_protocol.md`. Its initial frozen SHA256 is recorded in `protocol/protocol_lock.json`. Any change requires an entry in `protocol/plan_mutations.md`.

### Current expected state

- G0 security: expected PASS.
- G1 provenance: expected WARN until NSO/VNNIC primary provenance is complete.
- G2 semantics: expected FAIL until authoritative definitions and units are verified.
- G3 legacy-63 geography: expected PASS.
- G4 primary FTTH structural coverage: tested independently of semantic admissibility.
- Model construction: blocked while G2 is not PASS.
