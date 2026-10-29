"""Human-local hidden input only. Never pass a key as a command-line argument.

Prepared fallback, not executed by builder. Use only after approved dedicated key
creation through the correct authenticated official account. No login/key API.
"""
import getpass
import json
import os
from pathlib import Path
import sys
from provider import MODEL

ROOT=Path(__file__).resolve().parent
SECRET=ROOT/'.secrets'/'provider.json'


def store(key,target=SECRET):
    if not isinstance(key,str) or len(key.strip())<16 or any(ch.isspace() for ch in key):raise ValueError('Invalid secret input; no value is printed')
    target=Path(target)
    if target.parent.is_symlink():raise ValueError('Secret directory symlink refused')
    target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if target.parent.stat().st_mode&0o077:raise ValueError('Secret directory must be owner-only')
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'w') as f:json.dump({'NEBIUS_API_KEY':key,'NEBIUS_MODEL':MODEL,'FREIGHTSWITCH_ALLOW_LIVE':'approved','authorization':'2026-10-28 only;50 attempts;US$1 usage ceiling;synthetic-only'},f)


def load(target=SECRET):
    target=Path(target)
    if target.is_symlink() or target.parent.is_symlink() or target.stat().st_mode&0o077 or target.parent.stat().st_mode&0o077 or target.stat().st_uid!=os.getuid():raise ValueError('Secret file/directory must be owner-only and non-symlink')
    with target.open() as f:data=json.load(f)
    return {k:data[k] for k in ('NEBIUS_API_KEY','NEBIUS_MODEL','FREIGHTSWITCH_ALLOW_LIVE')}


if __name__=='__main__':
    if not sys.stdin.isatty():raise SystemExit('Use a local terminal with hidden input; no piped or command-line key')
    if SECRET.exists():raise SystemExit('Existing secret preserved; no overwrite')
    try:store(getpass.getpass('Dedicated FreightSwitch key (hidden; never paste in chat): '))
    except Exception:raise SystemExit('Secret setup refused; no value printed')
    print('Server-only secret stored with owner-only permissions. No inference or account action performed.')
