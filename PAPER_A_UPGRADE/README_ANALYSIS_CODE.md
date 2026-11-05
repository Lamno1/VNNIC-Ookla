# Analysis scripts: VNNIC i-Speed vs Ookla fixed broadband, 63 provinces, 2021-2024

This folder holds the Python scripts used for the province-level comparison of the manuscript "Common Direction, Window-Dependent Rankings". It contains no manuscript and no reviews. It does contain the processed input tables, the boundary file and the reference outputs that the spatial block results need.

**Start with [`README_REPRODUCTION.md`](README_REPRODUCTION.md)** for the research-facing execution guide and [`RESULTS_MAP.md`](RESULTS_MAP.md) for manuscript-to-output traceability. From the repository root run `python PAPER_A_UPGRADE/reproduce.py --mode tables`, or choose `--mode full --workers 14` for the documented spatial simulations as well. The runner uses a new isolated directory and never seeds generated outputs from reference files.

## Inputs
- Processed tables (province-month VNNIC i-Speed values and province-quarter Ookla aggregates) are in `data/` here and in `../data/`, `../RED_TEAM_DIAGNOSTICS/within_source_reliability/data/`; the 63-province boundary file is `data/CANONICAL_ADM1_63.geojson`. The table of inputs with their sources is in `README_REPRODUCTION.md`.
- Raw VNNIC response files and the raw Ookla tile archive (AWS Open Data registry) are not redistributed. Only the scripts that rebuild the tables from the raw Ookla archive (`build_ookla_*.py`) need it; they read it from the folder in the environment variable `OOKLA_RAW_DIR`.

## Paths
All locations are set in `paths.py` and are relative to this folder, with environment-variable overrides for the raw archives (`OOKLA_RAW_DIR`, `ADM1_GEOJSON`, `DTI_2023_TXT`). The scripts of this folder no longer contain absolute paths of the authors' machine, except the checker `rev14_tools/preflight.py`, which searches other scripts for such strings. The earlier data-acquisition pipeline in `../src/` and `../validate_project.py` still use a fixed workspace root; they are not needed for the results of `README_REPRODUCTION.md`.

## Layout
- `paths.py`: locations of inputs. `upg_common.py`: shared loaders and statistics.
- `run_upgrade.py`, `run_x9.py` ... `run_x18*.py`, `run_gates.py`, `run_q2_anomaly.py`: main analyses (levels, dispersion, rank agreement, change rankings, sensitivity analyses).
- `all_quarter_framework.py`, `allq_levels_rev16.py`: all-quarter framework.
- `halfyear_analysis_*`, `postshift_*`, `common_cells*`, `coverage_*`, `decision_*`: exploratory extensions, each with its `validate_*` check where present.
- `build_ookla_*`, `build_coverage_tiles_*`, `build_external_delta_supplement.py`, `build_figure*`: data construction and figures.
- `rev14_tools/`: regression checks.
- `reproduce.py`: entry point with tables/smoke/full profiles, hash-checked copy of inputs, per-step logs, environment and timing records. `reproduction_manifest.json` enumerates the 54 allowed code/input/specification/reference files. `check_reproduction_20261103.py` performs strict numerical/structural comparison and fails for missing files. `test_reproduction_entrypoint.py` checks failure and isolation contracts.
- Spatial block results (all are in `README_REPRODUCTION.md`): `spatial_block_bootstrap_20261103.py` (12 contiguous blocks and six regions), `validate_spatial_block_20261103.py` (second implementation), `spatial_block_contiguous_20261103.py` (8, 10, 12, 15, 20 blocks), `spatial_range_20261103.py` (dependence range and block extent), `block_resampling_facts_20261103.py` (what a replicate contains), `spatial_block_coverage_20261103.py` and `spatial_block_coverage_k_20261103.py` (coverage simulations, engine in `spatial_engine/`), `summarize_coverage_20261103.py`, `make_table_s34_20261103.py`, `check_reproduction_20261103.py`, with `spatial_block_spec/` (written specification, amendments, six-region mapping) and `reference_results/` (reported outputs).

File names carry internal stage labels (`x9`-`x18`, `revNN`); they are labels of the authors' work sequence, not versions of a package.

## Status
This is research code, not a maintained package. Run the execution-contract tests with `python PAPER_A_UPGRADE/test_reproduction_entrypoint.py` from the repository root. They test missing/different evidence and workspace protection, not scientific validity. The numerical comparison is `check_reproduction_20261103.py`; missing required outputs now fail rather than being skipped. Seed for the province bootstrap: 20261010. Python 3.13.2 and package versions: `requirements_repro.txt`. Full reproduction means the spatial package defined by the guide, not every historical analysis in this folder.
