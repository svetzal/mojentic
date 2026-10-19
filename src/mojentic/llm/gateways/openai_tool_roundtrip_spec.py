"""
Parity-protective spec for tool round trips through the public broker and real SDK.

Uses the canonical get_weather fixtures shared across mojentic-py, mojentic-ts,
mojentic-ex, and mojentic-ru. The fixture JSON files in
fixtures/openai_tool_roundtrip/ must remain byte-identical across all four ports.

Verifies that:
- The first LLM call's tools list includes a function named get_weather
- The get_weather tool is invoked with location == "Paris"
- The second LLM call's messages contain the correct assistant tool_call message
  (arguments as a JSON object, not a string-that-parses-to-a-string) and a tool-role
  message with the correct tool_call_id and JSON content
- The final returned text matches the second fixture response
"""

import json
from pathlib import Path

import pytest

from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.llm_tool import LLMTool
from scripts.inprocess_http import InProcessTokenizer, scripted_http

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "openai_tool_roundtrip"


def _load_fixture(name: str) -> dict:
    with open(_FIXTURES_DIR / name) as f:
        return json.load(f)


class GetWeatherTool(LLMTool):
    """Real LLMTool that returns the canonical tool-result fixture."""

    def run(self, location: str) -> dict:
        self.locations.append(location)
        return _load_fixture("tool-result.json")

    def __init__(self) -> None:
        self.locations: list[str] = []

    @property
    def descriptor(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"],
                },
            },
        }


def _broker(provider: str = "openai", model: str = "gpt-4o") -> LLMBroker:
    from mojentic.llm.gateways.omlx import OMLXGateway

    gateway = (
        OpenAIGateway(api_key="test-key") if provider == "openai" else OMLXGateway()
    )
    return LLMBroker(tokenizer=InProcessTokenizer(), model=model, gateway=gateway)


def _stream_chunk(delta: dict, finish_reason: str | None = None) -> dict:
    return {
        "id": "chatcmpl-stream",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "gpt-4o",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def _reply(data: dict | list[dict]) -> tuple:
    if isinstance(data, list):
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in data)
        return (
            200,
            {"content-type": "text/event-stream"},
            (body + "data: [DONE]\n\n").encode(),
        )
    return 200, {"content-type": "application/json"}, json.dumps(data).encode()


def _streams(calls: list[dict]) -> list[list[dict]]:
    return [
        [
            _stream_chunk(
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "index": index,
                            "id": call["id"],
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": ""},
                        }
                        for index, call in enumerate(calls)
                    ],
                }
            ),
            _stream_chunk(
                {
                    "tool_calls": [
                        {
                            "index": index,
                            "function": {"arguments": call["function"]["arguments"]},
                        }
                        for index, call in enumerate(calls)
                    ]
                }
            ),
            _stream_chunk({}, "tool_calls"),
        ],
        [
            _stream_chunk({"role": "assistant", "content": "Sunny."}),
            _stream_chunk({}, "stop"),
        ],
    ]


def _assert_follow_up(body: dict, calls: list[dict], prompt: str) -> None:
    assert body["model"] == "gpt-4o"
    assert body["messages"] == [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": "", "tool_calls": calls},
        *[
            {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(_load_fixture("tool-result.json")),
            }
            for call in calls
        ],
    ]
    assert [json.loads(call["function"]["arguments"]) for call in calls] == [
        {"location": location} for location in ["Paris", "London"][: len(calls)]
    ]


@pytest.fixture
def tool() -> GetWeatherTool:
    return GetWeatherTool()


@pytest.fixture
def round_trip(tool):
    first = _load_fixture("response-1-tool-call.json")
    final = _load_fixture("response-2-final.json")
    prompt = "What's the weather in Paris?"
    with scripted_http([_reply(first), _reply(final)]) as (_, requests):
        result = _broker().generate(
            [LLMMessage(role=MessageRole.User, content=prompt)], tools=[tool]
        )
    bodies = [json.loads(body) for _, body, _ in requests]
    assert [path for path, _, _ in requests] == ["/v1/chat/completions"] * 2
    assert [headers["authorization"] for _, _, headers in requests] == [
        "Bearer test-key"
    ] * 2
    return bodies, result, first["choices"][0]["message"]["tool_calls"], prompt


class DescribeOpenAIToolCallingRoundTrip:
    def should_include_get_weather_in_first_request_tools(self, round_trip, tool):
        bodies, _, _, prompt = round_trip

        assert bodies[0]["model"] == "gpt-4o"
        assert bodies[0]["messages"] == [{"role": "user", "content": prompt}]
        assert bodies[0]["tools"] == [tool.descriptor]

    def should_invoke_get_weather_tool_with_paris(self, round_trip, tool):
        assert tool.locations == ["Paris"]

    def should_include_correct_assistant_tool_call_in_second_request(self, round_trip):
        bodies, _, calls, prompt = round_trip

        _assert_follow_up(bodies[1], calls, prompt)

    def should_include_correct_tool_role_message_in_second_request(self, round_trip):
        bodies, _, calls, prompt = round_trip

        _assert_follow_up(bodies[1], calls, prompt)

    def should_return_final_text_from_second_response(self, round_trip):
        assert round_trip[1] == "It's currently 22°C and sunny in Paris."


def should_preserve_json_argument_types_and_provider_metadata():
    fixture = _load_fixture("response-1-tool-call.json")
    arguments = {
        "count": 2,
        "enabled": True,
        "items": ["one"],
        "filter": {"kind": None},
    }
    fixture["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = (
        json.dumps(arguments)
    )
    fixture["usage"] = {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}
    with scripted_http([_reply(fixture)]) as (_, requests):
        response = _broker(model="configured-model").generate_response(
            [LLMMessage(role=MessageRole.User, content="hi")]
        )

    assert json.loads(requests[0][1])["messages"] == [{"role": "user", "content": "hi"}]
    assert json.loads(requests[0][1])["model"] == "configured-model"
    assert response.tool_calls[0].id == "call_fixture_get_weather"
    assert response.tool_calls[0].name == "get_weather"
    assert response.tool_calls[0].arguments == arguments
    assert type(response.tool_calls[0].arguments["count"]) is int
    assert type(response.tool_calls[0].arguments["enabled"]) is bool
    assert response.usage == {
        **fixture["usage"],
        "completion_tokens_details": None,
        "prompt_tokens_details": None,
    }
    assert response.model == fixture["model"]
    assert response.finish_reason == "tool_calls"


class DescribeOpenAIStreamingToolCallRoundTrip:
    def should_carry_streamed_tool_call_id_into_follow_up_request(self, tool):
        calls = _load_fixture("response-1-tool-call.json")["choices"][0]["message"][
            "tool_calls"
        ]
        calls[0]["id"] = "call_abc123"
        prompt = "What's the weather in Paris?"
        with scripted_http([_reply(chunks) for chunks in _streams(calls)]) as (
            _,
            requests,
        ):
            output = list(
                _broker().generate_stream(
                    [LLMMessage(role=MessageRole.User, content=prompt)], tools=[tool]
                )
            )

        assert "".join(output) == "Sunny."
        assert tool.locations == ["Paris"]
        assert [json.loads(body)["stream"] for _, body, _ in requests] == [True, True]
        _assert_follow_up(json.loads(requests[1][1]), calls, prompt)


@pytest.fixture(params=[False, True], ids=["ordinary", "streaming"])
def streaming(request):
    return request.param


@pytest.fixture(params=["openai", "omlx"])
def parallel_round_trip(request, streaming, tool):
    calls = [
        {
            "id": identifier,
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({"location": location}),
            },
        }
        for identifier, location in [("call_paris", "Paris"), ("call_london", "London")]
    ]
    first = _load_fixture("response-1-tool-call.json")
    first["choices"][0]["message"]["tool_calls"] = calls
    final = _load_fixture("response-2-final.json")
    replies = _streams(calls) if streaming else [first, final]
    prompt = "Compare Paris and London weather."
    messages = [LLMMessage(role=MessageRole.User, content=prompt)]
    with scripted_http([_reply(reply) for reply in replies]) as (_, requests):
        broker = _broker(request.param)
        output = (
            "".join(broker.generate_stream(messages, tools=[tool]))
            if streaming
            else broker.generate(messages, tools=[tool])
        )
    expected = {False: "It's currently 22°C and sunny in Paris.", True: "Sunny."}[
        streaming
    ]
    return requests, calls, messages, prompt, output, expected


def should_keep_both_parallel_tool_call_ids_in_the_broker_follow_up(
    parallel_round_trip, streaming, tool
):
    requests, calls, messages, prompt, output, expected = parallel_round_trip

    assert output == expected
    assert tool.locations == ["Paris", "London"]
    assert json.loads(requests[0][1])["tools"] == [tool.descriptor]
    _assert_follow_up(json.loads(requests[1][1]), calls, prompt)
    assert [call.id for call in messages[1].tool_calls] == ["call_paris", "call_london"]
