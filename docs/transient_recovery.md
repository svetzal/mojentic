# Opt-in completion recovery

Recovery resends one failed provider completion. It preserves encoded request bytes
and keeps transport attempts separate from broker tool rounds. It never restarts
a session or executes a previously completed tool again.

Existing callers keep their SDK behavior and errors. Configure `recovery_policy`
on an `OllamaGateway`, `OMLXGateway`, or `OpenAIGateway` to opt in for `LLMBroker.generate`, `generate_response`,
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
that the provider terminated generation.

## Reports and explicit wire capture

`generate_response` and the async gateway return a response with a typed
`recovery_report`. Ordinary responses also expose safe report metadata under
`response.metadata["recovery"]`; streaming responses retain `recovery_report`.
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
reports and lifecycle serialization. Unsupported, malformed and outbound-echoed
provider codes and request IDs are omitted; validated non-echoed values are retained.
A syntactically valid UUID can still echo an outbound credential or payload.
Raw response headers remain available through `Failure.inspect_headers()`
and `RecoveryError.inspect_headers()`; these methods are explicitly sensitive.
Successful content, explicit application tracers, and explicit wire capture remain
caller-owned sensitive data.

## Capability boundaries

| Adapter / operation | Recovery in this increment | Remote cancellation / status / termination / idempotency |
| --- | --- | --- |
| Ollama ordinary and structured completion | Opt-in, loopback tested | Unsupported / unsupported / unknown / unsupported |
| Ollama tool-capable streaming | Opt-in recovery; explicit typed terminal outcomes and attempt evidence | Unsupported / unsupported / unknown / unsupported |
| Ollama raw stream events | Existing single-turn API; tools rejected | Recovery configuration does not enable retries |
| oMLX ordinary and structured completion | Opt-in, typed schema failures and retained format warnings | Unsupported / unsupported / unknown / unsupported |
| oMLX tool-capable streaming | Opt-in recovery; safe finish plus `[DONE]` required | Unsupported / unsupported / unknown / unsupported |
| oMLX raw stream events | Existing single-turn API; recovery policy is ignored | Recovery configuration does not enable retries |
| OpenAI ordinary / structured / tool-capable streaming | Opt-in owned HTTP; model controls adapted before immutable encoding | Unsupported / unsupported / unknown / unsupported |
| oMLX / OpenAI structured streaming | Unsupported; rejected before dispatch | No recovery claim |
| OpenAI raw stream events | Existing single-turn API; recovery policy is ignored | Recovery configuration does not enable retries |
| Anthropic ordinary completion | Opt-in owned HTTP; existing system/user message selection retained | Unsupported / unsupported / unknown / unsupported |
| Anthropic structured / tools / streaming | Unsupported; schema/tool recovery requests fail before dispatch, no streaming entrypoint | No new provider capability |
| Embeddings and realtime voice | Outside completion recovery scope | No recovery claim |

The existing `LLMMessage` and Ollama adapter do not represent native reasoning in
outgoing history. Recovery preserves the current encoded message history exactly
and returns native reasoning from successful responses; it does not add native
history support or change reasoning-disabled behavior. Replay after observed semantics, cross-port
parity, live inference, and experiment efficacy remain unverified and pending.
See the repository's `RECOVERY-CONFORMANCE.md` for actual assertion mappings.

## Migrating from the preserved first recovery increment

The opt-in APIs and immutable payload policy are retained. Consumers of
`provider_request_id` now receive exact validated provider IDs when supported.
Use private header inspection for omitted or untrusted values; client logical/attempt
UUIDs remain separate correlation metadata. Capture consumers now receive URL Basic authorization as sent and
must protect it along with bodies. Cancellation consumers should expect an
`attempt_failed` event for an active cancelled wire request before `cancelled`.
Use the report's wire count/history rather than counting request-capture or
`attempt_started` callbacks, since a callback can prevent dispatch. The legacy
SDK path and ordinary finish behavior are unchanged. The next
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

## oMLX migration

Use the same policy, admission and cancellation objects with `OMLXGateway`:

```python
from mojentic.llm.gateways.omlx import OMLXGateway

omlx = OMLXGateway(
    host="http://localhost:8000",
    recovery_policy=RecoveryPolicy(max_attempts=3, admission=admit),
)
omlx_session = ChatSession(LLMBroker("your-model", gateway=omlx))
```

`complete`, `complete_with_recovery`, `complete_stream` and
`complete_stream_with_recovery` support request recovery. Existing broker and
session APIs use these public completion paths. `generate_response` returns tools
to its caller; it does not execute a tool loop. Structured streaming remains
unsupported. `complete_stream_events` and broker `generate_stream_events` retain
the existing single-request parser, finish rules, error events and no-tool API.
Their legacy error details can contain provider text; use the recovery entrypoints
for safe typed errors and recovery-event serialization.

With recovery disabled, the configured transport, timeout, settings/authentication,
validation behavior and response-format warning logging remain unchanged. Opt-in
completion recovery uses its own HTTP transport, with hidden retries, redirects
and environment proxies disabled. Custom `OMLXTransport` instances continue to
serve legacy, embedding and model-management calls; they are bypassed for opt-in
completion recovery. No remote cancellation, request-status or idempotency API is
claimed.

An opt-in oMLX request retains connect/write/pool timeouts but removes the active
response read timeout. A recovery budget constrains waiting and resending rather
than healthy generation. Use `RecoveryCall` to cancel active local HTTP ownership.
This intentional opt-in difference does not alter legacy timeouts or prove remote
termination. Model loading, unloading, listing and embeddings are outside scope.

Recovery preserves `reasoning_effort`, native returned reasoning, supported message
history, tool arguments, schema and generation controls. The shared message model
cannot represent native reasoning in outgoing history; no support is added here.
Ordinary finish reasons (including `length`) are preserved. Recovering streams
require `stop` or `tool_calls` followed by `[DONE]`. Observed reasoning, content or
tool fragments prevent replay even before caller delivery. Keepalive bytes alone
are raw progress and still require explicit admission before resending.

Reported usage, including nested cache details and timing values, is preserved on
the completed response and `event.metrics.usage`. Arbitrary provider usage keys,
model and finish strings are excluded from safe recovery-event serialization and
representation; explicit access and successful responses are sensitive. Structured
format warnings remain in successful response metadata, but the opt-in path does
not log untrusted warning header values. Private inspection and wire capture retain
exact response headers and raw bytes, including partial error bodies.


## Migrating cloud completions

`OpenAIGateway` accepts the same `recovery_policy` and `recovery_call` options as
local gateways. `complete` and `complete_stream` route through owned HTTP when a
policy is present. `LLMBroker.generate`, `generate_response`, `generate_object`
and `generate_stream`, and `ChatSession.send` and `send_stream` retain their
existing return types. Asynchronous callers use `complete_with_recovery` or
`complete_stream_with_recovery`; use `aclosing` around an asynchronous iterator
when stopping early. A completed tool followed by a failed completion executes
once, and retrying that completion does not consume another tool round.
`generate_response` returns tool requests without executing them.

```python
from mojentic.llm import LLMBroker
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.recovery import RecoveryPolicy

# API key and endpoint continue to use the gateway's existing environment defaults.
gateway = OpenAIGateway(recovery_policy=RecoveryPolicy(
    max_attempts=3, base_delay=0.1, delay_ceiling=5, budget=30,
))
broker = LLMBroker("your-openai-model", gateway=gateway)
# broker.generate(messages) / broker.generate_object(messages, YourModel)
# broker.generate_stream(messages, tools=your_tools)
```

Cloud providers may retry eligible failures without an admission hook, matching
the reviewed Rust OpenAI distinction. Supplying a hook still makes recovery wait
for its explicit decision. Ollama and oMLX continue requiring explicit admission
for ambiguous local requests. Admission never confirms remote termination or
idempotency. A cloud resend can incur another provider request and charge.

OpenAI adapts temperature, token limits, reasoning effort and tool support before
encoding. Pydantic schemas use the SDK's public strict-schema conversion; the
response content is validated into the requested model. Structured parsing retains
the SDK requirement for strict function tools. A successful tool-only turn with
`content=None`, `finish_reason="tool_calls"`, and valid tool arguments returns
`object=None` and preserves the exact tool ID, name and arguments. The caller
can then execute that tool and continue its conversation. Non-null structured
content still validates against the schema, even when tools are also returned;
malformed arguments and unsafe structured finishes remain failures. This
combined schema/tool shape is supported by `OpenAIGateway.complete` and
`complete_with_recovery`; `LLMBroker.generate_object` offers no tools, and
`ChatSession` has no structured-output entrypoint. Ordinary broker/session
callers retain tool execution across retries without repeating completed tools.
oMLX structured completion still requires non-null JSON content. Schema validation and
unsafe structured finishes become typed recovery failures with privately
inspectable original causes. Ordinary finish handling stays unchanged. Streaming
requires a safe finish and `[DONE]`; once reasoning, content or a tool fragment
has been observed, interruption never starts another request. A failed capture
hook can have observed but undelivered semantics. Provider model, usage and
finish telemetry remain inspectable; missing timing/token counters are not
invented. Raw `complete_stream_events` / `generate_stream_events` continue their
single-turn compatibility behavior and ignore the recovery policy.

`AnthropicGateway(api_key=..., recovery_policy=...)` supports ordinary
`complete` / `complete_with_recovery`, `LLMBroker.generate` / `generate_response`,
and `ChatSession.send`. Its existing system/user selection and first text-block
mapping are retained. It has no streaming implementation. Nonempty tools or an
`object_model`, or a configured JSON output format, produce a pre-dispatch `RecoveryError` whose private cause is
`NotImplementedError`; `recovery_capabilities()` reports structured and streaming
recovery as false. This increment adds no Anthropic tool execution or structured
output capability.

Recovery bypasses both SDKs' HTTP transports. SDK transport customizations do
not configure the owned recovery connection. It freezes literal UTF-8 bytes once,
disables hidden retries, redirects and environment proxy discovery, preserves
connect/write/pool timeout values, and removes the active response read timeout.
Budget/deadline limits govern recovery decisions rather than total generation
length. Use a fresh `RecoveryCall` to cancel an operation explicitly.

The opt-in path raises `RecoveryError`, replacing SDK transport/status errors at
the public completion boundary. Safe errors, reports, lifecycle events and default
stream serialization omit credentials, payload echoes, provider text and raw
exception messages. Explicit `inspect_cause`, `inspect_response`, `inspect_headers`
and `wire_observer` access retain exact sensitive evidence. Protect captures as
credentials and conversation data. Capture consumers can inspect immutable
request bytes and actual headers, including authentication; the library never
stores those captures automatically. See `RECOVERY-CONFORMANCE.md` for executed
entrypoints, assertion scope and retained external evidence.

The default OpenAI raw stream-event transport disables SDK retries and HTTP redirects,
so a redirect is reported as an error after one send. Recovery remains disabled
for these raw event APIs.


## Validated provider metadata (October 11 correction)

Public failure reports, per-attempt history and lifecycle evidence retain exact
accepted `provider_request_id` and `provider_code` values. Recovered responses
retain failed-attempt metadata in `recovery_report.history`; ordinary responses
also expose the serialized report in `metadata["recovery"]`. Broker and session
errors propagate the same report. Streaming responses use `recovery_report`.

Ollama, oMLX and OpenAI read `x-request-id`. Anthropic prefers `request-id`,
falling back to `x-request-id` only when the former header is absent. Only a single
UUID spelling (canonical, simple hexadecimal, braced or UUID URN), optionally
prefixed with `req_`, is accepted. Arbitrary IDs, malformed UUIDs and combined or
duplicate header values are omitted. A valid spelling alone does not establish
trust: IDs and their unprefixed forms occurring in outbound headers, immutable
payload bytes, decoded JSON strings or credentials are also omitted. This includes
URL Basic authentication and explicitly supplied Basic authorization. Matching is
case insensitive and conservative; legitimate collisions are omitted.

Complete JSON errors expose only recognized `error.code` strings:
`rate_limit_exceeded`, `server_error`, `invalid_request_error`, `invalid_api_key`,
`model_not_found`, `insufficient_quota`, and `overloaded_error`. Anthropic prefers
`error.type`, additionally recognizing `rate_limit_error`, `authentication_error`,
`permission_error`, `not_found_error`, and `api_error`. Recognized codes echoed
from outbound data are omitted too. No error-message text becomes public metadata.
For streaming error frames, extraction occurs before capture or delivery callbacks.
A truncated body retains numeric status and accepted header metadata; it cannot
supply a code until a complete error object is available. Permanent statuses still
prevent retries. This correction does not add unsupported operations.

These safeguards constrain copying provider data into public evidence; they do
not certify that any provider-supplied UUID is an authentic correlation ID or
sanitize arbitrary observer code. Explicit `inspect_headers`, `inspect_response`
and `inspect_cause` retain original sensitive evidence, as does opt-in wire
capture. Protect those channels separately. Formatted errors, serialized reports
and lifecycle events omit rejected values. Assertions and external review/capture
locations are recorded in `RECOVERY-CONFORMANCE.md`.
