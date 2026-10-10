# Python recovery conformance evidence

This first public increment covers opt-in Ollama ordinary and structured HTTP
completion only. It makes no cross-port parity claim. Streaming and other adapters
remain pending. All tests use scripted loopback HTTP, without live inference,
provider SDK mocking, session restarts, or external harness writes.

The implementation was compared with exact Rust revision
`4ca1ed279c02eab37827a1ed07c30e961155ecf3`, specifically its recovery types,
policy, engine, adapter, and conformance notes. Shared decisions include immutable
payloads, UUID correlation, bounded full jitter, permanent-status priority over
body transport failure, observed-before-capture progress, explicit ambiguous-local
admission, and private typed causes. Rust's streaming and additional provider work
are not included here. This correction retains the Python increment at
`b7c6b3d15303bc023c2145bf1cf8dfb713d931f7` rather than rebuilding it.
Both October 9 intent files and the task-supplied October 10 correction constraints
govern this work. The binding task supplement and provenance are recorded in
`.foundry/OCTOBER-10-SUPPLEMENT.md`; a separate external supplement file has not
been supplied and is not represented as inspected. Git finalization belongs to
Foundry; no commit, ref update, release or sibling write is part of this run.

The exact Rust files inspected are retained in `.foundry/reference/rust/`.
Rust's `engine.rs` checks cancellation/expiry after request capture and lifecycle
callbacks, retains private response headers, and filters outbound echoes from
provider IDs. Python now checks those dispatch boundaries and retains private
headers; conservatively, it omits all provider IDs from safe models, including
UUIDs. This is an explicit capability difference, not a whole-mission parity claim.

## Assertions through actual HTTP/public entrypoints

Specifications are in `src/mojentic/llm/gateways/ollama_recovery_spec.py`.
The following table names executable methods, rather than planned coverage.

| Requirement | Actual assertion / method |
| --- | --- |
| Proof first, capture failure after semantics | `should_retain_observed_semantics_before_failed_capture_without_replay`: public broker, one actual request, observed reasoning/content, zero delivered output, identical original `OSError`, private exact response, ordered interrupted transitions, safe serialization |
| 503 then success through all entrypoints | `should_recover_admitted_503_with_identical_bytes`: generate, generate_response, generate_object, send; literal request bytes/path equality, controls, schema where applicable, reasoning control, capture bytes, two endpoint requests, distinct unmasked UUIDs, stable logical ID, exact eight transitions |
| Bounded persistent 504 | `should_exhaust_504_with_complete_typed_history_and_private_echoes`: exactly three requests, complete ordered history, typed HTTPStatusError causes for every failure, private echo bytes, exact lifecycle sequence, safe credential formatting |
| Permanent 400/401/403 even with truncated bodies | `should_never_replay_permanent_status_even_when_body_transport_fails`: deliberately oversized Content-Length causes real RemoteProtocolError; status wins even when caller selects that status; one send |
| Malformed responses / provider error / schema rejection | `should_reject_malformed_provider_responses_without_replay` and `should_preserve_structured_validation_cause`: no resend, private evidence, original ValueError or ValidationError |
| Ambiguous local execution | `should_require_explicit_permission_for_ambiguous_local_503` and `should_require_admission_after_an_actual_read_timeout`: required/reject/allow, numeric status or typed real ReadTimeout, unknown acceptance, counted actual requests |
| Pending is not permission | `should_leave_admission_pending_until_allowed`, `should_reject_after_a_pending_admission_without_another_wire_attempt`: pending request remains at one endpoint send until an explicit decision |
| Retry-After seconds/date/invalid/absent/past/ceiling/budget | `should_honor_retry_after_without_shortening_minima`: injected wall/jitter/sleeper, exact sleeps and refusal wire counts |
| Cancellation in request/admission/backoff | `should_cancel_active_request_retaining_headers_and_raw_progress`, `should_cancel_pending_waits_and_never_resend`, `should_make_native_task_cancellation_authoritative`: prompt completion, closed pending coroutine, one send, AttemptFailed before one cancellation for an actual active request, retained history |
| Public session cancellation and metadata | `should_cancel_a_synchronous_chat_session_during_admission`: thread-safe cancellation through ChatSession.send, one request, no assistant insertion; provider request ID specifications now omit even UUID-valued metadata safely; `should_structure_invalid_image_preparation_without_a_wire_attempt`: private typed preparation cause and count zero |
| Zero-wire cancellation | `should_cancel_before_dispatch_without_inventing_wire_attempt`: empty endpoint requests/history, count zero, no attempt ID |
| Budget and active generation boundary | `should_expire_budget_while_admission_is_pending`, `should_refuse_admission_that_consumed_the_recovery_budget`, `should_allow_active_generation_to_finish_after_recovery_deadline`: wait expiry/refusal and admitted successful generation beyond deadline |
| Observed content/reasoning/tool output before capture failure | `should_prohibit_replay_of_each_observed_semantic_kind_when_capture_fails`: each kind, semantic progress before hook, all delivered counters zero, no resend, typed original cause, exact evidence, safe repr/JSON |
| Capture and lifecycle callback failures | `should_stop_on_capture_failure_without_inventing_wire_history`, `should_keep_observer_exceptions_private_and_prohibit_replay`: request/header/body boundaries and transition failures, no extra inference, private exact original causes |
| No hidden redirects/retries | `should_not_follow_redirects_or_count_hidden_attempts`: real 307 Location remains one endpoint request; every other scenario asserts actual endpoint request count |
| Immutable images and configuration | `should_freeze_images_and_controls_once_before_admission`: mutation during admission cannot alter encoded file bytes, messages, controls, or format across wire attempts |
| Legacy compatibility | `should_preserve_legacy_success_and_one_send_by_default` plus pre-change characterization of Ollama/broker/session specifications: successful legacy result, native reasoning response, finish handling and no recovery metadata |
| Success history and capabilities | `should_expose_success_history_and_truthful_capabilities`: failed attempt inspectable after success, exact counts, delivered success progress, explicit unsupported/unknown facilities |
| Tool safety and depth | `should_execute_tool_once_and_recover_only_the_subsequent_completion`: broker/session tool result followed by failed/recovered completion, one tool execution, three sends, byte equality; `should_preserve_tool_depth_limit_across_recovered_completions`: transport retry does not replenish tool budget |
| Actual authenticated request capture | `should_capture_the_authenticated_request_actually_sent`: five public entrypoints (Ollama completion, broker generate/generate_response/generate_object, session send), real URL Basic authorization versus received headers, literal byte equality across retries, stable logical UUID and distinct unmasked attempt UUIDs |
| Callback cancellation boundaries | `should_make_callback_cancellation_authoritative`: request, AttemptStarted, headers, body and AttemptSucceeded callbacks; exact endpoint counts, zero phantom history before send, typed cancellation causes, private headers/status/raw bytes, observed content/reasoning with zero delivered output, AttemptFailed before exactly one Cancelled on actual cancelled attempts |
| Admission and backoff callback cancellation | `should_cancel_at_admission_and_backoff_callbacks_without_resending`: AttemptFailed, AdmissionPending/Allowed, DelayScheduled and RetryStarted; one actual request, retained original failure and headers, typed terminal cancellation, no resend |
| Callback deadline expiry | `should_refuse_callback_expiry_without_phantom_retry`: AdmissionAllowed, DelayScheduled, RetryStarted, retry request capture and AttemptStarted; one actual request/history entry, one exhausted event, no success |
| Expiry observer failure | `should_keep_predispatch_expiry_observer_failure_private`: zero HTTP requests/history, safe interrupted RecoveryError and exact private observer cause when reporting pre-dispatch exhaustion fails |
| UUID-shaped secret metadata | `should_keep_uuid_shaped_secret_echoes_private`: actual outbound UUID credential and payload echoes in X-Request-ID/body; omitted from safe errors/repr/serialization/lifecycle, retained in explicit private headers/body and opt-in wire evidence |

`src/mojentic/llm/recovery_spec.py` additionally verifies overflow-safe exponential
ceilings, strict positive attempt limits, finite timing controls, modern/obsolete
HTTP dates, huge invalid Retry-After, frozen policy and excluded callback metadata.
This run's proof, complete command logs, wire evidence and source hashes are
retained under `.foundry/`. The authentication probe genuinely rejected the
preserved implementation (missing captured Authorization), then passed after the
source change. A fresh reproduction against the preserved source with the expanded
boundary fixtures yielded 20 failures and 2 passes; the corrected matrix passed
all 22 cases. This reproduction is not an unavailable historical run artifact.

Full suite: 624 tests passed. The mandatory `uv run pytest --cov` reports 82%
coverage of imported files; `uv run pytest` with the configured `--cov=src`
reports 80% across the source tree, including unimported files. No coverage
threshold is configured in the project; no gate was lowered. Full Flake8, required selective
Flake8, Bandit, both unfiltered pip-audit invocations and documentation build passed.
`uvx pip-audit` used `PIPAPI_PYTHON_LOCATION` to audit the project environment.
Ruff 0.16.10 passes both changed recovery files; repository-wide `ruff check src`
fails with 871 findings in existing source. That required gate remains blocked;
this report does not claim all project gates passed. No dependency was upgraded,
advisory suppressed or broad formatting/runtime cleanup performed.

Independent review inspected the actual rejecting/corrected logs and corrected
boundary matrix and reported no blocking defect in that scope (22 passing cases
initially, then 23 after independently reviewing the expiry-observer correction).
Its result and complete run logs are retained in `.foundry/independent-review.md`.
Earlier increment proof/capture logs referenced by the preserved report were not
present in this worktree and could not be recovered; their contents are not fabricated.

## Pending or deliberately unchanged

- Ollama streaming recovery and partial-stream conformance: pending, explicitly forbidden in this increment.
- oMLX, OpenAI and Anthropic recovery: pending. Existing adapters are unchanged.
- Native reasoning in outgoing Ollama history: the existing message model/adapter omit it; this increment preserves current payloads and successful native reasoning responses. No new history parity claim.
- Ordinary finish handling and reasoning-disabled behavior: unchanged.
- Provider codes and IDs: untrusted values, including UUID-valued request IDs, are omitted from safe metadata; raw headers are explicitly inspectable.
- Remote termination/cancellation and inference idempotency: unsupported or unknown; never inferred from HTTP status, socket close, timeout, or model listing.
- Live inference, efficacy, experiment registration/restarts, releases and Git finalization: outside this Foundry worktree task.
