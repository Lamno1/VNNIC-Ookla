# Next safe action

Run a separate panel-construction sprint that:

1. builds the primary V05.05 fact only from `data/reference/nso_official_snapshot_20260913/nso_official_snapshot_long.parquet`;
2. builds annual VNNIC FTTH medians for April–December 2021–2024 without using `value` as a weight;
3. starts from an explicit 63 × 4 skeleton and records every 1:1 merge;
4. keeps gross entry intensity absent unless its universe compatibility is documented;
5. stops before descriptive/model stages until the new panel passes G6–G7.

Suggested command after implementing that bounded stage:

```powershell
python CONNECTIVITY_ENTERPRISE_STUDY\run_pipeline.py --stage panel
python CONNECTIVITY_ENTERPRISE_STUDY\validate_project.py
```

Do not reopen the Decision 2269 causal route.
