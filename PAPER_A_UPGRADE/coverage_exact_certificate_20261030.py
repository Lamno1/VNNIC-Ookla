"""Exact rational certificate for the shared growth interval, using tile speeds."""
from pathlib import Path
from fractions import Fraction
import hashlib,json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
CACHE=HERE/'data/coverage_tiles_canonical_20261030'
OUT=HERE/'coverage_identification_20261030'


def median_half_kbps_bounds(values,n):
    # Each published observed value is an integer kbps. The ordinary median's
    # numerator below is measured in half-kbps units, with no floating division.
    exact=values.to_numpy()*1000
    assert np.allclose(exact,np.rint(exact),atol=1e-7,rtol=0)
    x=np.sort(np.rint(exact).astype(np.int64));missing=n-len(x)
    central=[(n+1)//2,n//2+1]
    lower=sum(0 if k<=missing else int(x[k-missing-1]) for k in central)
    upper=None if any(k>len(x) for k in central) else sum(int(x[k-1]) for k in central)
    return lower,upper


def main():
    data={}
    for y in (2021,2023,2024):
        for q in range(1,5):
            f=pd.read_parquet(CACHE/f'{y}Q{q}.parquet');f=f[f.shapeISO!='']
            data[y,q]={s:g.set_index('quadkey').download_mbps for s,g in f.groupby('shapeISO')}
    rows=[]
    for start in (2021,2023):
        for q in range(1,5):
            lower={};upper={}
            for iso,a in data[start,q].items():
                e=data[2024,q][iso];n=len(set(a.index)|set(e.index))
                al,au=median_half_kbps_bounds(a,n);bl,bu=median_half_kbps_bounds(e,n)
                lower[iso]=Fraction(0) if au is None else Fraction(bl,au)
                upper[iso]=None if bu is None or al==0 else Fraction(bu,al)
            limiting_lower=max(lower,key=lower.get)
            finite_upper={iso:v for iso,v in upper.items() if v is not None}
            limiting_upper=min(finite_upper,key=finite_upper.get)
            lo=lower[limiting_lower];hi=finite_upper[limiting_upper]
            assert lo<hi # Exact integer cross multiplication through Fraction.
            rows.append(dict(period=f'{start}-2024',quarter=q,
                       growth_lower_numerator=lo.numerator,growth_lower_denominator=lo.denominator,
                       growth_upper_numerator=hi.numerator,growth_upper_denominator=hi.denominator,
                       growth_lower_decimal=float(lo),growth_upper_decimal=float(hi),
                       lower_limiting_province=limiting_lower,upper_limiting_province=limiting_upper,
                       exact_strict_shared_interval=True,
                       integer_cross_product_margin=hi.numerator*lo.denominator-lo.numerator*hi.denominator))
    pd.DataFrame(rows).to_csv(OUT/'exact_shared_interval_certificate.csv',index=False)
    report=dict(status='EXACT_RATIONAL_SHARED_INTERVAL_VERIFIED',configurations=len(rows),
                scope='Median endpoints recomputed from saved integer-kbps tile values. Fraction comparisons are exact.',
                all_permutations_claim_conditional_on_continuous_missing_value_model=True,
                not_a_simultaneous_completion_claim_for_all_configurations=True,
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'exact_certificate_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=='__main__':main()
