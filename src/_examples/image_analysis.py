import os
from pathlib import Path

from mojentic.llm.gateways import OllamaGateway, OpenAIGateway
from mojentic.llm.gateways.models import LLMMessage

llmg = OllamaGateway()

response = llmg.complete(
    model="gemma3:27b",
    messages=[
        LLMMessage(
            content="This is a Flash ROM chip on an adapter board. Extract the text on top of the chip.",
            image_paths=[
                str(Path.cwd() / "images" / "flash_rom.jpg")
            ]
        )
    ],
)

print(response)