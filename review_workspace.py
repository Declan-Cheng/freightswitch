"""Local synthetic interpretation audit, deliberately separate from agreement state."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from datetime import datetime,timezone
from uuid import uuid4
from fixtures import events
from provider import Analyzer,validate
from recorded_review import load_recorded

def now():return datetime.now(timezone.utc).isoformat()

class ReviewStore:
    def __init__(self,path):
        self.path=Path(path)
        if self.path.is_symlink() or self.path.parent.is_symlink():raise ValueError('Review symlink refused')
        self.path.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
        if not self.path.exists():os.close(os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600))
        if self.path.stat().st_mode&0o077:raise ValueError('Review database must be owner-only')
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS revisions(seq INTEGER PRIMARY KEY, id TEXT, revision TEXT UNIQUE, data TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY, revision TEXT, data TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS decisions(seq INTEGER PRIMARY KEY, action TEXT UNIQUE, request TEXT, data TEXT)')
    def connect(self):return sqlite3.connect(str(self.path),timeout=5)
    def source(self,ident,db=None):
        if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',ident):raise ValueError('Stable source ID required')
        if db is None:
            with self.connect() as conn:return self.source(ident,conn)
        row=db.execute('SELECT data FROM revisions WHERE id=? ORDER BY seq DESC LIMIT 1',(ident,)).fetchone()
        if not row:raise ValueError('Unknown source')
        return json.loads(row[0])
    def save(self,data):
        if set(data)!={'id','body','senderLabel'}:raise ValueError('Exact source schema required')
        ident,body,sender=(data[k] for k in ('id','body','senderLabel'))
        if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',ident):raise ValueError('Stable source ID required')
        if not isinstance(body,str) or not 1<=len(body)<=12000 or not isinstance(sender,str) or not 1<=len(sender)<=100:raise ValueError('Bounded synthetic source required')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT data FROM revisions WHERE id=? ORDER BY seq DESC LIMIT 1',(ident,)).fetchone()
            if old:
                previous=json.loads(old[0])
                if previous['body']==body and previous['senderLabel']==sender:return previous
            elif db.execute('SELECT count(DISTINCT id) FROM revisions').fetchone()[0]>=30:raise ValueError('30-source workspace limit')
            if db.execute('SELECT count(*) FROM revisions').fetchone()[0]>=1000:raise ValueError('Source revision limit reached')
            source=dict(id=ident,body=body,senderLabel=sender,sha256=hashlib.sha256(body.encode()).hexdigest(),revisionId=str(uuid4()),savedAt=now(),synthetic=True,identityVerified=False)
            db.execute('INSERT INTO revisions(id,revision,data) VALUES(?,?,?)',(ident,source['revisionId'],json.dumps(source)))
            return source
    def propose(self,ident,revision,mode):
        source=self.source(ident)
        if source['revisionId']!=revision:raise ValueError('Source revision changed; review again')
        if mode!='mock':raise ValueError('Only explicit offline mock; no live web route')
        versions=set(re.findall(r'(?<![\w-])v[1-9][0-9]{0,2}(?![\w-])',source['body']))
        doc={**source,'version':next(iter(versions)) if len(versions)==1 else None}
        result=Analyzer().analyze([doc],mode='mock')
        return self.add_proposal(source,result['observations'][0],'mock',False,result['questions'])
    def add_proposal(self,source,observation,mode,real,questions=None):
        fields=('messageId','kind','version','quote','confidence','explanation')
        questions=[] if questions is None else questions
        row=validate(dict(observations=[{k:observation[k] for k in fields}],questions=questions),[source])['observations'][0]
        item=dict(proposalId=str(uuid4()),sourceId=source['id'],sourceRevision=source['revisionId'],sourceSHA256=source['sha256'],mode=mode,realInference=real,recordedReplay=mode=='recorded-replay',createdAt=now(),observation=row,questions=questions,proposalOnly=True)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT count(*) FROM proposals').fetchone()[0]>=1000:raise ValueError('Proposal limit reached')
            db.execute('INSERT INTO proposals VALUES(?,?,?)',(item['proposalId'],source['revisionId'],json.dumps(item)))
        return item
    def import_recorded(self):
        record=load_recorded()
        if not record:raise ValueError('Validated recorded response unavailable')
        observation=next(r for r in record['observations'] if r['messageId']=='m07')
        doc=next(m for m in events() if m['id']=='m07')
        source=self.save(dict(id='m07',body=doc['body'],senderLabel='Fictional dispatcher · recorded fixture'))
        return dict(source=source,proposal=self.add_proposal(source,observation,'recorded-replay',True,record['questions']))
    def decide(self,data):
        fields={'actionId','proposalId','sourceRevision','sourceSHA256','decision','version','quote','note'}
        if set(data)!=fields or not isinstance(data['actionId'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',data['actionId']):raise ValueError('Exact decision schema/action ID required')
        if data['decision'] not in ('approve','reject','needs_clarification') or not isinstance(data['note'],str) or not 1<=len(data['note'])<=1000:raise ValueError('Decision and bounded reason required')
        if not isinstance(data['proposalId'],str) or len(data['proposalId'])>80:raise ValueError('Bounded proposal ID required')
        serialized=json.dumps(data,sort_keys=True)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT request,data FROM decisions WHERE action=?',(data['actionId'],)).fetchone()
            if old:
                if old[0]!=serialized:raise ValueError('Action ID already used for a different decision')
                return json.loads(old[1])
            if db.execute('SELECT count(*) FROM decisions').fetchone()[0]>=1000:raise ValueError('Audit limit reached')
            row=db.execute('SELECT data FROM proposals WHERE id=?',(data['proposalId'],)).fetchone()
            if not row:raise ValueError('Unknown proposal')
            proposal=json.loads(row[0]);source=self.source(proposal['sourceId'],db);obs=proposal['observation']
            if data['sourceRevision']!=source['revisionId'] or data['sourceRevision']!=proposal['sourceRevision'] or data['sourceSHA256']!=source['sha256']:raise ValueError('Stale source/proposal: review current revision')
            if data['version']!=obs['version'] or data['quote']!=obs['quote']:raise ValueError('Version/quote differs from reviewed proposal')
            if data['decision']=='approve' and (obs['kind']=='unclear' or obs['version'] is None):raise ValueError('Unclear interpretation requires clarification, not approval')
            item=dict(auditId=str(uuid4()),actionId=data['actionId'],proposalId=proposal['proposalId'],sourceId=source['id'],sourceRevision=source['revisionId'],sourceSHA256=source['sha256'],version=obs['version'],quote=obs['quote'],kind=obs['kind'],decision=data['decision'],note=data['note'],createdAt=now(),scope='interpretation-only',agreementChanged=False,synthetic=True)
            db.execute('INSERT INTO decisions(action,request,data) VALUES(?,?,?)',(data['actionId'],serialized,json.dumps(item)))
            return item
    def snapshot(self):
        with self.connect() as db:
            revisions=[json.loads(r[0]) for r in db.execute('SELECT data FROM revisions ORDER BY seq')]
            proposals=[json.loads(r[0]) for r in db.execute('SELECT data FROM proposals ORDER BY rowid')]
            audit=[json.loads(r[0]) for r in db.execute('SELECT data FROM decisions ORDER BY seq')]
        current={s['id']:s for s in revisions}
        for item in audit:item['appliesToCurrentSource']=item['sourceRevision']==current[item['sourceId']]['revisionId']
        return dict(sources=list(current.values()),sourceHistory=revisions,proposals=proposals,audit=audit,synthetic=True,liveWebRoute=False,agreementChanged=False)
