# Opt-in Ollama completion recovery

Recovery resends one failed provider completion. It preserves encoded request bytes
and keeps transport attempts separate from broker tool rounds. It never restarts
a session or executes a previously completed tool again.

Existing callers keep their SDK behavior and errors. Configure `recovery_policy`
on an `OllamaGateway` to opt in for `LLMBroker.generate`, `generate_response`,
`generate_object`, and `ChatSession.send`:

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
time. Both constrain admission and backoff. An admitted generation can finish
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
include any images encoded once before sending. Hooks must synchronously accept
an event or raise; returning an awaitable is unsupported. The caller owns capture
storage, access, redaction, and retention. The library never persists captures.
A hook failure retains response evidence and its typed original exception,
prevents success, and prohibits another request. Observed content, reasoning, or
tool evidence is recorded before calling the body hook, even when nothing was
delivered to the caller.

Recovery uses a dedicated HTTP transport with retries and redirects disabled.
No SDK or environment proxy retry layer runs underneath it. Provider text,
credentials, tool arguments, and raw exception text are excluded from safe
reports and lifecycle serialization. Arbitrary provider codes and request ID
strings are omitted; only UUID-valued `X-Request-ID` metadata is accepted.
Successful content, explicit application tracers, and explicit wire capture remain
caller-owned sensitive data.

## Capability boundaries

| Adapter / operation | Recovery in this increment | Remote cancellation / termination / idempotency |
| --- | --- | --- |
| Ollama ordinary and structured completion | Opt-in, loopback tested | Unsupported / unknown / unsupported |
| Ollama streaming | Pending; existing streaming behavior | No recovery claim |
| oMLX completion | Pending; existing adapter behavior | No recovery claim |
| OpenAI completion | Pending; existing adapter behavior | No recovery claim |
| Anthropic completion | Pending; existing adapter behavior | No recovery claim |
| Embeddings and realtime voice | Outside completion recovery scope | No recovery claim |

The existing `LLMMessage` and Ollama adapter do not represent native reasoning in
outgoing history. Recovery preserves the current encoded message history exactly
and returns native reasoning from successful responses; it does not add native
history support or change reasoning-disabled behavior. Streaming replay, cross-port
parity, live inference, and experiment efficacy remain unverified and pending.
See the repository's `RECOVERY-CONFORMANCE.md` for actual assertion mappings.
