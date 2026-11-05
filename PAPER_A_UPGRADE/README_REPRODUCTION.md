# Reproducing the spatial block results

This folder reproduces the spatial block bootstrap, the coverage simulations and the grouping-sensitivity table of the manuscript (Supplementary Note S8, Tables S33 to S35, and the Table S34 counts of groupings that exclude zero). Every path below is relative to this repository; nothing depends on the authors' machine.

## What is and is not reproduced
- Reproduced from the files in this repository: the province and block bootstrap intervals (`results_spatial_block_20261103/intervals.csv`, `intervals_contig.csv`), Table S34 (`table_S34.csv`), the dependence-range and block-extent summaries, the description of the resampling (`resampling_facts.json`), and the coverage simulations behind Table S35.
- Not re-run here: the construction of the province-month and province-quarter tables from the raw sources. The raw VNNIC downloads and the raw Ookla tile archive are not redistributed. The scripts that build the tables from the raw Ookla archive (`build_ookla_*.py`) read it from the folder given by the environment variable `OOKLA_RAW_DIR` (default `OOKLA_RAW/` in the repository root).
- Legacy scripts that still contain a fixed workspace root: `src/connectivity_enterprise/stages/s00_preflight.py`, `s10_ookla_pilot.py`, `tests/unit/test_paths.py` and `validate_project.py`. They belong to the earlier data-acquisition pipeline, are not used by the results above, and were not changed.

## Environment
Python 3.13.2 on Windows 11; packages and versions in `requirements_repro.txt` (`pip install -r PAPER_A_UPGRADE/requirements_repro.txt`). The coverage simulation uses `multiprocessing` (default 14 workers; `--workers N` changes it). Other operating systems have not been tested.

## Start from a fresh checkout

From a terminal in a directory where you want to create the checkout:

```text
git clone --branch analysis-code-vnnic-ookla-2021-2024 --single-branch https://github.com/Lamno1/VNNIC-Ookla.git
cd VNNIC-Ookla
python --version
python -m pip install -r PAPER_A_UPGRADE/requirements_repro.txt
cd PAPER_A_UPGRADE
```

Use the intended Python 3.13 environment for both installation and every command below. The installation command above runs from the repository root; the numbered reproduction commands run from `PAPER_A_UPGRADE/`. If you use a virtual environment, activate it before installing and running. The commands read the included processed inputs; downloading the raw archives or running `src/` is not part of this procedure.

## Inputs (all in the repository)
| File | Content |
|---|---|
| `data/processed/vnnic_q2_validation_2021_2024.parquet`, `data/interim/fact_vnnic_province_month.parquet`, `data/analysis/analysis_panel_2021_2024.parquet` | VNNIC i-Speed province-month values for the 63 provinces, as published on the VNNIC Internet Atlas interface |
| `data/processed/ookla_fixed_q2_adm1_2021_2024.parquet`, `RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet`, `PAPER_A_UPGRADE/data/ookla_province_quarter_ext.parquet` | Ookla Open Data fixed-broadband tiles assigned to provinces and aggregated by quarter |
| `PAPER_A_UPGRADE/data/CANONICAL_ADM1_63.geojson` | the 63-province boundary file used throughout (geoBoundaries ADM1, 2021 release); SHA-256 `c64a07c3fd5d3ca0339a5002983dc76ddd60a0ef88e889522e37ca2408f74400` |
| `PAPER_A_UPGRADE/spatial_block_spec/` | the written specification (hash recorded before the run), amendments 1 to 3 with their hashes, and `region_mapping_6.csv` (six administrative regions, with its source note) |
| `PAPER_A_UPGRADE/results_allq/`, `results_postshift_20261030/`, `results_x18/` | stored results of the earlier analyses; the bootstrap script reproduces them as a gate before it computes anything new |

Check the current terms of Ookla Open Data and of geoBoundaries before reusing the derived tables. The authors have no statement of reuse terms from VNNIC; this is why raw VNNIC response files are not redistributed.

## Steps
Run from `PAPER_A_UPGRADE/`. Each step writes into `results_spatial_block_20261103/`. Reference copies of the reported outputs are in `reference_results/`.

1. Spatial block bootstrap, 12 neighbour blocks and six regions (Table S33).
   `python spatial_block_bootstrap_20261103.py`
   It first reproduces the stored province-bootstrap results; the line `GATE PASSED` must appear (maximum deviation below 1e-9). Then it writes `intervals.csv`, `block_assignments.csv`, `reproduction_gate.csv`, `run_log.json`.
2. Check of the block intervals by a second implementation.
   `python validate_spatial_block_20261103.py`  (writes `validation.json`)
3. Contiguity-constrained blocks with 8, 10, 12, 15 and 20 blocks (Table S34) and the counts.
   `python spatial_block_contiguous_20261103.py`, then `python make_table_s34_20261103.py`
4. Dependence range and block extent (Table S35, first columns).
   `python spatial_range_20261103.py`
5. Description of the resampling (Note S8).
   `python block_resampling_facts_20261103.py`
6. Coverage simulations (long runs; 2,000 datasets in each of six configurations, 1,999 draws).
   `python spatial_block_coverage_20261103.py`  (province, six regions, 12 blocks)
   `python spatial_block_coverage_k_20261103.py`  (province, six regions, 8, 10, 12, 15, 20 blocks)
   then `python summarize_coverage_20261103.py` (writes `coverage_by_k_pooled.csv`, the numbers of Table S35).
   A quick test of the same code: add `--simulations 20 --bootstrap 199 --tag smoke`; the output is not comparable with the reported coverage.
7. Compare with the reported outputs: `python check_reproduction_20261103.py`.

### Success criteria

- Step 1 must print `GATE PASSED`; no failed gate should be ignored.
- Complete all numbered steps for a full reproduction. The short `--tag smoke` simulations only check execution and do not reproduce Table S35.
- Step 7 should print `identical` for all 15 reference files, with no `DIFFERENT` and no `not run` lines. The checker currently allows missing outputs to be labelled `not run` without changing its exit status, so exit code zero alone is not evidence that every step ran.
- Keep the console logs and generated `run_log.json`/`validation.json` when recording a reproduction. The measured times below describe the authors' earlier full clean-copy run, not an estimate that every machine will match.

## Measured run times
Measured on one Windows 11 machine with 14 workers, in a clean copy of the files listed above: steps 1 to 5 about 11 minutes in total (bootstrap 280 s, contiguity-constrained blocks about 6 minutes); coverage simulation of step 6, first script 23 minutes, second script 39 minutes. Every output compared in step 7 was identical to the reference copy.

## Seeds and determinism
Bootstrap seed 20261010 (5,000 replicates; the same draws are used for every statistic and both sources); the block clustering has no random element; the simulation uses fixed root seeds inside `spatial_engine/spatial_main.py`.

## Layout
`paths.py` holds every location; `upg_common.py` the data loaders and statistics; `spatial_engine/` the simulation engine; scripts named `*_20261103.py` produce the results of this folder.
