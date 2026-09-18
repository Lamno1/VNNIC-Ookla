# Reproducibility report

Run the bounded panel pipeline from `D:\Q1_RESEARCH`:

```powershell
python CONNECTIVITY_ENTERPRISE_STUDY\run_pipeline.py --stage panel
```

Do not use `--stage all` for the panel sprint. A second panel run must report `PASS_PANEL_READY_FOR_DESCRIPTIVE`, proving stable schemas and analytical values independent of run metadata.

Validate the latest run:

```powershell
python CONNECTIVITY_ENTERPRISE_STUDY\validate_project.py
```

Expected result: `PASS_PANEL_READY_FOR_DESCRIPTIVE`. The validator checks 2,268 locked-window monthly rows, 252 annual connectivity rows, 252 official NSO rows, the 252-row panel, both 1:1 merges, exact PXWeb values, historical-run immutability, effective protocol identity, artifact hashes, and absence of descriptive/model/Ookla outputs.

Verified run: `run_20260913T063323Z`.

This status authorizes only the next descriptive-analysis sprint. `CAUSAL_GATE` remains `CLOSED` and `DECISION_2269_GATE` remains `FAIL_PRIMARY_ROUTE`.
