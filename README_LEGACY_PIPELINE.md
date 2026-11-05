# Historical acquisition and validation pipeline

These are historical instructions, not the entry point for the current manuscript. Start at README.md.

# VNNIC-Ookla Repository

Data-acquisition and analysis code supporting *"Common Direction, Window-Dependent Rankings: A Multi-Level Comparison of VNNIC and Ookla Broadband Measurements in Vietnam, 2021–2024."*

**Current manuscript.** The analyses of the present manuscript, including the spatial block bootstrap, the coverage simulations and Table S34, are in `PAPER_A_UPGRADE/`. They run with relative paths from the files in this repository; start with [`PAPER_A_UPGRADE/README_REPRODUCTION.md`](PAPER_A_UPGRADE/README_REPRODUCTION.md) (environment, inputs, steps in order, run times and a comparison with the reported outputs) and see `PAPER_A_UPGRADE/README_ANALYSIS_CODE.md` for the layout.

**Earlier stage.** The sections below describe the earlier data-acquisition and validation pipeline: the scripts that acquire the two raw sources live under `OOKLA/` and `VNNIC/`, and the earlier descriptive and validation stages under `src/connectivity_enterprise/`. That pipeline keeps a fixed workspace root (`D:\Q1_RESEARCH`) and is not needed to reproduce the results of the current manuscript.

## Legacy pipeline notes

The gates and commands in the remaining sections describe the earlier pipeline, not the reproduction procedure for the current manuscript.

Earlier pipeline claim ceiling: `ASSOCIATIONAL`.

```text
CAUSAL_GATE = CLOSED
DECISION_2269_GATE = FAIL_PRIMARY_ROUTE
```

## Repository structure

```
VNNIC-Ookla/
├── PAPER_A_UPGRADE/  # Current manuscript analyses and reproduction guide
├── data/            # Processed inputs included for reproduction
├── RED_TEAM_DIAGNOSTICS/within_source_reliability/data/  # Quarterly input table
├── OOKLA/
│   └── CODE/       # Ookla schema-registration script
├── VNNIC/
│   └── CODE/       # VNNIC download and crosswalk/audit scripts
└── src/connectivity_enterprise/
    └── stages/     # Descriptive analysis, cross-source validation, figures/tables
```

`OOKLA/LOGS/`, `OOKLA/RAW/`, `VNNIC/LOGS/`, `VNNIC/RAW/`, and `VNNIC/DERIVED/` are produced locally by running the scripts below and are not tracked in Git (see `.gitignore`).

## Data acquisition (`OOKLA/`, `VNNIC/`)

Raw VNNIC responses and the full Ookla tile archive are not redistributed. Processed inputs and reference outputs for the current manuscript are included, as listed in `PAPER_A_UPGRADE/README_REPRODUCTION.md`. The following acquisition commands document the earlier workflow; they are not required by that reproduction guide.

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

This earlier pipeline produced historical descriptive and validation outputs. Its stage labels and table/figure numbers are not the current manuscript numbering. For the current spatial bootstrap, coverage simulations and Table S34, use `PAPER_A_UPGRADE/README_REPRODUCTION.md`.

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
