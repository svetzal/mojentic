from pydantic import BaseModel, Field

from mojentic.llm.gateways.ollama import OllamaGateway

gateway = OllamaGateway()

class Feeling(BaseModel):
    label: str = Field(..., description="The label describing the feeling.")

response = gateway.complete(
    model="llama3.2:1b",
    messages=[{'role': 'user', 'content': "Hello, how are you?"}],
    response_model=Feeling,
    temperature=1.0,
    num_ctx=32768,
    num_predict=-1
)
print(response)
