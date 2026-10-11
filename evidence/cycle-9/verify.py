"""Verify retained bytes; report historical omissions without filling them in."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'evidence/cycle-9'


def repository_path(name: str) -> Path:
    return ROOT / name.replace('docs/evidence/cycle-9/', 'evidence/cycle-9/')
CAPTURES = BASE / 'original/worktree/captures'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def historical_path(name: str) -> Path:
    if name.startswith('.foundry/'):
        return CAPTURES / name.removeprefix('.foundry/')
    return CAPTURES / 'final-source' / name


def verify() -> dict[str, object]:
    originals = json.loads((BASE / 'original-manifest.json').read_text())
    for item in originals:
        path = repository_path(item['repository_path'])
        assert path.stat().st_size == item['size'], path
        assert digest(path) == item['sha256'], path
    reports = {}
    for name in ['artifact-hashes.json', 'proof-hashes.json', 'final-source-hashes.json']:
        matched, missing, mismatched = [], [], []
        for path, expected in json.loads((CAPTURES / name).read_text()).items():
            resolved = historical_path(path)
            if not resolved.exists():
                missing.append(path)
            elif digest(resolved) != expected:
                mismatched.append({'path': path, 'expected': expected, 'actual': digest(resolved)})
            else:
                matched.append(path)
        reports[name] = {'matched': matched, 'missing': missing, 'mismatched': mismatched}
    assert not reports['artifact-hashes.json']['missing']
    assert not reports['artifact-hashes.json']['mismatched']
    snapshot_comparison = []
    for archived in sorted((CAPTURES / 'final-source').rglob('*')):
        if archived.is_file():
            relative = archived.relative_to(CAPTURES / 'final-source')
            delivered = ROOT / relative
            equal = delivered.exists() and archived.read_bytes() == delivered.read_bytes()
            snapshot_comparison.append({'source': str(relative), 'equals_delivered': equal})
            # Conformance documentation is intentionally amended by this retention correction.
            if str(relative) != 'RECOVERY-CONFORMANCE.md':
                assert equal, relative
    rejecting = (CAPTURES / 'rejecting-source.py').read_text()
    corrected = (CAPTURES / 'corrected-source.py').read_text()
    assert rejecting.replace('return await reject(context)', 'return await allow(context)') == corrected
    proof_hashes = json.loads((CAPTURES / 'proof-hashes.json').read_text())
    assert digest(CAPTURES / 'corrected-source.py') == proof_hashes['src/mojentic/llm/gateways/omlx_429_recovery_spec.py']
    proof_loopback = digest(CAPTURES / 'proof-loopback.jsonl')
    expected_loopback = json.loads((CAPTURES / 'proof-hashes.json').read_text())['.foundry/logs/loopback.jsonl']
    assert proof_loopback == expected_loopback
    receipts = []
    for metadata in ['quality-initial.json', 'quality.json', 'final-small-gates.json', 'audit-inventory-receipts.json']:
        for item in json.loads((CAPTURES / metadata).read_text()):
            receipt = item.get('capture_receipt', item.get('output', ''))
            if 'receipt' in item:
                receipt = historical_path(item['receipt']).read_text()
            exits = re.findall(r': exit (-?\d+)', receipt)
            assert exits and int(exits[-1]) == item['exit_code'], (metadata, item)
            logs = re.findall(r'(?:stdout|stderr): (.+)', receipt)
            assert len(logs) == 2, (metadata, item)
            for log in logs:
                assert historical_path(log).is_file(), log
            receipts.append({'metadata': metadata, 'command': item['command'], 'exit_code': item['exit_code'],
                             'full_logs': [str(historical_path(log).relative_to(ROOT)) for log in logs],
                             'exact_invocation_source_snapshot': 'not retained; final subset only'})
    for name in ['proof.json', 'original-proof.json']:
        location = BASE / 'original' / name
        proof = json.loads(location.read_text())
        assert proof['kind'] == 'behavioral'
        assert isinstance(proof['source_change'], str) and proof['source_change']
        for stage, expected in [('rejecting', 1), ('corrected', 0)]:
            assert type(proof[stage]['exit_code']) is int and proof[stage]['exit_code'] == expected
            assert isinstance(proof[stage]['command'], str) and proof[stage]['command']
            assert isinstance(proof[stage]['log'], str) and proof[stage]['log']
            log = proof[stage]['log']
            resolved = historical_path(log) if log.startswith('.foundry/') else BASE / 'original' / log
            assert resolved.is_file(), log
    current_manifest = BASE / 'current/source-manifest.json'
    if current_manifest.exists():
        for item in json.loads(current_manifest.read_text()):
            assert digest(ROOT / item['source']) == item['sha256'], item
            assert digest(BASE / 'current/source' / item['source']) == item['sha256'], item
    proof = json.loads((BASE / 'current/final-retention-proof.json').read_text())
    assert proof['kind'] == 'direct' and isinstance(proof['reason'], str) and proof['reason']
    assert type(proof['corrected']['exit_code']) is int and proof['corrected']['exit_code'] == 0
    assert isinstance(proof['corrected']['command'], str) and proof['corrected']['command']
    assert isinstance(proof['corrected']['log'], str) and proof['corrected']['log']
    assert (BASE / 'current' / Path(proof['corrected']['log']).name).is_file()
    current_receipts = []
    gates_path = BASE / 'current/gates.json'
    if gates_path.exists():
        for item in json.loads(gates_path.read_text()):
            assert item['source_manifest_sha256'] == digest(current_manifest), item
            receipt = (repository_path(item['receipt'])).read_text()
            exits = re.findall(r': exit (-?\d+)', receipt)
            assert exits and int(exits[-1]) == item['exit_code'], item
            logs = re.findall(r'(?:stdout|stderr): (.+)', receipt)
            assert len(logs) == 2, item
            for log in logs:
                assert (repository_path(log)).is_file(), log
            current_receipts.append(dict(item, full_logs=[str(repository_path(log).relative_to(ROOT)) for log in logs]))
    earlier_manifest = BASE / 'current/pre-relocation-source-manifest.json'
    if earlier_manifest.exists():
        for item in json.loads(earlier_manifest.read_text()):
            location = BASE / 'current/source' / item['source']
            if item['source'] == 'RECOVERY-CONFORMANCE.md':
                location = BASE / 'current/pre-relocation-source' / item['source']
            assert digest(location) == item['sha256'], item
        for name in ['initial-gates.json', 'pre-relocation-gates.json', 'before-helper-cleanup-gates.json']:
            for item in json.loads((BASE / 'current' / name).read_text()):
                expected_manifest = current_manifest if name == 'before-helper-cleanup-gates.json' else earlier_manifest
                assert item['source_manifest_sha256'] == digest(expected_manifest), item
                receipt = repository_path(item['receipt']).read_text()
                exits = re.findall(r': exit (-?\d+)', receipt)
                assert exits and int(exits[-1]) == item['exit_code'], item
                logs = re.findall(r'(?:stdout|stderr): (.+)', receipt)
                assert len(logs) == 2, item
                for log in logs:
                    assert repository_path(log).is_file(), log
    artifact_manifest = BASE / 'retained-hashes.json'
    if artifact_manifest.exists():
        for name, expected in json.loads(artifact_manifest.read_text()).items():
            assert digest(BASE / name) == expected, name
    audit_bindings = []
    inventories = [(CAPTURES, CAPTURES / 'environment.json', CAPTURES / 'audit-inventory-receipts.json')]
    if gates_path.exists():
        inventories.append((BASE / 'current', BASE / 'current/environment.json', gates_path))
    def normalize(name: str) -> str:
        return re.sub(r'[-_.]+', '-', name).lower()
    for location, environment_path, receipt_path in inventories:
        environment = json.loads(environment_path.read_text())
        expected = {(normalize(name), version) for name, version in environment['distributions']}
        for item in json.loads(receipt_path.read_text()):
            command = item['command']
            if '--format' not in command or 'json' not in command or 'pip-audit' not in command:
                continue
            if location == CAPTURES:
                receipt = item['output']
                log = historical_path(re.findall(r'stdout: (.+)', receipt)[0])
            else:
                receipt = (repository_path(item['receipt'])).read_text()
                log = ROOT / re.findall(r'stdout: (.+)', receipt)[0]
            audit = json.loads(log.read_text())
            dependencies = audit['dependencies']
            observed = {(normalize(d['name']), d['version']) for d in dependencies}
            assert observed == expected, (log, expected - observed, observed - expected)
            assert not any(d.get('vulns') or d.get('skip_reason') for d in dependencies), log
            audit_bindings.append({'inventory': str(log.relative_to(ROOT)), 'matches_environment': True,
                                   'distribution_count': len(observed), 'vulnerabilities': 0, 'skipped': 0})
    return {'current_receipts': current_receipts, 'audit_bindings': audit_bindings,
            'original_files_verified': len(originals), 'historical_hashes': reports,
            'historical_receipts': receipts, 'final_snapshot_comparison': snapshot_comparison,
            'proof_snapshots': 'exact one-line rejection-to-admission input change',
            'frozen_proof_loopback_hash_matches': True,
            'chronology': 'New proof does not repair historical chronology',
            'scope': 'No whole-mission alignment claim; no controller reconciliation claim'}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
