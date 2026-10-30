"""Run installed Node for JS logic checks; no installs, browser or paid calls."""
from pathlib import Path
import shutil
import subprocess
import unittest

@unittest.skipUnless(shutil.which('node'),'Optional installed Node required for JS logic regressions')
class UIConcurrencyTests(unittest.TestCase):
    def run_case(self,name):
        result=subprocess.run(['node',str(Path(__file__).with_name('ui_concurrency.js')),name],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_newer_scene_wins_out_of_order_response(self):self.run_case('sceneNewestWins')
    def test_old_failure_cannot_clear_new_loading_or_status(self):self.run_case('oldFailureCannotClearNewLoading')
    def test_source_inputs_locked_during_review_write_and_restored_after(self):self.run_case('reviewInputFreeze')

if __name__=='__main__':unittest.main(verbosity=2)
