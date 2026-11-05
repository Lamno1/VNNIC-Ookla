# Execution check of the reproduction entry point

Run completed 6 November 2026 (UTC+7), using Python 3.13.2 on Windows 11 and the pinned package versions in `requirements_repro.txt`. This is a same-team execution check, not an outside replication or a fresh environment installation.

Command from the repository root:

```text
python PAPER_A_UPGRADE/reproduce.py --mode smoke --workers 8 --run-dir reproduction_runs/validation_20261106_smoke_v2
```

Only the 54 declared code, input, specification and reference files were copied. Both generated-output directories were absent at the start. Prior simulation chunks were excluded. The manifest SHA256 for its LF byte representation was `0dbf492722e57f4d6910df076528ea12c2bd5c024fb917cfdd114ddd23aa9426`.

| Step | Exit code | Seconds |
|---|---:|---:|
| Bootstrap, original 5,000 draws | 0 | 350.425 |
| Second implementation, within the same team | 0 | 53.392 |
| Contiguous blocks, original 5,000 draws per grouping | 0 | 1220.803 |
| Table S34 | 0 | 2.520 |
| Spatial dependence range / block extent | 0 | 21.396 |
| Resampling facts | 0 | 4.785 |
| First simulation path, reduced size | 0 | 19.358 |
| Simulation by block count, reduced size | 0 | 21.024 |
| Coverage summary generation, reduced size | 0 | 1.696 |
| Strict output comparison | 0 | 1.569 |

Total subprocess time: 1,696.968 seconds, approximately 28 minutes. Timing depends on machine and load; earlier execution times are not a guarantee.

**Table result:** 13/13 required artifacts matched, with absolute numerical tolerance 1e-9 and structural JSON equality. The second-implementation maximum absolute deviation was 9.71445146547012e-17. Seven execution-contract tests also passed, including missing output, altered numeric input, existing workspace and input-hash failures.

**Simulation boundary:** each of the two reduced runs used six configurations, 20 datasets/configuration, 199 bootstrap draws and 200 reference datasets. Each generated 120 datasets and reported zero invalid bootstrap draws. This verifies execution of both paths. It does not reproduce full-size coverage estimates or establish statistical calibration; the two published coverage summaries are excluded from the 13-file comparison. Full mode requires their separate computation and a 15-file comparison.

The success status was `passed_smoke_not_full_reproduction`. The retained local run contains `run.json`, per-command logs, `comparison.json`, output hashes, configuration records and freshly computed products. Readers generate their own equivalent evidence by running the command above with a new run-directory name. See [README_REPRODUCTION.md](README_REPRODUCTION.md) for the contract and [RESULTS_MAP.md](RESULTS_MAP.md) for manuscript coverage.
