"""Compare the files written by the reproduction steps with the reported outputs in reference_results/ (tolerance 1e-9 for numbers).
Files that have not been produced yet are reported as 'not run'."""
import json, sys
import numpy as np, pandas as pd
from paths import HERE

NEW, REF = HERE / "results_spatial_block_20261103", HERE / "reference_results"
TOL = 1e-9
bad = 0
for ref in sorted(REF.iterdir()):
    new = NEW / ref.name
    if not new.exists():
        print("not run  ", ref.name); continue
    if ref.suffix == ".csv":
        a, b = pd.read_csv(ref), pd.read_csv(new)
        ok = a.shape == b.shape and list(a.columns) == list(b.columns)
        if ok:
            for c in a.columns:
                if np.issubdtype(a[c].dtype, np.number):
                    ok &= bool(np.allclose(a[c].to_numpy(float), b[c].to_numpy(float), rtol=0, atol=TOL, equal_nan=True))
                else:
                    ok &= bool((a[c].astype(str) == b[c].astype(str)).all())
    else:
        ok = json.loads(ref.read_text(encoding="utf-8")) == json.loads(new.read_text(encoding="utf-8"))
    print("identical" if ok else "DIFFERENT", ref.name); bad += (not ok)
sys.exit(1 if bad else 0)
