# Python 3.0.0 conformance — recovery admission

This is a partial decision map for the owner scope in
`mojentic-unify/RELEASE-3.0.0.md`. It does not declare Python or the
coordinated release ready. Versions and publication remain on hold.

## Executable admission decisions

The local executable set is **recovery-admission-v2** in
[src/mojentic/llm/gateways/recovery_admission_spec.py](src/mojentic/llm/gateways/recovery_admission_spec.py).
All named tests below belong to `DescribeRecoveryAdmission`. The matrix covers
Ollama, oMLX and OpenAI ordinary, structured and streaming recovery, and
Anthropic ordinary recovery (its only supported recovery operation). Requests
cross real loopback HTTP, rather than independently mocked SDKs. Existing
provider-specific specs continue covering tool variants and unsupported APIs.

| Decision | Named executable verification |
| --- | --- |
| Eligible OpenAI/Anthropic failures retry without a hook | `should_apply_admission_without_changing_retry_bytes[absent-*]` |
| Ambiguous Ollama/oMLX acceptance requires a hook | `should_apply_admission_without_changing_retry_bytes[absent-*]` |
| Explicit allow authorizes resend; explicit reject prevents it | `should_apply_admission_without_changing_retry_bytes[allow-*]` and `[reject-*]` |
| Hook completion without a decision prevents resend with distinct `admission_undecided` | `should_apply_admission_without_changing_retry_bytes[None-*]` |
| Ordinary and streaming synchronous APIs expose the same stable undecided outcome | `should_surface_undecided_through_synchronous_public_apis` |
| Local nonacceptance permits no-hook retry only with evidence | `should_retry_evidenced_connection_refusal_without_hook`: a bound, non-listening socket actually refuses the first connection, then starts a real HTTP server for the retry |
| Capture hooks raising a connection-shaped exception cannot fabricate nonacceptance | `should_not_invent_nonacceptance_from_a_capture_hook_exception` verifies an actual HTTP 200 remains acceptance `unknown` and terminal |
| Caller validation after HTTP 200 cannot fabricate nonacceptance | `should_keep_acceptance_unknown_when_caller_validation_fails[ConnectError/ConnectTimeout-ollama/omlx/openai]` asserts status, headers/raw progress, original cause, unknown acceptance, ineligibility and one request |
| Pending admission cancels or expires without another dispatch and closes its task | `should_stop_pending_admission[cancelled-*]` and `[budget_exhausted-*]` |
| Semantic delivery prevents replay, even with an allow hook | `should_never_replay_after_delivering_content`: receives content followed by EOF without a terminal marker |
| Retry payload remains byte-identical; logical IDs stable and attempt IDs unique; safe lifecycle serialization | `assert_wire` assertions in each test above compare real outbound requests to captured bytes, identities, paths, payload semantics, reports and lifecycle fields |

The preserved v1 admission behavior remains: absent hooks allow eligible remote
retries; ambiguous local failures require admission; explicit and undecided
outcomes remain distinct. The v2 set retains every v1 case and adds validator
and capture-hook exception coverage. Before this correction, all six validator
cases received real HTTP 200 and retained its progress/cause but failed because
acceptance was `no`. After the source correction, acceptance is `unknown`, the
failure is ineligible, and no second HTTP request occurs.

Only transport trace evidence of failed TCP, Unix-socket or TLS connection
establishment establishes nonacceptance for a dispatched request. Both ordinary
and streaming paths install the same per-attempt trace callback, and
`_Attempt.failure` consumes that evidence. Beginning to send request headers
clears earlier connection failure evidence. A received response overrides it.
An exception class alone, HTTP 429/5xx, read/write failures or missing output
cannot establish nonacceptance. Transports without such trace evidence remain
conservative. This uses the documented [HTTPCore trace extension](https://www.encode.io/httpcore/extensions/#trace).
No provider or operation support was removed. Cancellation, immutable encoding,
bounded history, privacy and stream interruption rules remain in place.

## Authoritative scope inspected

The initiative brief SHA-256 was verified as
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
The authoritative root files were available read-only in the local
`mojentic-unify` checkout at commit
`4b08dcd1d87f520a4c70928c33a2bc84c228093d`:

- `RELEASE-3.0.0.md`: SHA-256
  `ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
- `TRANSIENT-RECOVERY-2026-10.md`, including the October 12 amendment: SHA-256
  `a53a3a4eb118fa4687dd703d6ce918dd40dd6cb4eda796abc6c429a6e932e7a3`.

The root amendment requires a distinct stable undecided reason and permits
idiomatic names; `admission_undecided` satisfies that decision. The port's older
October 9 contract copy does not supersede the root amendment.

## Contract boundary and initiative finding

The changed consumer/provider boundary is the caller or experiment harness
consuming Mojentic Python's public recovery reports, admission context and
terminal stream outcome. Mojentic Python is the provider of this API. The
change does not alter the HTTP request/response contract with Ollama, oMLX,
OpenAI or Anthropic. Those services are upstream providers, not consumers of
the changed acceptance/outcome fields. Other language ports implement parallel
APIs; running their tests would not verify a Python consumer.

Reuse the existing executable admission mechanism at
`src/mojentic/llm/gateways/recovery_admission_spec.py`, now
**recovery-admission-v2**, preserving the v1 supported cases. The existing live
oMLX fixtures (documented under `fixtures/omlx/README.md` in the gateways tree,
from root fixture revision `63409fa`) remain unchanged; they describe a different
boundary and do not verify Python admission consumers. No shared consumer-side
admission runner or paired verification record was found in the available
root contracts, root fixtures or this port.

**Initiative finding PY-ADMISSION-CONSUMER-VERIFICATION (open):** identify every
Python recovery consumer/harness and authorize its repository separately. Have
that consumer express its required reports, optional metadata, errors,
undecided outcome, conservative acceptance, retry permissions and supported
v1/v2 behavior in this same identifiable executable set; run consumer and
Mojentic-provider verification against the identical version/hash in both
repositories' gates. Record both commits, commands and results, deriving any
doubles from those verified contracts. Include the real harness journey and
trace/history/tool-count continuity checks required by the root contract.

No Python consumer repository or tested consumer revision is identified by the
initiative brief (its named downstream projects consume Elixir or Rust).
Consumer verification command, commit and result: **unavailable, not run**.
The local loopback tests verify the Python implementation through real HTTP;
their independently authored response fixtures are not paired contracts or
live vendor verification. This correction cannot close the cross-repository
finding. No other repository was edited. Keep the coordinated publication hold
until this gap and all six ports' owner scope are satisfied.

## Unverified decisions

- Remaining October 12 robustness decisions are **unverified by this decision
  map**; the older recovery map and provider specs are prior evidence, not a
  completed 3.0.0 audit.
- Native reasoning, model metadata/request fidelity and other initiative audit
  fixes remain **unverified here** and outside this correction.
- Actual connection timeout, Unix-socket and TLS failure paths are **not
  exercised** by the deterministic TCP-refusal tests. Remote execution,
  inference termination, idempotency and provider request-status APIs remain
  **unverified/unsupported**. Admission does not prove termination or idempotency.

## Verification record

Provider tested commit: preserved `3e3b353c4893a9153a194e7123b668aecfae9ea0`
plus the uncommitted correction in this worktree. Foundry owns finalization;
no refs changed. Executable set: **recovery-admission-v2**, SHA-256
`0c6e83d37a7c7e78ffa568d45bbbf3c22788dd6aa5254cdfd9863e9b6c8a558b`.

All verification commands run through `foundry capture --log-dir .foundry/logs --`.
Writable caches use `UV_CACHE_DIR=/tmp/mojentic-uv-cache`,
`UV_TOOL_DIR=/tmp/mojentic-uv-tools` and `XDG_CACHE_HOME=/tmp/mojentic-cache`.
Dependency versions and audit scope are unchanged.

| Command | Result |
| --- | --- |
| `uv run pytest src/mojentic/llm/gateways/recovery_admission_spec.py --no-cov` | Exit 0; 105 passed |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0 |
| `uv run pytest` | Exit 0; 1,376 passed, 85% configured coverage |
| `uv run bandit -c .bandit -r src` | Exit 0; zero issues |
| `uv run pip-audit` | Exit 0; no known vulnerabilities |
| `uv run flake8 src` | Exit 0 |
| `uv run ruff check src` | Exit 0; zero findings |
| `uv run pytest --cov` | Exit 0; 1,376 passed, 86% coverage |
| `uv run mkdocs build` | Exit 0 |
| `uv export --format requirements-txt --no-emit-project` piped to `uvx pip-audit -r /dev/stdin --disable-pip` under `bash -o pipefail` | Exit 0; no known vulnerabilities |
| `uv pip list --outdated` | Exit 0; available updates reported, no dependency changes |

`uv run ruff format src` ran successfully. Its unrelated formatter-only edit
was restored; only the correction's Python files retain formatting changes.
The sole discovered gate file is the root `.hone-gates.json`; all four gates,
including both advisory gates, passed. No coverage minimum is configured in
this repository. No dependencies, versions, release tags or Git refs changed.

Behavioral proof was validated as JSON with the required field types and
existing logs. The six public validator cases rejected the preserved defect
(exit 1) and passed with corrected evidence (exit 0); the probe asserts real
HTTP responses, status/progress/cause and conservative acceptance.
The same probe was rerun successfully on the final source. This proof and the
105-case matrix are local implementation evidence, not paired verification.

