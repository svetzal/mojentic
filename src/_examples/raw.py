import os

from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

anthropic_args = {
    'model': "claude-3-5-haiku-20241022",
    'system': "You are a helpful assistant.",
    'messages': [
        {
            "role": "user",
            "content": "Say hello world",
        }
    ],
    'max_tokens': 2000,
}

response = client.messages.create(**anthropic_args)

print(response.content[0].text)