from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.tools.date_resolver import ResolveDateTool


def main():
    """
    Demonstrates streaming text generation with tool calling support.

    This example shows how generate_stream() handles tool calls seamlessly:
    1. Streams content as it arrives
    2. Detects tool calls in the stream
    3. Executes tools
    4. Recursively streams the LLM's response after tool execution
    """
    gateway = OllamaGateway()
    # gateway = OpenAIGateway(api_key=os.getenv("OPENAI_API_KEY"))
    broker = LLMBroker(
        model="qwen3:32b",
        # model="gpt-5",
        gateway=gateway
    )

    date_tool = ResolveDateTool()

    print("Streaming response with tool calling enabled...\n")

    stream = broker.generate_stream(
        messages=[
            LLMMessage(
                content=(
                    "Tell me a short story about a dragon. "
                    "In your story, reference several dates relative to today, "
                    "like 'three days from now' or 'last week'."
                )
            )
        ],
        tools=[date_tool],
        temperature=0.7,
        num_ctx=32768,
        num_predict=-1
    )
    for chunk in stream:
        print(chunk, end='', flush=True)

    print("\n\nDone!")


if __name__ == "__main__":
    main()
