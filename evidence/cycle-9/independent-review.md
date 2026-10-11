# Independent cycle-9 evidence reassessment

Reviewer: independent subagent `/root/evidence_review`, separate from the
implementing agent. This assessment reviewed source and evidence read-only; the
only reviewer edit is this record. The review does not approve controller landing
or reconstruct missing chronology. No Git refs were changed.

## Scope and provenance

The external archive reviewed was
`/home/svetzal/.foundry/evidence/95089e675fb7e7089e236c9841b5c338/7804437f-9e3c-4bce-8d14-89f77810293f/`.
All 107 retained files listed in [original-manifest.json](original-manifest.json)
were independently compared byte-for-byte with those originals, and their sizes
and SHA-256 values verified. The repository copies under
[original/worktree/captures](original/worktree/captures/) preserve the original
`worktree/.foundry` contents with a renamed directory ancestor. Embedded paths
remain historical provenance. The originals were not modified.

Review inspected the actual [429 specification](../../src/mojentic/llm/gateways/omlx_429_recovery_spec.py),
the threaded HTTP fixture in `ollama_recovery_spec.py`, rejecting/corrected source
snapshots, historical manifests, proof logs, loopback records, complete final gate
stdout/stderr, audit inventories and [historical review](original/worktree/captures/review.md).
It also inspected the amended [conformance document](../../RECOVERY-CONFORMANCE.md),
[verification script](verify.py), and available current receipts/source inventory.

## Assertion inspection

The specification declares independent literal UTF-8 request bytes for ordinary,
schema-bearing structured and streaming requests. Actual server-received
`(path, body)` tuples and wire-observer bodies equal these literals. The fixture
uses `ThreadingHTTPServer`, reads request bytes from the socket and sends the
configured status and body; these are actual loopback sends.

Success assertions inspect numeric 429, Retry-After seconds/date/past/invalid/
absent states and numeric minima/delays, original `httpx.HTTPStatusError`, original
request bytes and private `busy-429` body. Unmasked identity objects are compared
directly: stable logical request ID, distinct attempt IDs, wire attempts 1/2,
send identities and lifecycle identities. The eight lifecycle transitions and
scheduled delay are exact. Content, validated structured object, model, usage,
finish reason and typed streaming terminal outcome are asserted.

Limit refusals cover ceiling, total budget and budget consumed before/during
admission. They assert one literal send, retained original cause identity/body/
history, no sleep, exact lifecycle and terminal outcome. Missing/rejecting
admission asserts one send and exact required/rejected lifecycle. Admission
refusal cases do not assert every lifecycle identity or captured header status,
unlike limit cases. Counts and test names alone were not used as evidence.

No runtime defect was found in these assertions. The retained final specification
is byte-identical to the delivered source.

## Historical receipts and omissions

All 102 entries in `artifact-hashes.json` match retained bytes. Rejecting and
corrected snapshots differ only by `reject(context)` becoming `allow(context)`.
Rejecting assertions run before the typed error propagates; this is an admission
input correction, not a demonstrated production defect. Top-level proof logs
equal the inner log copies. Earlier read-only cache and raw streaming-response
inspection failures remain execution/fixture failures.

All 11 final historical gate receipts resolve to complete retained output and
record exit zero. Output supports 915 passing tests, default 84% coverage,
explicit 85% coverage, Bandit no issues and both audits no vulnerabilities.
Historical audit inventories retain all 96 project distributions without skips.
These outputs establish their recorded results; they do not authenticate exact
complete source at every invocation.

The final hash list names 211 files, but only 15 source/config snapshots survive;
those match their hashes and 196 are absent. Resolving the proof hash list against
retained snapshots yields 23 matches, an evolved specification mismatch and five
absent snapshots: `recovery_spec.py`, `omlx_protocol_spec.py`, `omlx_spec.py`,
`omlx_stream.py` and `omlx_stream_spec.py`. The frozen `proof-loopback.jsonl`
matches the original proof hash; the later appended `logs/loopback.jsonl` differs.
The early specification is distinct from the expanded final matrix.

Historical `authenticated_capture.jsonl` contains zero oMLX 429 records. The 122
oMLX 429 records in the appended loopback log preserve server bodies and headers,
but omit recovery identities. Traceback representations truncate IDs. Source
compares unmasked objects directly; comprehensive historical literal identity
records were not retained. Missing artifacts are disclosed, not reconstructed.

## Current retention checks and limits

At this review checkpoint, all 241 entries in the current source inventory match
both the retained snapshots and delivered files. Four available current receipts
(full Flake8, fatal-error selection, Ruff and format checking) record exit zero,
resolve to complete output and carry the exact source-manifest digest. Remaining
current gates are still executing and are not approved by this checkpoint.

The verification script checks retained-byte integrity, historical receipt exit
agreement and log existence, snapshots and current source hashes. At inspection
it does not validate current `gates.json` receipt/binding fields; the reviewer
independently checked the four available entries. The amended conformance text
accurately distinguishes source assertions from missing literal identity records
and historical output from per-invocation source authentication.

No current controller synchronization/conflict-free reconciliation receipt was
established. Local refs, status and historical receipts cannot establish current
upstream synchronization or landing. Assessment is limited to the retained
evidence and its qualified claims. Newly established proof cannot repair
historical chronology, supply missing snapshots, prove whole-mission alignment,
live inference behavior, remote termination or idempotency.

## Final reassessment after relocation

The deliverable now resides in `evidence/cycle-9/`, outside MkDocs input. This
supersedes the earlier directory location and pending-gate checkpoint. Original
bytes and provenance remain unchanged. The final README and conformance text
preserve the historical omissions and limited claims described above.

The reviewer reran `UV_CACHE_DIR=/tmp/mojentic-cycle10-uv-cache uv run python
evidence/cycle-9/verify.py`; it exited zero. The revised verifier validates
current receipt exits, complete-log existence, exact source-manifest digests,
current and pre-relocation source snapshots, retained hashes and both historical
and current audit inventories. All 13 final gate entries bind to manifest
SHA-256 `25f1e1fa3da492157d2ef9b3872702bfb382735624a9cdba85e3f7666024fd4c`.
Their complete stdout/stderr was independently inspected. Both pytest runs pass
915 tests; coverage is 84% default and 85% explicit. Full lint/format checks pass,
Bandit reports no issues, both unfiltered audits report no known vulnerabilities,
and both current JSON inventories match all 96 project distributions without
skips or vulnerabilities. Outdated inspection and MkDocs complete successfully.
The final MkDocs capture has no new archived-snapshot broken-link warnings.

Earlier current-run captures retain their original directory locators, resolved
by the verifier to the new ancestor. The pre-relocation conformance snapshot is
exactly the final snapshot with every `evidence/cycle-9` occurrence replaced by
`docs/evidence/cycle-9`. The full earlier manifest digest matches the value
recorded in each earlier receipt; shared source/config snapshots match. This
authenticates the disclosed current-run recovery against previously recorded
digests. It does not establish a missing historical cycle-9 snapshot or chronology.

The current controller trace query reports `expired or unknown`. Current
synchronization and conflict-free controller reconciliation/landing evidence
remain absent. This final assessment supports retaining the focused deliverable
and its qualified evidence claims; it does not approve controller landing or
broader mission alignment. Updating this review requires regenerating its entry
in the retained artifact hash inventory.

Final checkpoint: after retained helper import ordering and explicit subprocess
check handling were corrected, the reviewer independently checked the latest 13
passing receipts against the same `25f1e1fa...` source-manifest digest and read
their complete logs. Both test runs again pass 915 cases at 84%/85% coverage.
Unfiltered audits remain clean; read-only host audit-cache warnings remain visible
as execution limitations. Final helper Ruff output passes. All 559 entries in
the sealed artifact inventory match bytes at this checkpoint, and the captured
final verifier output confirms 107 original copies, current receipts and source
bindings. No new evidence gaps were found. This added checkpoint requires the
implementer to reseal the review hash; controller reconciliation remains pending.
