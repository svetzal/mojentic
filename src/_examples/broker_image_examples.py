import os
from pathlib import Path

from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OpenAIGateway
from mojentic.llm.gateways.models import LLMMessage


def openai_llm(model="gpt-4o"):
    api_key = os.getenv("OPENAI_API_KEY")
    gateway = OpenAIGateway(api_key)
    llm = LLMBroker(model=model, gateway=gateway)
    return llm


def ollama_llm(model="llama3.3-70b-32k"):
    llm = LLMBroker(model=model)
    return llm


def check_image_analysis(llm, image_path: Path = None):
    if image_path is None:
        image_path = Path.cwd() / 'images' / 'flash_rom.jpg'
    result = llm.generate(messages=[
        (LLMMessage(content='What is in this image?',
                    image_paths=[str(image_path)]))
    ])
    print(result)


models = ["gpt-4o", "gpt-4.1", "o3", "gpt-4.5-preview", "o4-mini"]
images = [
    Path.cwd() / 'images' / 'flash_rom.jpg',
    Path.cwd() / 'images' / 'screen_cap.png',
    Path.cwd() / 'images' / 'xbox-one.jpg',
]

for image in images:
    for model in models:
        print(f"Checking {model} with {str(image)}")
        check_image_analysis(openai_llm(model=model), image)
