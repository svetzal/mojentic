import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

base = Path('evidence/cycle-9/current')
tracked = subprocess.check_output(['git', 'ls-files'], text=True).splitlines()
selected = [name for name in tracked if name.startswith(('src/', '.github/workflows/')) or name in ['AGENTS.md', 'RECOVERY-CONFORMANCE.md', 'CHARTER.md', 'pyproject.toml', 'uv.lock', 'setup.cfg', 'pytest.ini', '.coveragerc', '.bandit', 'mkdocs.yml', '.python-version']]
manifest = []
for name in selected:
    source = Path(name)
    destination = base / 'source' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    manifest.append({'source': name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
(base / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
source_hash = hashlib.sha256((base / 'source-manifest.json').read_bytes()).hexdigest()
environment = {'python': sys.executable, 'version': sys.version, 'prefix': sys.prefix,
               'distributions': sorted([(d.metadata['Name'], d.version) for d in importlib.metadata.distributions()]),
               'UV_CACHE_DIR': os.environ.get('UV_CACHE_DIR'), 'UV_TOOL_DIR': os.environ.get('UV_TOOL_DIR'), 'PIPAPI_PYTHON_LOCATION': sys.executable}
(base / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
env = dict(os.environ, PIPAPI_PYTHON_LOCATION=sys.executable, PIP_CACHE_DIR='/tmp/mojentic-cycle10-pip-cache')
gates = [
    ('flake8', ['uv', 'run', 'flake8', 'src']),
    ('lint', ['uv', 'run', 'flake8', 'src', '--count', '--select=E9,F63,F7,F82', '--show-source', '--statistics']),
    ('ruff', ['uv', 'run', 'ruff', 'check', 'src']),
    ('format', ['uv', 'run', 'ruff', 'format', '--check', 'src']),
    ('test', ['uv', 'run', 'pytest']),
    ('coverage', ['uv', 'run', 'pytest', '--cov']),
    ('bandit', ['uv', 'run', 'bandit', '-c', '.bandit', '-r', 'src']),
    ('audit', ['uv', 'run', 'pip-audit']),
    ('uvx-audit', ['uvx', 'pip-audit']),
    ('audit-inventory', ['uv', 'run', 'pip-audit', '--format', 'json']),
    ('uvx-audit-inventory', ['uvx', 'pip-audit', '--format', 'json']),
    ('outdated', ['uv', 'pip', 'list', '--outdated']),
    ('docs', ['uv', 'run', 'mkdocs', 'build']),
]
results = []
for name, command in gates:
    capture = ['foundry', 'capture', '--log-dir', str(base / 'gates' / name), '--', *command]
    result = subprocess.run(capture, env=env, capture_output=True, text=True, check=False)
    receipt = result.stdout + result.stderr
    (base / 'gates').mkdir(exist_ok=True)
    (base / 'gates' / (name + '.receipt.log')).write_text(receipt)
    results.append({'name': name, 'command': command, 'exit_code': result.returncode,
                    'receipt': str(base / 'gates' / (name + '.receipt.log')),
                    'source_manifest_sha256': source_hash})
    (base / 'gates.json').write_text(json.dumps(results, indent=2) + '\n')
    print(name, result.returncode, receipt, flush=True)
    if result.returncode:
        print('Gate failed; stop and inspect full retained output.', flush=True)
        sys.exit(result.returncode)
