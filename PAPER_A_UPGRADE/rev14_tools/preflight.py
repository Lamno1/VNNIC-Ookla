"""Preflight for the revision 14 replay. Read-only. Every gate below is a real predicate and the script exits non-zero if any gate fails,
which the frozen scripts do not do (see known_issues_20261022.md). Descriptive checks are printed separately and never counted as gates.

Usage (from PAPER_A_UPGRADE/):  python rev14_tools/preflight.py            # check against rev14_tools/manifest_rev14.json
                                python rev14_tools/preflight.py --make-manifest   # write the manifest from the current files (do this only on a trusted state)
"""
import hashlib, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
PAU = HERE.parent
ROOT = PAU.parent
MANIFEST = Path(sys.argv[sys.argv.index("--manifest") + 1]) if "--manifest" in sys.argv else HERE / "manifest_rev14.json"
CONTRACT = json.loads((HERE / "replay_contract.json").read_text(encoding="utf-8"))
INPUTS = ["data/processed/vnnic_q2_validation_2021_2024.parquet", "data/processed/ookla_fixed_q2_adm1_2021_2024.parquet", "data/interim/fact_vnnic_province_month.parquet",
          "data/analysis/analysis_panel_2021_2024.parquet", "RED_TEAM_DIAGNOSTICS/within_source_reliability/data/ookla_province_quarter.parquet",
          "PAPER_A_UPGRADE/data/ookla_province_quarter_ext.parquet", "PAPER_A_UPGRADE/data/ookla_x9_province_quarter.parquet",
          "PAPER_A_UPGRADE/data/ookla_x18/fixed_2021Q2_tiles.parquet", "PAPER_A_UPGRADE/data/ookla_x18/fixed_2022Q2_tiles.parquet",
          "PAPER_A_UPGRADE/data/ookla_x18/fixed_2023Q2_tiles.parquet", "PAPER_A_UPGRADE/data/ookla_x18/fixed_2024Q2_tiles.parquet",
          "RED_TEAM_DIAGNOSTICS/population_data/population_province_year_2021_2024.csv"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tracked():
    files = [ROOT / p for p in set(INPUTS + CONTRACT['required_files'])]
    files += sorted(PAU.glob("run_*.py")) + sorted(PAU.glob("build_ookla_*.py")) + [PAU / "upg_common.py", PAU / "build_external_delta_supplement.py"]
    files += sorted((PAU / "data" / "external").rglob("*.csv"))
    files += sorted(PAU.glob("results*/*.csv"))
    files += sorted(HERE.glob('*.py')) + [HERE / 'replay_contract.json', PAU / 'build_figures_rev14.py']
    files = sorted(set(files))
    return [f for f in files if f.is_file()] , [f for f in files if not f.is_file()]


def rel(p):
    return str(p.relative_to(ROOT)).replace("\\", "/")


if "--make-manifest" in sys.argv:
    have, missing = tracked()
    if missing:
        print('FAIL missing required files; manifest not written:', [rel(m) for m in missing])
        sys.exit(1)
    MANIFEST.write_text(json.dumps({rel(f): sha(f) for f in have}, indent=0), encoding="utf-8")
    print("manifest written:", len(have), "files; missing (not listed):", [rel(m) for m in missing]); sys.exit(0)

gates, notes = [], []


def gate(name, ok, detail=""):
    gates.append((name, bool(ok), detail))


# G1 fingerprints: every file in the manifest exists and has the recorded hash
man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
have, missing = tracked()
required = {rel(p) for p in have + missing}
unlisted = sorted(required - set(man))
unexpected = sorted(set(man) - required)
unsafe = [k for k in man if not (ROOT / k).resolve().is_relative_to(ROOT.resolve())]
bad = [k for k, v in man.items() if k not in unsafe and (not (ROOT / k).is_file() or sha(ROOT / k) != v)]
gate("G1 manifest exists and is non-empty", len(man) > 0, f"{len(man)} files")
gate('G1 required file inventory is complete', not (missing or unlisted or unexpected or unsafe),
     f'missing files: {[rel(p) for p in missing]}; unlisted: {unlisted}; unexpected: {unexpected}; unsafe: {unsafe}')
gate("G1 every tracked file matches its recorded SHA256", not bad, f"{len(bad)} differ or are missing: {bad[:5]}")
if missing or unlisted or unexpected or unsafe or bad or not man:
    for n, ok, detail in gates:
        print(('PASS ' if ok else 'FAIL ') + n + ' [' + detail + ']')
    sys.exit(1)

# G2 VNNIC province-month fact table
f = pd.read_parquet(ROOT / "data/interim/fact_vnnic_province_month.parquet"); f = f[f.network == "ftth"]
gate("G2 VNNIC fixed: no duplicate province-month keys", f.duplicated(["province_id_legacy63", "month"]).sum() == 0)
gate("G2 VNNIC fixed: 63 provinces in each year 2021-2024", all(f[f.year == y].province_id_legacy63.nunique() == 63 for y in range(2021, 2025)))
gate("G2 VNNIC fixed: download finite and positive 2021-2024", bool(np.isfinite(f[f.year.between(2021, 2024)].download).all() and (f[f.year.between(2021, 2024)].download > 0).all()))
notes.append(f'Published auxiliary field minimum {f[f.year.between(2021, 2024)].value_raw.min()}; interpretation as sample count remains unverified. This is not a sample-size gate.')
notes.append(f"VNNIC fixed 2021-2024: minimum published value {int(f[f.year.between(2021, 2024)].value_raw.min())} (the manuscript reports 33); semantic status {sorted(f.semantic_status.unique())}")

# G3 Ookla Q2 province table
o = pd.read_parquet(ROOT / "data/processed/ookla_fixed_q2_adm1_2021_2024.parquet")
province_ids = set(pd.read_parquet(ROOT / INPUTS[0]).province_id_legacy63)
expected_keys = {(p, y) for p in province_ids for y in range(2021, 2025)}
gate("G3 Ookla Q2: exact 63-province x 2021-2024 grid", len(province_ids) == 63 and len(o) == 252 and set(zip(o.province_id_legacy63, o.year)) == expected_keys)
gate("G3 Ookla Q2: medians finite and positive", bool(np.isfinite(o.ookla_tile_median_download_mbps).all() and (o.ookla_tile_median_download_mbps > 0).all()))
gate("G3 Ookla Q2: at least one observed tile per province-year", bool((o.observed_ookla_tiles >= 1).all()), f"minimum {int(o.observed_ookla_tiles.min())} tiles")
e = pd.read_parquet(PAU / "data/ookla_province_quarter_ext.parquet")
gate("G3 Ookla extension: no duplicate province-quarter keys", e.duplicated(["shapeISO", "year", "quarter"]).sum() == 0)
for y in range(2021, 2025):
    t = pd.read_parquet(PAU / f"data/ookla_x18/fixed_{y}Q2_tiles.parquet")
    gate(f"G3 Ookla tiles {y}Q2: finite positive speed, positive test and device counts", bool(len(t) > 0 and np.isfinite(t.d).all() and (t.d > 0).all() and (t.tests >= 1).all() and (t.devices >= 1).all()), f"{len(t)} tiles")

# G4 the X10 correction is consistent with the placebo table
pl = pd.read_csv(PAU / "results_x10/q7_placebo.csv"); cs = pd.read_csv(PAU / "results_x10/q7_summary_corrected_20261022.csv")
summary = pd.read_csv(PAU / 'results_x10/q7_summary.csv')
ok = len(cs) == 3 and set(cs.family) == {'F1', 'F2', 'F4'} and not cs.family.duplicated().any()
for r in cs.itertuples():
    p = pl[(pl.family == r.family) & pl.valid_placebo]
    source = summary[summary.family == r.family]
    ok &= len(source) == 1 and len(p) > 0 and len(p) == r.m
    if len(source) == 1:
        ok &= abs(float(source.iloc[0].target) - r.target) < 1e-12
    ok &= int((p.mean_delta >= r.target).sum()) == r.n_placebo_ge_target
    ok &= abs((1 + int((p.mean_delta >= r.target).sum())) / (len(p) + 1) - r.empirical_upper_tail_fraction) < 1e-12
gate("G4 corrected X10 tail fractions equal (1 + count at or above target) / (m + 1)", ok)

# descriptive: absolute paths still hard-coded in the scripts (not a gate)
pat = re.compile(r"[A-Za-z]:[\\/][^\"'\s)]*")
for p in sorted(list(PAU.glob("*.py")) + list((ROOT / "src").rglob("*.py"))):
    if p.name.startswith(("make_rev", "build_figures_rev0", "build_figures_rev11")):
        continue
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        for m in pat.findall(line):
            if m.startswith(("D:/Q1", "D:\\Q1")) and not (p.name.startswith("build_figures") or p.name.startswith("build_claims")):
                notes.append(f"hard-coded path {rel(p)}:{i}: {m[:90]} (exists: {Path(m.rstrip('.,;')).exists()})")

for n, ok, d in gates:
    print(("PASS " if ok else "FAIL ") + n + (f"  [{d}]" if d else ""))
print("-- descriptive notes (not gates) --")
for n in notes:
    print(n)
failed = [g for g in gates if not g[1]]
print(f"{len(gates) - len(failed)} of {len(gates)} gates passed")
sys.exit(1 if failed else 0)
