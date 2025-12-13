# Structured Output Generation with Mojentic

## Why Use Structured Output?

When working with Large Language Models (LLMs), you often need more than just free-form text responses. Many applications require structured data that can be easily processed by your code. Structured output allows you to:

- Extract specific information in a predictable format
- Ensure consistency in LLM responses
- Integrate LLM outputs directly into your application's data flow
- Validate that responses contain all required fields

This capability transforms LLMs from simple text generators into powerful data extraction and structuring tools.

## When to Apply This Approach

Use structured output generation when:

- You need to extract specific data points from LLM responses
- Your application requires typed data rather than raw text
- You want to enforce a schema on LLM outputs
- You're building features that need to process LLM responses programmatically
- You need to ensure the LLM provides all required information

## Getting Started

Let's walk through an example of generating structured output using Mojentic. We'll use Pydantic models to define the structure we want the LLM to produce.

### Basic Implementation

Here's a simple example of generating structured output:

```python
from pydantic import BaseModel, Field
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.llm_broker import LLMBroker

# Define the structure we want the LLM to produce
class Sentiment(BaseModel):
    label: str = Field(..., title="Description", description="label for the sentiment")

# Create an LLM broker with a specified model
llm = LLMBroker(model="qwen3:14b")

# Generate structured output
result = llm.generate_object(
    messages=[LLMMessage(content="Hello, how are you?")],
    object_model=Sentiment
)

# Access the structured data
print(result.label)
```

This code will generate a structured response containing a sentiment label for the given prompt.

## Step-by-Step Explanation

Let's break down how this example works:

### 1. Define the data structure

```python
from pydantic import BaseModel, Field

class Sentiment(BaseModel):
    label: str = Field(..., title="Description", description="label for the sentiment")
```

This code:
- Creates a Pydantic model called `Sentiment`
- Defines a required string field called `label`
- Provides metadata about the field using `Field()`
- The `...` indicates that the field is required
- The `title` and `description` help the LLM understand what to provide

### 2. Set up the LLM broker

```python
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.llm_broker import LLMBroker

llm = LLMBroker(model="qwen3:32b")
```

Just like in the simple text generation example, we:
- Import the necessary components
- Create an LLM broker with a required model parameter
- The model parameter specifies which LLM to use (e.g., "qwen3:14b")

### 3. Generate structured output

```python
result = llm.generate_object(
    messages=[LLMMessage(content="Hello, how are you?")],
    object_model=Sentiment
)
```

The key differences from simple text generation:
- We use `generate_object()` instead of `generate()`
- We provide the `object_model` parameter with our Pydantic model
- The LLM will be instructed to generate output that conforms to this model

### 4. Access the structured data

```python
print(result.label)
```

The result is a Pydantic object of type `Sentiment`, not a string. We can access its fields directly as properties.

## Creating More Complex Structures

You can create more complex data structures for the LLM to fill:

```python
from pydantic import BaseModel, Field
from typing import List

class Point(BaseModel):
    x: float = Field(..., description="x coordinate")
    y: float = Field(..., description="y coordinate")

class Shape(BaseModel):
    name: str = Field(..., description="name of the shape")
    points: List[Point] = Field(..., description="coordinates of the shape's vertices")
    area: float = Field(..., description="calculated area of the shape")

# Generate a shape description
result = llm.generate_object(
    messages=[LLMMessage(content="Describe a triangle with vertices at (0,0), (1,0), and (0,1)")],
    object_model=Shape
)

print(f"Shape: {result.name}")
print(f"Area: {result.area}")
print("Points:")
for point in result.points:
    print(f"  ({point.x}, {point.y})")
```

## Using Different LLM Providers

Just like with simple text generation, you can use different LLM providers:

```python
import os
from mojentic.llm.gateways.openai import OpenAIGateway

# Set up OpenAI
api_key = os.getenv("OPENAI_API_KEY")
gateway = OpenAIGateway(api_key)
llm = LLMBroker(model="gpt-4o", gateway=gateway)

# Generate structured output
result = llm.generate_object(
    messages=[LLMMessage(content="Hello, how are you?")],
    object_model=Sentiment
)
```

## Summary

Structured output generation is a powerful feature of Mojentic that allows you to:

1. Define the exact structure of data you want from an LLM using Pydantic models
2. Generate responses that conform to that structure
3. Access the data programmatically through typed objects

This approach bridges the gap between free-form LLM responses and structured data that your application can easily process. By using Pydantic models, you get the added benefits of:

- Type validation
- Default values
- Field descriptions that help guide the LLM
- Nested structures and complex data types

Structured output generation is particularly useful for applications that need to extract specific information from LLM responses, such as sentiment analysis, entity extraction, data classification, and more.
