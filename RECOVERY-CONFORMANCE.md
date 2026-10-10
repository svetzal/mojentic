# Python recovery conformance evidence

This first public increment covers opt-in Ollama ordinary and structured HTTP
completion only. It makes no cross-port parity claim. Streaming and other adapters
remain pending. All tests use scripted loopback HTTP, without live inference,
provider SDK mocking, session restarts, or external harness writes.

This lint correction starts from Python revision
`c95d805e617f521c77cc04866b2232c11d0baba8`. The initial worktree was clean;
`git ls-remote origin refs/heads/main` returned that same revision. The explicit
Foundry restriction forbids ref changes, so fetch, rebase, commit and push were
not performed. Finalization belongs to Foundry.

The October 9 intent files and the current task's correction constraints govern
this work. The full task-supplied supplement is preserved verbatim with its
provenance in `.foundry/OCTOBER-10-SUPPLEMENT.md`. That provenance distinguishes
the supplied task from a separate owner-authored document requested from the user.

The inherited report cited Rust revision
`4ca1ed279c02eab37827a1ed07c30e961155ecf3`. This lint task does not repeat that
cross-port inspection or claim to possess its old reference artifacts. Python
continues to omit provider IDs from safe metadata while retaining explicit private
headers. New evidence below measures the corrected Python source only.

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
## October 10 lint correction and migration impact

Ruff 0.16.10 initially reported **871 findings** across `src` at the starting
revision. `.foundry/ruff-before.json` retains every finding;
`.foundry/ruff-settings.txt` retains all enabled rules and exclusions;
`.foundry/ruff-version.txt` and `.foundry/baseline-hashes.json` retain the tool
version and exact original-source hashes. The commands were `uv run ruff
--version`, `uv run ruff check src --show-settings` and `uv run ruff check src
--output-format json`, captured through Foundry. Rules, dependency pins, quality
thresholds, configuration and audit scope were not changed.

Mechanical formatting, imports, Python 3.11 annotations and equivalent aliases
are separated for review in `.foundry/mechanical.patch`. The follow-on changes
and regressions are in `.foundry/behavior-sensitive.patch`; these two patches
compose to the source diff. Direct imports from defining modules preserve public
exports and avoid three import cycles exposed by sorting. Stage snapshots are
supporting evidence, not commits or claims that an intermediate tree passes gates.

Each behavior-sensitive correction addresses an original lint finding within the
task's stated owner authorization:

| Finding | Corrected behavior and migration impact | Actual evidence |
| --- | --- | --- |
| BLE001 in Ollama structured validation | Catch `ValidationError`; unexpected validator defects propagate instead of becoming an empty structured result. Expected malformed/schema failures keep their fallback. | First proof uses real HTTP: original source fails to raise `TypeError`; corrected source raises after exactly one request, with schema and non-streaming payload assertions. `.foundry/proof.json` and both referenced logs retain exits 1/0. |
| BLE001 in file/image boundaries | Expected filesystem and value errors retain error results or skipped-image fallbacks. Unexpected programmer errors now propagate; callers relying on swallowing arbitrary exceptions must handle those explicitly. | `.foundry/logs/filesystem-rejecting.log`: nine rejecting cases; corrected log: 52 passes. `.foundry/logs/image-header-baseline.log`: both adapters reject after reading a real local image; corrected log: 19 passes, including missing-image fallbacks. No provider SDK/private-function mocks were added. |
| BLE001 in OpenAI validation | Catch `ValidationError` only. The public SDK parse path already propagates validator defects; this is compatibility characterization, not a claimed new rejecting case. | Real OpenAI-compatible loopback completion passes on original and corrected source; one HTTP request and the completion path are asserted. |
| B006 in aggregator/default gateway headers; RUF012 in session messages | Fresh omitted event-type lists prevent cross-agent leakage; explicitly supplied lists retain identity. Gateway omitted/None/empty/explicit headers preserve all three completion paths. Session history remains initialized per instance. Access history on a session instance rather than the removed shared class default. | Aggregator rejection and explicit-list compatibility in `.foundry/logs/defaults-date-rejecting.log`; 12 real HTTP header checks across ordinary, structured and streaming paths pass on both original and corrected source. |
| DTZ005/DTZ006 | Use an aware instant converted to the local timezone. Default local wall-clock formatting stays unchanged; current-date `%z`/`%Z` now show the offset/name matching the returned timestamp. Tracer display remains local. | Date regression rejects blank offset/name on original source; default format passes before and after. Corrected datetime/aggregator/recovery matrix has 90 passes. |
| ASYNC230, S110 and retained example catches | Example file reading moves to `asyncio.to_thread`; intentionally broad example failure reporting and close behavior remain, with diagnostic logging. No new lint suppression is used. | Full async/realtime/example collection and suite pass. Active exclusions remain; Ruff removes redundant source `noqa` comments when their rule is already satisfied. |

All **223 existing recovery assertions** are AST-identical to the starting source;
`.foundry/recovery-assertions.json` records that comparison. Existing HTTP tests
still assert literal payload bytes, distinct attempts, typed causes, authoritative
cancellation, privacy and completed-tool execution exactly once. The first proof
was captured before expanding fixtures/docs or running the full quality suite.

Final gate commands and actual exit codes are recorded in `.foundry/quality.json`;
full captures remain outside this worktree under
`/home/svetzal/.foundry/tool-logs/mojentic-py-lint-c3/`. Corrected-source hashes
are retained in `.foundry/corrected-hashes.json`. Ruff across all `src`, full and
selective Flake8, tests, tests with coverage, formatter verification, documentation
build, Bandit, both unfiltered audits and the outdated-package check all exited
zero; their successful entries and exact logs are retained in that manifest. The final full suite
passes **656 tests**. Configured `--cov=src` reports **82%** across the source
tree; the separately requested `uv run pytest --cov` reports **84%** for imported
files. No coverage threshold is configured, and none was introduced or lowered.

Both audits set `PIPAPI_PYTHON_LOCATION` to this worktree's `.venv/bin/python`.
`.foundry/environment.json` records its executable, prefix and 96 distributions;
`.foundry/audit-environment-proof.json` matches all 96 package names and versions
to the unfiltered verbose audit. The standalone `uvx pip-audit` therefore audits
the project environment, not its own tool environment or a pip-only interpreter.
The unfiltered audits found no known vulnerabilities. The outdated-package report
is retained without changing dependencies or adding advisory suppressions.

Independent review and its final evidence reconciliation are retained in
`.foundry/independent-review.md`. This report makes no claim that historical
increment capture files were reconstructed; the rejecting/corrected evidence
above was actually observed during this task.

## Pending or deliberately unchanged

- Ollama streaming recovery and partial-stream conformance: pending, explicitly forbidden in this increment.
- oMLX, OpenAI and Anthropic recovery: pending. Lint-only adapter corrections do not add recovery.
- Native reasoning in outgoing Ollama history: the existing message model/adapter omit it; this increment preserves current payloads and successful native reasoning responses. No new history parity claim.
- Ordinary finish handling and reasoning-disabled behavior: unchanged.
- Provider codes and IDs: untrusted values, including UUID-valued request IDs, are omitted from safe metadata; raw headers are explicitly inspectable.
- Remote termination/cancellation and inference idempotency: unsupported or unknown; never inferred from HTTP status, socket close, timeout, or model listing.
- Live inference, efficacy, experiment registration/restarts, releases and Git finalization: outside this Foundry worktree task.
