# Python recovery conformance evidence

Successful non-stream recovery responses from OpenAI, Ollama and oMLX report
`completed_tool_calls` as the number of validated tool calls in the response.
The attached recovery report and `attempt_succeeded` lifecycle event carry the
same count. Public broker tool rounds execute each completed tool exactly once.

## Cycle 13: validated provider metadata

This focused correction starts from clean worktree HEAD
`337566b` containing controller-synchronized `origin/main`
`a218e00fed5ce40c96064849b504e2d02a4992eb`. The worker inspected these refs
read-only and did not fetch, modify refs, reconcile prior cloud work, or finalize
Git. Foundry owns synchronization and landing. Dependencies, lockfile, gates,
thresholds, exclusions and runtime retry/tool behavior remain unchanged.

The source reference is Rust
`4ca1ed279c02eab37827a1ed07c30e961155ecf3`, specifically
`src/llm/recovery/engine.rs` and `types.rs`, obtained read-only from the local
Rust repository. Its UUID/prefixed-ID recognition, fixed code vocabulary and
outbound echo rejection guide this correction. Anthropic request-id/error-type
support and decoded JSON/Basic-credential echo rejection preserve Python's
binding privacy boundary. Unsupported arbitrary provider strings remain omitted.

`src/mojentic/llm/gateways/provider_metadata_spec.py` exercises real public
loopback HTTP, with exact accepted values rather than masked or count-only proof:

- Terminal public errors, failed-attempt history and lifecycle evidence retain
  exact UUID IDs and recognized error codes on Ollama/oMLX/OpenAI ordinary,
  structured and streaming paths, and Anthropic ordinary completion.
- Two failed attempts carry distinct IDs/codes through a third successful attempt,
  attached response history and its JSON serialization; request bytes are equal.
- UUID and prefixed UUID credential/payload echoes, explicit Basic-password echoes,
  recognized-code echoes, malformed UUIDs/codes and ambiguous headers are rejected.
- Safe formatting, serialization and lifecycle evidence exclude rejected values;
  explicit header/body/cause inspection and opt-in capture retain original evidence.
- Truncated permanent bodies retain exact header IDs and numeric status, omit
  incomplete codes, and send once. Complete in-band errors retain recognized codes.
- Public broker response and session send errors propagate exact accepted metadata
  for all four providers. Anthropic request-id and error-type are asserted directly.

The early rejecting run observed missing exact IDs through all ten supported
paths. An additional unsupported Anthropic structured case characterized existing
zero-dispatch behavior and was removed from the supported-path matrix. The
corrected probe passed before fixture/documentation expansion. The prior Ollama
null-only UUID characterization now expects the exact non-echoed UUID; its
existing credential/payload echo tests remain rejecting assertions.

Complete proof logs, wire captures, exact revisions/source hashes, gate results
and independent review are retained outside the repository at
[/home/svetzal/.foundry/tool-logs/mojentic-py-metadata-c13/](/home/svetzal/.foundry/tool-logs/mojentic-py-metadata-c13/).
The evidence manifest identifies capture hashes and actual exits. The independent
review caught explicit Basic credential decoding and strict UUID-format validation;
these were corrected and covered before final review. Historical sections below
remain records of earlier increments, not claims reconstructed in this cycle.

## Cycle 12: OpenAI strict structured-tool correction

This correction starts at the preserved cycle-11 revision
`edb15e23701e149552d2dc44641f41e247c6403a`, identified by the controller as
`foundry-task/mojentic-py-mojentic-py-transient-recovery-v2-c11-b1a244`.
The controller's [October 11 reconciliation receipt](/home/svetzal/.foundry/reconcile/2026-10-11.md)
records the missing cycle-11 worktree. Current read-only inspection finds this
worktree at the preserved revision and main/origin/main at
`f52f8ecc2784f3301b8e836b985894531220ff22`. These observations do not certify
fresh controller synchronization or conflict resolution. No worker fetch, ref
mutation, commit, merge, rebase, push, release or dependency change is performed;
Foundry must reconcile concurrent trunk arrivals and land the corrected work.

New evidence is retained in
[/home/svetzal/.foundry/tool-logs/mojentic-py-strict-tools-c12/](/home/svetzal/.foundry/tool-logs/mojentic-py-strict-tools-c12/).
It includes actual rejecting/passing logs and exit codes, full captures,
request/response bytes, source revisions and hashes, final gate receipts,
controller context and independent review. The [proof](/home/svetzal/.foundry/tool-logs/mojentic-py-strict-tools-c12/proof.json),
[wire captures](/home/svetzal/.foundry/tool-logs/mojentic-py-strict-tools-c12/wire-evidence.json),
[gate receipts](/home/svetzal/.foundry/tool-logs/mojentic-py-strict-tools-c12/gates/results.json),
[independent review](/home/svetzal/.foundry/tool-logs/mojentic-py-strict-tools-c12/whole-mission-review.md)
and [artifact hashes](/home/svetzal/.foundry/tool-logs/mojentic-py-strict-tools-c12/artifact-hashes.json)
identify this increment's evidence. Earlier sections remain historical
records; their counts and chronology are not reconstructed or asserted anew.
The new proof first characterized public SDK `OpenAIGateway.complete` over
scripted loopback HTTP. That call succeeds with a strict function tool plus
`object_model=Result`, null content and a `tool_calls` finish. The equivalent
public `complete_with_recovery` rejected both immediate and 503-then-success
responses at the preserved source. The correction passes the same response shape.
Early fixture mistakes and environment setup failures are retained separately
and are not presented as behavioral rejection proof.

Only OpenAI's `_decode_recovery` changes: shared response/tool validation still
runs, then JSON model validation is skipped only for null content, a nonempty
validated tool-call list, and exactly `finish_reason="tool_calls"`. No shared
oMLX decoder, ordinary finish policy, streaming finalizer or cloud integration
is rebuilt or changed. oMLX structured null-content tool turns still reject.

| New public specification in `openai_strict_tool_recovery_spec.py` | Assertions |
| --- | --- |
| `should_characterize_sdk_public_completion` | Real SDK parse HTTP request includes independently expected schema and strict tool; object stays null; exact ID/name/Paris arguments returned. SDK includes `stream=false` and uses its own key order. |
| `should_retain_null_object_and_exact_tool_through_public_recovery` | Immediate success and 503 then success; independently literal schema/tool UTF-8 bytes equal actual requests and captures across sends; numeric 503, original HTTPStatusError/status/body and history; stable logical ID, distinct attempt IDs and exact wire counts; exact eight recovery transitions with explicit admission; exact response captures, null object and exact tool fields. |
| Rejection specifications | Non-strict offered tools produce no send; malformed/non-object tool arguments, invalid non-null schema content, null/empty tools, stop/missing/unknown/length/content_filter null-tool finishes fail without resend and preserve the original cause. |
| oMLX boundary specifications | Public ordinary tool-only response still succeeds; public structured tool-only null response still fails after one send. Existing ordinary/structured/stream finalization specifications remain intact. |
| Broker/session specifications | `LLMBroker.generate_response` returns the exact tool without executing it; `generate` and `ChatSession.send` execute once before a later 503 recovers; second-round bytes and tool IDs remain unchanged. Existing completed-tool-executes-once and interrupted/exhausted tests remain unchanged. |

`LLMBroker.generate_object` does not offer tools and `ChatSession` has no
structured entrypoint, so neither supports a combined schema/tool probe.
OpenAI and oMLX structured streaming and Anthropic structured/tool/stream
completion remain unsupported. The migration guide names these limits.

Independent source review and whole-mission assessment compare both mission
requests and the retained exact Rust revision
`4ca1ed279c02eab37827a1ed07c30e961155ecf3`; all five Rust source hashes match
the preserved provenance receipt. Rust's public structured recovery offers no
tools, so this SDK compatibility correction is not a claim of combined
schema/tool Rust parity. The review receipt records no blocking source defect.
Independent focused acceptance passes 246 cases, including all 23 new cases,
and independently validates actual proof exits, full logs and literal wire evidence.
The final full suite and explicit `uv run pytest --cov` each pass 1,121 tests;
explicit coverage is 86%. No coverage floor is configured or changed.
Final fatal-selection/full Flake8, Ruff, whole-source format checking, Bandit,
MkDocs, package build, unfiltered project and uvx dependency audits, and outdated
inventory inspection all pass. Both audits inspect the same 96 project packages,
with no skips or vulnerabilities. Outdated packages are inventoried without
updates. Ruff is supplied through `uv run --with ruff` without modifying package
metadata or the lockfile. An initial import-order finding was corrected; all
final checks were rerun. Existing MkDocs notices remain in the complete logs.

Remaining whole-mission requirements are explicit: native reasoning in outgoing
history is unrepresented; supported provider operations remain incomplete as
listed above; safe validated provider code/request ID fields are not populated;
ordinary completion reports retain delivered tool counts but leave completed
tool counts at zero;
executable six-port/Elixir equivalence is unverified; and harness pin/lock,
fresh registered experiment, scripted provider integration and harness trace
persistence are external unverified deliverables. Remote cancellation/status
and idempotency are unsupported, inference termination unknown. None of the
fake-provider tests establishes remote termination, efficacy or the original
504's origin. This increment does not establish whole-mission alignment.

## Cycle 11: cloud completion recovery

This increment starts from the controller-preserved cycle-10 ref
`foundry-task/mojentic-py-mojentic-py-transient-recovery-v2-c10-e5b443`, at
`5031dd06d087bf8f0cffb722c7a5efbd6bd8f220`. The October 11 controller ledger
identifies that cancelled work item's preservation ref; the reconciliation
receipt is `/home/svetzal/.foundry/reconcile/2026-10-11.md`.
Read-only inspection finds main and origin/main at
`f52f8ecc2784f3301b8e836b985894531220ff22`, with common ancestor
`f51ecdaabb841fea13cba2867b414ab670be1281`. Main's dependency lock updates,
filesystem containment fix/specifications and changelog entry are preserved.
The incoming filesystem specifications needed formatting for the unchanged
whole-source formatter gate; their assertions and behavior are unchanged.
The worker does not fetch, rebase or modify refs. These observations and the
controller receipt do not claim a fresh remote fetch; Foundry owns final review
and direct-main landing.

Stacey's October 11 decision excludes cycle-10's `evidence/cycle-9` additions
from landing. No archival deliverable is rebuilt. Original cycle-9 captures,
proof, source hashes and independent review remain externally retained at
`/home/svetzal/.foundry/evidence/95089e675fb7e7089e236c9841b5c338/7804437f-9e3c-4bce-8d14-89f77810293f/`.
The immutable preserved commit also retains the excluded additions. Current
complete captures, proof, source/Rust hashes and source/assertion reassessment
are retained outside the repository at
`/home/svetzal/.foundry/tool-logs/mojentic-py-cloud-c11/` and in Foundry's run
archive. Scratch files are execution evidence, not repository deliverables.

### Proof before expansion

The first real loopback probe runs the preserved OpenAI streaming path with a
configured capture hook that raises an original `OSError` on a response body.
The server receives the request and returns semantic content; the preserved
path delivers it without consulting the hook, rejecting the typed-error and
zero-delivery assertion. After routing opt-in streaming through owned HTTP,
the same probe passes: one literal UTF-8 send, observed content, zero delivery,
original exception identity, exact private response bytes and ordered
started/failed/interrupted lifecycle. The behavioral proof retains actual
nonzero/zero exit codes and complete logs. This preceded cloud matrix expansion,
documentation and full gates. Failed timeout-adaptation fixture iterations and
all gate failures remain visible in retained captures.

### Executed entrypoints and assertions

`cloud_recovery_spec.py` and `openai_recovery_lifecycle_spec.py` add 177 passing
loopback cases. The literals are independent byte expectations, not generated
from production request builders. All inference traffic stays on loopback HTTP.

| Executed specifications | Boundary and assertion scope |
| --- | --- |
| `should_recover_503_with_literal_bytes_private_evidence_and_exact_lifecycle` | OpenAI `complete_with_recovery` ordinary/structured and `complete_stream_with_recovery` with/without offered tools; Anthropic ordinary `complete_with_recovery`. Every server send and capture equals literal UTF-8 bytes, including controls, strict schema or tools. Seconds/date/invalid Retry-After, original HTTP status cause, private headers/body, admission context, one retained failure, stable unmasked logical ID, distinct attempt IDs, exact eight transitions/identities/delay and typed terminal responses are asserted. |
| `should_reuse_frozen_literal_bytes_after_admission_mutates_caller_inputs` | All five operation variants retain identical literal bytes after message text, temperature, token limit and offered tool list are mutated during admission. |
| `should_freeze_model_specific_controls_and_tool_capabilities` | Reasoning model token parameters, temperature restrictions/retention, reasoning effort and unsupported/supported tools are frozen before dispatch; both real sends and request captures match literal expected bytes. Existing model adaptation methods are unchanged. |
| `should_refuse_retry_after_limits_before_admission`, `should_bound_504_with_complete_history`, `should_refuse_absent_or_rejected_admission`, `should_admit_cloud_retry_without_weakening_local_admission` | All variants: minimum-delay/budget refusals, two-send bounded 504 history with original causes/bodies and distinct attempt IDs, explicit admission rejection, and cloud retry without a hook. Numeric statuses, exact counts/bytes, transitions and outcomes are asserted. Despite the inherited test name, the cloud refusal parameter is explicit rejection only; absent hooks allow cloud recovery. Existing local admission-required conformance remains in the full suite. |
| `should_keep_truncated_permanent_status_despite_transport_eligibility`, `should_not_follow_redirects` | All variants: 400/401/403 survive truncated bodies as permanent despite transport eligibility; original `RemoteProtocolError`, private partial bytes and no admission/resend. Redirects produce one actual send with original HTTP status cause. |
| `should_cancel_an_active_request_and_close_the_owned_socket`, `should_cancel_owned_admission_or_backoff`, `should_keep_admission_pending_until_an_explicit_decision` | All variants: request/admission/backoff cancellation, exact request bytes/counts, original typed causes, pending ownership, no second send, lifecycle ordering and actual socket/task closure. Active generation succeeds past the configured SDK read timeout in `should_leave_active_generation_without_a_fixed_read_timeout`. |
| OpenAI `DescribeOpenAIStreamSafety`, `DescribeOpenAICaptureEvidence`, paused terminal/consumer tests | Comment-only keepalive recovery resets frame indices; OpenAI model metadata named `keepalive` cannot mask observed content/reasoning/tools (the synthetic marker belongs only to oMLX); observed content/reasoning/tool fragments prevent replay. Capture failure retains observed but undelivered semantics and original cause/bytes. Safe finish plus `[DONE]` completes tools; malformed/incomplete streams fail. Actual usage/model/finish evidence is retained with OpenAI identity; absent provider counters remain absent. Cancellation takes precedence while terminal telemetry is paused, and closing a paused consumer closes its socket without an explicit call cancellation. |
| OpenAI `DescribeOpenAIPublicCallers` | `LLMBroker.generate`, `generate_response`, `generate_object`, `generate_stream`, `ChatSession.send` and `send_stream` recover through existing synchronous paths. Completed-tool-then-failed-completion cases cover the four tool-executing paths (`generate`, `generate_stream`, `send`, `send_stream`): one tool execution, unchanged caller depth, logical completion depths `[2, 1]`, three wire sends with failed-completion bytes equal, and identities distinguishing tool rounds from retries. `generate_response` returns tool requests without executing them. Raw `generate_stream_events` remains a single 503 or 307 send with policy configured; the default SDK transport disables redirects as well as hidden retries. |
| `DescribeCloudPrivacy`, preparation/capture cases | Credentials/payload echoes are absent from safe error strings, repr, JSON reports/events and logs. Opt-in request/header/body evidence and typed original causes remain explicitly inspectable. Invalid preparation has no wire request/history; malformed tools and unsafe structured finishes never resend. |
| `DescribeAnthropicCapabilityBoundary` | Ordinary native, broker `generate`/`generate_response`, and session `send` paths recover. Schema, configured JSON output and nonempty tools reject before HTTP with private original `NotImplementedError`; capabilities report false structured/streaming recovery and streaming methods remain absent. |

### Rust comparison and limits

The exact comparator is Rust
`4ca1ed279c02eab37827a1ed07c30e961155ecf3`. Its immutable adapter, engine,
provider types, frames and OpenAI source are retained with Git-object SHA-256
hashes. OpenAI preserves the SDK strict-function-tool requirement for structured
parsing; configured JSON output also rejects at Anthropic preparation. Separate
rejecting/passing boundary regressions retain both corrections. Source checks
compare the preserved OpenAI adaptation/validation and raw
stream methods, unchanged Ollama source and unchanged policies/pins with current
source. A separate boundary reassessment compares literal bytes and assertions
through public APIs independently of the project fixture. Controller reviewer
approval remains a separate landing decision.

Rust's `Provider::local()` excludes OpenAI: eligible cloud requests can retry
without an admission hook, while ambiguous local requests require explicit
admission. Python preserves Ollama/oMLX admission and adds OpenAI/Anthropic to
the shared typed provider vocabulary. Explicit cloud admission still waits or
rejects. The reviewed Rust revision has no Anthropic adapter; no Anthropic parity
claim is made. Both cloud adapters use owned HTTP with SDK retries, redirects
and proxy discovery disabled, and no active generation read timeout. Recovery
limits apply to dispatch/admission/backoff, not total generation duration.

Anthropic retains its existing system/user message selection and first-text-block
mapping. It still lacks structured generation, streaming and tool execution.
OpenAI structured streaming remains unsupported. SDK/custom stream transports
are bypassed by opted-in completion recovery; raw stream-event methods retain
their existing compatibility boundary. Remote cancellation/status, inference
termination and idempotency are not established. Ordinary finish handling,
reasoning-disabled behavior, native reasoning in outgoing history, embeddings,
realtime, live inference and experiment efficacy are outside this increment.

The full suite passes 1,098 tests; explicit coverage is 86% and final gate
receipts are retained externally. No coverage floor is configured or changed.
Full/fatal-selection Flake8, Ruff, whole-source formatting, Bandit, MkDocs,
unfiltered project and uvx pip-audit, and outdated inventory inspection pass.
Both audits report no known vulnerabilities. The uvx audit targets the project
interpreter; its tool/cache directories are writable scratch because the host
uv tool directory is read-only. Existing MkDocs notices and pip audit cache
warnings remain in complete logs. The unchanged CI warning-mode Flake8 command exits zero with 169 retained
legacy diagnostics (13 complexity, 15 one-line-definition and 141 operator
layout diagnostics); its full output is retained, not reported as zero warnings.
The new specifications have no operator-layout diagnostics. New recovery helpers
stay within complexity 10; existing legacy OpenAI complete/stream methods exceed
that supplemental metric and remain preserved in this correction. Dependencies,
runtime pins, exclusions, thresholds and advisory suppressions are unchanged
relative to synchronized main. No release, commit, push or ref mutation occurs
in this worker.


## Cycle 9: oMLX HTTP 429 coverage at 8b437e4

This correction preserves the landed implementation at
`8b437e4bbca38c8c28f2d18dfbcb6d81fb8e499f` and adds
`src/mojentic/llm/gateways/omlx_429_recovery_spec.py`. No runtime source,
dependencies, provider support, release files or existing 503 cases changed.

The new proof precedes matrix expansion in this execution. A scripted loopback
429 with an HTTP-date minimum first rejects admission: assertions establish one
literal request, numeric 429, a three-second minimum and exact
started/failed/pending/rejected/exhausted transitions, before the typed
`RecoveryError` rejects the success probe. Changing only the admission input to
allow passes the same probe with two identical sends, original typed HTTP cause
and body, stable logical ID, distinct attempt IDs, exact recovery lifecycle and
successful terminal content. Complete captures, loopback records, rejecting and
passing source snapshots, source/log hashes and the behavioral proof are retained
in the Foundry evidence archive for this run. This is new assertion-bearing HTTP
evidence; it does not repair or reconstruct historical chronology. An earlier
launch failed on a read-only uv cache, and an initial assertion incorrectly tried
to read the streaming HTTP exception response directly; both failed captures are
retained. The accepted proof inspects retained response bytes through the public
failure evidence API. No production defect was inferred from those probe issues.

| Executed specification | Boundary and assertions |
| --- | --- |
| `should_recover_429_only_after_admission_with_exact_wire_evidence` (21 cases) | Public `OMLXGateway.complete_with_recovery` for ordinary and `object_model=Result` structured calls; public `complete_stream_with_recovery` for streaming. Independently literal UTF-8 request bytes, including schema or stream controls, equal every received send and request capture. Seconds/date minima exceed jitter and jitter exceeds seconds/date minima; past dates clamp to zero; invalid/absent headers retain their states and use jitter. Numeric 429, provider/operation/category, eligibility, original `HTTPStatusError`, request bytes, private response body, one retained failure, stable logical ID, distinct attempt IDs, admission context, exact eight transitions and their identities/delay, response content/structured object/model/usage/finish and typed streaming completion are asserted. |
| `should_refuse_429_minimum_outside_limits_without_another_send` (12 cases) | All three entrypoints; minimum exceeds delay ceiling, whole budget, remaining budget consumed before admission, or remaining budget consumed during admission. One literal wire send and capture, original cause/body and complete history, same final identity, no semantic output or scheduled sleep, exact terminal lifecycle with no retry start or success, and `RecoveryError` outcome `delay_ceiling` or `budget_exhausted`. Streaming additionally asserts the sole failed event, typed `StreamOutcome`, no response and matching report identity/outcome. |
| `should_refuse_eligible_429_without_admission` (6 cases) | All three entrypoints; absent or rejecting admission retains eligible numeric 429, original cause/body and history, one literal send/capture, no sleep, exact required/rejected terminal lifecycle and typed failure. |

The focused matrix passes all 39 cases. Both final full test runs pass 915 tests;
explicit coverage is 85% (the default run reports 84%). No coverage floor is
configured or changed. Full Ruff and format checking, full Flake8 and the
required fatal-error selection, MkDocs, Bandit, both unfiltered pip-audit commands
and outdated-package inspection pass. Both audits target this project's virtual
environment through `PIPAPI_PYTHON_LOCATION` and report no known vulnerabilities.
No dependency updates or audit suppressions were applied. Existing MkDocs
migration notices and read-only host pip-cache warnings remain in complete logs.
An initial import-order lint finding was corrected and final lint checks rerun.
Independent source review found a missing structured-object assertion, now added
and verified; no blocking source defects remain. Proof, gate receipts, full logs,
environment inventory, unchanged-source/policy comparison and final hashes are
retained in this run's Foundry evidence archive. These tests use scripted local HTTP only; no
live inference or nested experiment was run. High-level broker/session 429
coverage, other providers, remote termination and inference idempotency remain
outside this increment; existing broader evidence and limitations remain below.

The starting tree was clean at `8b437e4`; worker Git inspection is read-only.
No current controller synchronization receipt was supplied for this execution.
A local remote-tracking ref or historical receipt cannot certify reconciliation
with current upstream arrivals. Controller reconciliation, independent approval
and landing directly on main remain controller responsibilities. This worktree
retains the completed increment uncommitted for Foundry finalization.

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
