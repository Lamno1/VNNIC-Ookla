# VNNIC--Ookla Repository

Data-acquisition code and selected reproducibility artifacts supporting *Common Direction, Divergent Rankings: A Multi-Level Comparison of VNNIC and Ookla Broadband Measurements in Vietnam, 2021--2024*.

The frozen analysis version cited by the manuscript is commit `0473a09d3d61c49237a0083586e8ce23c2f3c2d6`.

## What is included

The repository contains acquisition and validation scripts under `VNNIC/CODE/` and `OOKLA/CODE/`, the full analysis pipeline under `src/connectivity_enterprise/`, selected processed datasets under `data/`, and tables, figures, companion figure CSV files, manifests, protocols, quality-control artifacts, and tests.

The repository does not redistribute the raw VNNIC response files or the large Ookla tile Parquet archive. These raw files and local logs are excluded by `.gitignore`. Selected processed and validation artifacts are included; therefore, it would be inaccurate to describe all derived data as absent from the repository.

## Raw data and provenance

VNNIC data are retrieved from the public VNNIC Internet Atlas endpoint used by `VNNIC/CODE/download_vnnic.py`. The script preserves raw response bytes and writes SHA256 values to a local manifest and download log. By default, these files are written under `VNNIC_RAW/`, `VNNIC_DERIVED/`, and `VNNIC_LOGS/` at the repository root.

Ookla fixed-broadband data are obtained from the [Ookla Open Data archive](https://registry.opendata.aws/speedtest-global-performance/). The repository does not download the large tile archive automatically. Download the required fixed-broadband Q2 files for 2021--2024, place them under `OOKLA_RAW/fixed/<year>/Q<quarter>/`, and create `OOKLA_RAW/SHA256_manifest.csv` before running `OOKLA/CODE/build_ookla_schema_registry.py`. That script validates an already downloaded archive; it is not an Ookla downloader.

The authoritative input inventory and hashes used for the frozen run are recorded in `artifacts/manifests/declared_inputs.csv` and `artifacts/manifests/source_inventory.csv`. Their `D:\Q1_RESEARCH\...` paths are provenance paths from the original analysis machine and must not be copied literally on another computer.

## Reproduction setup

Use Python 3.11 or newer and install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

The acquisition scripts use the repository root by default. To place raw, derived, and log directories elsewhere, set `VNNIC_OOKLA_ROOT`:

```powershell
$env:VNNIC_OOKLA_ROOT = (Get-Location).Path
```

From the repository root, run the full pipeline with:

```powershell
python run_pipeline.py --stage all
python validate_project.py
```

For only the acquisition and validation scripts:

```powershell
python VNNIC/CODE/download_vnnic.py
python VNNIC/CODE/attach_crosswalk_audit_panel.py
python OOKLA/CODE/build_ookla_schema_registry.py
```

The crosswalk script additionally requires the canonical geometry and province crosswalk specified by the project's source configuration. The full pipeline reads its remaining source paths from `config/sources.yml`.

At the current checkpoint, the full pipeline records semantic blockers and does not run causal models. The study's claim ceiling is descriptive/associational; neither source is treated as ground truth.

## Frozen protocol and limitations

The authoritative protocol is `protocol/research_protocol.md`; its lock and any amendments are recorded under `protocol/`. Re-running the VNNIC downloader may retrieve revised data, so the frozen commit and recorded input manifests should be retained with any reproduction.

## Citation

Please cite the manuscript and the frozen repository commit:

```text
Lamno1. (2026). VNNIC--Ookla: Data acquisition and analysis code supporting the VNNIC and Ookla broadband measurement comparison. GitHub repository, commit 0473a09d3d61c49237a0083586e8ce23c2f3c2d6.
```
