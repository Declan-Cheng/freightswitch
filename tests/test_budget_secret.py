from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from budget import Ledger,BudgetError,CEILING,RESERVE
from secret_input import store,load

class BudgetAndHiddenInputTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)/'private';self.path=self.folder/'usage.sqlite';self.clock=lambda:datetime.fromisoformat('2026-10-28T20:00:00-04:00')
    def tearDown(self):self.temp.cleanup()
    def test_actual_ledger_reopen_enforces_attempt_cap_and_cost_reserve(self):
        for _ in range(50):
            ledger=Ledger(self.path,self.clock);attempt=ledger.reserve();ledger.settle(attempt,dict(prompt_tokens=262144,completion_tokens=1800,total_tokens=263944))
        self.assertLessEqual(RESERVE*50,CEILING)
        with self.assertRaises(BudgetError):Ledger(self.path,self.clock).reserve()
    def test_unfinished_attempt_blocks_restart(self):
        Ledger(self.path,self.clock).reserve()
        with self.assertRaises(BudgetError):Ledger(self.path,self.clock).reserve()
    def test_accounting_uncertainty_freezes_further_calls(self):
        ledger=Ledger(self.path,self.clock);ident=ledger.reserve()
        with self.assertRaises(BudgetError):ledger.settle(ident,None)
        with self.assertRaises(BudgetError):Ledger(self.path,self.clock).reserve()
    def test_inconsistent_usage_and_expired_window_refused(self):
        ledger=Ledger(self.path,self.clock);ident=ledger.reserve()
        with self.assertRaises(BudgetError):ledger.settle(ident,dict(prompt_tokens=4,completion_tokens=3,total_tokens=999))
        expired=Ledger(Path(self.temp.name)/'late.sqlite',lambda:datetime.fromisoformat('2026-10-29T00:00:00-04:00'))
        with self.assertRaises(BudgetError):expired.reserve()
    def test_yesterdays_window_is_not_implicitly_renewed(self):
        old=Ledger(Path(self.temp.name)/'old.sqlite',lambda:datetime.fromisoformat('2026-10-27T20:00:00-04:00'))
        with self.assertRaises(BudgetError):old.reserve()
    def test_dollar_ceiling_is_checked_separately(self):
        ledger=Ledger(self.path,self.clock)
        with ledger.connect() as db:db.execute("INSERT INTO attempts(status,reserved,cost) VALUES('settled','0','0.999')")
        with self.assertRaises(BudgetError):ledger.reserve()
    def test_fake_secret_owner_only_never_overwrite_or_follow_symlink(self):
        target=self.folder/'provider.json';fake='FAKE_TEST_ONLY_NOT_A_REAL_KEY';store(fake,target)
        self.assertEqual(load(target)['NEBIUS_API_KEY'],fake);self.assertEqual(target.stat().st_mode&0o777,0o600)
        with self.assertRaises(FileExistsError):store('OTHER_FAKE_KEY_VALUE',target)
        link=self.folder/'link.json';link.symlink_to(target)
        with self.assertRaises(ValueError):load(link)
    def test_world_readable_secret_refused(self):
        target=self.folder/'provider.json';store('FAKE_TEST_ONLY_NOT_A_REAL_KEY',target);target.chmod(0o644)
        with self.assertRaises(ValueError):load(target)

if __name__=='__main__':unittest.main(verbosity=2)
