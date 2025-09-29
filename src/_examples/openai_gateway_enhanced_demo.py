"""
Demonstration of the enhanced OpenAI gateway with model registry system.

This script shows how the new infrastructure automatically handles parameter adaptation
for reasoning models vs chat models, provides detailed logging, and offers better
error handling.
"""

import os
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.gateways.openai_model_registry import get_model_registry
from mojentic.llm.gateways.models import LLMMessage, MessageRole

def demonstrate_model_registry():
    """Demonstrate the model registry capabilities."""
    print("=== Model Registry Demonstration ===")

    registry = get_model_registry()

    print("\n1. Registry contains default models:")
    registered_models = registry.get_registered_models()
    reasoning_models = [m for m in registered_models if registry.is_reasoning_model(m)]
    chat_models = [m for m in registered_models if not registry.is_reasoning_model(m) and not m.startswith('text-')]

    print(f"   Reasoning models: {reasoning_models[:3]}...")  # Show first 3
    print(f"   Chat models: {chat_models[:3]}...")  # Show first 3

    print("\n2. Model capability detection:")
    for model in ["o1-mini", "gpt-4o"]:
        capabilities = registry.get_model_capabilities(model)
        token_param = capabilities.get_token_limit_param()
        print(f"   {model}: type={capabilities.model_type.value}, token_param={token_param}")

    # Handle unknown model separately to show the warning works
    print("\n3. Unknown model handling:")
    print("   unknown-future-model: (will default to chat model with warning)")
    capabilities = registry.get_model_capabilities("unknown-future-model")
    token_param = capabilities.get_token_limit_param()
    print(f"   → Defaulted to: type={capabilities.model_type.value}, token_param={token_param}")

def demonstrate_parameter_adaptation():
    """Demonstrate parameter adaptation for different model types."""
    print("\n=== Parameter Adaptation Demonstration ===")

    # This would normally require an API key, but we're just showing the adaptation logic
    gateway = OpenAIGateway("fake-key-for-demo")

    print("\n1. Reasoning model parameter adaptation (o1-mini):")
    original_args = {
        'model': 'o1-mini',
        'messages': [LLMMessage(role=MessageRole.User, content="Hello")],
        'max_tokens': 1000,
        'tools': []  # Tools will be removed for reasoning models
    }

    adapted_args = gateway._adapt_parameters_for_model('o1-mini', original_args)
    print(f"   Original: max_tokens={original_args.get('max_tokens')}, has_tools={'tools' in original_args}")
    print(f"   Adapted: max_completion_tokens={adapted_args.get('max_completion_tokens')}, has_tools={'tools' in adapted_args}")

    print("\n2. Chat model parameter adaptation (gpt-4o):")
    original_args = {
        'model': 'gpt-4o',
        'messages': [LLMMessage(role=MessageRole.User, content="Hello")],
        'max_tokens': 1000,
        'tools': []
    }

    adapted_args = gateway._adapt_parameters_for_model('gpt-4o', original_args)
    print(f"   Original: max_tokens={original_args.get('max_tokens')}, has_tools={'tools' in original_args}")
    print(f"   Adapted: max_tokens={adapted_args.get('max_tokens')}, has_tools={'tools' in adapted_args}")

def demonstrate_model_validation():
    """Demonstrate model parameter validation."""
    print("\n=== Model Validation Demonstration ===")

    gateway = OpenAIGateway("fake-key-for-demo")

    print("\n1. Validating parameters for reasoning model:")
    args = {
        'model': 'o1-mini',
        'messages': [LLMMessage(role=MessageRole.User, content="Hello")],
        'max_tokens': 50000,  # High token count - will show warning
        'tools': []  # Tools for reasoning model - will show warning
    }

    try:
        gateway._validate_model_parameters('o1-mini', args)
        print("   Validation completed (check logs above for warnings)")
    except Exception as e:
        print(f"   Validation error: {e}")

def demonstrate_registry_extensibility():
    """Demonstrate how to extend the registry with new models."""
    print("\n=== Registry Extensibility Demonstration ===")

    registry = get_model_registry()

    print("\n1. Adding a new model to the registry:")
    from mojentic.llm.gateways.openai_model_registry import ModelCapabilities, ModelType

    new_capabilities = ModelCapabilities(
        model_type=ModelType.REASONING,
        supports_tools=True,  # Hypothetical future reasoning model with tools
        supports_streaming=True,
        max_output_tokens=100000
    )

    registry.register_model("o5-preview", new_capabilities)
    print(f"   Registered o5-preview as reasoning model")

    # Test the new model
    capabilities = registry.get_model_capabilities("o5-preview")
    print(f"   o5-preview: type={capabilities.model_type.value}, supports_tools={capabilities.supports_tools}")

    print("\n2. Adding a new pattern for model detection:")
    registry.register_pattern("claude", ModelType.CHAT)
    print("   Registered 'claude' pattern for chat models")

    # Test pattern matching
    capabilities = registry.get_model_capabilities("claude-3-opus")
    print(f"   claude-3-opus (inferred): type={capabilities.model_type.value}")

if __name__ == "__main__":
    print("OpenAI Gateway Enhanced Infrastructure Demo")
    print("=" * 50)

    demonstrate_model_registry()
    demonstrate_parameter_adaptation()
    demonstrate_model_validation()
    demonstrate_registry_extensibility()

    print("\n" + "=" * 50)
    print("Demo completed!")
    print("\nKey Benefits of the New Infrastructure:")
    print("✓ Registry-based model management (easy to extend)")
    print("✓ Automatic parameter adaptation (max_tokens ↔ max_completion_tokens)")
    print("✓ Enhanced logging for debugging")
    print("✓ Parameter validation with helpful warnings")
    print("✓ Pattern matching for unknown models")
    print("✓ Comprehensive test coverage")