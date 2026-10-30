"""Single-command offline judge verification; no dependency install or paid calls.

Runs development tests (including loopback HTTP), authored scene checks and
historical-file integrity. None are a fresh/held-out model evaluation.
"""
import argparse
from datetime import datetime,timezone
import io
import json
from pathlib import Path
import sys
import unittest
from build_id import BUILD_ID,SOURCE_DIGEST
from evaluate import report as scenario_report
from evaluation_audit import report as history_report

ROOT=Path(__file__).resolve().parent


def run():
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
    result=unittest.TextTestRunner(stream=stream,verbosity=1).run(suite)
    scenes=scenario_report();history=history_report()
    complete=result.wasSuccessful() and scenes['passed']==scenes['total'] and all(v['integrityPassed'] for v in history['evaluations'])
    return dict(format='freightswitch-offline-judge-check-v1',buildId=BUILD_ID,sourceDigest=SOURCE_DIGEST,checkedUTC=datetime.now(timezone.utc).isoformat(),
        passed=complete,developmentTests=dict(run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),output=stream.getvalue()),
        authoredScenarios=dict(passed=scenes['passed'],total=scenes['total'],modelQuality=None),historicalEvidence=history,
        realModelCallsExecuted=0,freshHeldOutModelScore=None,
        notice='Development regressions and local HTTP checks, not model accuracy. Live CLI remains paused; no deployment or submission was performed.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    target=Path(args.output)
    if target.exists():parser.error('Existing evidence preserved; choose a new output path')
    result=run();target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x') as output:json.dump(result,output,indent=2);output.write('\n')
    print(json.dumps(dict(buildId=result['buildId'],passed=result['passed'],developmentTests=result['developmentTests']['run'],
        failures=result['developmentTests']['failures'],errors=result['developmentTests']['errors'],authoredScenarios=result['authoredScenarios'],
        historicalIntegrity=all(v['integrityPassed'] for v in result['historicalEvidence']['evaluations']),realModelCallsExecuted=0,report=str(target))))
    sys.exit(0 if result['passed'] else 1)
