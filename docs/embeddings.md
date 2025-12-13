# Embeddings

Embeddings allow you to convert text into vector representations, which are useful for semantic search, clustering, and similarity comparisons.

## Setup

You need an embedding model. Ollama supports models like `mxbai-embed-large` or `nomic-embed-text`.

```python
from mojentic.llm.gateways import EmbeddingsGateway

# Initialize gateway
gateway = EmbeddingsGateway(model="mxbai-embed-large")
```

## Generating Embeddings

```python
text = "The quick brown fox jumps over the lazy dog."
vector = gateway.embed(text)

print(vector[:5])
# => [0.123, -0.456, ...]
```

## Batch Processing

You can embed multiple texts at once:

```python
texts = ["Hello", "World"]
vectors = gateway.embed_batch(texts)
```

## Cosine Similarity

Mojentic provides utilities to calculate similarity between vectors:

```python
from mojentic.utils.math import cosine_similarity

similarity = cosine_similarity(vector1, vector2)
```
