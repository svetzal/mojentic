# Python 3.0.0 conformance — recovery admission

This is a partial decision map for the owner scope in
[../RELEASE-3.0.0.md](../RELEASE-3.0.0.md). It does not declare Python or the
coordinated release ready. Versions and publication remain on hold.

## Executable admission decisions

The local executable set is **recovery-admission-v1** in
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
| Pending admission cancels or expires without another dispatch and closes its task | `should_stop_pending_admission[cancelled-*]` and `[budget_exhausted-*]` |
| Semantic delivery prevents replay, even with an allow hook | `should_never_replay_after_delivering_content`: receives content followed by EOF without a terminal marker |
| Retry payload remains byte-identical; logical IDs stable and attempt IDs unique; safe lifecycle serialization | `assert_wire` assertions in each test above compare real outbound requests to captured bytes, identities, paths, payload semantics, reports and lifecycle fields |

Before the implementation change, the smallest public probe observed a real
503 request followed by `admission_rejected` for a hook returning `None` and
failed the required `admission_undecided` assertion. The same probe passed after
the shared admission change. No marker toggle or private-helper test was used.

Connection-establishment failures (`httpx.ConnectError`, `httpx.ConnectTimeout`)
are the narrow nonacceptance evidence used by the implementation. HTTP 429/5xx,
read/write failures and missing output do not demonstrate nonacceptance.
Cancellation, eligibility, immutable encoding, history limits and privacy rules
remain in the shared engine. Admission cannot prove remote termination or
idempotency.

## Unverified decisions and coordination findings

- This document verifies only this correction's admission decisions. Remaining
  October 12 amendment decisions are **unverified by this decision map**;
  existing `RECOVERY-CONFORMANCE.md` and provider specs are prior evidence, not
  a completed 3.0.0 audit.
- Native reasoning, model metadata/request fidelity and the other initiative
  audit fixes are **unverified here** and outside this task.
- Actual connect-timeout evidence is **not exercised** by the deterministic
  refused-connection probe. Remote provider execution, inference termination,
  idempotency and provider request-status APIs are **unverified/unsupported**.
- The initiative brief was read and its SHA-256 verified as
  `ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
  The referenced sibling `RELEASE-3.0.0.md` and
  `TRANSIENT-RECOVERY-2026-10.md` are absent from this isolated checkout.
  Exhaustive root-contract conformance cannot be certified here. The plan
  explicitly requires a distinct undecided outcome; `admission_undecided` is
  the Python spelling implemented here and needs coordinated cross-port
  confirmation if the root contract defines a different spelling.
- The new stream enum member and changed failure acceptance/report semantics
  are public boundary changes. **Paired cross-repository executable verification
  is missing**: this local set has no consumer-side run and is not a claim of
  provider/consumer compatibility. Coordinate a shared versioned executable
  set with affected consumers before coordinated release. No consumer
  repository was changed. Independent loopback fixtures prove Python behavior,
  not agreement with a live provider or another port.

## Verification record

Tested base commit: `e13328ff14052f7489f25829b29425084ab4964e`, plus the
uncommitted correction in this worktree. Foundry owns finalization; no refs were
changed. The final executable-set SHA-256 is
`7414bf79139efc31b12d9b63726e3a22c92e83e40d485e1a70a82f45663ef04a`
(`recovery-admission-v1`, the spec file above).

All commands below ran through `foundry capture --log-dir .foundry/logs --`.
Writable caches were selected with `UV_CACHE_DIR=/tmp/mojentic-uv-cache`,
`UV_TOOL_DIR=/tmp/mojentic-uv-tools` and `XDG_CACHE_HOME=/tmp/mojentic-cache`;
audit scopes and dependency versions were preserved.

| Command | Final result |
| --- | --- |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0 |
| `uv run pytest` | Exit 0; 1,360 passed, 85% coverage under configured `--cov=src` |
| `uv run bandit -c .bandit -r src` | Exit 0; zero issues |
| `uv run pip-audit` | Exit 0; no known vulnerabilities |
| `uv run flake8 src` | Exit 0 |
| `uv run ruff check src` | Exit 0; zero findings |
| `uv run pytest --cov` | Exit 0; 1,360 passed, 86% coverage; no repository coverage minimum is configured |
| `uv run mkdocs build` | Exit 0 |
| `uv export --format requirements-txt --no-emit-project` piped to `uvx pip-audit -r /dev/stdin --disable-pip` under `bash -o pipefail` | Exit 0; no known vulnerabilities |
| `uv pip list --outdated` | Exit 0; available updates reported; no dependency changes needed for an advisory |

`uv run ruff format src` also ran; the unrelated formatter-only edit was
restored, and the changed Python files were formatted. The final discovered
gate inventory contains only the root `.hone-gates.json`; all four gates
passed, including both advisory gates. The focused public admission suite
contains 89 passing cases. Behavioral proof JSON, field types, actual rejecting
exit 1 and corrected exit 0, and both existing capture logs were validated.

Consumer-side verification command/result/commit: **not available, not run**.
The Python results and local executable-set hash above do not fill that gap.

