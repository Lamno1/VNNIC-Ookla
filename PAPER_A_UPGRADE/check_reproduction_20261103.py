"""Strict output comparison. Missing or different files fail.

This compares files, not their execution history. Use reproduce.py for a run
with initially absent output directories and preserved per-command evidence.
"""
from pathlib import Path
import argparse
import json
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TOL = 1e-9


def compare(actual, reference, names=None):
    refs = sorted(reference.iterdir()) if reference.is_dir() else []
    if names is not None:
        refs = [reference / n for n in names]
    rows = []
    for ref in refs:
        if not ref.is_file():
            rows.append(dict(file=ref.name, status='missing_reference')); continue
        new = actual / ref.name
        if not new.is_file():
            rows.append(dict(file=ref.name, status='missing_output')); continue
        try:
            if ref.suffix == '.csv':
                a, b = pd.read_csv(ref), pd.read_csv(new)
                ok = a.shape == b.shape and list(a.columns) == list(b.columns)
                if ok:
                    for c in a.columns:
                        if pd.api.types.is_numeric_dtype(a[c]):
                            ok = ok and bool(np.allclose(a[c].to_numpy(float), b[c].to_numpy(float), rtol=0, atol=TOL, equal_nan=True))
                        else:
                            ok = ok and bool((a[c].fillna('<NA>').astype(str) == b[c].fillna('<NA>').astype(str)).all())
            elif ref.suffix == '.json':
                ok = json.loads(ref.read_text(encoding='utf-8-sig')) == json.loads(new.read_text(encoding='utf-8-sig'))
            else:
                ok = ref.read_bytes() == new.read_bytes()
            rows.append(dict(file=ref.name, status='identical' if ok else 'different'))
        except Exception as exc:
            rows.append(dict(file=ref.name, status='error', detail=str(exc)))
    return dict(passed=bool(rows) and all(r['status'] == 'identical' for r in rows), tolerance=TOL, files=rows)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--actual', type=Path, default=HERE/'results_spatial_block_20261103')
    p.add_argument('--reference', type=Path, default=HERE/'reference_results')
    p.add_argument('--files', nargs='+', help='Explicit subset for a declared partial reproduction')
    p.add_argument('--json-out', type=Path)
    a = p.parse_args(argv)
    if a.files and any(Path(n).name != n for n in a.files):
        p.error('--files accepts simple filenames only')
    result = compare(a.actual, a.reference, a.files)
    for row in result['files']:
        print(row['status'], row['file'])
    print('PASS' if result['passed'] else 'FAIL', sum(r['status']=='identical' for r in result['files']), '/', len(result['files']))
    if a.json_out:
        a.json_out.parent.mkdir(parents=True, exist_ok=True)
        a.json_out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
