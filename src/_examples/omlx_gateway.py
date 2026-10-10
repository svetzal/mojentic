"""
Run one turn against a local oMLX server.

Reads OMLX_HOST (default http://localhost:8000) and OMLX_API_KEY (optional). Pass a model
id as the first argument, or the first model the server lists is used.

    uv run python src/_examples/omlx_gateway.py Qwen3.8-27B-MLX-8bit
"""

import sys

from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways import OMLXGateway
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.stream_events import StreamCompleted, StreamContent


def main():
    gateway = OMLXGateway()
    model = sys.argv[1] if len(sys.argv) > 1 else gateway.get_available_models()[0]
    messages = [
        LLMMessage(
            role=MessageRole.User, content="In one sentence, what is Apple Silicon?"
        )
    ]

    response = gateway.complete(
        model=model, messages=messages, config=CompletionConfig(max_tokens=2048)
    )
    print(f"Thinking: {response.thinking}")
    print(f"Answer ({response.finish_reason}): {response.content}")
    print(f"Usage: {response.usage}")

    print("\nStreaming the same turn:")
    for event in gateway.complete_stream_events(
        model=model, messages=messages, config=CompletionConfig(max_tokens=2048)
    ):
        if isinstance(event, StreamContent):
            print(event.text, end="", flush=True)
        elif isinstance(event, StreamCompleted):
            print(
                f"\nCompleted by {event.metadata.provider_model}: {event.metadata.usage}"
            )
        else:
            print(
                f"\nStream failed: {event.reason.value} {event.detail or ''} {event.metadata or ''}"
            )


if __name__ == "__main__":
    main()
