"""Local release file integrity check (requires no third-party libraries)."""
from pathlib import Path
import csv, hashlib, sys
ROOT=Path(__file__).resolve().parent
errors=[];count=0
with (ROOT/'MANIFEST_SHA256.csv').open(newline='',encoding='utf-8') as f:
    for row in csv.DictReader(f):
        rel=row['path'];p=ROOT/rel
        if not p.is_file():errors.append(f'Missing: {rel}');continue
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        if digest != row['sha256']:errors.append(f'Checksum mismatch: {rel}')
        count+=1
print('Checked',count,'release files')
if errors:
    print('\n'.join(errors));sys.exit(1)
print('All manifest checksums passed')
