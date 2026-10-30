"""Source-tree digest captured at server startup, not process attestation."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
digest=hashlib.sha256()
for path in sorted(list(ROOT.glob('*.py'))+list((ROOT/'static').glob('*'))):
    if path.is_file():digest.update(str(path.relative_to(ROOT)).encode()+b'\0'+path.read_bytes()+b'\0')
SOURCE_DIGEST=digest.hexdigest()
BUILD_ID='FS-1.6-public-'+SOURCE_DIGEST[:12]
