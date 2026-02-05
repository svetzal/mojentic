# Using Different LLMs

Leveraging an LLM is a powerful way to drive your agent's behaviour. There are a lot to choose from, though.

At this time, Mojentic can leverage local Ollama models, or any hosted OpenAI model you may have access to through
your own OpenAI account.

## Local Models

By default, the [LLMBroker] will use a locally running [Ollama](https://ollama.com/) instance to launch different models
and generate responses. Refer to the Ollama website to get it installed and running locally, and pull down some models
you can use.

Use `ollama list` to list the available models on your computer, and give you a handy reference to each of their names.

```
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

For details on reasoning effort, see [Reasoning Effort Control](reasoning_effort.md).

## Using llms.txt for Configuration

Mojentic now supports a simple configuration file called `llms.txt` that makes it easier to manage your LLM configurations. This is especially useful when you want to switch between different models or environments without changing your code.

Create a file named `llms.txt` in your project directory with the following format:

```
# Comments start with #
# Each line defines a model configuration in the format: name=model_name,gateway_type,param1=value1,param2=value2,...

# Local Ollama models
local_qwen=qwen3:14b,ollama
local_phi=phi4:14b,ollama,host=http://localhost:11434

# OpenAI models
gpt4=gpt-4o,openai,api_key=your_api_key_here
gpt4mini=gpt-4o-mini,openai,api_key=your_api_key_here,base_url=https://api.openai.com/v1
```

Then, you can use these configurations in your code:

```py { linenums=1 }
import os
from mojentic.llm import LLMBroker

# This will load the configuration from llms.txt
llm = LLMBroker.from_config("local_llama")

# You can also override parameters
llm = LLMBroker.from_config("gpt4", api_key=os.getenv("OPENAI_API_KEY"))
```

The `llms.txt` file can be placed in:
1. The current working directory
2. Your home directory
3. A location specified by the `MOJENTIC_CONFIG` environment variable

This makes it easy to share configurations across projects or maintain different configurations for different environments.
