import os

from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import MessageRole, LLMMessage
from mojentic.llm.tools.date_resolver import resolve_date_tool

api_key = os.getenv("OPENAI_API_KEY")
gateway = OpenAIGateway(api_key)

# llm = LLMBroker(model="llama3.3-70b-32k")
llm = LLMBroker(model="gpt-4o", adapter=gateway)


# result = llm.generate([{'role': 'user', 'content': "Hello, how are you?"}])
# print(result)
#
# class Sentiment(BaseModel):
#     label: str = Field(..., title="Description", description="label for the sentiment")
#
# result = llm.generate_object([{'role': 'user', 'content': "Hello, how are you?"}], object_model=Sentiment)
# print(result.label)

result = llm.generate(messages=[(LLMMessage(content='What is the date on Friday?'))],
                      tools=[resolve_date_tool])
print(result)
