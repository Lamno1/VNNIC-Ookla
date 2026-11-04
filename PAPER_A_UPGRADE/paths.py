"""Locations of inputs, relative to this folder, with environment-variable overrides for the raw archives.
Nothing here depends on the authors' machine. The raw Ookla archive and the DTI text are only needed by the data-construction
scripts (build_ookla_*.py, run_x16.py), not by the block bootstrap, the coverage simulation or Table S34."""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEO = Path(os.environ.get("ADM1_GEOJSON", HERE / "data" / "CANONICAL_ADM1_63.geojson"))      # geoBoundaries ADM1, 63 provinces
SPEC = HERE / "spatial_block_spec"                                                              # frozen specification and region mapping
ENGINE = HERE / "spatial_engine"                                                                # spatial simulation engine
RAW_OOKLA = Path(os.environ.get("OOKLA_RAW_DIR", ROOT / "OOKLA_RAW"))                         # raw Ookla Open Data tiles (not redistributed)
DTI_2023 = Path(os.environ.get("DTI_2023_TXT", ROOT / "SOURCE_ACQUISITION" / "DTI_2023.txt"))  # optional, descriptive check only
