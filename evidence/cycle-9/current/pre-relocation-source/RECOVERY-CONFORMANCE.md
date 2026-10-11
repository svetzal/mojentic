# Python recovery conformance evidence

## Cycle 9: durable evidence recovered from f51ecda

This retention correction preserves the existing oMLX 429 implementation and
specification at `f51ecdaabb841fea13cba2867b414ab670be1281`. Runtime source,
fixtures, dependencies, quality policies and release files are unchanged.

Recovered original captures now live in
[docs/evidence/cycle-9](docs/evidence/cycle-9/README.md). The
[provenance manifest](docs/evidence/cycle-9/original-manifest.json) maps every
external archive path to its repository-relative copy and SHA-256. The original
archive is unchanged. Only the directory ancestor `worktree/.foundry` becomes
`original/worktree/captures`; original file bytes and embedded historical paths
remain intact. Those embedded paths describe the archived execution, not current
committed locations.

The retained [rejecting snapshot](docs/evidence/cycle-9/original/worktree/captures/rejecting-source.py)
and [corrected snapshot](docs/evidence/cycle-9/original/worktree/captures/corrected-source.py)
differ only in the admission input, reject to allow. The real loopback 429
HTTP-date probe first asserts one literal request, numeric status 429, a
three-second minimum and rejection lifecycle, then propagates `RecoveryError`.
The corrected probe asserts two identical sends and successful admitted recovery.
[Full proof output](docs/evidence/cycle-9/original/worktree/captures/logs/)
and [frozen loopback records](docs/evidence/cycle-9/original/worktree/captures/proof-loopback.jsonl)
are retained. Newly established proof does not repair historical chronology.
Earlier read-only cache and raw streaming-response inspection failures are
execution/fixture failures, not evidence of production defects.

The delivered [HTTP specification](src/mojentic/llm/gateways/omlx_429_recovery_spec.py)
uses independent literal UTF-8 payloads for ordinary, structured and streaming
requests. Success cases compare actual server sends and captures, numeric 429
and Retry-After states/minima, original HTTP causes/body, unmasked logical and
attempt identities, exact eight lifecycle transitions, scheduled delay and typed
terminal responses. Limit refusals compare lifecycle identities and captured
429 status, one actual send, original cause/history, no sleep and typed terminal
failure. Admission refusals assert one send and exact transitions/outcomes but
do not assert every lifecycle identity or captured header status. Counts and
names alone do not establish these assertions.

The [independent reassessment](docs/evidence/cycle-9/independent-review.md)
qualifies the historical retention claims. All 102 artifact hashes match. Only
15 of 211 final source/config snapshots survive; 196 are missing. Exact complete
source at each historical gate invocation is not retained. The proof-stage
specification differs from the expanded final specification; the frozen proof
loopback matches its historical hash while the subsequently appended log differs.
Five proof source snapshots are absent. Historical loopback records contain
literal wire bodies/headers, but omit recovery identities; traceback IDs are
truncated. Source assertions compare unmasked objects, which does not establish
comprehensive historical literal identity records. See the
[verification output](docs/evidence/cycle-9/current/verification/) for every hash,
receipt and snapshot comparison. The retained final specification equals trunk.

Historical [gate receipts](docs/evidence/cycle-9/original/worktree/captures/quality.json)
resolve to full output supporting 915 passing tests, default 84% and explicit
85% coverage, and clean unfiltered audits. No coverage floor is configured.
[Current gate receipts](docs/evidence/cycle-9/current/gates.json) and full captures
are bound to the [current source inventory](docs/evidence/cycle-9/current/source-manifest.json).
Current results and limitations are recorded in the evidence index; historical
receipts are not promoted to per-invocation source authentication.

The starting tree was clean at `f51ecda`. Read-only controller status/history/trace
captures are retained in the evidence index. They do not substitute for a current
synchronization and conflict-free landing receipt. Foundry must reconcile arrivals,
stop on conflicts and land this focused deliverable directly on main. Worker refs
are unchanged; this deliverable remains uncommitted for controller review. No
whole-mission alignment, release, live inference, sibling write or experiment
restart is claimed.

## oMLX provider increment at d8ad832

This increment adds opt-in oMLX ordinary, structured and tool-capable streaming
completion recovery from `d8ad832deb786415eb89adeae27325c809d9c828`.
It does not establish whole-mission or coordinated-port conformance. Historical
Ollama evidence and missing-artifact disclosures below remain preserved.

The starting tree was clean. Worker Git operations were read-only: HEAD and
`refs/remotes/origin/main` both named the starting revision; `git ls-remote origin
refs/heads/main` returned that same revision during implementation. The retained
controller receipt records earlier fetch/pull at `c95d805`, an ancestor; it does
not certify current controller synchronization. Foundry must reconcile arrivals,
stop on conflicts, review and land directly on main. No worker ref mutation,
release, dependency change or live inference was performed.

The comparison uses retained Rust source for exactly
`4ca1ed279c02eab37827a1ed07c30e961155ecf3`, especially `frames.rs`,
`engine.rs` and `types.rs`, together with both normative root documents. The
October 10 supplement was recovered from the controller's Python definition JSON
and preserved verbatim in the evidence archive. Prior missing historical evidence
remains disclosed; this does not reconstruct old stages.

Durable evidence is under
`/home/svetzal/.foundry/tool-logs/mojentic-py-omlx-c8/`: early rejecting/passing
proof and source, complete foundry captures, loopback wire records, exact source
and Rust hashes, controller receipt/supplement, and independent source review.
The first rejecting probe exposed the absent public recovery API; its corrected
run asserted content observation before capture-hook failure at actual loopback
HTTP, zero delivered content, original typed cause, exact partial bytes, one wire
request, and started/failed/interrupted lifecycle order. Additional probe results
and gates are recorded in the archive without relabeling failed fixture runs.

| Acceptance evidence in `omlx_recovery_spec.py` | Public boundary and assertions |
| --- | --- |
| `should_recover_503_with_stable_exact_semantic_bytes_and_lifecycle` | Ordinary, structured and streaming gateway calls; seconds/date/invalid Retry-After, deterministic clock/jitter/sleep, literal independently specified history/tools/schema/control bytes, bearer authentication, same logical ID, distinct attempt IDs, exact sends and lifecycle |
| `should_refuse_retry_after_outside_limits`, `should_bound_504_exhaustion_without_success` | All three operations; delay ceiling/budget refusal and bounded status/cause/history without success |
| `should_keep_truncated_permanent_status_even_with_transport_eligibility` | 400/401/403 across all three operations; numeric status, original `RemoteProtocolError`, seven exact partial bytes, headers/history, no resend despite caller-selected eligibility |
| `should_require_admission_for_ambiguous_local_failure`, `should_leave_admission_pending_until_explicit_allow` | Ambiguous truncated 200: absent/rejected/allowed admission; pending decisions send nothing until explicit allow |
| `should_require_admission_after_keepalive_and_reset_frame_indices` | Keepalive-only EOF retains raw bytes without semantics, then admitted recovery resets frame indices |
| `should_interrupt_observed_semantics_without_replay`, `should_reject_malformed_or_unfinished_sse_without_retry` | Content/reasoning/tool interruption; malformed SSE, unfinished frame and marker without safe finish; no successful completion or replay |
| `should_retain_all_observed_channels_before_capture_failure` | All three operations and observed channels; private bytes and typed capture cause before delivery, zero delivered progress, no second request |
| `should_never_follow_redirects` | Redirects stay one actual request; recovery HTTP transport has retries=0 and redirects/proxy discovery disabled |
| `should_preserve_terminal_telemetry_and_reject_length`, fixture usage tests | Reported counters/model/finish/nested cache and float usage preserved; rejected finish emits telemetry then failure, never completed tools |
| `should_cancel_pending_admission_and_backoff_without_a_new_request`, active request and paused telemetry tests | All applicable operations; owned tasks/socket close promptly, actual attempt failed before one cancelled event, terminal failure precedence, no success |
| `should_recover_through_broker_and_session` | `generate`, `generate_response`, `generate_object`, `generate_stream`, `send`, `send_stream` recover through real HTTP |
| `should_execute_completed_tool_once_before_typed_subsequent_failure` | Broker/session ordinary and streaming loops execute once, preserve tool result/history and depth, retry only the next completion, propagate typed cause |
| `should_keep_echoed_secrets_out_of_safe_errors_events_and_logs`, usage privacy test | Credential/payload echoes absent from safe strings/serialization/logs/events; caller capture retains actual authentication and response headers/body |
| `should_validate_schema_and_preserve_format_warning`, invalid schema tests | Successful structured format warning metadata and typed Pydantic failure; ordinary finish unchanged |
| `should_keep_invalid_control_errors_typed_and_private_before_dispatch` | Ordinary/streaming invalid controls: zero requests, no attempt identity/history, safe summary and original private validation cause |
| Existing `omlx_spec`, `omlx_stream_spec`, `omlx_protocol_spec` plus raw event test | Legacy success/failure/settings/authentication/schema/keepalive/tools retained; raw broker event path stays single-request with policy configured |

Recovery support: oMLX `complete` / `complete_with_recovery` and
`complete_stream` / `complete_stream_with_recovery`. `recovery_capabilities()`
reports unsupported remote cancellation/status/idempotency and unknown inference
termination. Structured streaming, embeddings/model management, native reasoning
in outgoing history, OpenAI and Anthropic recovery remain unsupported or outside
this increment. Raw `complete_stream_events` / `generate_stream_events` preserve
the reviewed Rust single-turn compatibility boundary. Healthy oMLX generation has
no active read timeout under opt-in recovery; connect/write/pool settings remain.
See the migration guide for the custom-transport and warning-log differences.

The final source passes all discovered gates: full Ruff and formatting, full
Flake8 and the required fatal-error selection, pytest and explicit coverage,
MkDocs, Bandit, both unfiltered dependency audits and outdated-package inspection.
Both test commands pass 876 tests. Explicit coverage is 85% overall and 90%
for the oMLX decoder. The default configured run reports 84%; no coverage floor
is configured or changed. Exact complete gate logs are indexed in the archive. The uvx audit uses `PIPAPI_PYTHON_LOCATION` to inspect
this project's interpreter; its normalized inventory matches all 96 installed
distributions, without skips or vulnerabilities. The outdated check lists
available upgrades; none were applied. Existing MkDocs migration notices and
read-only host audit cache warnings remain visible in full captures.

Independent review resolved eight findings and separately ran 20 malformed-field,
resource-close and actual-fixture checks plus nine exact-byte 503 cases. Review
covers the final source and exact Rust provider files as well as the engine.
Controller reconciliation and landing remain pending.

The original early proof is retained unchanged as `early-proof.json` in the
archive. A supplementary proof then exercised the exact starting oMLX source
loaded from its immutable Git object at real HTTP: legacy streaming delivered
content and failed the zero-delivery/typed-error assertion; corrected streaming
retained observation, private bytes and original hook cause, delivered nothing,
made one request, and emitted started/failed/interrupted in order. Both actual
exit codes and full logs are retained in the current proof archive. Existing
thresholds, pins, Ruff rules, Flake8 scope, Bandit exclusions/skips and coverage
omissions are unchanged. No advisory suppression or allowlist was added.

## Retained preceding evidence


The current increment covers opt-in Ollama ordinary, structured, and tool-capable
streaming HTTP completion. Remaining provider alignment stays pending. Tests use scripted
loopback HTTP and local files; no live inference or experiment restart occurred.

## Ollama streaming EOF correction (c7)

This correction preserves the accumulated streaming implementation at
`5627d288b448f8d44eb271b08922540464378b57`; the worktree was clean before edits.
The controller receipt and Python logs cited below remain historical
synchronization evidence. Read-only observations show local `origin/main` at
`49ea5504b1ea3d7a0062105b4ddbab28d1f0d968`, an ancestor of this HEAD; they do
not prove a fresh remote fetch. The worker does not mutate refs. Foundry owns
review and direct-main landing without a PR; no release is part of this task.

The exact Rust `4ca1ed279c02eab37827a1ed07c30e961155ecf3` stream engine
classifies EOF and failed HTTP reads by whether a protocol frame is pending.
The Python correction preserves that distinction and typed HTTP causes:

- Pending NDJSON bytes at clean EOF or truncation are protocol-ineligible even
  with caller admission. A JSON object without a newline cannot deliver a
  completed response, content, reasoning, or executable tools.
- EOF between complete keepalive-only frames is transport-eligible, subject to
  explicit admission. Absence and rejection each retain one wire request.
- Semantics observed in an unfinished object remain private progress evidence;
  delivered counts stay zero. Request bytes, response bytes, headers, bounded
  history, actual attempt identities and lifecycle order remain asserted.
- The public async gateway, synchronous broker and chat session propagate these
  outcomes. Interrupted tool frames never execute tools or store a completed
  assistant reply. Existing cancellation, capture privacy, terminal telemetry,
  immutable requests and completed-tool-once tests remain unchanged.

Before fixture expansion or full gates, the five-case public loopback probe
rejected the preserved source with exit 1 (four failing cases) and passed the
corrected source with exit 0. Rejection included an unauthorized second request,
semantic/success delivery from an unterminated frame, transport overwriting the
protocol category, and failure to admit a keepalive-only clean EOF recovery.
The durable proof includes both exact probe source snapshots, source hashes,
actual exit codes and full logs. The expanded public-boundary suite retains
complete private wire captures and exercises admission rejection/absence,
retry exhaustion, tool interruption and broker/session propagation.

Durable evidence for this correction resides at
`/home/svetzal/.foundry/tool-logs/mojentic-py-eof-c7/`, including controller
receipt/logs, exact retained Rust source, Python snapshots, wire captures,
quality-gate records and independent source review. This adds no providers,
dependencies, runtime pins, rules, thresholds, exclusions or suppressions.
The c6 verification below describes the prior increment, separately from c7.

C7 final verification passes full Ruff and formatting, full and selective
Flake8, both full pytest runs (762 tests each), MkDocs, Bandit, both unfiltered
dependency audits and the outdated-package check. The explicit `pytest --cov`
run reports 85% coverage; the configured default run reports 83%. No coverage
floor is configured or changed. Both audit inventories match all 96 installed
project distributions exactly using this worktree's interpreter, without skips
or vulnerabilities. Existing documentation-tool warnings remain visible.
Independent review passes all 41 EOF specifications and verifies final hashes.

An additional McCabe diagnostic (separate from configured lint gates) confirms
the changed HTTP exchange function is at most 10. It also flags the unchanged
`run_stream` function at 12 on both preserved and corrected source. The inherited
finding remains disclosed rather than expanding this EOF correction or changing
lint policy. No suppression was added. Exact diagnostic logs remain archived.

## Tool-capable Ollama streaming increment (c6)

This worker started at clean `49ea5504b1ea3d7a0062105b4ddbab28d1f0d968`.
Controller synchronization evidence is the Python entry in
`/home/svetzal/.foundry/operations/mojentic-port-alignment-20261010/status-recovery/receipt.json`:
the controller fetched and pulled main at `c95d805e617f521c77cc04866b2232c11d0baba8`.
That commit is an ancestor of this starting HEAD. This is historical controller
evidence, not a claim of a fresh worker fetch or current remote synchronization.
Worker HEAD/status observations are read-only; Foundry owns direct-main landing.
No refs, releases, dependencies, rules, thresholds or suppressions are changed.

The exact Rust comparison is `4ca1ed279c02eab37827a1ed07c30e961155ecf3`,
including its decoder, engine, public HTTP tests, migration guide, and conformance
report. Verbatim reference files, hashes, controller receipt, proof, current source
snapshots, commands, and complete capture logs reside durably in
`/home/svetzal/.foundry/tool-logs/mojentic-py-stream-c6-fa223f/`.
Missing historical c3 evidence remains disclosed below; this run does not recover
or relabel it. Independent source/assertion review is retained with source hashes.

The early proof exercised actual loopback HTTP through `complete_stream`: baseline
ignored recovery capture and failed to raise. Corrected source retains observed
UTF-8 content, the exact capture exception and bytes, zero delivery, one wire
attempt and `attempt_started -> attempt_failed -> interrupted`. The proof was
established before expanding fixtures, documentation or full gates.

`ollama_stream_recovery_spec.py` exercises public gateway recovery streams,
compatibility `complete_stream`, broker `generate_stream`, and session `send_stream`.
Assertion-level evidence includes:

| Case | Assertions at public HTTP boundary |
| --- | --- |
| Admitted 503 and Retry-After | Numeric/date/invalid delays use injected wall clock/sleeper; immutable request bytes, actual Basic authorization, reasoning controls and options match received requests. Logical IDs remain stable, attempt IDs distinct and unmasked; excessive minima refuse before admission. |
| Persistent 504 and admission | Exact wire count and complete bounded history, typed HTTP causes and body bytes; no hook requires admission, reject prevents resend, pending remains pending until cancellation. |
| Permanent truncated rejection | Each of 400/401/403 retains status, private headers, partial bytes, raw-byte count and original `RemoteProtocolError`, even with transport and selected status eligibility enabled. One send, ineligible. |
| Semantic interruption | Content/reasoning/tool fragments prevent replay; delivered UTF-8 bytes and tool fragment counts survive the typed interrupted outcome. Capture-failed variants with and without newline retain observed evidence and zero delivery. Valid stop tools retain completed-tool evidence before capture; malformed preceding JSON prevents fabricated completion counts. |
| Nonsemantic progress | Keepalive bytes and empty JSON progress can recover after admission; raw byte evidence survives, semantics stay absent, per-attempt frame indices restart at one. |
| Terminal telemetry | Valid length terminal has exact typed progress and metrics, reported counters/durations/throughput, `Progress -> Metrics -> Failed`, no semantic output or completed tools. Malformed fields and tool IDs yield only failure. Missing metrics stay absent; successful response retains reported model/finish/evidence. |
| Cancellation ownership | Active request test observes local socket EOF; pending hooks/backoff close through deterministic events. Paused progress/metrics and buffered terminal capture yield only cancelled failure thereafter. Actual failed attempt precedes exactly one cancellation; length rejection or simultaneous capture failure retains the original typed failure. No successful completion or completed tools follows. |
| Tool and session safety | A successful completed tool executes once before a later exhausted or partial completion. Failed recovery evidence survives; session stores no partial completed assistant reply. Successful retries consume wire attempts separately from tool depth; native tool argument types are retained. |
| Privacy and compatibility | Credentials/payload echoes are absent from default error/event formatting and JSON. Explicit cause/header/body/capture/model inspection retains evidence. Legacy SDK length/error behavior is characterized; raw event APIs still make one send. Generic iterator callers remain supported by optional close ownership. |

Public additions are `complete_stream_with_recovery`, `RecoveryStreamEvent`,
`StreamOutcome`, `StreamFrameProgress`, and `StreamMetrics`. Existing synchronous
stream shapes remain compatible; opt-in failures raise typed `RecoveryError`.
Raw single-turn event APIs retain their reviewed behavior and reject tools.
Ordinary/structured assertions remain intact except the capability snapshot's
intended additive `streaming_recovery=True` and explicit unsupported request status. No disabled-reasoning parity or
ordinary finish change is included. Outgoing native reasoning history remains
limited by the existing Python message model; no six-port parity is claimed.
Remote cancellation/status and inference idempotency remain unsupported;
termination remains unknown. No live inference or benchmark was run.

Final gate commands, exit codes, full log paths/hashes, audit environment proof,
and independent review are indexed in the durable evidence directory.

| Final gate | Actual result |
| --- | --- |
| Full and required selective Flake8; full Ruff; full formatting check | Exit 0; zero lint findings. Added stream engine also passes complexity <= 10. |
| `uv run pytest` and `uv run pytest --cov` | Both exit 0, 721 tests pass. Explicit coverage is 85%; stream engine 92%. The existing coverage omissions are unchanged; no coverage floor is configured. |
| `uv run mkdocs build` | Exit 0; existing documentation tool warnings remain visible in the complete log. |
| `uv run bandit -c .bandit -r src` | Exit 0, no findings; existing policy/exclusions unchanged. |
| `uv run pip-audit` and `uvx pip-audit` | Both unfiltered audits exit 0, no vulnerabilities. JSON audit inventories match all 96 installed project distributions exactly, without skips; both use this project's interpreter via `PIPAPI_PYTHON_LOCATION`. |
| `uv pip list --outdated` | Exit 0; informational report retained, no dependency changes. |

Initial formatting/export-lint failures and their corrected reruns remain retained.
Independent review passed 105 focused streaming/broker/session cases and the final
57-case streaming suite, and inspected
source, exact Rust behavior, assertions, privacy, compatibility and capability
claims. Full project gates above are separate parent verification. Review does
not prove exhaustive scheduler interleavings or live-provider efficacy.

## Focused CreateDirectoryTool proof closure (c5)

This worker started from clean `cd0817e22def141c8d9708cc1a2ddec263c773cb`.
The sections below retain the separate c4 evidence; they do not establish a
historical sequence or completion of the whole recovery mission. This increment
adds assertions and migration guidance only, preserving the licensed exception
correction already present in the starting source.

`src/mojentic/llm/tools/create_directory_boundary_spec.py` exercises
`CreateDirectoryTool.run()` with a real `FilesystemGateway`. A path object's
`__fspath__` raises an original `RuntimeError`; the assertion requires that exact
object to escape and verifies unchanged directory entries and sentinel bytes.
The identical assertion rejects `c95d805e617f521c77cc04866b2232c11d0baba8`
because its catch-all returns an error string. It passes on the starting source.
No private method or library internals are mocked.

Early proof was recorded in `.foundry/proof.json` before compatibility expansion
or full gates. Durable evidence resides in
`/home/svetzal/.foundry/tool-logs/mojentic-py-directory-c5/`: `proof.json`,
`early-proof-spec.py`, `proof-rejecting.json`, `proof-corrected.json`, and their
complete captures. An exploratory TypeError identity assertion failed because
`os.path.join` replaces that exception; those captures remain retained and are
not presented as passing evidence. The final RuntimeError probe avoids that
library replacement without changing runtime code.
`final-boundary-rejecting.json` and `final-boundary-corrected.json` also exercise
the final formatted specification: one rejection plus four compatibility passes
on the baseline, and all five passes on the corrected revision.

`compatibility-rejecting.json` and `compatibility-corrected.json` record four
passing specifications on each exact revision: nested and repeated creation,
sandbox escape rejection, an actual existing-file collision, and the retained
permission error message. PermissionError is supplied by a path protocol object,
not by an OS permission fixture; this characterizes the handler rather than
claiming platform permission enforcement. The constructor still takes a direct
`FilesystemGateway`, and `src/_examples/coding_file_tool.py` still passes `fs`.

`source-hashes.json`, `synchronization.json`, `preservation.json`, and
`evidence-index.json` retain revisions, source/evidence hashes, read-only ref
observations and unchanged policy/runtime files. Remote main was observed at
the starting revision; this does not prove any unobserved controller state.
Foundry owns landing directly on main; this worker makes no ref mutations.
`review.md` records independent assertion and compatibility review.
`quality.json` retains actual final-source gate commands, exits and full capture
hashes. `audit-environment-proof.json` compares both unfiltered audit inventories
with the project interpreter's installed distributions. No rules, thresholds,
pins, dependencies, exclusions, suppressions or existing recovery assertions
are changed by this increment.

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

- Other-provider streaming recovery and remaining provider conformance.
- oMLX, OpenAI and Anthropic recovery/provider alignment.
- Native reasoning in outgoing Ollama history; existing payload behavior is preserved.
- Ordinary finish handling and disabled-reasoning parity.
- Remote cancellation/termination and inference idempotency remain unsupported or unknown.
- Live inference, experiment restarts, releases and Git finalization are outside this task.
