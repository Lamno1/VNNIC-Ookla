"""Main spatial evaluation; specification in SPATIAL_MAIN_ADDENDUM.md. Reuses the pilot engine unchanged."""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_v] = '1'
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import multiprocessing as mp
import sys
import time

import numpy as np
import pandas as pd

import spatial_pilot as s

HERE = Path(__file__).resolve().parent
CHUNK = 250
REFERENCE = int(os.environ.get("SPATIAL_REF", "20000"))
_STATE = {}


def configurations():
    cfg = []
    for g in (0, 1):
        for strength in (0., .3, .6, .85):
            for rounded in ([False, True] if g == 0 and strength in (0., .85) else [False]):
                cfg.append(dict(name=f'sym_g{g}_rho{strength}_rounded{rounded}', graph=g, strengths=(strength,)*3,
                                rounded=rounded, symmetric=True))
    for g in (0, 1):
        for sv, so in ((0., .85), (.85, 0.)):
            cfg.append(dict(name=f'diff_g{g}_V{sv}_O{so}', graph=g, strengths=(sv, so, .6), rounded=False, symmetric=False))
    for i, c in enumerate(cfg):
        c['id'] = i
    return cfg


def matched_configurations():
    cfg = []
    for g in (0, 1):
        for xs, label in ((.32, 'DTI'), (.71, 'NSO'), (.74, 'HH')):
            cfg.append(dict(name=f'matched_g{g}_V0.0_O0.81_X{xs}_{label}', graph=g, strengths=(0., .81, xs), rounded=False, symmetric=False))
    for i, c in enumerate(cfg):
        c['id'] = 14 + i
    return cfg


def init():
    graphs, groups, multipliers, geo = s.geometry()
    _STATE.update(graphs=graphs, groups=groups, multipliers=multipliers, geo=geo, factors={})


def factor(graph, strength):
    key = (graph, strength)
    if key not in _STATE['factors']:
        _STATE['factors'][key] = s.spatial_factor(_STATE['graphs'][graph], strength)
    return _STATE['factors'][key]


def draw(rng, cfg):
    channel = np.linalg.cholesky(np.array([[1, .45, .25], [.45, 1, .25], [.25, .25, 1]]))
    t = np.arange(16)
    temporal = np.linalg.cholesky(.7 ** np.abs(t[:, None] - t[None, :]))
    z = rng.normal(size=(63, 16, 3)) @ channel.T
    z = np.einsum('tu,iuc->itc', temporal, z)
    out = np.empty_like(z)
    for c in range(3):
        out[:, :, c] = factor(cfg['graph'], cfg['strengths'][c]) @ z[:, :, c]
    return out


def estimate_only(z, rounded):
    pair_list, coeff, _ = s.pairs(z, rounded)
    return s.statistics(pair_list, coeff, np.ones((1, 63)))[0]


def reference_target(cfg):
    rng = s.rng_for(7, 100 + cfg['graph'], cfg['id'])
    est = np.array([estimate_only(draw(rng, cfg), cfg['rounded']) for _ in range(REFERENCE)])
    return est.mean(axis=0), est.std(axis=0, ddof=1) / np.sqrt(REFERENCE)


def reference_task(cfg):
    if not _STATE:
        init()
    m, se = reference_target(cfg)
    return cfg['id'], m.tolist(), se.tolist()


def chunk_task(args):
    cfg, start, stop, b, outdir = args
    if not _STATE:
        init()
    path = Path(outdir) / f"chunk_{cfg['id']:02d}_{start:05d}.csv"
    if path.exists():
        return str(path)
    rows = []
    for sim in range(start, stop):
        z = draw(s.rng_for(1, 100 + cfg['graph'], cfg['id'], sim), cfg)
        recs = s.run_dataset(z, cfg['rounded'], b, 100 + cfg['graph'], cfg['id'], sim, _STATE['groups'], _STATE['multipliers'])
        for r in recs:
            r.update(configuration=cfg['name'], config_id=cfg['id'], simulation=sim, symmetric=cfg['symmetric'])
        rows.extend(recs)
    pd.DataFrame(rows).to_csv(str(path) + '.tmp', index=False)
    os.replace(str(path) + '.tmp', path)
    return str(path)


def summarize(frame, targets, b):
    frame = frame.copy()
    out = []
    names = s.NAMES
    for (cid, method, outcome), g in frame.groupby(['config_id', 'method', 'outcome']):
        j = names.index(outcome)
        t = targets[cid][j]
        valid = g.dropna(subset=['lo', 'hi', 'p_zero'])
        n = len(valid)
        cover = ((valid.lo <= t) & (t <= valid.hi)).astype(float)
        sym = bool(g.symmetric.iloc[0])
        null = sym and outcome != 'L4_log_Q2'
        rej5 = float((valid.p_zero < .05).mean()); rej1 = float((valid.p_zero < .01).mean())
        row = dict(configuration=g.configuration.iloc[0], method=method, outcome=outcome, datasets=len(g), valid_datasets=n,
                   target=t, target_source='model' if sym else 'reference_simulation',
                   coverage=float(cover.mean()), coverage_mcse=float(np.sqrt(cover.mean()*(1-cover.mean())/n)),
                   mean_length=float(valid.length.mean()), mean_bias=float((g.estimate - t).mean()),
                   invalid_bootstrap_draws=int(g.invalid_bootstrap_draws.sum()), mean_tie_fraction_X=float(g.tie_fraction_X.mean()),
                   reject_zero_005=rej5, reject_zero_001=rej1, rejection_is_type_I=bool(null),
                   reject_mcse_005=float(np.sqrt(rej5*(1-rej5)/n)), seconds_mean=float(g.seconds_method_all_four_outcomes.mean()))
        out.append(row)
    return pd.DataFrame(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--simulations', type=int, default=2000)
    parser.add_argument('--bootstrap', type=int, default=1999)
    parser.add_argument('--workers', type=int, default=14)
    parser.add_argument('--tag', default=None)
    parser.add_argument('--set', default='main', choices=['main', 'matched'])
    args = parser.parse_args()
    cfgs = matched_configurations() if args.set == 'matched' else configurations()
    tag = args.tag or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    outdir = HERE / 'spatial_main_runs' / tag
    outdir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    checks = s.checks()
    init()
    config = dict(seed=s.SEED, simulations=args.simulations, bootstrap=args.bootstrap, reference_datasets=REFERENCE,
                  configurations=[{k: v for k, v in c.items()} for c in cfgs], checks=checks,
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  engine_sha256=hashlib.sha256((HERE / 'spatial_pilot.py').read_bytes()).hexdigest(),
                  addendum_sha256=hashlib.sha256((HERE / 'SPATIAL_MAIN_ADDENDUM.md').read_bytes()).hexdigest(),
                  geometry=_STATE['geo'], python=sys.version)
    (outdir / 'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    with mp.Pool(args.workers, initializer=init) as pool:
        asym = [c for c in cfgs if not c['symmetric']]
        ref = {cid: (m, se) for cid, m, se in pool.map(reference_task, asym)}
        print('reference targets done', round(time.perf_counter() - start), 's', flush=True)
        tasks = [(c, a, min(a + CHUNK, args.simulations), args.bootstrap, str(outdir))
                 for c in cfgs for a in range(0, args.simulations, CHUNK)]
        done = 0
        files = []
        for f in pool.imap_unordered(chunk_task, tasks):
            files.append(f); done += 1
            if done % 10 == 0 or done == len(tasks):
                print(f'chunks {done}/{len(tasks)} elapsed {time.perf_counter()-start:.0f}s', flush=True)
    frame = pd.concat([pd.read_csv(f) for f in sorted(files)], ignore_index=True)
    frame.to_csv(outdir / 'replicates.csv', index=False)
    targets = {}
    for c in cfgs:
        if c['symmetric']:
            targets[c['id']] = s.TARGETS.tolist()
        else:
            targets[c['id']] = ref[c['id']][0]
    summary = summarize(frame, targets, args.bootstrap)
    summary.to_csv(outdir / 'summary.csv', index=False)
    reference = [dict(configuration=c['name'], outcome=n, reference_mean=ref[c['id']][0][j], reference_mcse=ref[c['id']][1][j])
                 for c in cfgs if not c['symmetric'] for j, n in enumerate(s.NAMES)]
    pd.DataFrame(reference).to_csv(outdir / 'reference_targets.csv', index=False)
    report = dict(run=str(outdir), configurations=len(cfgs), datasets=int(frame[['config_id', 'simulation']].drop_duplicates().shape[0]),
                  records=len(frame), invalid_bootstrap_draws=int(frame.invalid_bootstrap_draws.sum()),
                  elapsed_seconds=time.perf_counter() - start)
    (outdir / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    mp.freeze_support()
    main()
