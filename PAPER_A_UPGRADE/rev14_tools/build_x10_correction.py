"""Build the separately versioned correction without altering frozen X10 output."""
import argparse
from pathlib import Path
import pandas as pd


def build(folder):
    folder = Path(folder)
    summary = pd.read_csv(folder/'results_x10/q7_summary.csv')
    placebo = pd.read_csv(folder/'results_x10/q7_placebo.csv')
    if len(summary) != 3 or set(summary.family) != {'F1', 'F2', 'F4'}:
        raise ValueError('Expected exactly F1, F2, F4 in X10 summary')
    rows = []
    for r in summary.itertuples():
        p = placebo[(placebo.family == r.family) & placebo.valid_placebo]
        if len(p) != r.m or not len(p):
            raise ValueError(f'Invalid placebo count for {r.family}')
        n = int((p.mean_delta >= r.target).sum())
        rows.append(dict(family=r.family, target=r.target, m=len(p), n_placebo_ge_target=n,
                         empirical_upper_tail_fraction=(1+n)/(len(p)+1), stored_p_one_sided=r.p_one_sided))
    target = folder/'results_x10/q7_summary_corrected_20261022.csv'
    pd.DataFrame(rows).to_csv(target, index=False)
    print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--analysis-dir', type=Path, required=True)
    build(parser.parse_args().analysis_dir)
