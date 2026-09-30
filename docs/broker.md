# Using Different LLMs

Leveraging an LLM is a powerful way to drive your agent's behaviour. There are a lot to choose from, though.

At this time, Mojentic can leverage local Ollama models, or any hosted OpenAI model you may have access to through
your own OpenAI account.

## Local Models

By default, the [LLMBroker] will use a locally running [Ollama](https://ollama.com/) instance to launch different models
and generate responses. Refer to the Ollama website to get it installed and running locally, and pull down some models
you can use.

Use `ollama list` to list the available models on your computer, and give you a handy reference to each of their names.

```shell
❯ ollama list
NAME                                TAG       ID              SIZE      MODIFIED
qwen3:32b                         latest    7fc23b05c176    20 GB     3 weeks ago
gpt-oss:20b                       latest    a8f12e90d4c3    12 GB     2 weeks ago
qwen3:14b                         latest    8c17a193a96d    9.0 GB    1 month ago
phi4:14b                          latest    9b2c5a1f8e7d    8.5 GB    1 week ago
qwen3-coder:30b                   latest    c4d8f2a1b9e6    18 GB     2 weeks ago
gemma3:27b                        latest    e7a3c9d2f8b1    16 GB     3 weeks ago
qwen3:8b                          latest    42182419e950    4.7 GB    2 months ago
```

Each model has strengths and weaknesses. A good system of agents will use a variety of models to optimize for speed
and memory use. You can choose to use a single large LLM on a powerful machine, or several smaller LLMs tuned for
specific tasks.

In general, you will want to use the largest model or models you can fit in memory, in terms of their number of
parameters. The trade-offs are speed and memory usage.

Many if not all models may be quantized, that is instead of using 32-bit floating point numbers, they use 16-bit or
4-bit floating point numbers for model weights, cutting their memory footprint in half or a quarter.

eg Favour a 70B model over an 8B model, or an 8B model over a 2B model. If you have a choice between a large parameter
model and a large quantization, favour the larger parameter model. 4-bit quantization can retain surprisingly good
results.

If you're using Ollama, the simplest way to instantiate an [LLMBroker] is:

```python
from mojentic.llm import LLMBroker

llm = LLMBroker("phi4:14b")
```

## Explicitly Specifying a Gateway

### Using OllamaGateway

The [LLMBroker] can be initialized with an explicit gateway, which will be used to connect to the model.

In this case connect to a local Ollama instance that has the `phi4:14b` model available.

```py { linenums=1 }
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OllamaGateway

llm = LLMBroker("qwen3:32b", gateway=OllamaGateway())
```

If you want to connect to an Ollama instance on a different computer or server, you can specify the host and port:

```py { linenums=1 }
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OllamaGateway

llm = LLMBroker(
    "gpt-oss:20b",
    gateway=OllamaGateway(host="http://myserver.local:11434")
)
```

You can also pass through any headers you may need for authentication or other purposes:

```py { linenums=1 }
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OllamaGateway

llm = LLMBroker(
    "qwen3:14b",
    gateway=OllamaGateway(
        host="http://myserver.local:11434",
        headers={"x-some-header": "some value"}
    )
)
```

### Using OpenAIGateway

If you have access to an OpenAI model, you can use the [OpenAIGateway] to connect to it.

```py { linenums=1 }
import os
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OpenAIGateway

llm = LLMBroker(
    "gpt-4o-mini",
    gateway=OpenAIGateway(
        api_key=os.getenv("OPENAI_API_KEY")
    )
)
```

#### Environment variables and precedence

OpenAIGateway supports environment-variable defaults so you don’t need to hardcode secrets:

- If you omit `api_key`, it will use the `OPENAI_API_KEY` environment variable.
- If you omit `base_url`, it will use the `OPENAI_API_ENDPOINT` environment variable (useful for custom endpoints like Azure or OpenAI-compatible proxies).
- Precedence: values you pass explicitly to `OpenAIGateway(api_key=..., base_url=...)` always override environment variables.

Examples:

```py { linenums=1 }
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OpenAIGateway

# 1) Rely on environment variables
#    export OPENAI_API_KEY=sk-...
#    export OPENAI_API_ENDPOINT=https://api.openai.com/v1   # optional
llm = LLMBroker(
    "gpt-4o-mini",
    gateway=OpenAIGateway()  # picks up OPENAI_API_KEY/OPENAI_API_ENDPOINT automatically
)

# 2) Explicitly override one or both values
llm = LLMBroker(
    "gpt-4o-mini",
    gateway=OpenAIGateway(api_key="your_key", base_url="https://api.openai.com/v1")
)
```

### Using OMLXGateway

[oMLX](https://github.com/jundot/omlx) is an LLM server for Apple Silicon. It speaks
the OpenAI chat completions protocol, but use `OMLXGateway` rather than pointing
`OpenAIGateway` at it. The OpenAI gateway rewrites requests for model names it does not
know, drops `reasoning_content`, and chunks embeddings with the OpenAI tokenizer.
`OMLXGateway` sends your configuration as you wrote it.

```py { linenums=1 }
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OMLXGateway
from mojentic.llm.gateways.models import LLMMessage

llm = LLMBroker("Qwen3.8-27B-MLX-8bit", gateway=OMLXGateway())
print(llm.generate([LLMMessage(content="Reply with exactly: hello")]))
```

#### Configuration

| Setting | Constructor | Environment | Default |
| ------- | ----------- | ----------- | ------- |
| Host | `host` | `OMLX_HOST` | `http://localhost:8000` |
| API key | `api_key` | `OMLX_API_KEY` | none |
| Timeout | `timeout`, in seconds | `OMLX_TIMEOUT`, in milliseconds | 600 seconds |

- An explicit value wins over the environment, and the environment wins over the default.
- The host has no `/v1` suffix. The gateway adds `/v1` to every path.
- With an API key, the gateway sends `Authorization: Bearer <key>`. Without one, it
  sends no authorization header.
- One timeout covers every request, including `load_model`. Local models are slow: a
  16384-token reply at 16 tokens a second takes 17 minutes.

#### Requests

The gateway builds each request from `CompletionConfig` with no per-model changes. It
always sends `temperature` and `max_tokens` (never `max_completion_tokens`), and sends
`reasoning_effort` unchanged when you set it. It does not send `num_ctx` or
`num_predict`, because oMLX sets the context length per model.

`reasoning_effort` goes to the model's chat template, so its effect depends on the
model. Leave it unset to keep the model's default. Qwen 3 models think by default.

#### Thinking

oMLX reports the model's reasoning in `reasoning_content`. The gateway puts it in
`LLMGatewayResponse.thinking`, and `complete_stream` yields it as thinking chunks.
`generate_stream_events` has no thinking event, so reasoning produces no events there.

#### Truncation

When `max_tokens` ends generation during thinking, a non-streaming response puts the
partial reasoning in `content`, leaves `thinking` empty, and reports a `length` finish
reason. A streaming response keeps it as thinking. The gateway maps the fields as they
arrive and does not move text between them. **`content` is not an answer unless
`finish_reason` is `stop`.**

#### Structured output and the `Warning` header

`generate_object` sends `response_format: {type: "json_schema", json_schema: {name:
"response", schema: <schema>}}` and validates the content against your model.

When oMLX cannot compile a grammar for a `json_object` or `json_schema` request, it
falls back to instructions in the prompt and says so in a `Warning` response header. For
a structured output request, the gateway records that header in
`response.metadata["response_format_warning"]` (several headers are joined with `, `)
and logs a warning. It does not retry and does not fail. The header is ignored for text
or absent response formats. Validate the content either way.

#### Streaming

oMLX opens every stream with a keep-alive frame whose `model` is `keepalive`, and sends
more during long prefill. The gateway drops these frames before parsing, in both
`complete_stream` and `generate_stream_events`, so `keepalive` never appears as the
provider model. `generate_stream_events` follows the rules in
[Single-turn streaming with completion evidence](streaming.md#single-turn-streaming-with-completion-evidence).

#### Models and embeddings

```py { linenums=1 }
gateway = OMLXGateway()
gateway.get_available_models()               # the server's model ids, sorted
gateway.load_model("Qwen3.8-27B-MLX-8bit")   # returns when the model is in memory
gateway.unload_model("Qwen3.8-27B-MLX-8bit")
gateway.calculate_embeddings("some text", model="your-embedding-model")
```

- A chat request loads its model automatically. Use `load_model` to warm a model up
  ahead of time.
- oMLX downloads models only through its admin dashboard. There is no pull operation.
- `calculate_embeddings` needs a model, because oMLX has no standard embedding model.
  A missing or empty model raises `ValueError` before any request. The text goes in one
  request, with no client-side chunking.

#### Errors

A non-2xx response raises `httpx.HTTPStatusError`. Its `response` carries the status and
the oMLX error body, for example a 404 `not_found_error` for an unknown model, or a 400
`invalid_request_error` when you unload a model that is not loaded or embed with a chat
model. In `generate_stream_events` the same response is a `PROVIDER_ERROR` whose detail
holds `status_code` and the `error` object.

## Configuration with CompletionConfig

You can fine-tune LLM behavior using `CompletionConfig`:

```python
from mojentic.llm import LLMBroker, CompletionConfig

llm = LLMBroker("qwen3:32b")

config = CompletionConfig(
    temperature=0.3,      # Lower = more focused
    max_tokens=500,
    reasoning_effort="high"  # Enable extended thinking
)

messages = [LLMMessage(role=MessageRole.User, content="Explain quantum computing")]
response = llm.generate(messages, config=config)
```

### Available Parameters

- **temperature** (float): Controls randomness. Default: 1.0
- **num_ctx** (int): Context window size in tokens. Default: 32768
- **max_tokens** (int): Maximum tokens to generate. Default: 16384
- **num_predict** (int): Tokens to predict (-1 = no limit). Default: -1
- **reasoning_effort** (str | None): Extended thinking level — `"low"`, `"medium"`, `"high"`, or `None`. Default: None
- **response_format** (`ResponseFormat` | None): Output format to request from the provider. Default: None

For details on reasoning effort, see [Reasoning Effort Control](reasoning_effort.md).

### Requesting a response format

`response_format` asks the provider for plain text, a JSON object, or JSON that
follows a schema. The OpenAI and Ollama gateways forward it in streaming and
non-streaming requests.

```python
from mojentic.llm import CompletionConfig, ResponseFormat

json_mode = CompletionConfig(response_format=ResponseFormat(type="json_object"))

schema_mode = CompletionConfig(response_format=ResponseFormat(
    type="json_object",
    json_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
))
```

| Value | OpenAI request | Ollama request |
| ----- | -------------- | -------------- |
| `None` | unchanged | unchanged |
| `ResponseFormat(type="text")` | `response_format: {"type": "text"}` | no `format` |
| `ResponseFormat(type="json_object")` | `response_format: {"type": "json_object"}` | `format: "json"` |
| `ResponseFormat(type="json_object", json_schema=s)` | `response_format: {"type": "json_schema", "json_schema": {"name": "response", "schema": s}}` | `format: s` |

This records what you asked for. It does not prove that the provider enforced
the format, so validate the returned content yourself. `generate_object()` keeps
its own schema handling and takes precedence over `response_format`.

## Caller-owned context and native responses

Use `generate_response(messages, tools=tools)` to receive one native gateway response without
executing tools, extending history or making a follow-up request. Assemble the
complete message array before each call. The broker traces the supplied request
and returned response; it does not read repository guidance or apply a context policy.

The existing convenience completion method still executes tools and follows up.
Choose a serial or parallel runner according to the tools' effects. Parallel
execution does not make dependent edits safe.

Set `CompletionConfig(max_tool_iterations=None)` to disable the tool-round limit.
Existing finite defaults remain unchanged. Concurrency controls simultaneous
work; it is not a task budget or a loop detector.

Unknown tools now reach the runner and produce error receipts. The optional broker `tool_context` forwards cancellation and callbacks.

## Single-turn streaming with completion evidence

`generate_stream_events(messages, config)` streams one turn as typed events and
ends with exactly one terminal event: `StreamCompleted` with the finish reason,
usage and provider model, or `StreamError`. Use it when truncated or unfinished
output must never be treated as a result. It sends one request, supplies no tools
and never retries. See [Single-turn streaming with completion evidence](streaming.md#single-turn-streaming-with-completion-evidence).

Native responses preserve the fields supplied by the gateway. Missing provider
usage or termination evidence must remain unknown; configured model names and
text length are not substitutes for reported metadata. Response traces carry the
same evidence; see [Provider evidence in response traces](tracer.md#provider-evidence-in-response-traces).

### Image references in OpenAI messages

`LLMMessage.image_paths` accepts local files, HTTP(S) URLs and data URIs with
`OpenAIGateway`. URLs and data URIs pass through unchanged; local files are
encoded as base64 data URIs. The same adapter is used by `OMLXGateway`. Choose
an image-capable model.

```python
message = LLMMessage(
    content="Describe this image",
    image_paths=["https://example.com/photo.png"],
)
```

`LLMMessage.content` is optional plain text. Lists of content parts are not
accepted, including for system and tool messages.
