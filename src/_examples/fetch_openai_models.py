"""
Script to fetch current OpenAI models and update the registry with up-to-date model lists.
"""

import os
from mojentic.llm.gateways.openai import OpenAIGateway

def fetch_current_openai_models():
    """Fetch the current list of OpenAI models."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        return None

    try:
        gateway = OpenAIGateway(api_key)
        models = gateway.get_available_models()
        return models
    except Exception as e:
        print(f"ERROR: Failed to fetch models from OpenAI API: {e}")
        return None

def categorize_models(models):
    """Categorize models by type based on naming patterns."""
    reasoning_models = []
    chat_models = []
    embedding_models = []
    other_models = []

    for model in models:
        model_lower = model.lower()

        # Reasoning models: o1, o3, o4, and gpt-5 series
        if (any(pattern in model_lower for pattern in ['o1-', 'o3-', 'o4-', 'gpt-5']) or
            model_lower in ['o1', 'o3', 'o4', 'gpt-5']):
            reasoning_models.append(model)
        elif 'embedding' in model_lower:
            embedding_models.append(model)
        elif any(pattern in model_lower for pattern in ['gpt-4', 'gpt-3.5']):
            chat_models.append(model)
        else:
            other_models.append(model)

    return {
        'reasoning': sorted(reasoning_models),
        'chat': sorted(chat_models),
        'embedding': sorted(embedding_models),
        'other': sorted(other_models)
    }

def print_model_lists(categorized_models):
    """Print the categorized models in a format ready for the registry."""
    print("=== Current OpenAI Models ===\n")

    print("# Reasoning Models (o1, o3, o4, gpt-5 series)")
    print("reasoning_models = [")
    for model in categorized_models['reasoning']:
        print(f'    "{model}",')
    print("]\n")

    print("# Chat Models (GPT-4 and GPT-4.1 series)")
    print("gpt4_and_newer_models = [")
    gpt4_and_newer = [m for m in categorized_models['chat'] if 'gpt-4' in m.lower()]
    for model in gpt4_and_newer:
        print(f'    "{model}",')
    print("]\n")

    print("# Chat Models (GPT-3.5 series)")
    print("gpt35_models = [")
    gpt35 = [m for m in categorized_models['chat'] if 'gpt-3.5' in m.lower()]
    for model in gpt35:
        print(f'    "{model}",')
    print("]\n")

    print("# Embedding Models")
    print("embedding_models = [")
    for model in categorized_models['embedding']:
        print(f'    "{model}",')
    print("]\n")

    print("# Other Models (for reference)")
    print("# other_models = [")
    for model in categorized_models['other']:
        print(f'#     "{model}",')
    print("# ]\n")

if __name__ == "__main__":
    print("Fetching current OpenAI models...")
    models = fetch_current_openai_models()

    if models:
        print(f"Found {len(models)} models\n")
        categorized = categorize_models(models)
        print_model_lists(categorized)

        print("\n=== Summary ===")
        print(f"Reasoning models: {len(categorized['reasoning'])}")
        print(f"Chat models: {len(categorized['chat'])}")
        print(f"Embedding models: {len(categorized['embedding'])}")
        print(f"Other models: {len(categorized['other'])}")

        print("\nCopy the model lists above and update the _initialize_default_models() method in openai_model_registry.py")
    else:
        print("Failed to fetch models. Please check your API key and try again.")