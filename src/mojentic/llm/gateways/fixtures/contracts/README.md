# Executable contract fixtures

The current conformance record is `CONFORMANCE-3.0.0.md` at the repository root.
It lists exact SHA-256 identities, working-tree source identity, public consumers,
production gateway verification and actual installed-wheel results.

- `native_reasoning_v1.json` retains the shared semantic cases originally copied
  from Elixir `98b54a0cf0b028b82d38655ac59ebafcd7988077`; its root reasoning
  source hash and bytes are unchanged.
- `request_fidelity_v1.json` retains all seven configurations and response cases
  originally copied from Elixir `ff479d92067b6ffbd99d3cd5533f96e13ebc09b0`.
  Its source hash now identifies `MODEL-METADATA-2026-10.md@4ae2f73`.
- `first_token_v1.json` remains Python's `py-stream-first-token-v1`, using
  `ts-stream-first-token-v1` as a read-only behavioral reference. Its cases are
  unchanged; the revised parent metadata hash is now recorded explicitly.
- `src/mojentic/llm/contracts/context_window_v1.json` retains every case and updates its
  parent metadata source hash in the same way.

Tests exercise the real public APIs and provider SDKs over the in-process
httpx/httpx2 transport in `scripts/inprocess_http.py`. Python-specific assistant
roles and native Anthropic envelopes preserve the shared response semantics.
Timing uses an injected clock with exact values, never sleeps or elapsed bounds.
No socket, live provider, service, registry or counterpart executable is needed.
The October 17 library self-validation policy applies; changed running-service
boundaries still require separately authorized paired contract verification.
