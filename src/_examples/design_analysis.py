from pathlib import Path

from mojentic.llm.gateways import OllamaGateway
from mojentic.llm.gateways.models import LLMMessage

llmg = OllamaGateway()


def complete(prompt: str):
    response = llmg.complete(
        model="gemma3:27b",
        messages=[
            LLMMessage(
                content=prompt.strip(),
                image_paths=[
                    str(Path.cwd() / "images" / "screen_cap.png")
                ]
            )
        ],
    )
    return response.content


# It's quite good at extracting text from images
result = complete("Extract the text from the attached image in markdown format.")
print(result)

# It's not bad at extracting and structuring the text it finds in images
result = complete("""
Extract the title and text boxes from the attached image in the form of a JSON object.
Use descriptive key names like `title` or `bullet` or `footer`. In the values, use html
but don't attempt to convert all of the visual formatting, just simple formatting like
paragraphs, bold, or italic.
""")
print(result)

# Gemma3 is not very good at determining hex colours :)
result = complete("""
Extract the colours from the attached image in the form of a JSON object, where the key
is the description of how the colour is used, and the value is the colour in hex format.
""")
print(result)
