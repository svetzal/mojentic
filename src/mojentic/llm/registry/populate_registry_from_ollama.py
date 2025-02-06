import requests

from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.registry.llm_registry import LLMRegistry, LLMRegistryEntry, LLMCharacteristics


def query_ollama_server(url: str):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def register_llms_from_ollama(url: str, registry: LLMRegistry):
    tags_data = query_ollama_server(url)

    for model in tags_data['models']:
        # tm = {
        #     'details': {
        #         'families': ['qwen2'],
        #         'family': 'qwen2',
        #         'format': 'gguf',
        #         'parameter_size': '32.8B',
        #         'parent_model': '',
        #         'quantization_level': 'Q4_K_M'
        #     },
        #     'digest': '4bd6cbf2d094264457a17aab6bd6acd1ed7a72fb8f8be3cfb193f63c78dd56df',
        #     'model': 'qwen2.5-coder:32b',
        #     'modified_at': '2025-01-29T22:37:29.191797577-05:00',
        #     'name': 'qwen2.5-coder:32b',
        #     'size': 19851349856
        # }

        # Map parameter_size to one of the LLMSize values
        family = model['details']['family']
        characteristics = LLMCharacteristics(
            model=model['model'],
            quantization_level=model['details']['quantization_level'],
            parameter_size=(model['details']['parameter_size']),
            family=family,
            tools=family in ['qwen2', 'llama', 'mistral'] and "instruct" not in model['model'],
            structured_output="instruct" in model['model'],
            embeddings="mxbai" in model['model']
        )
        adapter = OllamaGateway()  # All models from ollama can be accessed via the OllamaGateway
        entry = LLMRegistryEntry(name=model['name'], characteristics=characteristics, adapter=adapter)
        registry.register(entry)


# Example usage
ollama_url = "http://localhost:11434/api/tags"
registry = LLMRegistry()
register_llms_from_ollama(ollama_url, registry)

# print(f"Tool using: {registry.find_first(tools=True, structured_output=True).name}")
print(f"Fastest model: {registry.find_fastest().name}")
print(f"Fastest model with tools: {registry.find_fastest(tools=True).name}")
print(f"Fastest model with structured output: {registry.find_fastest(structured_output=True).name}")
print(f"Smartest model: {registry.find_smartest().name}")
print(f"Smartest model with tools: {registry.find_smartest(tools=True).name}")
print(f"Smartest model with structured output: {registry.find_smartest(structured_output=True).name}")
