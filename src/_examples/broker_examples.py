import os
from pathlib import Path

from pydantic import BaseModel, Field

from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool


def openai_llm(model="gpt-4o"):
    api_key = os.getenv("OPENAI_API_KEY")
    gateway = OpenAIGateway(api_key)
    llm = LLMBroker(model=model, gateway=gateway)
    return llm


def ollama_llm(model="llama3.3-70b-32k"):
    llm = LLMBroker(model=model)
    return llm


def check_simple_textgen(llm):
    result = llm.generate(messages=[(LLMMessage(content='Hello, how are you?'))])
    print(result)


def check_structured_output(llm):
    class Sentiment(BaseModel):
        label: str = Field(..., title="Description", description="label for the sentiment")

    result = llm.generate_object(messages=[LLMMessage(content="Hello, how are you?")], object_model=Sentiment)
    print(result.label)


def check_tool_use(llm):
    result = llm.generate(messages=[(LLMMessage(content='What is the date on Friday?'))],
                          tools=[ResolveDateTool()])
    print(result)

def check_image_analysis(llm):
    result = llm.generate(messages=[
        (LLMMessage(content='What is in this image?',
                    image_paths=[str(Path.cwd() / 'images' / 'flash_rom.jpg')]))
    ])
    print(result)

check_simple_textgen(openai_llm())
check_structured_output(openai_llm())
check_tool_use(openai_llm())
check_image_analysis(openai_llm())

check_simple_textgen(ollama_llm())
check_structured_output(ollama_llm())
check_tool_use(ollama_llm())
check_image_analysis(ollama_llm(model="gemma3:27b"))