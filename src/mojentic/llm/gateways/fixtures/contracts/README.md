The October 17 library self-validation policy supersedes historical counterpart
requirements below. These unchanged contracts are exercised through Python public
APIs, production gateways against controlled HTTP and a fresh installed wheel.
Current commands, identities and limits are in `CONFORMANCE-3.0.0.md` at the
repository root. External adoption verifies released versions in its own scope.

# Native reasoning contract v1

`native_reasoning_v1.json` is an unchanged copy of
`mojentic-ex/test/contracts/native_reasoning_v1.json`, inspected read-only at
Elixir revision `98b54a0cf0b028b82d38655ac59ebafcd7988077`.
SHA-256: `be212ff011125f1d0927e3a65a0d7cd87eedbf9f5ff69e803b4112a80ae6b1f6`.
Its source hash identifies the binding `REASONING-PROTOTYPE-2026-10.md`.

`native_reasoning_spec.py` executes its controls and semantic payloads through
public Python gateways and broker continuations. Scripted HTTP responses derive
from this shared set; the existing live-captured oMLX fixtures also test the
original proof case. The normal `uv run pytest` gate includes this verification.
External consumer/provider runs against the same set remain coordination work.
Do not infer live compatibility from local scripted HTTP verification.


# Request fidelity contract v1

`request_fidelity_v1.json` is an unchanged copy of
`mojentic-ex/test/contracts/request_fidelity_v1.json`, inspected read-only at
`ff479d92067b6ffbd99d3cd5533f96e13ebc09b0`.
SHA-256: `6f02088311f50707b9c12154d888f844928c23d359043cb2e5d5654bf7e5eaea`.
`request_fidelity_spec.py` runs all seven configurations through public gateways,
broker/session routes, structured completion, supported legacy/event streams,
recovery resends and tool continuations, capturing actual loopback HTTP payloads.
Scripted response semantics and retryable errors derive from this set. Python's
strict response parsers additionally need assistant roles; Anthropic needs its
native response envelope. These enrichments preserve the shared response content.
`uv run pytest` includes this verification. The supported API is unreleased 3.0;
explicit migration settings reproduce supported 2.1 config defaults. Independent
external provider/consumer verification remains unfinished.
