import pandas as pd

from connectivity_enterprise.core.paths import WORKING_ROOT


def test_legacy_dimension_has_63_unique_rows():
    dim = pd.read_parquet(WORKING_ROOT / "data/reference/dim_province_legacy63.parquet")
    assert len(dim) == 63
    assert dim["province_id_legacy63"].nunique() == 63


def test_analysis_panel_has_locked_skeleton_when_released():
    path = WORKING_ROOT / "data/analysis/analysis_panel_2021_2024.parquet"
    if path.exists():
        panel = pd.read_parquet(path)
        assert len(panel) == 252
        assert not panel.duplicated(["province_id_legacy63", "year"]).any()
