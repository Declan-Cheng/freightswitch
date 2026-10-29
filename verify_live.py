"""One explicitly selected synthetic provider probe; never an automatic test loop.

Uses the same durable daily ledger and server-only key as analyze_cli. Responses
are advisory, and authored-case agreement is not an unseen accuracy benchmark.
"""
import argparse
import json
from pathlib import Path
import time
from fixtures import events
from provider import Analyzer,MODEL,ProviderError
from secret_input import load,SECRET
from budget import Ledger

CASES={
    'risk': [('m05','propose','v2'),('m07','received','v2'),('m08','accept','v1')],
    'withdrawal': [('m12','propose','v3'),('m14','withdraw','v3'),('m15','accept','v3')],
}

def run(case,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    report=folder/(case+'.json');envelope=folder/(case+'-envelope.json')
    if report.exists() or envelope.exists():raise ValueError('Existing evidence preserved; choose a new output directory')
    source={m['id']:m for m in events()};expected=CASES[case]
    sample=[source[ident] for ident,_,_ in expected]
    record=dict(case=case,provider='Nebius Token Factory',model=MODEL,syntheticOnly=True,
                sourceIds=[m['id'] for m in sample],realNetworkAttempt=False,
                expected=[dict(messageId=i,kind=k,version=v) for i,k,v in expected],
                limitation='Authored known cases; advisory wording classification, not sender authenticity, rerouting, delivery or general model accuracy.')
    start=time.monotonic()
    try:
        env=load();ledger=Ledger(SECRET.parent/'usage.sqlite')
        record['realNetworkAttempt']=True
        result=Analyzer().analyze(sample,'live',env=env,ledger=ledger,response_path=envelope)
        actual=[{k:r[k] for k in ('messageId','kind','version')} for r in result['observations']]
        record.update(validationPassed=True,result=result,authoredLabelsMatch=sorted(actual,key=lambda x:x['messageId'])==sorted(record['expected'],key=lambda x:x['messageId']))
    except ProviderError as exc:record.update(validationPassed=False,error=str(exc))
    record['elapsedSeconds']=round(time.monotonic()-start,3)
    with report.open('x') as f:json.dump(record,f,indent=2)
    print(json.dumps({k:v for k,v in record.items() if k not in ('result','expected')}))
    return record

if __name__=='__main__':
    raise SystemExit('Legacy favorable-probe runner disabled in v1.4. Await fresh frozen protocol and canonical shared ledger.')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',choices=CASES,required=True);p.add_argument('--output-dir',required=True)
    args=p.parse_args();run(args.case,args.output_dir)
