"""Execute the spatial-results package in a new, isolated workspace.

Scientific kernels are unchanged. A hashed manifest supplies only code, inputs,
specifications and references. Generated outputs are absent at the start.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
COVERAGE={'coverage_by_k_pooled.csv','coverage_summary_blocks_vs_province.csv'}
TABLE_STEPS=[('01_bootstrap','spatial_block_bootstrap_20261103.py'),
 ('02_validate','validate_spatial_block_20261103.py'),
 ('03_contiguous','spatial_block_contiguous_20261103.py'),
 ('04_table_s34','make_table_s34_20261103.py'),
 ('05_range','spatial_range_20261103.py'),
 ('06_resampling','block_resampling_facts_20261103.py')]


def digest(path, text=False):
    b=path.read_bytes()
    if text:b=b.replace(b'\r\n',b'\n')
    return hashlib.sha256(b).hexdigest()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['tables','smoke','full'],default='tables')
    parser.add_argument('--run-dir',type=Path,help='New directory; an existing path is rejected')
    parser.add_argument('--workers',type=int,default=min(14,os.cpu_count() or 1))
    parser.add_argument('--plan',action='store_true',help='Print commands without executing')
    a=parser.parse_args(argv)
    if a.workers<1:parser.error('--workers must be positive')
    manifest=json.loads((HERE/'reproduction_manifest.json').read_text(encoding='utf-8'))
    if any('/spatial_main_runs/' in f['path'] or '/results_spatial_block_20261103/' in f['path'] for f in manifest['files']):
        raise RuntimeError('Manifest must not include generated output directories')
    refs=sorted(x['path'].rsplit('/',1)[1] for x in manifest['files'] if x['role']=='reference_output')
    selected=refs if a.mode=='full' else [n for n in refs if n not in COVERAGE]
    steps=[(name,[script]) for name,script in TABLE_STEPS]
    if a.mode in {'smoke','full'}:
        extra=['--workers',str(a.workers)]
        if a.mode=='smoke':extra+=['--simulations','20','--bootstrap','199']
        steps += [('07_coverage',['spatial_block_coverage_20261103.py','--tag','reviewer_blocks',*extra]),
                  ('08_coverage_k',['spatial_block_coverage_k_20261103.py','--tag','reviewer_blocks_k',*extra]),
                  ('09_coverage_summary',['summarize_coverage_20261103.py','reviewer_blocks_k','reviewer_blocks'])]
    steps += [('10_compare',['check_reproduction_20261103.py','--files',*selected,'--json-out','comparison.json'])]
    if a.plan:
        print(json.dumps({'mode':a.mode,'compared_files':selected,'commands':steps},indent=2));return 0
    run=(a.run_dir or ROOT/'reproduction_runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6])).resolve()
    if run.exists():parser.error('--run-dir already exists; use a new directory to prevent stale-output reuse')
    if run==ROOT or ROOT.is_relative_to(run):parser.error('run directory cannot contain the source repository')
    for f in manifest['files']:
        src=(ROOT/f['path']).resolve()
        if not src.is_relative_to(ROOT) or not src.is_file():raise RuntimeError('Missing/invalid input '+f['path'])
        if digest(src,f['text'])!=f['sha256']:raise RuntimeError('Input hash mismatch '+f['path'])
    run.mkdir(parents=True)
    work=run/'workspace';logs=run/'logs';logs.mkdir()
    for f in manifest['files']:
        dst=work/f['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/f['path'],dst)
    task=work/'PAPER_A_UPGRADE'
    assert not (task/'results_spatial_block_20261103').exists()
    assert not (task/'spatial_engine/spatial_main_runs').exists()
    packages={}
    for package in ['numpy','pandas','scipy','pyarrow','shapely','pyproj','scikit-learn','matplotlib']:
        try:packages[package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:packages[package]='MISSING'
    versions={line.split('==')[0]:line.split('==')[1] for line in (HERE/'requirements_repro.txt').read_text().splitlines() if '==' in line}
    differences={n:{'expected':v,'actual':packages.get(n)} for n,v in versions.items() if packages.get(n)!=v}
    if differences:print('Environment differs from recorded requirements; see run.json',differences,flush=True)
    report=dict(mode=a.mode,status='running',started_utc=datetime.now(timezone.utc).isoformat(),
                run_directory=str(run),python=sys.version,executable=sys.executable,platform=platform.platform(),
                packages=packages,version_differences=differences,workers=a.workers,
                generated_directories_initially_absent=True,reference_files_compared=selected,
                manifest_sha256=digest(HERE/'reproduction_manifest.json'),runner_sha256=digest(Path(__file__)),
                full_simulations=(a.mode=='full'),steps=[])
    env=os.environ.copy()
    for name in ['ADM1_GEOJSON','OOKLA_RAW_DIR','DTI_2023_TXT']:env.pop(name,None)
    env['PYTHONIOENCODING']='utf-8';env['PYTHONUNBUFFERED']='1'
    env['SPATIAL_REF']='200' if a.mode=='smoke' else '20000'
    report['reference_simulations']=int(env['SPATIAL_REF'])
    def save():(run/'run.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    save()
    try:
        for name,args in steps:
            command=[sys.executable,*args];start=time.perf_counter()
            print('START',name,' '.join(args),flush=True)
            with (logs/(name+'.log')).open('wb') as log:
                result=subprocess.run(command,cwd=task,env=env,stdout=log,stderr=subprocess.STDOUT)
            rec=dict(name=name,command=command,exit_code=result.returncode,seconds=round(time.perf_counter()-start,3),log='logs/'+name+'.log')
            report['steps'].append(rec);save()
            if result.returncode:raise RuntimeError(name+' failed; inspect '+rec['log'])
            if name=='02_validate':
                v=json.loads((task/'results_spatial_block_20261103/validation.json').read_text())
                if v.get('passed') is not True:raise RuntimeError('Second-implementation validation failed')
            print('DONE',name,rec['seconds'],'s',flush=True)
        comparison=json.loads((task/'comparison.json').read_text())
        if not comparison['passed']:raise RuntimeError('Output comparison failed')
        report['status']='passed_full_spatial_package' if a.mode=='full' else ('passed_smoke_not_full_reproduction' if a.mode=='smoke' else 'passed_tables_only')
        outputs=task/'results_spatial_block_20261103'
        (run/'output_manifest.json').write_text(json.dumps({p.relative_to(work).as_posix():digest(p) for p in outputs.rglob('*') if p.is_file()},indent=2),encoding='utf-8')
        report['comparison']=comparison
    except Exception as exc:
        report['status']='failed';report['error']=str(exc);save();print('FAIL',str(exc),flush=True);return 1
    finally:
        report['finished_utc']=datetime.now(timezone.utc).isoformat();save()
    print(report['status'],len(selected),'reference files; evidence:',run,flush=True)
    return 0


if __name__=='__main__':sys.exit(main())
