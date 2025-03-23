import os

from mojentic.llm.gateways import OllamaGateway, OpenAIGateway

ollama = OllamaGateway()
print(len(ollama.calculate_embeddings("Hello, world!")))

openai = OpenAIGateway(os.environ["OPENAI_API_KEY"])
print(len(openai.calculate_embeddings("Hello, world!")))