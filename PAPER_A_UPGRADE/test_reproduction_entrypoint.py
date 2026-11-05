"""Contract tests for missing/stale evidence and numerical comparison failures."""
from pathlib import Path
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class EvidenceContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.actual=self.base/'actual';self.ref=self.base/'ref'
        self.actual.mkdir();self.ref.mkdir();self.check=load('check_reproduction_20261103')
    def test_missing_output_fails(self):
        (self.ref/'one.csv').write_text('x\n1.0\n')
        with contextlib.redirect_stdout(io.StringIO()):code=self.check.main(['--actual',str(self.actual),'--reference',str(self.ref)])
        self.assertEqual(code,1)
    def test_empty_reference_does_not_pass(self):
        self.assertFalse(self.check.compare(self.actual,self.ref)['passed'])
    def test_numerical_difference_fails(self):
        (self.ref/'one.csv').write_text('x\n1.0\n');(self.actual/'one.csv').write_text('x\n1.01\n')
        self.assertFalse(self.check.compare(self.actual,self.ref)['passed'])
    def test_recorded_tolerance_and_missing_values(self):
        (self.ref/'one.csv').write_text('x,y\n1.0,a\n,\n')
        (self.actual/'one.csv').write_text('x,y\n1.0000000001,a\n,\n')
        self.assertTrue(self.check.compare(self.actual,self.ref)['passed'])
    def test_json_difference_fails(self):
        (self.ref/'one.json').write_text('{"passed": true}')
        (self.actual/'one.json').write_text('{"passed": false}')
        self.assertFalse(self.check.compare(self.actual,self.ref)['passed'])
    def test_existing_run_directory_rejected(self):
        run=load('reproduce')
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as caught:
            run.main(['--run-dir',str(self.base)])
        self.assertEqual(caught.exception.code,2)
    def test_changed_input_rejected_before_run(self):
        run=load('reproduce');p=self.base/'PAPER_A_UPGRADE';p.mkdir()
        (self.base/'input.csv').write_text('changed')
        (p/'reproduction_manifest.json').write_text(json.dumps({'files':[{'path':'input.csv','role':'processed_input','text':True,'sha256':'0'*64}]}))
        dest=self.base/'new_run'
        with patch.object(run,'HERE',p),patch.object(run,'ROOT',self.base):
            with self.assertRaisesRegex(RuntimeError,'hash mismatch'):run.main(['--run-dir',str(dest)])
        self.assertFalse(dest.exists())

if __name__=='__main__':unittest.main()
