import os
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.gateways.models import LLMMessage, MessageRole

def check_model_characterization():
    """
    Test the model characterization functionality with different OpenAI models.
    This demonstrates how the gateway adapts parameters based on model type.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY environment variable not set. Skipping actual API calls.")
        return

    gateway = OpenAIGateway(api_key)

    # Test messages for chat models
    chat_messages = [
        LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
        LLMMessage(role=MessageRole.User, content="What is 2 + 2? Give a brief answer.")
    ]

    # Test messages for reasoning models (no system message supported)
    reasoning_messages = [
        LLMMessage(role=MessageRole.User, content="What is 2 + 2? Give a brief answer.")
    ]

    # Test with different model types
    test_models = [
        ("gpt-4o", "chat model"),
        ("gpt-4o-mini", "chat model"),
        ("o1-mini", "reasoning model"),
        ("o1-preview", "reasoning model")
    ]

    print("Testing model characterization and parameter adaptation:")
    print("=" * 60)

    for model, model_type in test_models:
        print(f"\nTesting {model} ({model_type}):")

        # Test model classification
        is_reasoning = gateway._is_reasoning_model(model)
        print(f"  Classified as reasoning model: {is_reasoning}")

        # Use appropriate messages based on model type
        messages = reasoning_messages if gateway._is_reasoning_model(model) else chat_messages

        # Test parameter adaptation
        original_args = {
            'model': model,
            'messages': messages,
            'max_tokens': 100
        }

        adapted_args = gateway._adapt_parameters_for_model(model, original_args)

        if 'max_tokens' in adapted_args:
            print(f"  Using parameter: max_tokens = {adapted_args['max_tokens']}")
        elif 'max_completion_tokens' in adapted_args:
            print(f"  Using parameter: max_completion_tokens = {adapted_args['max_completion_tokens']}")

        try:
            response = gateway.complete(**adapted_args)
            print(f"  Response: {response.content[:50]}...")
        except Exception as e:
            print(f"  Error: {str(e)}")

    print("\n" + "=" * 60)
    print("Model characterization test completed!")

if __name__ == "__main__":
    check_model_characterization()
