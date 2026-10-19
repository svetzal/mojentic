# Python 3.0 conformance

This living record replaces superseded loopback and wall-clock proof claims.
Production behavior, public APIs, dependency versions and package version are
unchanged by this correction. The tested base commit is `0e2d3dc52715313349a9b9a81292f94b659dd16a`;
`docs/release_3_0_0_source.sha256` identifies the tested working-tree inputs,
including specifications and the shared transport helper. Actual commands,
source identity, artifact identity and results are maintained in
`docs/release_3_0_0_validation.json` and `docs/release_3_0_0_acceptance.json`.

The reconciled `openai_tool_roundtrip_spec.py` preserves all 11 ordinary, metadata,
streaming and parallel-tool cases through public broker APIs. The real OpenAI SDK and
production oMLX transport run against `scripted_http`; assertions inspect serialized
requests, exact tool IDs/results, typed JSON arguments, provider usage/model/finish
reason and final output. Injecting an incorrect tool result rejected all four parallel
cases; restoring the canonical result passed. Canonical shared fixture bytes and
production behavior remain unchanged.

## Binding identities

The authoritative parent was inspected read-only at
`mojentic-unify@4ae2f73a0a5465b0f6509b87e1148d254f3f64cd` (`4ae2f73`). The local recovery
contract is byte-identical to that parent, including the October 12 amendment.
Context-window and request-fidelity v1 retain every behavioral case, updating
only their source hash to the revised root metadata contract. The Python
first-token v1 contract now records that source hash explicitly. Native reasoning
v1 is unchanged. No sibling checkout or ref was modified.

| Contract | SHA-256 |
| --- | --- |
| `root-recovery@4ae2f73` (`TRANSIENT-RECOVERY-2026-10.md`) | `141d4ee5fcfbc18c940a7e7fe8d5ba9e381abc41a6d03f300f541e0fd5236f9d` |
| `context-window-v1` (`src/mojentic/llm/contracts/context_window_v1.json`) | `f93a35e4de9c55e87c0a55551d4ab735289b040bbb673d87269fd3b4b8e41466` |
| `py-stream-first-token-v1` (`src/mojentic/llm/gateways/fixtures/contracts/first_token_v1.json`) | `78dc6691c65ba84faa6e9a3490e6361bc3330dfd8341a27de5a4d7c2af833ab5` |
| `native-reasoning-v1` (`src/mojentic/llm/gateways/fixtures/contracts/native_reasoning_v1.json`) | `be212ff011125f1d0927e3a65a0d7cd87eedbf9f5ff69e803b4112a80ae6b1f6` |
| `request-fidelity-v1` (`src/mojentic/llm/gateways/fixtures/contracts/request_fidelity_v1.json`) | `6a5ebca721a9f9e84323d0118b543d5dc71c7f68bb7067b2cdf6ad40daddcfc8` |
| Parent `MODEL-METADATA-2026-10.md@4ae2f73` | `d9945dca45ce09e2163843263a75b5e93028b00ee1baf191fc3ff13396830e9c` |
| Parent `REASONING-PROTOTYPE-2026-10.md@4ae2f73` | `0a40f3ad45c593bc779411021e45db569e73d3ecce86c99b201e7f8ebb656809` |

## Verification boundary

The consumer is Python's public broker/session/gateway API. Provider verification
executes the production gateway encoding, SDK, HTTP hooks, decoder and recovery
engine against those same contract-derived responses, within this repository.
The suite hash identifies these executable consumers and providers together.
The October 17 library self-validation policy applies: this test-only correction
changes no running-application/service boundary and requires no counterpart
repository mutation. Adoption of a released library verifies in the dependent's
scope; these results make no claim of live-provider or downstream compatibility.

`scripts/inprocess_http.py` substitutes HTTP transports for both httpx and
httpx2, plus monotonic/scheduler/wall clocks, sleepers and tokenizer gateways.
It preserves real SDK request encoding, exact headers and payloads. The original
`scripted_http`, `unfinished_http`, cloud and oMLX fixture exports remain usable
by every importer. The library pytest guard and both installed-wheel scripts
use a scoped Python audit hook to reject Internet socket construction, DNS,
connect (including connect_ex), bind and datagram sends before I/O, and reject
blocking sleep. No native socket class or module method is replaced. The hook
is permanently registered but inert outside offline contexts; a process-wide
nesting count restores activation even when a context raises.
Async sleepers cooperate without timers; injected retry waits advance virtual
time. asyncio's internal Unix socketpair is permitted. Tests and verifiers call
no service or registry. Package preparation and dependency audits may access
registries; they are outside the acceptance boundary.

`offline_spec.py` reconciles the preserved characterizations through
`LLMBroker.generate_response`. Exact request byte assertions distinguish the
SDK/httpx2 and recovery/httpx routes. Both retain Authorization and answer
content; the supported recovery wire observer exposes the exact unmasked
`x-request-id` and links its logical identity to the public recovery report.
The ordinary success model has no `provider_metadata` projection. Native
`socket.socket.__init__` is a standard-library Python function, while connect
and bind remain native method descriptors. The original guard rejected this
reconciled probe; the audit-hook correction passed. Nested guard unwinding,
outer transport restoration and unhandled routes after transport exit all pass.

## Decision mapping

Every row's executable assertions run in the full pytest gate; the acceptance
record reports its actual passed case count and outcome. Paths below are spec
basenames under `src/mojentic/`; each name resolves uniquely in this checkout.

| Binding decision | Replacement executable proof | Expected public result |
| --- | --- | --- |
| Offline enforcement with native socket methods | `offline_spec.py`; `LLMBroker.generate_response` | Seven cases preserve exact SDK/recovery serialization, Authorization, answer and raw request identity; nested contexts restore transports and deny unstubbed routes before I/O. |
| 503 recovery and 504 exhaustion | `ollama_recovery_spec.py`, `omlx_recovery_spec.py`, `cloud_recovery_spec.py`; `complete`, `complete_with_recovery`, `generate`, `generate_response`, `generate_object`, `ChatSession.send` | 503 retries only with permission; 504 stops at max_attempts; exact payload bytes persist, attempt IDs differ within one logical ID, lifecycle and complete history agree. |
| 429 and Retry-After | `omlx_429_recovery_spec.py`, `cloud_recovery_spec.py`, `ollama_recovery_spec.py`; `complete_with_recovery`, `complete_stream_with_recovery` | Seconds, IMF-fixdate, RFC850 and asctime retain the provider minimum; invalid/absent dates use deterministic backoff; ceiling/budget refuses excessive delays. |
| Ambiguous local execution and no-hook admission | `recovery_admission_spec.py`, `ollama_recovery_spec.py`, `omlx_recovery_spec.py`; `complete`, `complete_with_recovery`, `complete_stream_with_recovery` | Ollama/oMLX ambiguous failures require admission; allow/reject/pending/undecided remain distinct. Remote eligible failures may retry without a hook. |
| Evidenced nonacceptance | `recovery_admission_spec.py`; `complete_with_recovery`, `complete_stream_with_recovery` | Transport emits connection.connect_tcp.failed with ECONNREFUSED; first acceptance is no, retry succeeds without hook, exactly one provider request follows two dispatch captures. Capture-hook ConnectError and validation exceptions retain unknown. |
| Active cancellation and cleanup | `ollama_stream_recovery_spec.py`, `omlx_recovery_spec.py`, `openai_recovery_lifecycle_spec.py`, `cloud_recovery_spec.py`; `complete_with_recovery`, `complete_stream_with_recovery` | After transport entry, cancellation closes the suspended transport coroutine/body, preserves CancelledError and attempt 1, emits attempt_started / attempt_failed / cancelled, and never resends. |
| Admission and backoff cancellation | `ollama_recovery_spec.py`, `omlx_recovery_spec.py`, `openai_recovery_lifecycle_spec.py`, `cloud_recovery_spec.py`; `complete_with_recovery`, `ChatSession.send`, `complete_stream_with_recovery` | Explicit cancellation and native task cancellation settle pending hooks/sleepers through finally cleanup with one send; synchronous session cancellation reaches its worker. |
| Pending budget expiry and active-generation deadline | `recovery_admission_spec.py`, `ollama_recovery_spec.py`; `complete_with_recovery`, `complete` | Injected scheduler expiry closes pending admission and returns budget_exhausted. Active generation may finish after the retry deadline; no fixed read timeout is introduced. |
| No fixed active read timeout | `cloud_recovery_spec.py`; `complete_with_recovery`, `complete_stream_with_recovery` | Captured HTTP transport timeout extension has read=None for ordinary/structured/stream/tool-stream/Anthropic operations, independently of configured SDK read timeout. |
| Paused stream and local close | `cloud_recovery_spec.py`, `ollama_stream_recovery_spec.py`, `omlx_recovery_spec.py`, `openai_recovery_lifecycle_spec.py`, `first_token_spec.py`; `complete_stream_with_recovery`, `complete_stream`, `generate_stream`, `ChatSession.send_stream` | Paused-consumer cancellation and iterator close settle local resources; close emits no invented public terminal event; unsent close has no timing. |
| Partial reasoning/content/tool fragments | `readiness_boundary_spec.py`, `ollama_stream_eof_spec.py`, `ollama_stream_recovery_spec.py`, `omlx_recovery_spec.py`, `openai_recovery_lifecycle_spec.py`; `complete_stream_with_recovery`, `generate_stream`, `ChatSession.send_stream` | Each observed semantic channel interrupts without replay, including failed capture and partial/truncated EOF; raw/observed/delivered progress and safe lifecycle fields remain distinct. |
| Malformed frames, empty EOF and stream errors | `ollama_stream_eof_spec.py`, `ollama_stream_events_spec.py`, `openai_stream_events_spec.py`, `omlx_stream_spec.py`, `first_token_spec.py`; `complete_stream_events`, `complete_stream_with_recovery` | Malformed data and incomplete terminal frames retain typed protocol/transport causes; noniterable choices are INVALID_STREAM_EVENT, with preserved earlier content and timing. |
| Keepalive-only progress | `ollama_stream_eof_spec.py`, `omlx_recovery_spec.py`, `omlx_stream_spec.py`, `first_token_spec.py`; `complete_stream_events`, `complete_stream_with_recovery` | Keepalive bytes remain raw progress, with no semantic token or frame-index/provider-metadata pollution; empty success has no first token. |
| Permanent errors and eligibility controls | `typed_errors_spec.py`, `readiness_boundary_spec.py`, `cloud_recovery_spec.py`, `ollama_recovery_spec.py`; `complete`, `complete_with_recovery`, `generate`, `generate_response`, `generate_object`, `ChatSession.send` | 400/401/unsupported/malformed responses do not replay blindly; selected statuses/categories, including 500/502, change eligibility; redirects never create hidden sends. |
| Typed policy, provider and operation vocabulary | `typed_errors_spec.py`, `recovery_capabilities_spec.py`; `gateway constructors`, `complete`, `complete_with_recovery`, `generate_object`, `ChatSession.send` | Invalid policies use RecoveryPolicyError on every route; ordinary/structured/streaming and provider values are closed; capture/length/validation causes remain typed and private. |
| Safe provider IDs and code vocabulary | `provider_metadata_spec.py`, `ollama_recovery_spec.py`; `complete_with_recovery`, `complete_stream_with_recovery`, `generate_object`, `ChatSession.send` | Accepted request ID is req_12345678-1234-4234-8234-123456789abc and accepted codes include invalid_api_key, rate_limit_exceeded, server_error, and Anthropic overloaded_error. Distinct history ID 87654321-4321-4321-8321-cba987654321 remains exact; credential/payload echoes and duplicate header IDs return None. |
| Privacy and explicit raw inspection | `provider_metadata_spec.py`, `typed_errors_spec.py`, `cloud_recovery_spec.py`, `ollama_recovery_spec.py`; `complete`, `complete_with_recovery`, `complete_stream_with_recovery` | str/repr/JSON/lifecycle serialization omit secret payload/credential sentinels; raw response, headers and original causes are available only by explicit inspection. |
| Capabilities and supported legacy projections | `recovery_capabilities_spec.py`; `gateway.recovery_capabilities`, `model_dump`, `model_validate` | All four adapters expose local cancellation, remote cancellation, status, idempotency and exact-attempt termination with dated documentation evidence; exact termination stays unknown; supported old/new projections and JSON round trips remain valid. |
| Tool safety and recursion depth | `completed_tool_recovery_spec.py`, `openai_strict_tool_recovery_spec.py`, `openai_tool_roundtrip_spec.py`, `ollama_recovery_spec.py`, `omlx_recovery_spec.py`; `generate`, `generate_response`, `generate_object`, `ChatSession.send` | Validated completed tool counts match responses/reports/lifecycle events; tool executes once per round, byte-identical continuation retries preserve IDs/results/reasoning, and recovery never resets max_tool_iterations. |
| Image/control freezing and authenticated bytes | `ollama_recovery_spec.py`, `cloud_recovery_spec.py`, `request_fidelity_spec.py`; `complete`, `generate`, `generate_response`, `generate_object`, `ChatSession.send` | Preparation freezes images, controls and tools before admission. Actual Authorization equals Basic dXNlcm5hbWU6cGFzc3dvcmQ= on both attempts; exact captured SDK body bytes match transport requests. |
| Legacy one-send compatibility | `ollama_recovery_spec.py`, `omlx_recovery_spec.py`, `request_fidelity_spec.py`; `complete`, `complete_stream`, `generate`, `ChatSession.send` | Default success and disabled recovery retain one send, successful output, supported legacy/event routes and explicit 2.1 migration control settings. |
| Native reasoning controls and continuations | `native_reasoning_spec.py`, `anthropic_history_spec.py`, `anthropic_structured_spec.py`; `complete`, `complete_stream_events`, `generate`, `generate_object` | All native-reasoning-v1 controls produce exact provider fields. Visible/retained reasoning, structured objects, real tool continuations and native Anthropic history envelopes remain distinct and preserved. |
| Model window discovery | `context_window_spec.py`; `get_model_context_window`, `effective_context_window`, `complete` | All context-window-v1 cases preserve exact model selection, authorization, optional metadata, architecture prefixes, invalid values, 404 and registry behavior. Discovery leaves completion bytes unchanged; helper precedence and clamping match every fixture. |
| Request fidelity | `request_fidelity_spec.py`; `complete`, `generate`, `generate_response`, `generate_object`, `generate_stream`, `ChatSession.send`, `ChatSession.send_stream` | All seven request-fidelity-v1 configurations assert full payloads: unset omission, explicit zero/individual controls, provider naming and schema, structured/stream controls and retry/tool-history preservation. |
| First-token definition and supported routes | `first_token_spec.py`, `stream_timing_spec.py`; `complete_stream_events`, `complete_stream`, `complete_stream_with_recovery`, `generate_stream`, `ChatSession.send_stream` | Thinking/content/arguments select the first real frame; exact first-token and duration are 31.25 ms for a single delayed frame. Error after a later frame retains first=31.25 ms and duration=93.75 or 218.75 ms. Empty/error-without-token has None first-token evidence. |
| Timing lifecycle exclusions and retry clock | `first_token_spec.py`; `complete_stream_with_recovery`, `generate_stream`, `ChatSession.send_stream` | Lazy/capture delays before dispatch are excluded (62.5 ms measured); admitted wait adds 125 ms to a 31.25 ms response (=156.25 ms); tool continuation resets its clock (prior first=125 ms, final=31.25 ms), with exact tool history. |
| Dispatcher in-flight ordering | `async_dispatcher_spec.py`; `start`, `dispatch`, `wait_for_empty_queue`, `stop` | Termination settles through the queue; empty-queue wait remains pending while the agent is suspended, then includes its follow-up event before completing. |
| Recursive-agent public outcomes | `simple_recursive_agent_spec.py`; `solve`, `EventEmitter.emit` | Gateway-driven DONE/FAIL, case variants, prose substrings, max iterations, exact iteration sequence, prompts, lifecycle events and handler errors remain verified. An immediate caller deadline raises TimeoutError while background completion is explicitly settled. |
| Aggregator immediate timeout | `async_aggregator_agent_spec.py`; `receive_event_async`, `wait_for_events` | An immediate scheduler timeout returns the exact partial result; complete event sets settle the waiting public future without sleeping. |
| Tool concurrency and order | `runner_spec.py`; `SerialToolRunner.run_batch`, `AsyncParallelToolRunner.run_batch` | Active concurrency peaks exactly at 4 or 2; no work remains active. Controlled completion c,b,a returns input order a,b,c. Pre-cancelled contexts skip pending calls with CancelledError; hooks and failures retain order. |
| Realtime interruption and cleanup | `session_spec.py`; `RealtimeSession.events`, `RealtimeSession.close` | Barge-in occurs only after tool entry, triggers interruption, settles the tool cleanup event and closes session; function outputs precede response.create. |
| Wall-time-independent utilities | `current_datetime_spec.py`, `date_resolver_spec.py`, `event_store_spec.py`, `tracer_events_spec.py`, `tracer_system_spec.py`; `CurrentDateTimeTool.run`, `ResolveDateTool.run`, `EventStore`, `TracerSystem` | Fixed winter/summer instants preserve local EST/EDT formatting and exact timestamps; next Friday resolves exactly 2023-10-06; tracer/store queries use a fixed epoch. |

## Installed artifact verification

The scripts retain their supported invocation arguments and responsibilities.
Run from a fresh environment outside the checkout; each asserts that imported
production modules come from the installed wheel. The checkout is read only for
JSON contract inputs and verifier/helper code.

```bash
uv build
uv export --format requirements-txt --no-emit-project --no-dev --output-file /tmp/mojentic-runtime.txt
uv venv /tmp/mojentic-inprocess-consumer/.venv
uv pip install --python /tmp/mojentic-inprocess-consumer/.venv/bin/python \
  -r /tmp/mojentic-runtime.txt dist/mojentic-3.0.0-py3-none-any.whl
```

With `checkout` set to this checkout's absolute path, invoke:

```bash
uv run --offline --no-project --no-sync --directory /tmp/mojentic-inprocess-consumer \
  --python /tmp/mojentic-inprocess-consumer/.venv/bin/python \
  "$checkout/scripts/verify_readiness.py" "$checkout"
uv run --offline --no-project --no-sync --directory /tmp/mojentic-inprocess-consumer \
  --python /tmp/mojentic-inprocess-consumer/.venv/bin/python \
  "$checkout/scripts/verify_stream_timing.py" \
  "$checkout/src/mojentic/llm/gateways/fixtures/contracts/first_token_v1.json"
uv run python scripts/verify_stream_timing.py --source-id
```

`verify_readiness.py` checks every model-window response/error and exact request,
reasoning controls, structured results, native tool continuation, Anthropic
history, immutable admitted retries and permanent errors. `verify_stream_timing.py`
checks Ollama, oMLX and OpenAI events, broker/session/recovery routes, empty
streams, malformed choices and unsent/paused-close metadata. Its clock assertions
are exactly 31.25 ms. Both run with the same network and sleeper guards as the
library tests. The `--source-id` digest includes both scripts and the helper.

## Quality and limits

Final verification: **2,664 tests passed**, **86.74% coverage** in the configured
`--cov=src` pytest gate (85% minimum),
all four `.hone-gates.json` gates exited 0, full flake8/ruff/format checks passed,
and both security audits reported no known vulnerabilities. Both installed-wheel
scripts exited 0 under the audit-hook/sleeper guards. The additional bare
`uv run pytest --cov` run also passed all 2,664 cases (88.06%, including
executed helpers outside the configured source scope). The exact tested source ID is
`6cadd9ab8dfeb22bd4f3930b925b0ae9ac783ff2a01fc0d6d65d3016ebe41b8d`.

Nineteen previously dormant dispatcher/aggregator tests used `test_*` names while
pytest collected only `should_*`. Their checks now run under the configured
naming rule; aggregator replacement checks use public receive/wait entrypoints.
No test-discovery rule or gate was weakened.

All root `.hone-gates.json` commands and applicable coverage, full flake8/ruff,
formatting, locked-dependency audit, outdated-dependency inventory, documentation
build and fresh-wheel verification are recorded with actual exits in the
validation record. Coverage must remain above 85%; no cases, gates, thresholds,
audit scope or production APIs were weakened. GitHub Actions jobs each have
`timeout-minutes: 15`. Foundry owns Git finalization; no commit, push, release,
version bump or ref mutation is part of this correction.
