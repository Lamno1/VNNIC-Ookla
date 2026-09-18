from pathlib import Path
import pytest

from connectivity_enterprise.core.paths import WORKING_ROOT, assert_output_path


def test_output_root_accepts_project_path():
    assert assert_output_path(WORKING_ROOT / "artifacts" / "x.txt").is_relative_to(WORKING_ROOT)


def test_output_root_rejects_external_path():
    with pytest.raises(RuntimeError):
        assert_output_path(Path(r"D:\Q1_RESEARCH\VNNIC_RAW\x.txt"))
