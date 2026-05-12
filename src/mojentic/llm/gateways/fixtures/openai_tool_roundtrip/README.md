# OpenAI Tool Round-Trip Fixtures

These three JSON files are **shared verbatim** across all four Mojentic language ports:

- `mojentic-py` (Python)
- `mojentic-ts` (TypeScript)
- `mojentic-ex` (Elixir)
- `mojentic-ru` (Rust)

**If you change any of these files, you MUST update all four ports.** The files must remain
byte-identical across ports so that the round-trip scenario is tested at the same layer
with the same data everywhere.

## Scenario

A user asks "What's the weather in Paris?"

1. The LLM responds with a `get_weather` tool call with `{"location": "Paris"}`
   — captured in `response-1-tool-call.json`.
2. The tool returns `{"temperature_c": 22, "conditions": "sunny"}`
   — captured in `tool-result.json`.
3. The LLM produces the final answer `It's currently 22°C and sunny in Paris.`
   — captured in `response-2-final.json`.
