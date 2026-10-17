# Model context windows

Call `gateway.get_model_context_window(model)` to ask what the provider advertises.
The result is a `ModelContextWindow` with positive `max_context_tokens`, a source
`field`, and optional Ollama `model_num_ctx`. `None` means not advertised or
unsupported. Discovery never applies metadata to later completion requests.

```python
from mojentic.llm import CompletionConfig, effective_context_window
from mojentic.llm.gateways.ollama import OllamaGateway

gateway = OllamaGateway(host="http://localhost:11434")
window = gateway.get_model_context_window("qwen3:8b")
config = CompletionConfig(num_ctx=8192)
upper_bound = effective_context_window(window, config)
```

Ollama sends `POST /api/show` with exactly `{"model": model}` and the configured
headers. Any architecture's `*.context_length` supplies the advertised window.
The model's `parameters` text may supply `model_num_ctx`; this does not replace
the advertised window. oMLX uses its configured host and API key for
`GET /v1/models`, matches the exact model ID, and reads `max_model_len`.
OpenAI uses only exact entries in its local model registry, with `field="registry"`,
and sends no request. Unknown OpenAI models return `None` even if completion's
existing pattern fallback recognizes their names. Other gateways return `None`.

HTTP discovery raises `httpx.TransportError` when the server cannot be reached,
`httpx.HTTPStatusError` for non-success status (including unknown-model 404), and
`ValueError` for malformed JSON or metadata. A missing window is distinct from
an invalid advertised value; booleans, strings, zero and negative windows fail
validation. Discovery does not retry or change completion recovery behavior.

`effective_context_window(window, config)` is a pure helper. Caller `num_ctx`
takes precedence over `model_num_ctx`, and the selected size is clamped to the
advertised maximum. Without either setting it returns the advertised maximum;
without metadata it returns `None`, even when the caller supplied `num_ctx`.
Ollama server environment settings remain unknown, so the result is an upper
bound. It does not change `ChatSession.max_context`, configure a request, or
measure first-token timing.

Python verifies the unchanged `context-window-v1` JSON contract in
`src/mojentic/llm/contracts/context_window_v1.json` through loopback HTTP and
contract-derived gateway doubles. Run:

```bash
uv run pytest src/mojentic/llm/gateways/context_window_spec.py
sha256sum --check src/mojentic/llm/contracts/context_window_v1.manifest.sha256
```

These checks also run in the normal pytest gate. External server and
cross-repository consumer verification remain unfinished; see
[CONFORMANCE-3.0.0.md](https://github.com/svetzal/mojentic-py/blob/main/CONFORMANCE-3.0.0.md).
The coordinated publication hold remains in force.

::: mojentic.llm.model_context_window.ModelContextWindow
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.llm.model_context_window.effective_context_window
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false
