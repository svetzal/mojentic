# Opt-in Ollama completion recovery

Recovery resends one failed provider completion. It preserves encoded request bytes
and keeps transport attempts separate from broker tool rounds. It never restarts
a session or executes a previously completed tool again.

Existing callers keep their SDK behavior and errors. Configure `recovery_policy`
on an `OllamaGateway` to opt in for `LLMBroker.generate`, `generate_response`,
`generate_object`, `generate_stream`, `ChatSession.send`, and `send_stream`:

```python
from mojentic.llm import LLMBroker
from mojentic.llm.chat_session import ChatSession
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.recovery import AdmissionContext, RecoveryError, RecoveryPolicy


async def admit(context: AdmissionContext) -> str:
    # Replace with your own ownership/termination check. Reject until it succeeds.
    # HTTP 503/504, timeout, or socket close alone does not prove inference ended.
    return "reject"


gateway = OllamaGateway(recovery_policy=RecoveryPolicy(
    max_attempts=3,
    base_delay=0.1,
    delay_ceiling=30,
    budget=60,
    admission=admit,
))
broker = LLMBroker("your-model", gateway=gateway)
session = ChatSession(broker)
try:
    answer = session.send("Explain request recovery")
except RecoveryError as error:
    safe_summary = error.report.model_dump_json()
    # Explicit inspection is sensitive; apply your own storage policy.
    original_exception = error.inspect_cause()
    exact_response_bytes = error.inspect_response()
    exact_response_headers = error.inspect_headers()
```

A policy defaults to one attempt, including the original request. Eligible errors
include transport/client timeouts and HTTP 429/500/502/503/504. A caller-selected
status cannot override permanent 400/401/403 or semantic-output safety. Malformed
responses, invalid structured output, provider errors, redirects, and capture
failures never trigger a resend. Ordinary finish handling remains unchanged.
The opted-in structured path raises a `RecoveryError` with the original Pydantic
`ValidationError`; the legacy path retains its existing validation behavior.

Every ambiguous local resend requires explicit asynchronous admission. A pending
coroutine remains pending. Only `"allow"` admits a retry; `"reject"` stops it.
No hook yields `admission_required`. Neither generated IDs nor caller admission
prove idempotency or remote inference termination.

Backoff uses full jitter below the smaller of the delay ceiling and exponential
base delay. Retry-After seconds or HTTP dates set a minimum delay. Invalid and
absent values are explicit; excessive minima cause refusal rather than shortening.
A duration budget starts at the first failure; `deadline` is absolute monotonic
time. Both constrain admission, backoff, and dispatch, including time consumed
by request-capture and lifecycle callbacks. An admitted generation can finish
later. No automatic whole-generation timeout is added; an explicitly configured
Ollama timeout still applies. Clocks, sleeper, and jitter are injectable.

## Asynchronous admission and cancellation

Use the native asynchronous gateway call in an event loop. Run the existing
synchronous broker/session APIs with `asyncio.to_thread` when needed. Supply a
fresh `RecoveryCall` for each concurrent call. `recovery_call` on the gateway is
convenient for a single synchronous broker/session operation:

```python
import asyncio

from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.recovery import RecoveryCall


async def complete(gateway):
    call = RecoveryCall()
    task = asyncio.create_task(gateway.complete_with_recovery(
        call=call, model="your-model", messages=[LLMMessage(content="Hello")]))
    # Your controller can call call.cancel() from another task or thread.
    return await task
```

Cancellation closes locally owned HTTP resources, admission, and backoff without
a later attempt. The opted-in path raises `RecoveryError` with outcome `cancelled`,
including when its task is cancelled. Closing the request does not establish
that Ollama terminated generation.

## Reports and explicit wire capture

`generate_response` and the async gateway return a response with a typed
`recovery_report`. Safe report metadata is also under `response.metadata["recovery"]`.
The report includes a final identity/progress and one history entry per failed
wire attempt. Each history entry has explicit sensitive inspection methods.
Pre-dispatch failure/cancellation records zero wire attempts and no attempt ID.
Admission/backoff cancellation retains the prior failed attempt and adds a
separate final cancellation classification. Logical IDs remain stable across
retries; attempt UUIDs are distinct, unmasked correlation values.

`observer` receives immutable, payload-free `LifecycleEvent` models in order.
`wire_observer` explicitly receives sensitive `WireEvent` objects for the actual
request, response headers/status, and each raw response-body chunk. Request bytes
include any images encoded once before sending. Capture includes HTTPX's outgoing
headers and URL-based Basic authorization on the same request that is sent.
The request hook precedes dispatch: it can prevent the request, so a capture alone
does not prove a wire attempt occurred. Hooks must synchronously accept
an event or raise; returning an awaitable is unsupported. The caller owns capture
storage, access, redaction, and retention. The library never persists captures.
A hook failure retains response evidence and its typed original exception,
prevents success, and prohibits another request. Observed content, reasoning, or
tool evidence is recorded before calling the body hook, even when nothing was
delivered to the caller.

Cancellation requested by a request or `attempt_started` hook is checked before
dispatch and produces no wire history. Header/body capture cancellation retains
the received status, private headers, bytes and observed semantics, with no
delivered output. An actual cancelled request emits `attempt_failed` before one
terminal `cancelled` event. Admission/backoff cancellation retains the earlier
failed request and adds a typed cancellation cause to the terminal failure.

Recovery uses a dedicated HTTP transport with retries and redirects disabled.
No SDK or environment proxy retry layer runs underneath it. Provider text,
credentials, tool arguments, and raw exception text are excluded from safe
reports and lifecycle serialization. Provider codes and request IDs are omitted,
including syntactically valid UUIDs: a UUID can echo an outbound credential or
payload. Raw response headers remain available through `Failure.inspect_headers()`
and `RecoveryError.inspect_headers()`; these methods are explicitly sensitive.
Successful content, explicit application tracers, and explicit wire capture remain
caller-owned sensitive data.

## Capability boundaries

| Adapter / operation | Recovery in this increment | Remote cancellation / status / termination / idempotency |
| --- | --- | --- |
| Ollama ordinary and structured completion | Opt-in, loopback tested | Unsupported / unsupported / unknown / unsupported |
| Ollama tool-capable streaming | Opt-in recovery; explicit typed terminal outcomes and attempt evidence | Unsupported / unsupported / unknown / unsupported |
| Ollama raw stream events | Existing single-turn API; tools rejected | Recovery configuration does not enable retries |
| oMLX completion | Pending; existing adapter behavior | No recovery claim |
| OpenAI completion | Pending; existing adapter behavior | No recovery claim |
| Anthropic completion | Pending; existing adapter behavior | No recovery claim |
| Embeddings and realtime voice | Outside completion recovery scope | No recovery claim |

The existing `LLMMessage` and Ollama adapter do not represent native reasoning in
outgoing history. Recovery preserves the current encoded message history exactly
and returns native reasoning from successful responses; it does not add native
history support or change reasoning-disabled behavior. Replay after observed semantics, cross-port
parity, live inference, and experiment efficacy remain unverified and pending.
See the repository's `RECOVERY-CONFORMANCE.md` for actual assertion mappings.

## Migrating from the preserved first recovery increment

The opt-in APIs and immutable payload policy are retained. Consumers of
`provider_request_id` must use private header inspection when they need the
untrusted provider value; client logical/attempt UUIDs remain safe correlation
metadata. Capture consumers now receive URL Basic authorization as sent and
must protect it along with bodies. Cancellation consumers should expect an
`attempt_failed` event for an active cancelled wire request before `cancelled`.
Use the report's wire count/history rather than counting request-capture or
`attempt_started` callbacks, since a callback can prevent dispatch. The legacy
SDK path, other adapters, and ordinary finish behavior are unchanged. The next
streaming increment described below adds recovery only to the tool-capable path.

## Directory tool exception compatibility

`CreateDirectoryTool` continues to accept a `FilesystemGateway` directly:

```python
from mojentic.llm.tools.file_manager import CreateDirectoryTool, FilesystemGateway

tool = CreateDirectoryTool(FilesystemGateway("/your/sandbox"))
result = tool.run("nested/directory")
```

Successful creation, including an existing directory, returns the same success
string. Sandbox violations, permission failures and other OS errors retain their
error strings. Unexpected programming failures propagate with their original
exception object instead of being converted to strings. Callers that previously
treated every failure as a returned string should let unexpected exceptions
reach their application error boundary. The focused regression uses a real
filesystem gateway and a failing path protocol object; it verifies exception
identity and no filesystem mutation. This documents the preserved lint-cleanup
correction and adds no new runtime behavior or completion-recovery guarantee.


## Migrating tool-capable streams

Configuring `recovery_policy` now also opts `OllamaGateway.complete_stream`,
`LLMBroker.generate_stream`, and `ChatSession.send_stream` into recovery of each
individual completion. The synchronous APIs continue yielding their existing
chunks or strings. They raise `RecoveryError` on interruption or exhaustion;
they never commit partial session text as a completed assistant reply. Completed
tools execute once. Subsequent completion retries preserve that tool's result,
and transport attempts do not consume additional tool depth.

For native asynchronous consumption, use the additive typed stream API:

```python
from contextlib import aclosing

from mojentic.llm import LLMMessage, StreamOutcome
from mojentic.llm.recovery import RecoveryCall


async def consume(gateway):
    call = RecoveryCall()
    async with aclosing(gateway.complete_stream_with_recovery(
        call=call, model="your-model", messages=[LLMMessage(content="Hello")]
    )) as events:
        async for event in events:
            if event.kind == "content":
                print(event.text, end="")
            elif event.kind == "completed":
                assert event.outcome is StreamOutcome.SUCCEEDED
                return event.response
            elif event.kind == "failed":
                # report is safe; inspecting error causes or raw bytes is sensitive.
                raise event.error
```

Events include content, reasoning, tool fragments, frame progress, terminal
metrics, and exactly one `completed` or `failed` outcome. Tool fragments are
observations; only a successful completed response provides executable tool calls.
Every event carries the logical/attempt identity. `frame_index` starts at one for
each attempt's decoded frames. `StreamFrameProgress` uses UTF-8 byte lengths;
`StreamMetrics` preserves Ollama's counter names and nanosecond durations, with
missing values left `None`. Throughput is calculated only from reported eval
count and nonzero eval duration. Model and finish strings remain available in
explicit metrics inspection and the completed response, but are excluded from
safe metric formatting and serialization because providers can echo secrets.
Semantic event fields and responses likewise require explicit inspection.

A structurally valid `length` terminal emits frame progress, metrics, then failure.
It delivers no semantics or completed tools from that frame. Malformed frames
emit no telemetry. Any observed content, reasoning, or tool fragment prevents
replay, including when capture fails before delivery. Keepalive-only progress can
recover after explicit admission. Capture failures remain terminal and retain
the original exception, raw bytes, private headers, and observed evidence.

Recovery streams require newline-terminated NDJSON frames. At clean EOF or HTTP
truncation, any unfinished frame is a protocol failure and cannot be replayed,
even when admission would allow it. A complete JSON object without its trailing
newline is still unfinished: its semantics may be observed privately but are
never delivered as content, reasoning, executable tools, or success. Exact
response bytes and headers remain inspectable; HTTP truncation retains its
original typed transport cause while the failure category stays `protocol`.

EOF between complete frames without terminal proof is a transport interruption.
Complete keepalive-only frames permit another attempt only after explicit caller
admission; absent or rejected admission sends no second request. Previously
observed semantics still prevent replay. These outcomes propagate through
`complete_stream_with_recovery`, `LLMBroker.generate_stream`, and
`ChatSession.send_stream`. Broker and session callers receive `RecoveryError`
on failure and do not execute tools or store a completed assistant message from
an unfinished frame. Ordinary and structured permanent HTTP status handling
retains its existing behavior.

The stream owns its HTTP/admission tasks independently of consumer pacing.
`call.cancel()` closes locally owned resources even while consumption is paused;
cancellation wins over buffered terminal telemetry and completed responses.
Close iterators when abandoning consumption. Socket closure is local evidence,
not proof of remote inference termination. Local cancellation, request status,
and idempotency capabilities retain the limits in the table above.

`complete_stream_events` and `generate_stream_events` remain single-turn raw
compatibility APIs and reject tool use. Recovery configuration does not alter
them. Without a recovery policy, tool-capable SDK streaming retains its existing
finish handling and provider error types. Native reasoning history that the
Python message model cannot represent remains an explicit gap; supported outgoing
reasoning controls, ordinary/structured recovery and finish handling are preserved.
