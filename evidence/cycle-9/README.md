# Cycle 9 evidence retention

This deliverable recovers available originals from external archive
`/home/svetzal/.foundry/evidence/95089e675fb7e7089e236c9841b5c338/7804437f-9e3c-4bce-8d14-89f77810293f/`
for source commit `f51ecdaabb841fea13cba2867b414ab670be1281`. The archive
and runtime remain unchanged. New retention verification does not repair
historical chronology or establish whole-mission alignment.

## Original evidence

[original-manifest.json](original-manifest.json) records every original archive
path, retained repository path, size and SHA-256. Original bytes are unchanged;
`worktree/.foundry/` is mapped to `original/worktree/captures/` so the retained
files are ordinary repository deliverables. Historical embedded execution paths
are preserved as provenance. They are resolved by [verify.py](verify.py), not
interpreted as current scratch locations. The local [.gitignore](.gitignore)
retains full `.log` files otherwise excluded by the project ignore rule.

| Evidence | Repository location |
| --- | --- |
| Original wrapper proof and logs | [proof](original/proof.json), [original proof](original/original-proof.json), [rejecting](original/rejecting.log), [corrected](original/corrected.log) |
| Worker behavioral proof | [proof.json](original/worktree/captures/proof.json) |
| Exact probe sources | [rejecting](original/worktree/captures/rejecting-source.py), [corrected](original/worktree/captures/corrected-source.py) |
| Full proof, failed fixture and gate captures | [logs](original/worktree/captures/logs/) |
| Frozen proof wire records | [proof-loopback.jsonl](original/worktree/captures/proof-loopback.jsonl) |
| Later appended wire records | [loopback.jsonl](original/worktree/captures/logs/loopback.jsonl) |
| Original hashes | [artifacts](original/worktree/captures/artifact-hashes.json), [proof](original/worktree/captures/proof-hashes.json), [final source](original/worktree/captures/final-source-hashes.json) |
| Gate receipts | [quality](original/worktree/captures/quality.json), [initial failures](original/worktree/captures/quality-initial.json), [final small gates](original/worktree/captures/final-small-gates.json) |
| Retained final snapshots | [final-source](original/worktree/captures/final-source/) |
| Environment and audit inventories | [environment](original/worktree/captures/environment.json), [audit bindings](original/worktree/captures/audit-environment-proof.json), [audit receipts](original/worktree/captures/audit-inventory-receipts.json) |
| Policy comparison and dirty state | [unchanged policies](original/worktree/captures/unchanged-source-policy.json), [dirty state](original/worktree/captures/final-dirty-state.log) |
| Original independent review and validation | [review](original/worktree/captures/review.md), [validation](original/worktree/captures/validation.json) |

## Verified claims and missing artifacts

All 102 historical artifact hashes match. All final gate receipts resolve to
retained full stdout/stderr and report exit zero. Their output supports 915
passing tests, 84% default / 85% explicit coverage, clean Bandit and both clean
unfiltered audits. This authenticates output, not the complete exact historical
source of each invocation.

Only 15 of 211 final source/config snapshots survive; 196 are missing. Five
proof-stage source snapshots are absent: `recovery_spec.py`,
`omlx_protocol_spec.py`, `omlx_spec.py`, `omlx_stream.py`, and `omlx_stream_spec.py`.
The early proof specification hash matches `corrected-source.py`, not the evolved
final matrix. The proof loopback hash matches the frozen `proof-loopback.jsonl`,
not the later appended `logs/loopback.jsonl`. The verifier reports these differences
explicitly. Original claims and hash lists remain preserved, with these qualifications.

Rejecting and corrected snapshots differ only by the admission input from reject
to allow. Failed read-only-cache and streaming-response-inspection runs establish
execution/fixture problems, not demonstrated production defects. The retained
final 429 specification equals delivered trunk byte-for-byte. Source asserts
independent literal UTF-8 payloads against actual loopback server receives and
wire captures. It checks numeric statuses/minima, original causes/body, unmasked
identity objects, lifecycle order, limit/admission refusals and typed terminal
outcomes. See [independent-review.md](independent-review.md) for precise assertion
scope and qualifications.

Historical wire records contain server bytes and headers; the 122 oMLX 429
loopback entries omit recovery identities. `authenticated_capture.jsonl` contains
no oMLX 429 records and traceback IDs are truncated. Direct comparisons of
unmasked identity objects in source do not establish retained complete literal
identity records. Missing artifacts are disclosed, not reconstructed.

## Current validation

[retention-proof.json](current/retention-proof.json) records the first direct
acceptance probe. Its original scratch locator is retained as provenance; the
same complete output is [retained here](current/2-1791688581580232652.stdout.log).
[Final direct proof](current/final-retention-proof.json) and
[retention-probe.py](current/retention-probe.py) verify every copy and the final
specification comparison. [Verification output](current/verification/) includes
individual hash, receipt and snapshot results; rerun with
`uv run python evidence/cycle-9/verify.py`.

[Source manifest](current/source-manifest.json) and [exact source/config copies](current/source/)
bind current [gate receipts](current/gates.json) to the resulting source, rather
than to an inferred historical tree. [Environment inventory](current/environment.json)
records the interpreter and installed versions. Both unfiltered pip-audit commands
use `PIPAPI_PYTHON_LOCATION` for this project interpreter; writable uv/pip caches
address host cache restrictions. Scope, pins, dependencies, policies, floors,
exclusions and suppressions are unchanged. Ruff formatting is checked without
rewriting production files. No coverage floor is configured.

[Controller status](current/controller-status/), [history](current/controller-history/)
and [historical execution trace](current/controller-trace/) are read-only queries.
They do not certify current synchronization or conflict-free landing. A current
controller reconciliation receipt is missing. Foundry must synchronize arrivals,
stop on conflicts, independently review and land the focused deliverable directly
on main. The worker does not fetch, rebase, commit, push, merge, tag or mutate refs.

Final validation runs full Flake8 and the required fatal-error selection, Ruff and
format checking, pytest and explicit coverage, Bandit, both unfiltered audits,
both JSON audit inventories, outdated-package inspection and MkDocs. All 13
checks pass. Both test runs pass 915 tests; coverage is 84% default / 85% explicit.
Both audit inventories exactly match all 96 installed project distributions,
with zero skips or vulnerabilities. No source, dependency or policy edits were
needed. The first standalone audit failed on a read-only uv tool directory;
[initial receipts](current/initial-gates.json) retain that execution failure.
The successful retry uses a temporary `UV_TOOL_DIR` as recorded in the environment.

Full captures produced before relocation retain their original output paths;
the verifier resolves `docs/evidence/cycle-9/` to `evidence/cycle-9/`. Earlier
current-run receipts are checked against a
[pre-relocation manifest](current/pre-relocation-source-manifest.json).
Its documentation snapshot was recovered by reversing only the link ancestor
rename and verifying the complete manifest against the SHA-256 recorded before
each earlier invocation. Shared runtime/config snapshots are identical. This is
explicitly current-run recovery, not a recovered historical cycle-9 snapshot.
[Tool versions](current/tooling/) and [Ruff settings](current/ruff-settings/) are
retained. [Worker dirty state](current/worker-git/) and [read-only refs](current/refs/)
show the focused uncommitted deliverable. The
[current controller trace query](current/controller-current-trace/) returned
expired/unknown; the synchronization/landing receipt remains missing.

[retained-hashes.json](retained-hashes.json) inventories retained files (excluding
itself and its final verification captures to avoid recursive self-hashing).
