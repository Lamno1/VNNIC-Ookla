"""Exercise real failure paths without changing canonical inputs or outputs."""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAU = HERE.parent
ROOT = PAU.parent


def main():
    parent = ROOT/'reports/rev14_wrapper_checks'
    parent.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='checks_', dir=parent))
    manifest = json.loads((HERE/'manifest_rev14.json').read_text())
    checks = []
    for name, content in [('incomplete', dict(list(manifest.items())[:1])),
                          ('wrong_hash', {**manifest, next(iter(manifest)): '0'*64})]:
        path = out/f'{name}.json'
        path.write_text(json.dumps(content), encoding='utf-8')
        p = subprocess.run([sys.executable, str(HERE/'preflight.py'), '--manifest', str(path)],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        (out/f'{name}.log').write_text(p.stdout+p.stderr, encoding='utf-8')
        checks.append({'case': name, 'exit': p.returncode, 'passed': p.returncode != 0})
    # A copied preflight with absent required inputs must not issue a manifest.
    stub = out/'missing_project/PAPER_A_UPGRADE/rev14_tools'
    stub.mkdir(parents=True)
    for filename in ['preflight.py', 'replay_contract.json']:
        (stub/filename).write_bytes((HERE/filename).read_bytes())
    p = subprocess.run([sys.executable, str(stub/'preflight.py'), '--make-manifest'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    (out/'missing_inputs.log').write_text(p.stdout+p.stderr, encoding='utf-8')
    checks.append({'case': 'make_manifest_with_missing_inputs', 'exit':p.returncode,
                   'passed':p.returncode != 0 and not (stub/'manifest_rev14.json').exists()})

    spec = importlib.util.spec_from_file_location('tested_runner', HERE/'run_all.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    fixture = out/'noop_project/PAPER_A_UPGRADE'
    fixture.mkdir(parents=True)
    for script in runner.ORDER:
        (fixture/script).write_text('raise SystemExit(0)\n')
    (fixture/'upg_common.py').write_text('from pathlib import Path\nROOT = HERE.parent\n')
    for name in ['stale.csv', 'correction.csv']:
        (fixture/'results').mkdir(exist_ok=True)
        (fixture/'results'/name).write_text('value\n123\n')
    contract = {'analysis_outputs':['results/stale.csv'], 'correction_output':'results/correction.csv',
                'historical_artifacts':[]}
    report = runner.replay(fixture, fixture.parent, contract, out/'noop_replay/PAPER_A_UPGRADE')
    (out/'noop_report.json').write_text(json.dumps(report,indent=2), encoding='utf-8')
    checks.append({'case':'noop_scripts_cannot_reuse_stale_results',
                   'passed':not report['passed'] and 'results/stale.csv' in report['missing']
                            and report['initial_result_csv_count']==0})
    (out/'report.json').write_text(json.dumps(checks,indent=2), encoding='utf-8')
    print(json.dumps({'evidence':str(out),'checks':checks},indent=2))
    return 0 if all(c['passed'] for c in checks) else 1


if __name__ == '__main__':
    sys.exit(main())
