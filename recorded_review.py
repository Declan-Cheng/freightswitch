"""Read and revalidate a fixed synthetic runtime record. Never calls a provider."""
import json
from pathlib import Path
from fixtures import events
from provider import MODEL,validate

RECORD=Path(__file__).resolve().parent/'evidence'/'live-probes-20261028'/'risk.json'

def load_recorded(path=RECORD):
    try:
        raw=Path(path).read_bytes()
        if len(raw)>131072:return None
        report=json.loads(raw)
        if report.get('validationPassed') is not True or report.get('syntheticOnly') is not True:return None
        result=report['result']
        if result.get('realInference') is not True or result.get('model')!=MODEL or result.get('mode')!='live':return None
        ids=report['sourceIds'];docs=[m for m in events() if m['id'] in ids]
        if len(docs)!=len(ids):return None
        fields=('messageId','kind','version','quote','confidence','explanation')
        data=validate(dict(observations=[{k:r[k] for k in fields} for r in result['observations']],questions=result['questions']),docs)
        hashes={m['id']:m['sha256'] for m in docs}
        if any(r.get('evidenceSHA256')!=hashes.get(r['messageId']) for r in result['observations']):return None
        return dict(provider='Nebius Token Factory',model=MODEL,recordedOn='2026-10-28',
                    realInference=True,recordedReplay=True,proposalOnly=True,
                    usage=result['usage'],sourceIds=ids,**data)
    except (OSError,ValueError,KeyError,TypeError):return None
