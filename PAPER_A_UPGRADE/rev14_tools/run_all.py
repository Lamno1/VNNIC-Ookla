"""Replay frozen analyses in a fresh copy with no saved results or figures.

Inputs are read from the original project. Only upg_common.ROOT in the copy
is changed. No existing replay directory is removed. See REPRODUCE_rev14.md.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAU = HERE.parent
ROOT = PAU.parent
ORDER = ['run_upgrade.py', 'run_x13.py', 'run_x15.py', 'run_q2_anomaly.py',
         'run_x9.py', 'run_x16.py', 'run_x18.py', 'run_x10.py', 'run_x17.py',
         'run_x11.py', 'run_x16_d3.py', 'run_x12.py', 'run_x18_d1.py',
         'run_x14.py', 'run_x18_d2.py', 'build_external_delta_supplement.py',
         'build_figures_rev14.py']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replay(pau, project_root, contract, destination):
    """Destination must not exist; contract lists all expected result CSVs."""
    pau, project_root, destination = map(Path, (pau, project_root, destination))
    expected = contract['analysis_outputs']
    assembled = contract.get('assembled_outputs', [])
    figure_pngs = contract.get('figure_pngs', [])
    corrected = contract['correction_output']
    baseline = {k: sha(pau / k) for k in expected + assembled + [corrected]}
    source_hashes = {s: sha(pau / s) for s in ORDER}

    def ignore(folder, names):
        ignored = [n for n in names if n == '__pycache__']
        if Path(folder) == pau:
            ignored += [n for n in names if n.startswith(('results', 'figures_rev'))]
        return ignored

    shutil.copytree(pau, destination, ignore=ignore)
    if list(destination.glob('results*/*.csv')) or list(destination.glob('results*.csv')):
        raise RuntimeError('Saved result CSVs leaked into the fresh workspace')
    common = destination / 'upg_common.py'
    txt = common.read_text(encoding='utf-8')
    if txt.count('ROOT = HERE.parent') != 1:
        raise RuntimeError('Unexpected ROOT definition; refuse implicit path repair')
    common.write_text(txt.replace('ROOT = HERE.parent', f'ROOT = Path({str(project_root)!r})', 1), encoding='utf-8')
    steps, owners = [], {}
    for script in ORDER:
        before = {p.relative_to(destination).as_posix(): sha(p)
                  for p in destination.glob('results*/*.csv')}
        started = time.time()
        proc = subprocess.run([sys.executable, str(destination / script)], cwd=destination,
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
        (destination / f'{script}.log').write_text(proc.stdout + proc.stderr, encoding='utf-8')
        for p in destination.glob('results*/*.csv'):
            key = p.relative_to(destination).as_posix()
            if key not in before or sha(p) != before[key]:
                owners.setdefault(key, []).append(script)
        step = {'script': script, 'exit': proc.returncode, 'seconds': round(time.time()-started, 2)}
        steps.append(step)
        print(f'{script}: exit {proc.returncode} in {step["seconds"]}s', flush=True)
        if proc.returncode:
            break
    if all(s['exit'] == 0 for s in steps) and len(steps) == len(ORDER):
        proc = subprocess.run([sys.executable, str(HERE / 'build_x10_correction.py'),
                               '--analysis-dir', str(destination)], capture_output=True,
                              text=True, encoding='utf-8', errors='replace')
        (destination / 'x10_correction.log').write_text(proc.stdout+proc.stderr, encoding='utf-8')
        steps.append({'script': 'rev14_tools/build_x10_correction.py', 'exit': proc.returncode})
        if proc.returncode == 0:
            owners[corrected] = ['rev14_tools/build_x10_correction.py']
    actual = {p.relative_to(destination).as_posix() for p in list(destination.glob('results*/*.csv')) + list(destination.glob('results*.csv'))}
    wanted = set(expected + assembled + [corrected])
    missing = sorted(wanted - actual)
    extra = sorted(actual - wanted)
    differ = sorted(k for k in wanted & actual if sha(destination/k) != baseline[k])
    unchanged_sources = all(sha(pau/s) == value for s, value in source_hashes.items())
    figures = {}
    if figure_pngs:
        from PIL import Image, ImageChops
        for key in figure_pngs:
            if not (destination/key).is_file():
                figures[key] = False
                continue
            with Image.open(pau/key) as a, Image.open(destination/key) as b:
                a, b = a.convert('RGB'), b.convert('RGB')
                figures[key] = a.size == b.size and ImageChops.difference(a,b).getbbox() is None
    report = {'workspace': str(destination), 'initial_result_csv_count': 0,
              'steps': steps, 'analysis_tables_expected': len(expected),
              'analysis_tables_identical': sum(k in actual and sha(destination/k)==baseline[k] for k in expected),
              'assembled_outputs': assembled, 'figure_pixels_identical': figures,
              'correction_output': corrected, 'historical_artifacts_not_replayed': contract['historical_artifacts'],
              'missing': missing, 'unexpected': extra, 'different': differ,
              'output_writers': owners, 'original_script_hashes_unchanged': unchanged_sources}
    report['passed'] = (len(steps) == len(ORDER)+1 and all(s['exit']==0 for s in steps)
                        and not (missing or extra or differ) and unchanged_sources
                        and all(figures.values()))
    return report


def main():
    preflight = subprocess.run([sys.executable, str(HERE/'preflight.py')])
    if preflight.returncode:
        return 2
    contract = json.loads((HERE/'replay_contract.json').read_text(encoding='utf-8'))
    if '--dry-run' in sys.argv:
        print(json.dumps({'scripts': ORDER, 'analysis_tables': len(contract['analysis_outputs']),
                          'correction': contract['correction_output'],
                          'historical': contract['historical_artifacts']}, indent=2))
        return 0
    parent = ROOT / 'reports' / 'replay_rev14_runs'
    parent.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix='run_', dir=parent))
    report = replay(PAU, ROOT, contract, run_dir/'PAPER_A_UPGRADE')
    serialized = json.dumps(report, indent=2)
    (run_dir/'report.json').write_text(serialized, encoding='utf-8')
    (HERE/'last_replay_report.json').write_text(serialized, encoding='utf-8')
    print(serialized, flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
