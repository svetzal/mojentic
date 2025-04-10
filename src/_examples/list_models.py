import os

from mojentic.llm.gateways import OllamaGateway, OpenAIGateway
from mojentic.llm.gateways.anthropic import AnthropicGateway

ollama = OllamaGateway()
print("Ollama Models:")
for model in ollama.get_available_models():
    print(f"- {model}")

print()

openai = OpenAIGateway(os.environ["OPENAI_API_KEY"])
print("OpenAI Models:")
for model in openai.get_available_models():
    print(f"- {model}")

print()

anthropic = AnthropicGateway(os.environ["ANTHROPIC_API_KEY"])
print("Anthropic Models:")
for model in anthropic.get_available_models():
    print(f"- {model}")
