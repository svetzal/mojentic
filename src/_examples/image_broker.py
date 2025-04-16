from pathlib import Path

from mojentic.llm import LLMBroker
from mojentic.llm.message_composers import MessagesBuilder, MessageBuilder

llm = LLMBroker(model="gemma3:27b")

message = MessageBuilder("What is in this image?") \
    .add_image(Path.cwd() / 'images' / 'xbox-one.jpg') \
    .build()

result = llm.generate(messages=[message])

print(result)
