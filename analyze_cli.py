"""Private advisory runner. Live mode needs separate approval and secure environment.

A process-local one-attempt guard is not a platform dollar/billing hard stop.
"""
import argparse
import json
from pathlib import Path
from fixtures import events,SCENES
from provider import Analyzer,ProviderError,status

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('mock','live'),default='mock')
    parser.add_argument('--scene',choices=[s['id'] for s in SCENES],default='risk')
    parser.add_argument('--output',required=True)
    args=parser.parse_args();output=Path(args.output)
    if args.mode=='live':parser.exit(2,'v1.4 paid evaluation paused until a fresh frozen independent protocol; do not initialize a separate daily ledger\n')
    if output.exists():parser.error('Existing output preserved; select a new path')
    count=next(s['count'] for s in SCENES if s['id']==args.scene)
    env=None;ledger=None
    if args.mode=='live':
        try:
            from secret_input import load,SECRET
            from budget import Ledger
            env=load()
            ledger=Ledger(SECRET.parent/'usage.sqlite')
        except Exception:parser.exit(2,'Secure server-only key/configuration unavailable; no provider call attempted\n')
    try:result=Analyzer().analyze(events()[:count],mode=args.mode,env=env,ledger=ledger)
    except ProviderError as exc:parser.exit(2,str(exc)+'\n')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(mode=result['mode'],realInference=result['realInference'],model=result['model'],proposalOnly=True,output=str(output))))
