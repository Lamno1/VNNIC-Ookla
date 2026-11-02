"""Analytical context added after review; not a calibrated null for measured ranks."""
from pathlib import Path
import hashlib
import json
from math import comb
import numpy as np
import pandas as pd
from scipy.stats import hypergeom

HERE=Path(__file__).resolve().parent
OUT=HERE/'decision_stability_20261030'


def main():
    c=pd.read_csv(OUT/'comparisons.csv')
    primary=c[(c.panel=='base')&(c.metric=='log')&(c.axis=='source')&(c.k==10)]
    assert len(primary)==14 and primary.N.eq(63).all()
    n,k=63,10
    pmf=np.array([comb(k,j)*comb(n-k,k-j)/comb(n,k) for j in range(k+1)])
    assert abs(pmf.sum()-1)<1e-14
    expectation=float(np.dot(np.arange(k+1),pmf))
    assert abs(expectation-k*k/n)<1e-14
    assert abs(float(pmf[4:].sum())-hypergeom.sf(3,n,k,k))<1e-14
    assert primary.tied_in_either_pairs.eq(0).all()
    identity_error=float(np.abs(primary.inversion_fraction-(1-primary.kendall_tau_b)/2).max())
    assert identity_error<1e-14
    report=dict(N=n,k=k,uniform_independent_sets_expected_common=k*k/n,
                uniform_independent_sets_expected_replacements=k-k*k/n,
                observed_mean_common_by_period=primary.groupby('period').common_top_mass.mean().to_dict(),
                hypergeometric_tail_at_four=float(pmf[4:].sum()),
                primary_rows=14,primary_tied_pairs=0,kendall_identity_max_error=identity_error,
                status='DESCRIPTIVE_REFERENCE_NOT_A_SPATIALLY_CALIBRATED_TEST',
                warnings=['Uniform independent selection of two fixed-size sets is a mathematical reference, not a fitted model of these data.',
                          'Observed windows overlap; do not test their mean as 14 independent samples.',
                          'An observed mean of 1.143 versus reference 1.587 does not establish below-chance agreement or equivalence to random selection.',
                          'The 0.0439 tail at four is an unadjusted reference probability; do not label a window significant.',
                          'Pair inversion is determined by Kendall tau when there are no ties; it is not separate evidence.',
                          'These are L4 change rankings; the manuscript also reports Kendall for L3 speed levels, a different target.'],
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                comparisons_sha256=hashlib.sha256((OUT/'comparisons.csv').read_bytes()).hexdigest())
    (OUT/'reference_context.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
