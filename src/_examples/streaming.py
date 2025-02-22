from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.tools.date_resolver import ResolveDateTool

#
# This is here 2025-02-21 to demonstrate a deficiency in Ollama/llama tool calling
# using the Stream option. We can't get chunk by chunk responses from the LLM
# when using tools. This limits our ability to explore streaming capabilities
# in the mojentic API, so I'm pausing this work for now until this is resolved.
# https://github.com/ollama/ollama/issues/7886
#


def main():
    ollama = OllamaGateway()
    date_tool = ResolveDateTool()
    
    stream = ollama.complete_stream(
        model="MFDoom/deepseek-r1-tool-calling:70b",
        messages=[
            LLMMessage(content="Tell me a story about a dragon. In your story, reference several dates relative to today, "
                              "like 'three days from now' or 'last week'.")
        ],
        tools=[date_tool],
        temperature=0.5,
        num_ctx=32768,
        num_predict=-1
    )
    
    for chunk in stream:
        print(chunk.content, end='', flush=True)

if __name__ == "__main__":
    main()