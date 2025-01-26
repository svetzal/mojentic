import os

from pydantic import BaseModel, Field

from mojentic.llm.gateways.openai import OpenAIGateway

api_key = os.getenv("OPENAI_API_KEY")
gateway = OpenAIGateway(api_key)


class Feeling(BaseModel):
    label: str = Field(..., description="The label describing the feeling.")


response = gateway.complete(
    model="gpt-4o-mini",
    messages=[{'role': 'user', 'content': "Hello, how are you?"}],
    response_model=Feeling,
    temperature=1.0,
    num_ctx=32768,
    num_predict=-1
)
print(response)
