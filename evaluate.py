"""Repeatable synthetic scenario report; no model-quality score or network call."""
import argparse
import json
from pathlib import Path
from fixtures import events,recovery_events,RECOVERY_SCENE,SCENES
from domain import evaluate


def report():
    rows=[]
    expected=['ALIGNED','AT_RISK','AT_RISK','ALIGNED','CLARIFY','ALIGNED']
    for scene,status in zip(SCENES+[RECOVERY_SCENE],expected):
        state=evaluate(recovery_events()[:scene['count']]);rows.append(dict(scene=scene['id'],expected=status,actual=state['status'],passed=state['status']==status,state=state))
    return dict(format='freightswitch-synthetic-evaluation-v1',synthetic=True,scenes=rows,passed=sum(r['passed'] for r in rows),total=len(rows),realInferenceCalls=0,realCarrierCalls=0,modelQuality=None,latencyBenchmark=None,notice='Authored synthetic scenarios visible to implementers. Deterministic behavior checks, not extraction accuracy or competitor/judging metrics.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    r=report();Path(args.output).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='scenes'}))
    if r['passed']!=r['total']:raise SystemExit(1)
