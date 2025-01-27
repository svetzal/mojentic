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
❯ ollama list
NAME                                ID              SIZE      MODIFIED     
deepseek-r1:70b                     0c1615a8ca32    42 GB     5 days ago      
gemma2:2b                           8ccf136fdd52    1.6 GB    2 weeks ago     
phi4:latest                         ac896e5b8b34    9.1 GB    2 weeks ago     
mxbai-embed-large:latest            468836162de7    669 MB    3 weeks ago     
llama3.1-instruct-8b-32k:latest     9824a1505287    6.9 GB    3 weeks ago     
llama3.3-instruct-70b-32k:latest    9f0ff3847e57    58 GB     3 weeks ago     
llama3.3-70b-32k:latest             591f0115a6ff    42 GB     3 weeks ago     
llama3.3-instruct:latest            d98d94e280ea    58 GB     6 weeks ago     
llama3.3:latest                     a6eb4748fd29    42 GB     7 weeks ago     
llama3.1:70b                        c0df3564cfe8    39 GB     2 months ago    
llama3.1:8b                         42182419e950    4.7 GB    2 months ago    
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

llm = LLMBroker("llama3.3")
```

## Explicitly Specifying a Gateway

### Using OllamaGateway

The [LLMBroker] can be initialized with an explicit gateway, which will be used to connect to the model.

In this case connect to a local Ollama instance that has the `llama3.3` model available.

```python
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OllamaGateway

llm = LLMBroker("llama3.3", gateway=OllamaGateway())
```

If you want to connect to an Ollama instance on a different computer or server, you can specify the host and port:

```python
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OllamaGateway

llm = LLMBroker(
    "llama3.3",
    gateway=OllamaGateway(host="http://myserver.local:11434")
)
```

You can also pass through any headers you may need for authentication or other purposes:

```python
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OllamaGateway

llm = LLMBroker(
    "llama3.3",
    gateway=OllamaGateway(
        host="http://myserver.local:11434",
        headers={"x-some-header": "some value"}
    )
)
```

### Using OpenAIGateway

If you have access to an OpenAI model, you can use the [OpenAIGateway] to connect to it.

```python
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
