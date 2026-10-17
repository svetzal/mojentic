# Native reasoning controls and history

`CompletionConfig` accepts six distinct `ReasoningEffort` values. Lowercase string
values also work. Leaving `reasoning_effort=None` sends no reasoning control;
this does not mean reasoning is disabled or imply equivalent provider defaults.

| Effort | Ollama | oMLX |
| --- | --- | --- |
| `Disabled` | `think: false` | `enable_thinking: false` |
| `Enabled` | `think: true` | `enable_thinking: true` |
| `Low` | `think: "low"` | `reasoning_effort: "low"` |
| `Medium` | `think: "medium"` | `reasoning_effort: "medium"` |
| `High` | `think: "high"` | `reasoning_effort: "high"` |
| `XHigh` | `think: "xhigh"` | `reasoning_effort: "xhigh"` |

These controls apply to ordinary, streaming, recovery and structured output.
Structured JSON remains in content/object; reasoning stays separate.

## Explicit model profiles

```python
from mojentic.llm import CompletionConfig, ReasoningEffort, ReasoningProfile

config = CompletionConfig(
    reasoning_profile=ReasoningProfile.qwen3_8(),
    reasoning_effort=ReasoningEffort.XHigh,
    retain_reasoning=True,
)
```

Qwen3.8 supports exactly Disabled, Low, Medium and XHigh, plus native history.
Enabled and High fail configuration validation for this profile. Omitted effort
remains unspecified. Profiles are chosen by the caller, never inferred from a
model identifier or alias. A custom `ReasoningProfile` declares `name`,
`supported_efforts` and `supports_reasoning_history`. Unsupported efforts or
retention fail before HTTP. Without a profile the gateway forwards exact controls
and the provider decides model support.

## Native history and tool continuation

Gateway responses expose native reasoning in `LLMGatewayResponse.thinking`.
Assistant history uses `LLMMessage.thinking`; visible text stays in `content`,
with tool calls and results in their own fields. Ollama serializes assistant
reasoning as `thinking`; oMLX serializes it as `reasoning_content`.

Broker retention is off by default. Pass `retain_reasoning=True` to `generate`
or `generate_stream` to attach completed tool-turn reasoning to assistant history
before the next request. Streamed visible output remains text only. Partial,
failed, capped or cancelled turns never supply retained reasoning. Native history
is never reconstructed from visible content. For an outer turn managed by your
application, explicitly copy a completed gateway response's `thinking` into an
assistant message when desired.

With retention enabled oMLX requests
`chat_template_kwargs: {"preserve_thinking": true}`. This records the client
request; forced server settings can override it. Tool identifiers and arguments
remain distinct from reasoning. oMLX carries tool-call identifiers; the Ollama
SDK's tool protocol uses function names and arguments without native call IDs.

## Migration from the old effort switch

Earlier Python versions mapped every Ollama level to `think: true`. Use
`ReasoningEffort.Enabled` for that boolean behavior. Named levels now send their
exact strings. Qwen3.8 callers should choose its explicit profile and a supported
level rather than Enabled. Ollama ordinary tool arguments now retain JSON types,
and assistant history includes every tool call in its original order.

OpenAI retains existing Low/Medium/High handling and model parameter adaptation.
It rejects Disabled, Enabled, XHigh, explicit profiles, retention and native
assistant history with `ValueError`; it does not accept the oMLX extension.
Existing temperature/token defaults and deprecated individual keyword arguments
are unchanged by this reasoning correction. Metadata/request fidelity is separate
3.0.0 work.

Local tests execute `native-reasoning-v1` through public gateway HTTP and broker
continuations. External consumers and live model servers have not verified this
set. See `CONFORMANCE-3.0.0.md` for identities, commands and remaining verification;
the coordinated publication hold remains.
