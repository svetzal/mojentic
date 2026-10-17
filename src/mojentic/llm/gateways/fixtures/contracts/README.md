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
