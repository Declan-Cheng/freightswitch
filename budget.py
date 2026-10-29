"""Durable tonight-only inference budget. Accounting uncertainty stops further calls.

Conservative input reserve uses the complete published262144-token context cap,
plus1800 output tokens. Rates are the previously verified public rates; recheck before a real call, not a
platform billing stop. No automatic retry, top-up, recharge or ledger reset.
"""
from datetime import datetime
from decimal import Decimal
import os
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

MAX_REQUESTS=50
CEILING=Decimal('1.00')
INPUT_RATE=Decimal('0.06')/Decimal(1000000)
OUTPUT_RATE=Decimal('0.24')/Decimal(1000000)
INPUT_CAP=262144
OUTPUT_CAP=1800
RESERVE=INPUT_CAP*INPUT_RATE+OUTPUT_CAP*OUTPUT_RATE
EXPIRY=datetime.fromisoformat('2026-10-29T00:00:00-04:00')
START=datetime.fromisoformat('2026-10-28T00:00:00-04:00')


class BudgetError(ValueError):pass


class Ledger:
    def __init__(self,path,clock=None):
        self.path=Path(path);self.clock=clock or (lambda:datetime.now(ZoneInfo('America/Toronto')))
        self.path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        if self.path.is_symlink():raise BudgetError('Budget symlink refused')
        if not self.path.exists():
            fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        if self.path.stat().st_mode&0o077:raise BudgetError('Budget ledger must be owner-only')
        with self.connect() as db:db.execute('CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY,status TEXT NOT NULL,reserved TEXT NOT NULL,cost TEXT,usage TEXT)')
    def connect(self):return sqlite3.connect(str(self.path),timeout=5)
    def reserve(self):
        current=self.clock()
        if current.utcoffset() is None or not START<=current<EXPIRY:raise BudgetError('Tonight-only approval window expired or not active')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');rows=db.execute('SELECT status,cost FROM attempts').fetchall()
            if any(s!='settled' for s,_ in rows):raise BudgetError('Uncertain or unfinished accounting; further calls stopped')
            if len(rows)>=MAX_REQUESTS:raise BudgetError('50-attempt limit reached')
            spent=sum((Decimal(cost) for _,cost in rows),Decimal(0))
            if spent+RESERVE>CEILING:raise BudgetError('US$1 ceiling cannot cover conservative token reserve')
            cursor=db.execute('INSERT INTO attempts(status,reserved) VALUES(?,?)',('reserved',str(RESERVE)))
            return cursor.lastrowid
    def uncertain(self,ident):
        with self.connect() as db:db.execute("UPDATE attempts SET status='uncertain' WHERE id=? AND status='reserved'",(ident,))
    def settle(self,ident,usage):
        import json
        if not isinstance(usage,dict) or any(type(usage.get(k)) is not int for k in ('prompt_tokens','completion_tokens','total_tokens')):
            self.uncertain(ident);raise BudgetError('Missing accounting; further calls stopped')
        prompt=usage['prompt_tokens'];output=usage['completion_tokens']
        if not 0<=prompt<=INPUT_CAP or not 0<=output<=OUTPUT_CAP or usage['total_tokens']!=prompt+output:
            self.uncertain(ident);raise BudgetError('Token accounting inconsistent with approved reserve')
        cost=prompt*INPUT_RATE+output*OUTPUT_RATE
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT status FROM attempts WHERE id=?',(ident,)).fetchone()
            if row!=('reserved',):raise BudgetError('Attempt already settled or uncertain')
            db.execute("UPDATE attempts SET status='settled',cost=?,usage=? WHERE id=?",(str(cost),json.dumps(usage),ident))
        return str(cost)
