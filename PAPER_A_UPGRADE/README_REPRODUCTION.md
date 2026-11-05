# Reproduce and inspect the spatial-results package

This guide is an execution contract for Supplementary Note S8, Tables S33–S35 and the associated main-text sensitivity statements. It tells a reader which files are inputs, which are expected references, which are freshly generated outputs, and how to verify a run.

## 1. Scope before running

Recomputed from deposited province-level inputs: paired province/block bootstrap intervals, contiguous-group sensitivity, Table S34, dependence-range and block-size summaries, second-implementation checks and, in full mode, the two coverage simulations. The same seeds and scientific kernels as the reported results are used.

Not claimed by this procedure: downloading raw VNNIC responses or the full Ookla archive, reconstructing every original data-extraction decision, regenerating every earlier L2/external-indicator analysis, or rebuilding the manuscript PDFs. The stored earlier estimates used by the bootstrap gate are explicitly baseline inputs, not outputs counted as freshly generated. [RESULTS_MAP.md](RESULTS_MAP.md) records these boundaries by result.

## 2. Environment and installation

Recorded environment: **Python 3.13.2, Windows 11**, packages pinned in `requirements_repro.txt`. The new run records actual versions and any differences. Other operating systems are not yet validated.

```text
git clone --branch analysis-code-vnnic-ookla-2021-2024 --single-branch https://github.com/Lamno1/VNNIC-Ookla.git
cd VNNIC-Ookla
python --version
python -m venv .venv
```

Windows PowerShell, without requiring environment activation:

```powershell
.\.venv\Scripts\python.exe -m pip install -r PAPER_A_UPGRADE/requirements_repro.txt
.\.venv\Scripts\python.exe PAPER_A_UPGRADE/reproduce.py --mode tables --run-dir reproduction_runs/tables_01
```

On an already configured reference environment, use `python` for the same commands. On Unix-like systems the virtual-environment executable is `.venv/bin/python`; those platforms have not been tested by the authors. All entry-point commands in this guide start from the **repository root**. A chosen `--run-dir` must not exist; use a new name for a second run.

## 3. Choose the run you intend to verify

| Mode | Command from repository root | What is actually computed | Success label and reference checks |
|---|---|---|---|
| Tables | `python PAPER_A_UPGRADE/reproduce.py --mode tables` | Original 5,000-draw bootstrap, second implementation, contiguous blocks, S34, range/extent and resampling facts | `passed_tables_only`; 13/13 files. Coverage simulations not run. |
| Smoke | `python PAPER_A_UPGRADE/reproduce.py --mode smoke --workers 8` | Same full table calculations, then both simulation paths at 20 datasets/configuration, 199 resamples and 200 reference datasets | `passed_smoke_not_full_reproduction`; 13/13 table files. Simulation products are diagnostic, not Table S35 evidence. |
| Full spatial package | `python PAPER_A_UPGRADE/reproduce.py --mode full --workers 14` | All tables plus both simulations at 2,000 datasets/configuration, 1,999 resamples and 20,000 reference datasets | `passed_full_spatial_package`; 15/15 files including S35 summaries. |

Print the exact script sequence without running it:

```text
python PAPER_A_UPGRADE/reproduce.py --mode full --plan
```

The scientific table steps retain their original replicate counts in every mode. Therefore smoke is not an instant installation test. The fresh entry-point check on 6 November took approximately 28 minutes including both reduced simulation paths; see [the execution record](VALIDATION_REPRODUCTION_20261106.md). Earlier table steps took about 11 minutes and the two full simulation calls approximately 23 and 39 minutes on the authors' Windows machine. These are measurements under different loads, not a time guarantee. Use the per-step seconds in your own `run.json`.

## 4. What the runner reads and creates

Before any computation the runner verifies 54 files against `reproduction_manifest.json`, then copies only the allowed files into a new workspace. Text hashes normalize Windows CRLF to LF; binary inputs are hashed unchanged. No generated output directory or previous simulation chunk is copied. Environment overrides for external data paths are cleared inside this isolated run.

```text
reproduction_runs/<run-id>/
├── run.json                              # status, versions, commands, exit codes, timing
├── output_manifest.json                  # hashes of freshly generated table products
├── logs/
│   ├── 01_bootstrap.log                  # look for GATE PASSED
│   ├── 02_validate.log                   # independent implementation within same team
│   ├── 03_contiguous.log
│   ├── 04_table_s34.log
│   ├── 05_range.log
│   ├── 06_resampling.log
│   ├── 07_coverage.log                   # smoke/full only
│   ├── 08_coverage_k.log                 # smoke/full only
│   ├── 09_coverage_summary.log           # smoke/full only
│   └── 10_compare.log                    # per-file verdicts
└── workspace/
    ├── data/...                          # copied processed inputs
    ├── RED_TEAM_DIAGNOSTICS/...          # copied quarterly input
    └── PAPER_A_UPGRADE/
        ├── reference_results/            # expected values, separate from generated files
        ├── results_allq/...              # only baseline gate inputs
        ├── results_postshift_20261030/... # only baseline gate inputs
        ├── results_x18/...               # only baseline gate inputs
        ├── comparison.json               # machine-readable final comparison
        ├── results_spatial_block_20261103/# FRESH table outputs and bootstrap draws
        └── spatial_engine/
            └── spatial_main_runs/
                ├── reviewer_blocks/      # FRESH first simulation
                └── reviewer_blocks_k/    # FRESH by-block-count simulation
```

The two generated directories above must be absent initially. A second invocation targeting the same run directory is rejected, rather than silently accepting cached simulation chunks. Repository `reference_results/` and previously deposited result files remain untouched.

## 5. Exact steps, dependencies and manuscript links

Individual commands below run from the isolated `workspace/PAPER_A_UPGRADE/` directory, using the same Python executable. The entry point runs them in this order automatically.

| Step / script | Required inputs | Generated files under `results_spatial_block_20261103/` | What to inspect |
|---|---|---|---|
| 1 `spatial_block_bootstrap_20261103.py` | Processed VNNIC/Ookla, boundary, region mapping and the five baseline gate CSVs | `intervals.csv`, `block_assignments.csv`, `block_sizes.csv`, `reproduction_gate.csv`, `draws_*.csv`, `run_log.json` | S33 and paired-province reference intervals. Gate deviation must be below 1e-9 before block calculations. `neigh12` is the earlier Ward grouping; contiguous primary/sensitivity groupings are in step 3. |
| 2 `validate_spatial_block_20261103.py` | Step 1 assignments/intervals and processed data | `validation.json` | Same-team second implementation of eight statistics × two rules; `passed` must be true. |
| 3 `spatial_block_contiguous_20261103.py` | Step 1 intervals, processed data, boundary, amendment 2 | `intervals_contig.csv`, `block_assignments_contig.csv`, `block_sizes_contig.csv`, `draws_contig*.csv`, `run_log_contig.json` | S34, contiguous 8/10/12/15/20 groups plus six regions; graph connectivity checks must pass. |
| 4 `make_table_s34_20261103.py` | `intervals_contig.csv` | `table_S34.csv` | S34's displayed estimates, excl/incl labels and count of excluding groupings. |
| 5 `spatial_range_20261103.py` | Processed data and assignments from steps 1/3 | `moran_correlogram.csv`, `moran_correlogram_median.csv`, `dependence_range.json`, `block_extent.csv` | S35 range/extent columns and Note S8 dependence boundary. |
| 6 `block_resampling_facts_20261103.py` | Contiguous block assignments from step 3 | `resampling_facts.json` | Note S8: block sizes, repeated/distinct provinces and equal-probability block draws. |
| 7 `spatial_block_coverage_20261103.py --tag reviewer_blocks` | Step 1 assignments, boundary and simulation engine | Separate engine run directory, `summary.csv`, `reference_targets.csv`, `config.json`, `report.json`, chunks and `replicates.csv` | Simulation of province/six-region/earlier-12 grouping; full defaults 2,000 × 1,999. |
| 8 `spatial_block_coverage_k_20261103.py --tag reviewer_blocks_k` | Steps 1/3 assignments and engine | Separate engine run directory with the same evidence types | Simulation across contiguous block counts; full defaults 2,000 × 1,999. |
| 9 `summarize_coverage_20261103.py reviewer_blocks_k reviewer_blocks` | Engine `summary.csv` files from steps 7/8 | `coverage_by_k_pooled.csv`, `coverage_summary_blocks_vs_province.csv` | S35 coverage columns. Only full-mode summaries may be compared with the published coverage results. The summary's MCSE convention assumes the full run size. |
| 10 `check_reproduction_20261103.py` | Generated outputs and the distinct `reference_results/` | `comparison.json` when `--json-out` is supplied | Every required file must match. Missing, malformed or different files fail. |

## 6. Inputs and provenance

All paths below are relative to the repository root; individual file hashes and roles are in the manifest.

| Input location | Unit / use |
|---|---|
| `data/processed/vnnic_q2_validation_2021_2024.parquet` | Frozen 63-province identifiers and Q2 VNNIC values |
| `data/interim/fact_vnnic_province_month.parquet` | Published monthly VNNIC fixed-series values |
| `data/analysis/analysis_panel_2021_2024.parquet` | Deposited analytical panel |
| `data/processed/ookla_fixed_q2_adm1_2021_2024.parquet` | Q2 province aggregates and alternative summaries |
| `RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet` | All-quarter Ookla province input |
| `PAPER_A_UPGRADE/data/ookla_province_quarter_ext.parquet` | Extended quarter support |
| `PAPER_A_UPGRADE/data/CANONICAL_ADM1_63.geojson` | Historical boundary; geoBoundaries 2021 release, SHA256 c64a07c3fd5d3ca0339a5002983dc76ddd60a0ef88e889522e37ca2408f74400 |
| `PAPER_A_UPGRADE/spatial_block_spec/` | Frozen specifications, amendments and six-region mapping/source note |
| `PAPER_A_UPGRADE/results_allq/{allq_L1_growth,allq_L3_change}.csv`, `results_postshift_20261030/{L4,stability}.csv`, `results_x18/s2_difference.csv` | Earlier stored values read only by the bootstrap reproduction gate; not copied into new generated outputs |

The providers' current terms apply to reused data. The authors do not redistribute raw VNNIC response files or the full Ookla tiles. The documented pipeline reproduces statistics from deposited aggregates; it does not recover undocumented historical VNNIC processing or resolve sample-representation limits.

## 7. Verify your own run

Open `run.json`: status must be the success label for your chosen mode, all step exit codes must be zero and versions must be recorded. Then inspect `logs/01_bootstrap.log` (`GATE PASSED`), `workspace/PAPER_A_UPGRADE/results_spatial_block_20261103/validation.json` (`passed: true`) and `workspace/PAPER_A_UPGRADE/comparison.json` (`passed: true`, 13 or 15 files as declared).

To compare a completed full run again from repository root:

```text
python PAPER_A_UPGRADE/check_reproduction_20261103.py --actual reproduction_runs/<run-id>/workspace/PAPER_A_UPGRADE/results_spatial_block_20261103 --json-out reproduction_runs/<run-id>/recheck.json
```

For a tables-only run, compare the explicit 13 filenames listed in that run's `reference_files_compared` using `--files`. Omitting the two coverage files is allowed only for the declared partial mode. The checker returns nonzero for a missing required file, a shape/column/order difference, a numerical difference beyond absolute tolerance 1e-9 (rtol=0), unequal JSON content or an empty reference selection. NaNs are compared as missing values; JSON is compared structurally. Byte hashes are recorded separately and can differ across platforms despite numerical equivalence.

An existing-file comparison alone does not prove fresh execution. Keep the whole run directory, especially `run.json`, command logs, `comparison.json` and `output_manifest.json`. These provide the execution and artifact evidence. A numerical match does not validate sampling, historical definitions, spatial calibration or scientific generalization.

## 8. Troubleshooting and integrity

- Hash mismatch: use an unmodified checkout of the intended revision. Do not edit expected hashes to force a pass. Investigational modifications require their own disclosed manifest/version.
- Existing run directory: choose a new path; do not delete reference files or reuse simulation chunks.
- Failed step: stop and read its named log. Do not substitute the expected reference file for a missing generated file.
- `missing_output`, `different` or `error`: the comparison failed. A partial mode is labelled partial explicitly.
- Worker/memory limits: lower `--workers`; seeds are tied to configurations and simulation indices, not the process count. Actual run time will change.
- Smoke coverage summaries are not published estimates or correctly sized full-run uncertainty summaries. Use them only to exercise execution paths.

Bootstrap seed 20261010 with 5,000 paired province draws. Simulation root seed 20261024; full numerical defaults are 2,000 datasets/configuration, 1,999 resampling draws and 20,000 reference datasets for asymmetric targets. The original kernels and written specifications retain the modeling assumptions and limitations.
