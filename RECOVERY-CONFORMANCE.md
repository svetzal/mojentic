# Python recovery conformance

The current evidence is fully in-process and deterministic. This document
supersedes historical server/socket/elapsed-time proof claims. Binding identities,
source revision/hash, package verification, gate commands and actual results are
maintained in `CONFORMANCE-3.0.0.md` and
`docs/release_3_0_0_validation.json`; per-decision outcomes are in
`docs/release_3_0_0_acceptance.json`.

All 31 decision groups in the acceptance record passed. Final verification ran
2,657 tests at 88.13% coverage, with all four project gates and both guarded
installed-wheel scripts returning exit 0.

The reconciled `openai_tool_roundtrip_spec.py` preserves all 11 ordinary, metadata,
streaming and parallel-tool cases through public broker APIs. The real OpenAI SDK and
production oMLX transport run against `scripted_http`; assertions inspect serialized
requests, exact tool IDs/results, typed JSON arguments, provider usage/model/finish
reason and final output. Injecting an incorrect tool result rejected all four parallel
cases; restoring the canonical result passed. Canonical shared fixture bytes and
production behavior remain unchanged.

## Replacement proof by recovery decision

The authoritative contract is `root-recovery@4ae2f73`, copied byte-for-byte into
`TRANSIENT-RECOVERY-2026-10.md` (SHA-256
`141d4ee5fcfbc18c940a7e7fe8d5ba9e381abc41a6d03f300f541e0fd5236f9d`). It includes
all October 12 decisions. Public ordinary, structured and supported streaming
routes execute production gateways with the shared HTTP transport double.

| Decision | Executable specifications | Exact expected behavior |
| --- | --- | --- |
| 503 recovery and 504 exhaustion | `ollama_recovery_spec.py`, `omlx_recovery_spec.py`, `cloud_recovery_spec.py` | 503 retries only with permission; 504 stops at max_attempts; exact payload bytes persist, attempt IDs differ within one logical ID, lifecycle and complete history agree. |
| 429 and Retry-After | `omlx_429_recovery_spec.py`, `cloud_recovery_spec.py`, `ollama_recovery_spec.py` | Seconds, IMF-fixdate, RFC850 and asctime retain the provider minimum; invalid/absent dates use deterministic backoff; ceiling/budget refuses excessive delays. |
| Ambiguous local execution and no-hook admission | `recovery_admission_spec.py`, `ollama_recovery_spec.py`, `omlx_recovery_spec.py` | Ollama/oMLX ambiguous failures require admission; allow/reject/pending/undecided remain distinct. Remote eligible failures may retry without a hook. |
| Evidenced nonacceptance | `recovery_admission_spec.py` | Transport emits connection.connect_tcp.failed with ECONNREFUSED; first acceptance is no, retry succeeds without hook, exactly one provider request follows two dispatch captures. Capture-hook ConnectError and validation exceptions retain unknown. |
| Active cancellation and cleanup | `ollama_stream_recovery_spec.py`, `omlx_recovery_spec.py`, `openai_recovery_lifecycle_spec.py`, `cloud_recovery_spec.py` | After transport entry, cancellation closes the suspended transport coroutine/body, preserves CancelledError and attempt 1, emits attempt_started / attempt_failed / cancelled, and never resends. |
| Admission and backoff cancellation | `ollama_recovery_spec.py`, `omlx_recovery_spec.py`, `openai_recovery_lifecycle_spec.py`, `cloud_recovery_spec.py` | Explicit cancellation and native task cancellation settle pending hooks/sleepers through finally cleanup with one send; synchronous session cancellation reaches its worker. |
| Pending budget expiry and active-generation deadline | `recovery_admission_spec.py`, `ollama_recovery_spec.py` | Injected scheduler expiry closes pending admission and returns budget_exhausted. Active generation may finish after the retry deadline; no fixed read timeout is introduced. |
| No fixed active read timeout | `cloud_recovery_spec.py` | Captured HTTP transport timeout extension has read=None for ordinary/structured/stream/tool-stream/Anthropic operations, independently of configured SDK read timeout. |
| Paused stream and local close | `cloud_recovery_spec.py`, `ollama_stream_recovery_spec.py`, `omlx_recovery_spec.py`, `openai_recovery_lifecycle_spec.py`, `first_token_spec.py` | Paused-consumer cancellation and iterator close settle local resources; close emits no invented public terminal event; unsent close has no timing. |
| Partial reasoning/content/tool fragments | `readiness_boundary_spec.py`, `ollama_stream_eof_spec.py`, `ollama_stream_recovery_spec.py`, `omlx_recovery_spec.py`, `openai_recovery_lifecycle_spec.py` | Each observed semantic channel interrupts without replay, including failed capture and partial/truncated EOF; raw/observed/delivered progress and safe lifecycle fields remain distinct. |
| Malformed frames, empty EOF and stream errors | `ollama_stream_eof_spec.py`, `ollama_stream_events_spec.py`, `openai_stream_events_spec.py`, `omlx_stream_spec.py`, `first_token_spec.py` | Malformed data and incomplete terminal frames retain typed protocol/transport causes; noniterable choices are INVALID_STREAM_EVENT, with preserved earlier content and timing. |
| Keepalive-only progress | `ollama_stream_eof_spec.py`, `omlx_recovery_spec.py`, `omlx_stream_spec.py`, `first_token_spec.py` | Keepalive bytes remain raw progress, with no semantic token or frame-index/provider-metadata pollution; empty success has no first token. |
| Permanent errors and eligibility controls | `typed_errors_spec.py`, `readiness_boundary_spec.py`, `cloud_recovery_spec.py`, `ollama_recovery_spec.py` | 400/401/unsupported/malformed responses do not replay blindly; selected statuses/categories, including 500/502, change eligibility; redirects never create hidden sends. |
| Typed policy, provider and operation vocabulary | `typed_errors_spec.py`, `recovery_capabilities_spec.py` | Invalid policies use RecoveryPolicyError on every route; ordinary/structured/streaming and provider values are closed; capture/length/validation causes remain typed and private. |
| Safe provider IDs and code vocabulary | `provider_metadata_spec.py`, `ollama_recovery_spec.py` | Accepted request ID is req_12345678-1234-4234-8234-123456789abc and accepted codes include invalid_api_key, rate_limit_exceeded, server_error, and Anthropic overloaded_error. Distinct history ID 87654321-4321-4321-8321-cba987654321 remains exact; credential/payload echoes and duplicate header IDs return None. |
| Privacy and explicit raw inspection | `provider_metadata_spec.py`, `typed_errors_spec.py`, `cloud_recovery_spec.py`, `ollama_recovery_spec.py` | str/repr/JSON/lifecycle serialization omit secret payload/credential sentinels; raw response, headers and original causes are available only by explicit inspection. |
| Capabilities and supported legacy projections | `recovery_capabilities_spec.py` | All four adapters expose local cancellation, remote cancellation, status, idempotency and exact-attempt termination with dated documentation evidence; exact termination stays unknown; supported old/new projections and JSON round trips remain valid. |
| Tool safety and recursion depth | `completed_tool_recovery_spec.py`, `openai_strict_tool_recovery_spec.py`, `openai_tool_roundtrip_spec.py`, `ollama_recovery_spec.py`, `omlx_recovery_spec.py` | Validated completed tool counts match responses/reports/lifecycle events; tool executes once per round, byte-identical continuation retries preserve IDs/results/reasoning, and recovery never resets max_tool_iterations. |
| Image/control freezing and authenticated bytes | `ollama_recovery_spec.py`, `cloud_recovery_spec.py`, `request_fidelity_spec.py` | Preparation freezes images, controls and tools before admission. Actual Authorization equals Basic dXNlcm5hbWU6cGFzc3dvcmQ= on both attempts; exact captured SDK body bytes match transport requests. |
| Legacy one-send compatibility | `ollama_recovery_spec.py`, `omlx_recovery_spec.py`, `request_fidelity_spec.py` | Default success and disabled recovery retain one send, successful output, supported legacy/event routes and explicit 2.1 migration control settings. |

## Proof mechanics and scope

A refused connection is represented at the transport boundary by the same
HTTPCore trace event (`connection.connect_tcp.failed`) and an ECONNREFUSED cause;
a ConnectError from a caller callback never counts as nonacceptance. The public
recovery admission tests prove both decisions and preserve exact body/model/path.
Read timeout is raised while advancing a real HTTP response stream after headers;
it preserves `client_timeout`, unknown acceptance, received headers and zero raw
body bytes, without waiting on a real clock.

Active cancellation waits for transport entry, cancels the public call and awaits
the transport's cleanup event. Paused-body close uses an async byte stream with an
explicit `aclose` event. Pending admission expiry advances the injected event-loop
clock, so its cancellation/finally ordering is deterministic. Async sleeping is a
cooperative yield; explicit retry waits advance virtual time. Default retry random
inputs and wall/monotonic clocks are injected in every changed recovery case.

Shared cloud/oMLX fixtures and all original import paths are preserved. No
server-only contract decision was removed: request identity, authentication, exact
payloads, provider metadata, retry admission, cancellation, cleanup, progress,
reasoning, completed tools and timing have the replacement proof above.

The first authentication probe rejected loss of the exact Authorization header
on all five gateway/broker/session entrypoints; restoring transport capture made
all five pass. Foundry archives that behavioral red/green evidence. Verification
is local to this library under the October 17 self-validation policy; no sibling
or running-service boundary was changed or claimed verified.
