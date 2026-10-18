# Testing

Run the library specifications with `uv run pytest --cov --cov-fail-under=85`.
Specifications live beside implementation modules as `*_spec.py`, with `Describe*`
classes and `should_*` methods. Separate setup, action and assertions with blank
lines. Test names explain behavior; method docstrings and phase comments add no
required evidence.

## Public APIs and I/O doubles

Drive the API as a caller does. Real brokers, chat sessions, provider SDKs,
decoders and recovery engines execute normally. Substitute gateway, HTTP
transport, clock and sleeper boundaries only. Use `mocker.Mock(spec=GatewayClass)`
for gateway mocks. Never patch SDK clients or private library methods in new tests.

`scripts/inprocess_http.py` supplies the shared HTTP transport double used by
recovery, request fidelity, native reasoning, metadata and first-token specs.
It intercepts both httpx and the OpenAI SDK's httpx2 network transport. Responses
come from existing versioned contract cases or their documented provider
response envelopes. Capture assertions compare encoded bytes, full JSON payloads,
exact accepted IDs/codes and lifecycle order. A count alone is insufficient.
The shared fixture exports remain available from their original spec modules.

`scripted_http` supports finite statuses, headers, body chunks, injected read
errors and truncated responses. Chunk delays advance a virtual monotonic clock;
they never sleep. `unfinished_http` exposes started/closed events for cancelling
an active send or closing a paused response. Use these events to prove cleanup.
`virtual_sleep` records retry time on that clock. Inject deterministic jitter and
use a scheduler clock when testing a pending budget deadline. First-token tests
use exact binary-fraction values such as 31.25 ms and 156.25 ms.

The autouse socket guard rejects AF_INET/AF_INET6 socket construction, DNS,
connect and bind operations. It rejects blocking sleeps and substitutes a
cooperative asynchronous sleeper. asyncio's internal Unix socketpair is allowed.
Tests must explicitly inject a tokenizer gateway when token math is incidental,
so a cold tiktoken cache cannot trigger a download. No live provider, service,
local server, registry, credential or model installation is required.

Dispatcher and recursive-agent specs synchronize on public results and events.
Tool-runner specs assert active invocation counts and completion order; realtime
interruption waits for tool entry and cleanup. No elapsed-time bound constitutes
acceptance evidence. GitHub Actions jobs carry explicit time limits to bound
broken or deadlocked runs.

## Packaged verification

Both existing verification scripts retain their installed-wheel checks and
public API responsibilities. Run them outside the checkout after installing the
built wheel into a fresh uv environment. They load only JSON contracts from the
checkout and share the in-process transport helper beside the scripts. They
reject source production imports and network access. See the exact commands,
source identity, contract hashes and actual outcomes in
`CONFORMANCE-3.0.0.md` and
`RECOVERY-CONFORMANCE.md` at the repository root.

Run `uv run flake8 src`, `uv run ruff check src`, `uv run bandit -c .bandit -r src`,
`uv run pip-audit`, and `uv run mkdocs build` as well as the complete pytest gate.
The lockfile export audit checks locked dependencies; package-manager and audit
commands may access registries, while the tests and verification scripts may not.
