"""Historical artifact integrity tests, never current model rescoring."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation_audit import audit_evaluation,report,ROOT

class EvaluationAuditTests(unittest.TestCase):
    def test_original_evidence_is_intact_and_scores_remain_frozen(self):
        data=report();self.assertEqual(data['newModelCalls'],0);self.assertIsNone(data['currentModelAccuracy'])
        self.assertTrue(all(v['integrityPassed'] for v in data['evaluations']))
        v2=data['evaluations'][1]
        self.assertEqual(v2['frozenIndependentScore']['completeCases'],dict(passed=4,total=12))
        self.assertEqual(v2['rejectedCases'],7)
        self.assertEqual(v2['failureInventory'],{'Unsupported complete version token':5,'Proposed action lacks explicit supported source language':2})
        self.assertFalse(v2['currentRevisionRescore'])
    def test_tampered_historical_input_is_detected_not_repaired(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'v2';shutil.copytree(ROOT/'evaluation'/'v2',path)
            original=(path/'inputs.jsonl').read_text();changed=original.replace('I explicitly accept','I explicitly reject',1)
            (path/'inputs.jsonl').write_text(changed)
            result=audit_evaluation(path)
            self.assertFalse(result['integrityPassed']);self.assertFalse(result['integrityChecks']['sourceHashesMatch'])
            self.assertEqual((path/'inputs.jsonl').read_text(),changed)
    def test_missing_attempt_is_detected_without_inflated_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'v2';shutil.copytree(ROOT/'evaluation'/'v2',path)
            lines=(path/'attempts.jsonl').read_text().splitlines();(path/'attempts.jsonl').write_text('\n'.join(lines[:-1])+'\n')
            result=audit_evaluation(path);self.assertFalse(result['integrityPassed']);self.assertFalse(result['integrityChecks']['caseInventoryMatches'])

if __name__=='__main__':unittest.main(verbosity=2)
