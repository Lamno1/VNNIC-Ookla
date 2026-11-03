# Analysis scripts: VNNIC i-Speed vs Ookla fixed broadband, 63 provinces, 2021-2024

This folder holds the Python scripts used for the province-level comparison. It contains code only: no manuscript, no reviews, and no raw or derived data.

## Inputs (not included)
- VNNIC i-Speed province-month values for the fixed series, and Ookla Open Data fixed-broadband tiles (AWS Open Data registry). Raw files are not redistributed here; obtain them from the original providers under their terms.
- A 63-province boundary file (geoBoundaries ADM1, 2021 release), used to assign tile centroids.

## Known limitation
Several scripts contain absolute Windows paths from the authors' machine, for example `D:\Q1_RESEARCH\VNNIC-Ookla\OOKLA\RAW` and `D:\Q1_RESEARCH\GIS_DERIVED\CANONICAL_ADM1_63.geojson`. Edit these to your local locations before running. The scripts were not modified for portability so that they match the versions that produced the reported results.

## Layout
- `upg_common.py`: shared helpers.
- `run_upgrade.py`, `run_x9.py` ... `run_x18*.py`, `run_gates.py`, `run_q2_anomaly.py`: main analyses (levels, dispersion, rank agreement, change rankings, sensitivity analyses).
- `all_quarter_framework.py`, `allq_levels_rev16.py`: all-quarter framework.
- `halfyear_analysis_*`, `postshift_*`, `common_cells*`, `coverage_*`, `decision_*`: exploratory extensions, each with its `validate_*` check where present.
- `build_ookla_*`, `build_coverage_tiles_*`, `build_external_delta_supplement.py`, `build_figure*`: data construction and figures.
- `rev14_tools/`: regression checks.
- `spatial_block_bootstrap_20261103.py`, `spatial_block_coverage_20261103.py`, `validate_spatial_block_20261103.py`: spatial block bootstrap (12 Ward neighbour blocks and six administrative regions), its coverage simulation, and a second-implementation check. These need two inputs that are not in this repository: the six-region mapping table (`region_mapping_6.csv`, built from the General Statistics Office region table) and, for the coverage script, the earlier spatial-simulation engine (`spatial_pilot.py`, `spatial_main.py`). Both are referenced by absolute paths on the authors' machine.
- `spatial_block_contiguous_20261103.py`, `spatial_block_coverage_k_20261103.py`, `spatial_range_20261103.py`: contiguity-constrained blocks with 8, 10, 12, 15 and 20 blocks, the coverage simulation by number of blocks, and the dependence-range (Moran's I by distance band) and block-extent summary. They need the same two inputs that are not in this repository (the six-region mapping table and the earlier spatial-simulation engine).

File names carry internal stage labels (`x9`-`x18`, `revNN`); they are labels of the authors' work sequence, not versions of a package.

## Status
This is research code, not a maintained package. No automated test suite is provided for these scripts. Seed for the province bootstrap: 20261010.
