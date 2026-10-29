import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from recorded_review import load_recorded,RECORD

class RecordedReviewTests(unittest.TestCase):
    def test_actual_record_revalidates_and_is_read_only_replay(self):
        result=load_recorded()
        self.assertIsNotNone(result);self.assertTrue(result['realInference']);self.assertTrue(result['recordedReplay']);self.assertTrue(result['proposalOnly'])
        self.assertEqual([(r['messageId'],r['kind'],r['version']) for r in result['observations']],[('m05','propose','v2'),('m07','received','v2'),('m08','accept','v1')])
    def test_tampered_quote_hash_or_inference_claim_is_not_served(self):
        original=json.loads(RECORD.read_text())
        for mutation in ('quote','hash','mock'):
            record=copy.deepcopy(original)
            if mutation=='quote':record['result']['observations'][0]['quote']='invented'
            elif mutation=='hash':record['result']['observations'][0]['evidenceSHA256']='bad'
            else:record['result']['realInference']=False
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'record.json';path.write_text(json.dumps(record));self.assertIsNone(load_recorded(path))
    def test_missing_or_malformed_record_does_not_break_demo(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'record.json';self.assertIsNone(load_recorded(path));path.write_text('{}');self.assertIsNone(load_recorded(path))

if __name__=='__main__':unittest.main(verbosity=2)
