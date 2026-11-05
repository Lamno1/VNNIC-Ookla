# VNNIC–Ookla: reproducible analysis

Code and processed inputs supporting *Common Direction, Window-Dependent Rankings: A Multi-Level Comparison of VNNIC and Ookla Broadband Measurements in Vietnam, 2021–2024*.

## Start here

**[Complete reproduction guide](PAPER_A_UPGRADE/README_REPRODUCTION.md)** · **[Result-to-script map](PAPER_A_UPGRADE/RESULTS_MAP.md)**

The guide specifies what to run, input/output paths, which manuscript results each output supports, numerical tolerances, failure criteria and run evidence. The tested reference environment is Python 3.13.2 on Windows 11; exact packages are in `PAPER_A_UPGRADE/requirements_repro.txt`.

[Entry-point execution check, 6 November 2026](PAPER_A_UPGRADE/VALIDATION_REPRODUCTION_20261106.md): 13/13 table artifacts reproduced, both reduced simulation paths exercised; full-size coverage simulations were not rerun for that check.

From the repository root, using the intended Python environment:

```text
python -m pip install -r PAPER_A_UPGRADE/requirements_repro.txt
python PAPER_A_UPGRADE/reproduce.py --mode tables
```

The command creates a **new** directory in `reproduction_runs/`, regenerates the spatial bootstrap tables, runs the second-implementation check and compares 13 generated files against immutable references. It does not overwrite repository results. For coverage simulations as well:

```text
python PAPER_A_UPGRADE/reproduce.py --mode full --workers 14
```

Full means the documented **spatial-results package**, not every analysis or raw-data acquisition in the paper. Full mode compares 15 reference files. See the guide for boundaries and run times.

## Repository layout

```text
VNNIC-Ookla/
├── README.md                            # entry point
├── README_LEGACY_PIPELINE.md             # historical acquisition instructions
├── data/                                # deposited processed input tables
├── RED_TEAM_DIAGNOSTICS/
│   └── within_source_reliability/data/   # deposited Ookla quarter table
├── PAPER_A_UPGRADE/
│   ├── README_REPRODUCTION.md            # commands, workflow, evidence
│   ├── RESULTS_MAP.md                    # manuscript ↔ script ↔ output
│   ├── reproduce.py                      # isolated execution entry point
│   ├── reproduction_manifest.json        # input/code/reference checksums
│   ├── requirements_repro.txt            # pinned reference environment
│   ├── data/                            # boundary and extended-quarter input
│   ├── spatial_block_spec/               # specification, amendments, mapping
│   ├── reference_results/               # expected outputs, never run products
│   ├── spatial_engine/                  # simulation implementation
│   └── *_20261103.py                    # individual scientific steps
├── reproduction_runs/                   # new local runs; ignored by Git
└── src/, OOKLA/, VNNIC/                 # earlier acquisition pipeline
```

Raw VNNIC response files and the large Ookla tile archive are not redistributed. The supplied processed inputs support the documented comparison. Source definitions, third-party access terms, nominal uncertainty and same-team replication limits are described in the guide and manuscript. An output match verifies computation from the supplied inputs, not measurement accuracy or causal validity.
