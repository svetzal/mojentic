import hashlib
import json
from pathlib import Path

records = json.loads(Path('evidence/cycle-9/original-manifest.json').read_text())
for record in records:
    data = Path(record['repository_path']).read_bytes()
    assert len(data) == record['size']
    assert hashlib.sha256(data).hexdigest() == record['sha256']
path = 'src/mojentic/llm/gateways/omlx_429_recovery_spec.py'
assert Path('evidence/cycle-9/original/worktree/captures/final-source', path).read_bytes() == Path(path).read_bytes()
print(f'PASS: {len(records)} original artifacts retain exact bytes; final 429 specification equals delivered trunk.')
