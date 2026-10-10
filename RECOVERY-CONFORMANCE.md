# Python recovery conformance evidence

This increment covers opt-in Ollama ordinary and structured HTTP completion.
Streaming and remaining provider alignment stay pending. Tests use scripted
loopback HTTP and local files; no live inference or experiment restart occurred.

## Reconciliation provenance

The worker began with clean HEAD `1cacf50037c9f60e91161df29e6efd955aa2d535`,
the preserved lint cleanup, and did not rebuild it. Its parent is
`c95d805e617f521c77cc04866b2232c11d0baba8`. The historical c3 synchronization
capture names that parent as remote main. This historical receipt is not a claim
that the controller or remote was independently synchronized during this run.
Read-only observations are retained in the durable `synchronization.json`.
Foundry owns landing directly on main; the worker performed no ref mutations.

All evidence named below resides durably in
`/home/svetzal/.foundry/tool-logs/mojentic-py-lint-c4/` unless explicitly marked c3.
`TASK-POLICY.txt` is the verbatim task-supplied correction plan and authorization;
it is not a separately authenticated owner document. Baseline and preserved
directories contain verbatim tracked source, policies and manifests, with
`baseline-hashes.json` and `preserved-hashes.json`. `evidence-index.json` hashes
the completed evidence set. These replace the inherited dangling `.foundry`
references; the missing old supplement, stage snapshots and review were not
recovered and are not claimed verified.

Historical captures survive in
`/home/svetzal/.foundry/tool-logs/mojentic-py-lint-c3/` and are indexed with hashes
in `historical-log-index.json`. The rejecting/corrected probes and final checks
below were reproduced in this run, not relabeled historical captures. The exact
prior suppression-guard flagged payload and its provenance were unavailable in
the inspected c3 evidence. Independent inspection resolves the observable source
and policy questions, without claiming to verify that unavailable guard input.

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

## Lint correction and behavioral proof

The original cleanup remains in `preserved.patch`. Full independent source
review covers all 175 changed files in `review-full.diff`, with normalized AST
inspection in `review-semantic.diff`. Worker refinements name the Ollama local
structured result and annotate session history on its instance. They introduce
no additional runtime behavior. Focused worker changes are separated into
`mechanical.patch` and `behavior-sensitive.patch`; old missing staged patches
have not been reconstructed.

The first probe ran before fixture expansion or full quality checks. It exercised
public structured completion through the real Ollama SDK and loopback HTTP:
baseline exit 1 (validator TypeError swallowed), corrected exit 0 (TypeError
propagated). It asserts exact schema, literal immutable request bytes, actual
authentication and exactly one wire request. `.foundry/proof.json` and its two
existing logs satisfy the behavioral proof shape; durable copies, commands and
hashes are `proof.json`, `rejecting-proof.json`, `corrected-proof.json` and
`foundry-evidence/`. The failed intermediate probe expectations are retained
honestly in `proof-corrected*` captures; the final passing probe fixes header
casing and expected SDK serialization, without changing runtime logic.

| Licensed change | Reproduced rejecting and corrected evidence |
| --- | --- |
| Structured validator exception boundary | First probe above; additional `structured_boundary_spec.py` tests the public broker with exact schema/payload/auth and one request. OpenAI SDK already propagated validator defects on baseline; its schema/payload/auth checks are compatibility characterization. |
| Filesystem/image exception boundaries | `behavior-rejecting` captures TypeError swallowed for filesystem and both real-image adapters; `behavior-corrected` passes those tests and missing-file/image fallback tests. |
| Mutable defaults | Aggregator omitted lists are isolated; baseline rejection and corrected pass in behavior captures. Explicit-list identity passes on both. The twelve real HTTP header checks preserve omitted/None/empty/explicit headers on ordinary, structured and streaming paths. |
| Session class history | Baseline class-level history exists and rejects the instance-only contract; corrected history is isolated, system message retained, and no shared class list remains. |
| Local timezone | Baseline lacks offset/name for `%z %Z`; corrected local aware instant matches returned timestamp. Default wall-clock format passes on both. |
| Async example file I/O | `async-file-rejecting` and `async-file-corrected` execute the exact original file-read source slice against a real FIFO. Baseline blocks the event loop heartbeat; corrected preserves Unicode file contents and permits the heartbeat before reading completes. This is a source-slice probe, not execution of the model-using whole example. |

Behavior commands, actual exits and complete log hashes are in
`behavior-rejecting.json`, `behavior-corrected.json`, `async-file-rejecting.json`
and `async-file-corrected.json`. Specs are durably retained in `behavior-specs/`.
No SDK or private function mocks were introduced. Public broker proof mocks only
our tokenizer gateway with its class spec.

## Suppression and policy reconciliation

`policy-comparison.json` verifies dependencies, lockfile, runtime requirements,
Bandit skips/exclusions, coverage settings and configured test/lint gates remain
identical to c95d805. `baseline-ruff` reproduces exact findings; `baseline-settings`
and `final-settings` retain enabled rules, exclusions and resolution. No enabled
rule, threshold, dependency, audit scope or active suppression was changed here.

Independent `review-policy-inventory.json` retains exact annotated source and
hashes. `review-ble001-baseline.json`, `review-ble001-cleanup.json`,
`review-ruf100-baseline.json` and `review-ble001-rule.log` explain the preserved
cleanup: four necessary broad-catch annotations remain; two formerly silent
close handlers now log with `exc_info=True`, satisfying BLE001 directly; one
removed annotation was already redundant. Restoring redundant annotations would
introduce RUF100. No genuine suppression was waived and no advisory accepted.
These isolated rule diagnostics do not replace the full project Ruff check.

## Final verification and independent review

`quality.json` records exact commands and actual final exit codes for full Ruff,
format application/check, full and required selective Flake8, pytest, pytest
--cov, MkDocs, Bandit, both unfiltered audits and the outdated-package check.
Complete captures and tool versions remain outside the worktree. Early uvx
captures failed because its default tool directory was read-only; reruns use a
writable UV_TOOL_DIR and preserve the same audit scope.

`environment.json` records the project interpreter, prefix and distribution
versions. Both audits explicitly use this `.venv/bin/python` via
PIPAPI_PYTHON_LOCATION. `audit-environment-proof.json` matches their complete
verbose JSON dependency name/version sets against this project environment and
checks empty ignore lists and vulnerability lists. The uvx tool interpreter is
separate; the inspected packages are the project environment. No dependency was
updated in response to the outdated report.

`recovery-assertions.json` proves every baseline recovery assertion remains in
order. Full executed tests retain exact bytes, real auth headers, distinct
unmasked logical/attempt IDs, typed causes, cancellation ordering and completed
tool execution once. Public exports and import-cycle safety were independently
reviewed and exercised by full collection. `corrected-hashes.json` records final
source. `review.md` and `final-review.md` retain independent findings and final
reconciliation, including the explicit unavailable-provenance limitation.

## Pending

- Streaming recovery and partial-stream conformance.
- oMLX, OpenAI and Anthropic recovery/provider alignment.
- Native reasoning in outgoing Ollama history; existing payload behavior is preserved.
- Ordinary finish handling and disabled-reasoning parity.
- Remote cancellation/termination and inference idempotency remain unsupported or unknown.
- Live inference, experiment restarts, releases and Git finalization are outside this task.
