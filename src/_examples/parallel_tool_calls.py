"""
Parallel tool execution against the chat-completions broker.

The sync :class:`LLMBroker` defaults to :class:`SerialToolRunner` for
backward-compat. Opt into :class:`AsyncParallelToolRunner` to fan out
when a single assistant turn requests several tool calls.

Note: ``AsyncParallelToolRunner`` is async. With the sync broker it is
still useful — the broker drives a single ``asyncio.run`` per batch, so
the parallel speed-up still applies even from a sync call site. For
realtime / fully-async use cases, prefer the ``RealtimeVoiceBroker``
which is async end-to-end.
"""
from mojentic.llm.gateways.models import LLMGatewayResponse, LLMMessage, LLMToolCall
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.tools.runner import AsyncParallelToolRunner, ToolRunner


class _SlowAddTool(LLMTool):
    """Sleeps briefly so parallel dispatch is visible."""

    def run(self, a: str = "0", b: str = "0") -> dict:
        import time
        time.sleep(0.2)
        return {"sum": float(a) + float(b)}

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "slow_add",
                "description": "Adds two numbers slowly.",
                "parameters": {
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
            },
        }


class _DemoGateway:
    """
    Minimal in-memory gateway that pretends a model returned three
    tool_calls then a final text response. Lets the example run
    without an API key.
    """

    def __init__(self):
        self._returned_tools = False

    def complete(self, model, messages, tools=None, config=None, **_):
        if not self._returned_tools:
            self._returned_tools = True
            return LLMGatewayResponse(
                content="",
                object=None,
                tool_calls=[
                    LLMToolCall(
                        id=f"c{i}",
                        name="slow_add",
                        arguments={"a": str(i), "b": str(i + 1)},
                    )
                    for i in range(3)
                ],
            )
        return LLMGatewayResponse(content="Done.", object=None, tool_calls=[])

    def get_available_models(self):
        return ["demo"]

    def calculate_embeddings(self, text, model=None):
        return []


def _run_with(runner: ToolRunner) -> float:
    import time

    broker = LLMBroker("demo", gateway=_DemoGateway(), tool_runner=runner)
    start = time.time()
    broker.generate(
        [LLMMessage(content="Add some numbers in parallel.")],
        tools=[_SlowAddTool()],
    )
    return time.time() - start


def main() -> None:
    serial = _run_with(__import__("mojentic.llm.tools.runner", fromlist=["SerialToolRunner"]).SerialToolRunner())
    parallel = _run_with(AsyncParallelToolRunner(max_concurrency=4))
    print(f"Serial   : {serial * 1000:.0f}ms (3 tools × ~200ms each)")
    print(f"Parallel : {parallel * 1000:.0f}ms (3 tools fanned out)")


if __name__ == "__main__":
    main()
