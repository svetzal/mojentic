import os

from mojentic.llm.gateways import OllamaGateway, OpenAIGateway

ollama = OllamaGateway()
print("Ollama Models:")
for model in ollama.get_available_models():
    print(f"- {model}")

print()

openai = OpenAIGateway(os.environ["OPENAI_API_KEY"])
print("OpenAI Models:")
for model in openai.get_available_models():
    print(f"- {model}")