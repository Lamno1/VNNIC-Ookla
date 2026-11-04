"""Code/runtime pilot of spatial inference; never selects a method for the paper."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.metadata
import json
import sys
import time

import numpy as np
import pandas as pd
from scipy.cluster.vq import kmeans2
from scipy.sparse.csgraph import connected_components
from scipy.spatial.distance import cdist
from scipy.stats import spearmanr
from shapely.geometry import shape

HERE = Path(__file__).resolve().parent
SEED = 20261024
NAMES = ['delta', 'q2_first_minus_last', 'mean4_last_minus_first', 'L4_log_Q2']
TARGETS = np.array([0., 0., 0., 6 / np.pi * np.arcsin(.45 / 2)])


def rng_for(*keys):
    return np.random.default_rng(np.random.SeedSequence([SEED, *keys]))


def geometry():
    path = HERE.parent / 'data' / 'CANONICAL_ADM1_63.geojson'   # identical bytes to portable_checks/inputs/provinces.geojson (same SHA-256)
    gj = json.loads(path.read_text(encoding='utf-8'))
    fs = sorted(gj['features'], key=lambda f: f['properties']['shapeISO'])
    assert len(fs) == 63 and len({f['properties']['shapeISO'] for f in fs}) == 63
    polys = [shape(f['geometry']) for f in fs]
    lonlat = np.array([[g.centroid.x, g.centroid.y] for g in polys])
    lon, lat = np.radians(lonlat).T
    xyz = 6371.0088 * np.c_[np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)]
    distances = cdist(xyz, xyz)
    neighbours = np.argsort(distances, axis=1)[:, 1:6]
    adj = np.array([[i != j and a.intersects(b) for j, b in enumerate(polys)] for i, a in enumerate(polys)], dtype=float)
    isolated = np.where(adj.sum(axis=1) == 0)[0]
    repairs = []
    for i in isolated:
        j = neighbours[i, 0]
        adj[i, j] = adj[j, i] = 1
        repairs.append([fs[i]['properties']['shapeISO'], fs[j]['properties']['shapeISO']])
    knn = np.zeros((63, 63))
    for i in range(63):
        knn[i, neighbours[i]] = 1
    knn = np.maximum(knn, knn.T)
    graphs = [adj, knn]
    groups = {}
    xy = np.c_[lonlat[:, 0] * np.cos(np.radians(16)), lonlat[:, 1]]
    for k in (6, 8, 12):
        _, labels = kmeans2(xy, k, minit='++', seed=np.random.default_rng(11))
        groups[k] = [np.flatnonzero(labels == j) for j in range(k)]
        assert all(len(g) for g in groups[k])
    bandwidth = float(np.median(np.sort(distances, axis=1)[:, 5]))
    multipliers = {}
    for factor in (1, 2):
        cov = np.exp(-distances / (factor * bandwidth))
        eigenvalues, vectors = np.linalg.eigh(cov)
        assert eigenvalues.min() > -1e-10
        multipliers[factor] = vectors * np.sqrt(np.maximum(eigenvalues, 0))
    metadata = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'iso_order': [f['properties']['shapeISO'] for f in fs],
                'centroids_lonlat': lonlat.tolist(), 'isolated_repairs': repairs,
                'graphs': [{'name': name, 'edges': int(a.sum()/2), 'components': int(connected_components(a)[0])} for name, a in zip(['adjacency', 'symmetric_knn5'], graphs)],
                'bandwidth_km': bandwidth, 'cluster_sizes': {k: [len(g) for g in members] for k, members in groups.items()},
                'coordinate_rule': 'lon/lat polygon centroids, chord distance in 3D sphere; earlier scaled lon/lat for kmeans'}
    return graphs, groups, multipliers, metadata


def spatial_factor(adjacency, strength):
    w = adjacency / adjacency.sum(axis=1, keepdims=True)
    a = np.linalg.solve(np.eye(len(w)) - strength*w, np.eye(len(w)))
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    cov = a @ a.T
    assert np.linalg.eigvalsh(cov).min() > 0 and np.allclose(np.diag(cov), 1)
    return a


def draw_field(rng, factor):
    channel = np.linalg.cholesky(np.array([[1, .45, .25], [.45, 1, .25], [.25, .25, 1]]))
    t = np.arange(16)
    temporal = np.linalg.cholesky(.7 ** np.abs(t[:, None] - t[None, :]))
    z = rng.normal(size=(63, 16, 3)) @ channel.T
    z = np.einsum('tu,iuc->itc', temporal, z)
    return np.einsum('ij,jtc->itc', factor, z)


def pairs(z, rounded=False):
    x = np.round(z[:, 0, 2]*3)/3 if rounded else z[:, 0, 2]
    pair_list = [(z[:, 0, 0], x), (z[:, 0, 1], x)]
    pair_list += [(z[:, t, 0], z[:, t, 1]) for t in [*range(4), *range(12, 16)]]
    pair_list += [(z[:, 13, 0]-z[:, 1, 0], z[:, 13, 1]-z[:, 1, 1])]
    coeff = np.zeros((4, len(pair_list)))
    coeff[0, :2] = [1, -1]
    coeff[1, 3], coeff[1, 7] = 1, -1
    coeff[2, 2:6], coeff[2, 6:10] = -.25, .25
    coeff[3, 10] = 1
    return pair_list, coeff, 1 - len(np.unique(x))/len(x)


def rank_masks(values):
    return (values[None, :] < values[:, None]).astype(float) + .5*(values[None, :] == values[:, None])


def weighted_rho(x, y, weights):
    """Exact midranks of repeated observations from multiplicity rows."""
    weights = np.atleast_2d(weights).astype(float)
    totals = weights.sum(axis=1)
    center = (totals + 1)[:, None] / 2
    rx = weights @ rank_masks(x).T + .5 - center
    ry = weights @ rank_masks(y).T + .5 - center
    numerator = np.sum(weights * rx * ry, axis=1)
    denominator = np.sqrt(np.sum(weights*rx**2, axis=1)*np.sum(weights*ry**2, axis=1))
    out = np.full(len(weights), np.nan)
    np.divide(numerator, denominator, out=out, where=(denominator > 0) & (totals > 1))
    return out


def statistics(pair_list, coeff, weights):
    return np.stack([weighted_rho(x, y, weights) for x, y in pair_list], axis=1) @ coeff.T


def bootstrap_counts(rng, b, groups=None):
    if groups is None:
        indices = rng.integers(0, 63, (b, 63))
        counts = np.zeros((b, 63), dtype=int)
        for i, row in enumerate(indices):
            counts[i] = np.bincount(row, minlength=63)
        return counts
    k = len(groups)
    indices = rng.integers(0, k, (b, k))
    cluster_counts = np.zeros((b, k), dtype=int)
    for i, row in enumerate(indices):
        cluster_counts[i] = np.bincount(row, minlength=k)
    membership = np.zeros((k, 63), dtype=int)
    for j, members in enumerate(groups):
        membership[j, members] = 1
    return cluster_counts @ membership


def inference(distribution):
    valid = np.isfinite(distribution).all(axis=0)
    lo = np.full(4, np.nan); hi = lo.copy(); p = lo.copy()
    if valid.any():
        x = distribution[:, valid]
        lo[valid], hi[valid] = np.percentile(x, [2.5, 97.5], axis=0)
        b = len(x)
        p[valid] = np.minimum(1, 2*np.minimum((1+(x <= 0).sum(axis=0))/(b+1), (1+(x >= 0).sum(axis=0))/(b+1)))
    return lo, hi, p, np.sum(~np.isfinite(distribution), axis=0)


def run_dataset(z, rounded, b, graph_id, config_id, simulation, groups, multipliers):
    pair_list, coeff, tie_share = pairs(z, rounded)
    estimate = statistics(pair_list, coeff, np.ones((1, 63)))[0]
    methods = [('province', None), *[(f'kmeans{k}', groups[k]) for k in (6, 8, 12)]]
    draws = {}
    timings = {}
    for method_id, (name, members) in enumerate(methods):
        started = time.perf_counter()
        draws[name] = statistics(pair_list, coeff, bootstrap_counts(rng_for(2, graph_id, config_id, simulation, method_id), b, members))
        timings[name] = time.perf_counter() - started
    started = time.perf_counter()
    deleted = statistics(pair_list, coeff, np.ones((63, 63)) - np.eye(63))
    influence = 62*(estimate - deleted)
    influence -= influence.mean(axis=0)
    jackknife_seconds = time.perf_counter() - started
    for factor, root in multipliers.items():
        started = time.perf_counter()
        external = rng_for(3, graph_id, config_id, simulation, factor).normal(size=(b, 63)) @ root.T
        name = f'spatial_multiplier_bw{factor}'
        draws[name] = estimate + external @ influence / 63
        timings[name] = time.perf_counter() - started + jackknife_seconds/len(multipliers)
    records = []
    for method, dist in draws.items():
        lo, hi, p, failures = inference(dist)
        for j, outcome in enumerate(NAMES):
            records.append({'method': method, 'outcome': outcome, 'estimate': estimate[j], 'target': TARGETS[j],
                            'lo': lo[j], 'hi': hi[j], 'p_zero': p[j], 'invalid_bootstrap_draws': int(failures[j]),
                            'covered': bool(lo[j] <= TARGETS[j] <= hi[j]) if np.isfinite(lo[j]) else None,
                            'length': hi[j]-lo[j], 'bias': estimate[j]-TARGETS[j], 'tie_fraction_X': tie_share,
                            'seconds_method_all_four_outcomes': timings[method]})
    return records


def checks():
    rng = rng_for(99)
    count_cases = 0
    for tied in (False, True):
        x, y = rng.normal(size=(2, 63))
        if tied:
            x, y = np.round(x), np.round(y)
        for k in range(12):
            c = rng.integers(0, 4, 63)
            explicit = spearmanr(np.repeat(x, c), np.repeat(y, c)).statistic
            assert abs(weighted_rho(x, y, c)[0] - explicit) < 1e-14
            count_cases += 1
    assert np.isnan(weighted_rho(np.ones(63), y, np.ones(63))[0])
    factor = np.eye(63)
    z = draw_field(rng_for(101), factor)
    pair_list, coeff, _ = pairs(z)
    observed = statistics(pair_list, coeff, np.ones(63))[0]
    direct = [spearmanr(a, b).statistic for a, b in pair_list]
    assert np.max(np.abs(observed - np.array(direct) @ coeff.T)) < 1e-14
    explicit = np.array([
        spearmanr(z[:, 0, 0], z[:, 0, 2]).statistic - spearmanr(z[:, 0, 1], z[:, 0, 2]).statistic,
        spearmanr(z[:, 1, 0], z[:, 1, 1]).statistic - spearmanr(z[:, 13, 0], z[:, 13, 1]).statistic,
        np.mean([spearmanr(z[:, t, 0], z[:, t, 1]).statistic for t in range(12, 16)]) - np.mean([spearmanr(z[:, t, 0], z[:, t, 1]).statistic for t in range(4)]),
        spearmanr(z[:, 13, 0]-z[:, 1, 0], z[:, 13, 1]-z[:, 1, 1]).statistic,
    ])
    assert np.max(np.abs(observed-explicit)) < 1e-14
    swapped = z[:, :, [1, 0, 2]]
    p2, c2, _ = pairs(swapped)
    obs2 = statistics(p2, c2, np.ones(63))[0]
    assert np.max(np.abs(obs2 - observed*np.array([-1, 1, 1, 1]))) < 1e-14
    assert np.array_equal(draw_field(rng_for(101), factor), z)
    return {'explicit_scipy_repeated_sample_comparisons': count_cases, 'constant_input_returns_nan': True,
            'all_four_statistics_match_direct_scipy': True, 'window_indices_and_directions_checked_independently': True,
            'source_swap_invariance': True, 'seeded_field_identical': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--simulations', type=int, default=12)
    parser.add_argument('--bootstrap', type=int, default=199)
    args = parser.parse_args()
    assert args.simulations > 0 and args.bootstrap >= 99
    output = HERE / 'spatial_pilot_runs' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True)
    start = time.perf_counter()
    test_results = checks()
    graphs, groups, multipliers, geo = geometry()
    config = {'seed': SEED, 'simulations': args.simulations, 'bootstrap': args.bootstrap,
              'mode': 'CODE_AND_RUNTIME_PILOT_NOT_CALIBRATION', 'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'addendum_sha256': hashlib.sha256((HERE/'SPATIAL_PILOT_ADDENDUM.md').read_bytes()).hexdigest(),
              'geometry': geo, 'python': sys.version,
              'packages': {p: importlib.metadata.version(p) for p in ['numpy', 'pandas', 'scipy', 'shapely']}, 'checks': test_results}
    (output/'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    records = []; configurations = []; benchmarks = []
    for graph_id, adjacency in enumerate(graphs):
        for level, strength in enumerate([0., .3, .6, .85]):
            for rounded in ([False, True] if graph_id == 0 and level in (0, 3) else [False]):
                config_id = level*2 + int(rounded)
                factor = spatial_factor(adjacency, strength)
                name = f'graph{graph_id}_rho{strength}_rounded{rounded}'
                configurations.append(name)
                for simulation in range(args.simulations):
                    z = draw_field(rng_for(1, graph_id, config_id, simulation), factor)
                    rows = run_dataset(z, rounded, args.bootstrap, graph_id, config_id, simulation, groups, multipliers)
                    for row in rows:
                        row.update(configuration=name, graph_id=graph_id, rho=strength, rounded=rounded, simulation=simulation)
                    records.extend(rows)
                print('Pilot complete:', name, flush=True)
                pd.DataFrame(records).to_csv(output/'replicates.csv', index=False)
        z = draw_field(rng_for(10, graph_id), spatial_factor(adjacency, .6))
        bench = run_dataset(z, False, 1999, graph_id, 99, 0, groups, multipliers)
        benchmarks.extend([dict(row, graph_id=graph_id) for row in bench])
    frame = pd.DataFrame(records)
    grouped = frame.groupby(['configuration', 'method', 'outcome'])
    rows = []
    for keys, g in grouped:
        valid = g.dropna(subset=['lo', 'hi', 'p_zero'])
        is_null = bool(g.target.iloc[0] == 0)
        rows.append(dict(zip(['configuration', 'method', 'outcome'], keys)) | {
            'datasets': len(g), 'valid_datasets': len(valid),
            'invalid_bootstrap_draws': int(g.invalid_bootstrap_draws.sum()),
            'coverage': float(valid.covered.astype(float).mean()),
            'reject_zero_005': float((valid.p_zero < .05).mean()) if is_null else None,
            'reject_zero_001': float((valid.p_zero < .01).mean()) if is_null and 2/(args.bootstrap+1) < .01 else None,
            'minimum_attainable_two_tail_p': 2/(args.bootstrap+1),
            'mean_length': float(valid.length.mean()), 'mean_bias': float(g.bias.mean()),
            'mean_tie_fraction_X': float(g.tie_fraction_X.mean()),
            'warning': 'PILOT_TOO_SMALL_FOR_CALIBRATION'})
    pd.DataFrame(rows).to_csv(output/'pilot_summary.csv', index=False)
    pd.DataFrame(benchmarks).to_csv(output/'benchmark_B1999.csv', index=False)
    costs = pd.DataFrame(benchmarks).drop_duplicates(['graph_id', 'method']).seconds_method_all_four_outcomes
    seconds_per_dataset = float(costs.sum()/len(graphs))
    report = {'mode': config['mode'], 'run': str(output), 'checks': test_results,
              'configurations': len(configurations), 'simulated_datasets': len(frame[['configuration', 'simulation']].drop_duplicates()),
              'method_outcome_records': len(frame), 'invalid_bootstrap_draws': int(frame.invalid_bootstrap_draws.sum()),
              'elapsed_seconds': time.perf_counter()-start,
              'B1999_measured_seconds_per_dataset_all_methods_four_outcomes': seconds_per_dataset,
              'approx_main_seconds_10configs_2000datasets': seconds_per_dataset*10*2000,
              'geometry_components': geo['graphs'],
              'limitations': ['Small pilot, not a method-selection or calibration result.',
                              'Multiplier on jackknife influence values is experimental for these statistics.',
                              'Different-source spatial covariance and broader main-grid scenarios remain unimplemented.',
                              'Benchmark projection is approximate; startup, data writes and main-grid cost can differ.']}
    (output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (HERE/'last_spatial_pilot.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
