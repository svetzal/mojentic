import json
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel
from structlog.testing import capture_logs

from mojentic.llm.completion_config import CompletionConfig, ResponseFormat
from mojentic.llm.gateways import OMLXGateway
from mojentic.llm.gateways.models import LLMMessage, LLMToolCall, MessageRole
from mojentic.llm.gateways.ollama import StreamingResponse
from mojentic.llm.gateways.omlx import OMLXTransport
from mojentic.llm.gateways.omlx_protocol import OMLXSettings
from mojentic.llm.gateways.stream_events import (
    CompletionMetadata,
    StreamCompleted,
    StreamContent,
    StreamError,
    StreamErrorReason,
)
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.tracer import TracerSystem

FIXTURES = Path(__file__).parent / "fixtures" / "omlx"
MODEL = "Qwen3.8-27B-MLX-8bit"
KEEPALIVE = (
    'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":0,"model":"keepalive",'
    '"choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}'
)


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text())


def fixture_lines(name):
    return (FIXTURES / name).read_text().splitlines()


def ok(payload, headers=None):
    return httpx.Response(200, json=payload, headers=headers)


def status_error(status, payload):
    request = httpx.Request("POST", "http://localhost:8000/v1/anything")
    return httpx.HTTPStatusError(
        "oMLX error",
        request=request,
        response=httpx.Response(status, json=payload, request=request),
    )


def generator(items):
    yield from items


def tracked(lines, closed):
    try:
        yield from lines
    finally:
        closed.append(True)


class Person(BaseModel):
    name: str
    age: int


class ResolveDate(LLMTool):
    def run(self, relative):
        return "2026-09-29"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "resolve_date",
                "description": "Resolve a relative date",
                "parameters": {
                    "type": "object",
                    "properties": {"relative": {"type": "string"}},
                },
            },
        }


@pytest.fixture
def transport(mocker):
    return mocker.Mock(spec=OMLXTransport)


@pytest.fixture
def gateway(transport):
    return OMLXGateway(transport=transport)


@pytest.fixture
def messages():
    return [LLMMessage(role=MessageRole.User, content="Reply with exactly: hello")]


class DescribeOMLXGateway:
    class DescribeConfiguration:
        @pytest.fixture(autouse=True)
        def clean_environment(self, monkeypatch):
            for name in ["OMLX_HOST", "OMLX_API_KEY", "OMLX_TIMEOUT"]:
                monkeypatch.delenv(name, raising=False)

        def should_default_to_localhost_with_no_key(self, transport):
            gateway = OMLXGateway(transport=transport)

            assert gateway.settings == OMLXSettings(
                base_url="http://localhost:8000/v1", headers={}, timeout=600.0
            )

        def should_read_the_environment(self, transport, monkeypatch):
            monkeypatch.setenv("OMLX_HOST", "http://studio.local:8000")
            monkeypatch.setenv("OMLX_API_KEY", "env-key")
            monkeypatch.setenv("OMLX_TIMEOUT", "30000")

            gateway = OMLXGateway(transport=transport)

            assert gateway.settings == OMLXSettings(
                base_url="http://studio.local:8000/v1",
                headers={"Authorization": "Bearer env-key"},
                timeout=30.0,
            )

        def should_prefer_explicit_values_over_the_environment(
            self, transport, monkeypatch
        ):
            monkeypatch.setenv("OMLX_HOST", "http://studio.local:8000")
            monkeypatch.setenv("OMLX_API_KEY", "env-key")
            monkeypatch.setenv("OMLX_TIMEOUT", "30000")

            gateway = OMLXGateway(
                host="http://explicit:9000",
                api_key="explicit-key",
                timeout=5.0,
                transport=transport,
            )

            assert gateway.settings == OMLXSettings(
                base_url="http://explicit:9000/v1",
                headers={"Authorization": "Bearer explicit-key"},
                timeout=5.0,
            )

        def should_build_a_transport_over_the_resolved_settings(self):
            gateway = OMLXGateway(host="http://explicit:9000", api_key="k")

            assert isinstance(gateway.transport, OMLXTransport)

    class DescribeComplete:
        def should_post_the_chat_body_to_chat_completions(
            self, gateway, transport, messages
        ):
            transport.post.return_value = ok(load_fixture("chat_thinking.json"))

            gateway.complete(
                model=MODEL,
                messages=messages,
                config=CompletionConfig(reasoning_effort="high"),
            )

            path, body = transport.post.call_args.args
            assert (
                path,
                body["model"],
                body["reasoning_effort"],
                "stream" in body,
            ) == ("/chat/completions", MODEL, "high", False)

        def should_build_the_config_from_keyword_arguments_when_none_is_given(
            self, gateway, transport, messages
        ):
            transport.post.return_value = ok(load_fixture("chat_thinking.json"))

            gateway.complete(
                model=MODEL, messages=messages, temperature=0.3, max_tokens=99
            )

            body = transport.post.call_args.args[1]
            assert (body["temperature"], body["max_tokens"]) == (0.3, 99)

        def should_map_reasoning_content_to_thinking(
            self, gateway, transport, messages
        ):
            transport.post.return_value = ok(load_fixture("chat_thinking.json"))

            response = gateway.complete(
                model=MODEL, messages=messages, config=CompletionConfig()
            )

            assert (
                response.content,
                response.thinking.startswith("We need to reply exactly"),
            ) == ("hello", True)

        def should_leave_thinking_empty_when_thinking_is_disabled(
            self, gateway, transport, messages
        ):
            transport.post.return_value = ok(
                load_fixture("chat_thinking_disabled.json")
            )

            response = gateway.complete(
                model=MODEL, messages=messages, config=CompletionConfig()
            )

            assert response.thinking is None

        def should_report_length_with_content_unchanged(
            self, gateway, transport, messages
        ):
            transport.post.return_value = ok(load_fixture("chat_length.json"))

            response = gateway.complete(
                model=MODEL, messages=messages, config=CompletionConfig(max_tokens=5)
            )

            assert (response.finish_reason, response.content, response.thinking) == (
                "length",
                "We need to respond to",
                None,
            )

        def should_parse_a_tool_call(self, gateway, transport, messages):
            transport.post.return_value = ok(load_fixture("chat_tool_call.json"))

            response = gateway.complete(
                model=MODEL,
                messages=messages,
                tools=[ResolveDate()],
                config=CompletionConfig(),
            )

            assert response.tool_calls == [
                LLMToolCall(
                    id="call_bd4d55c2",
                    name="resolve_date",
                    arguments={"relative": "today"},
                )
            ]

        def should_propagate_a_provider_error_with_its_status_and_body(
            self, gateway, transport, messages
        ):
            transport.post.side_effect = status_error(
                404, load_fixture("error_model_not_found.json")
            )

            with pytest.raises(httpx.HTTPStatusError) as raised:
                gateway.complete(
                    model="nope", messages=messages, config=CompletionConfig()
                )

            assert (
                raised.value.response.status_code,
                raised.value.response.json(),
            ) == (404, load_fixture("error_model_not_found.json"))

    class DescribeToolRoundTrip:
        def should_send_the_tool_result_back_and_return_the_final_answer(
            self, gateway, transport, messages
        ):
            transport.post.side_effect = [
                ok(load_fixture("chat_tool_call.json")),
                ok(load_fixture("chat_after_tool_result.json")),
            ]
            broker = LLMBroker(model=MODEL, gateway=gateway)

            answer = broker.generate(messages, tools=[ResolveDate()])

            second_body = transport.post.call_args_list[1].args[1]
            assert (answer, second_body["messages"][-1]) == (
                "Today's date is **September 29, 2026** (2026-09-29).",
                {
                    "role": "tool",
                    "content": '"2026-09-29"',
                    "tool_call_id": "call_bd4d55c2",
                },
            )

    class DescribeStructuredOutput:
        def should_request_the_object_schema_and_validate_the_content(
            self, gateway, transport, messages
        ):
            transport.post.return_value = ok(load_fixture("chat_json_schema.json"))

            response = gateway.complete(
                model=MODEL,
                messages=messages,
                object_model=Person,
                config=CompletionConfig(),
            )

            body = transport.post.call_args.args[1]
            assert (body["response_format"], response.object) == (
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "response",
                        "schema": Person.model_json_schema(),
                    },
                },
                Person(name="Ada", age=36),
            )

        @pytest.mark.parametrize(
            "fixture", ["chat_thinking.json", "chat_tool_call.json"]
        )
        def should_leave_the_object_empty_when_the_content_does_not_validate(
            self, gateway, transport, messages, fixture
        ):
            transport.post.return_value = ok(load_fixture(fixture))

            response = gateway.complete(
                model=MODEL,
                messages=messages,
                object_model=Person,
                config=CompletionConfig(),
            )

            assert response.object is None

        def should_record_and_log_a_warning_header_on_a_structured_request(
            self, gateway, transport, messages
        ):
            transport.post.return_value = ok(
                load_fixture("chat_json_schema.json"),
                headers={"Warning": '299 - "json_schema not enforced"'},
            )

            with capture_logs() as logs:
                response = gateway.complete(
                    model=MODEL,
                    messages=messages,
                    object_model=Person,
                    config=CompletionConfig(),
                )

            assert (
                response.metadata,
                [log["log_level"] for log in logs if "response_format_warning" in log],
            ) == (
                {"response_format_warning": '299 - "json_schema not enforced"'},
                ["warning"],
            )

        def should_join_several_warning_headers(self, gateway, transport, messages):
            transport.post.return_value = ok(
                load_fixture("chat_json_schema.json"),
                headers=[("Warning", "first"), ("Warning", "second")],
            )

            response = gateway.complete(
                model=MODEL,
                messages=messages,
                object_model=Person,
                config=CompletionConfig(),
            )

            assert response.metadata == {"response_format_warning": "first, second"}

        def should_record_a_warning_for_a_configured_json_format(
            self, gateway, transport, messages
        ):
            transport.post.return_value = ok(
                load_fixture("chat_json_schema.json"), headers={"Warning": "degraded"}
            )
            config = CompletionConfig(
                response_format=ResponseFormat(type="json_object")
            )

            response = gateway.complete(model=MODEL, messages=messages, config=config)

            assert response.metadata == {"response_format_warning": "degraded"}

        @pytest.mark.parametrize("response_format", [None, ResponseFormat(type="text")])
        def should_ignore_a_warning_header_without_a_structured_request(
            self, gateway, transport, messages, response_format
        ):
            transport.post.return_value = ok(
                load_fixture("chat_thinking.json"), headers={"Warning": "unrelated"}
            )

            response = gateway.complete(
                model=MODEL,
                messages=messages,
                config=CompletionConfig(response_format=response_format),
            )

            assert response.metadata == {}

    class DescribeCompleteStream:
        def should_stream_without_usage_options(self, gateway, transport, messages):
            transport.stream_lines.return_value = generator(
                fixture_lines("stream_thinking.sse")
            )

            list(
                gateway.complete_stream(
                    model=MODEL,
                    messages=messages,
                    tools=[ResolveDate()],
                    config=CompletionConfig(),
                )
            )

            path, body = transport.stream_lines.call_args.args
            assert (
                path,
                body["stream"],
                "stream_options" in body,
                len(body["tools"]),
            ) == ("/chat/completions", True, False, 1)

        def should_yield_the_content_then_one_complete_tool_call_from_the_fixture(
            self, gateway, transport, messages
        ):
            transport.stream_lines.return_value = generator(
                fixture_lines("stream_tool_call.sse")
            )

            chunks = list(
                gateway.complete_stream(
                    model=MODEL,
                    messages=messages,
                    tools=[ResolveDate()],
                    config=CompletionConfig(),
                )
            )

            assert [chunk for chunk in chunks if not chunk.thinking] == [
                StreamingResponse(content="\n\n"),
                StreamingResponse(
                    tool_calls=[
                        LLMToolCall(
                            id="call_659d0e77",
                            name="resolve_date",
                            arguments={"relative": "today"},
                        )
                    ]
                ),
            ]

        def should_yield_thinking_chunks(self, gateway, transport, messages):
            transport.stream_lines.return_value = generator(
                fixture_lines("stream_thinking.sse")
            )

            chunks = list(
                gateway.complete_stream(
                    model=MODEL, messages=messages, config=CompletionConfig()
                )
            )

            assert (
                [c.content for c in chunks if c.content],
                len([c for c in chunks if c.thinking]),
            ) == (["\n\nhello"], 10)

        def should_drop_keepalive_frames(self, gateway, transport, messages):
            transport.stream_lines.return_value = generator([KEEPALIVE, "data: [DONE]"])

            chunks = list(
                gateway.complete_stream(
                    model=MODEL, messages=messages, config=CompletionConfig()
                )
            )

            assert chunks == []

        def should_refuse_structured_output(self, gateway, transport, messages):
            with pytest.raises(NotImplementedError):
                list(
                    gateway.complete_stream(
                        model=MODEL,
                        messages=messages,
                        object_model=Person,
                        config=CompletionConfig(),
                    )
                )

    class DescribeCompleteStreamEvents:
        def should_send_one_streaming_request_with_usage_and_no_tools(
            self, gateway, transport, messages
        ):
            transport.stream_lines.return_value = generator([])
            config = CompletionConfig(
                response_format=ResponseFormat(type="json_object")
            )

            list(
                gateway.complete_stream_events(
                    model=MODEL, messages=messages, config=config
                )
            )

            path, body = transport.stream_lines.call_args.args
            assert (
                transport.stream_lines.call_count,
                path,
                body["stream"],
                body["stream_options"],
                body["response_format"],
                "tools" in body,
            ) == (
                1,
                "/chat/completions",
                True,
                {"include_usage": True},
                {"type": "json_object"},
                False,
            )

        def should_complete_the_thinking_fixture_with_content_only(
            self, gateway, transport, messages
        ):
            transport.stream_lines.return_value = generator(
                fixture_lines("stream_thinking.sse")
            )

            events = list(
                gateway.complete_stream_events(
                    model=MODEL, messages=messages, config=CompletionConfig()
                )
            )

            assert events == [
                StreamContent(text="\n\nhello"),
                StreamCompleted(
                    metadata=CompletionMetadata(
                        finish_reason="stop",
                        provider_model=MODEL,
                        usage=load_stream_usage("stream_thinking.sse"),
                    )
                ),
            ]

        def should_report_the_length_fixture_as_an_incomplete_completion(
            self, gateway, transport, messages
        ):
            transport.stream_lines.return_value = generator(
                fixture_lines("stream_length.sse")
            )

            events = list(
                gateway.complete_stream_events(
                    model=MODEL, messages=messages, config=CompletionConfig()
                )
            )

            assert events == [
                StreamError(
                    reason=StreamErrorReason.INCOMPLETE_COMPLETION,
                    metadata=CompletionMetadata(
                        finish_reason="length",
                        provider_model=MODEL,
                        usage=load_stream_usage("stream_length.sse"),
                    ),
                )
            ]

        def should_report_the_tool_call_fixture_as_unexpected_tool_calls(
            self, gateway, transport, messages
        ):
            transport.stream_lines.return_value = generator(
                fixture_lines("stream_tool_call.sse")
            )

            events = list(
                gateway.complete_stream_events(
                    model=MODEL, messages=messages, config=CompletionConfig()
                )
            )

            assert events == [
                StreamContent(text="\n\n"),
                StreamError(reason=StreamErrorReason.UNEXPECTED_TOOL_CALLS),
            ]

        def should_end_a_keepalive_only_stream_as_incomplete_with_no_provider_model(
            self, gateway, transport, messages
        ):
            transport.stream_lines.return_value = generator([KEEPALIVE, ""])

            events = list(
                gateway.complete_stream_events(
                    model=MODEL, messages=messages, config=CompletionConfig()
                )
            )

            assert events == [
                StreamError(reason=StreamErrorReason.INCOMPLETE_STREAM, metadata=None)
            ]

        def should_report_an_error_status_as_a_provider_error(
            self, gateway, transport, messages
        ):
            def failing(path, body):
                raise status_error(404, load_fixture("error_model_not_found.json"))
                yield

            transport.stream_lines.side_effect = failing

            events = list(
                gateway.complete_stream_events(
                    model="nope", messages=messages, config=CompletionConfig()
                )
            )

            assert events == [
                StreamError(
                    reason=StreamErrorReason.PROVIDER_ERROR,
                    detail={
                        "status_code": 404,
                        "error": load_fixture("error_model_not_found.json")["error"],
                    },
                )
            ]

        def should_report_a_connection_failure_as_request_failed(
            self, gateway, transport, messages
        ):
            def failing(path, body):
                yield KEEPALIVE
                raise httpx.ReadError("connection reset")

            transport.stream_lines.side_effect = failing

            events = list(
                gateway.complete_stream_events(
                    model=MODEL, messages=messages, config=CompletionConfig()
                )
            )

            assert events == [
                StreamError(
                    reason=StreamErrorReason.REQUEST_FAILED, detail="connection reset"
                )
            ]

        def should_close_the_request_when_the_consumer_stops_early(
            self, gateway, transport, messages
        ):
            closed = []
            transport.stream_lines.return_value = tracked(
                iter(fixture_lines("stream_thinking.sse")), closed
            )
            events = gateway.complete_stream_events(
                model=MODEL, messages=messages, config=CompletionConfig()
            )
            next(events)

            events.close()

            assert closed == [True]

        def should_trace_the_real_provider_model_through_the_broker(
            self, gateway, transport, messages
        ):
            from mojentic.tracer.tracer_events import LLMResponseTracerEvent

            transport.stream_lines.return_value = generator(
                fixture_lines("stream_thinking.sse")
            )
            tracer = TracerSystem()
            broker = LLMBroker(model=MODEL, gateway=gateway, tracer=tracer)

            list(broker.generate_stream_events(messages))

            response = tracer.get_events(event_type=LLMResponseTracerEvent)[0]
            assert (response.content, response.provider_model, response.usage) == (
                "\n\nhello",
                MODEL,
                load_stream_usage("stream_thinking.sse"),
            )

    class DescribeModels:
        def should_list_model_ids_sorted(self, gateway, transport):
            transport.get.return_value = ok(
                {"object": "list", "data": [{"id": "b"}, {"id": "a"}]}
            )

            models = gateway.get_available_models()

            assert (transport.get.call_args.args, models) == (("/models",), ["a", "b"])

        def should_list_the_fixture_model(self, gateway, transport):
            transport.get.return_value = ok(load_fixture("models.json"))

            assert gateway.get_available_models() == [MODEL]

        @pytest.mark.parametrize("operation", ["load_model", "unload_model"])
        @pytest.mark.parametrize("model", ["", " ", "\t\n"])
        def should_reject_blank_model_ids_without_a_request(
            self, gateway, transport, operation, model
        ):
            with pytest.raises(ValueError):
                getattr(gateway, operation)(model)

            assert transport.method_calls == []

        def should_load_a_model_and_return_nothing(self, gateway, transport):
            transport.post.return_value = ok(load_fixture("model_load.json"))

            result = gateway.load_model(MODEL)

            assert (transport.post.call_args.args, result) == (
                (f"/models/{MODEL}/load",),
                None,
            )

        def should_unload_a_model_and_return_nothing(self, gateway, transport):
            transport.post.return_value = ok(load_fixture("model_unload.json"))

            result = gateway.unload_model(MODEL)

            assert (transport.post.call_args.args, result) == (
                (f"/models/{MODEL}/unload",),
                None,
            )

        def should_percent_encode_the_model_id_as_one_path_segment(
            self, gateway, transport
        ):
            transport.post.return_value = ok(load_fixture("model_load.json"))

            gateway.load_model("mlx-community/Qwen3 8B")

            assert transport.post.call_args.args == (
                "/models/mlx-community%2FQwen3%208B/load",
            )

        def should_report_unloading_a_model_that_is_not_loaded_as_a_provider_error(
            self, gateway, transport
        ):
            transport.post.side_effect = status_error(
                400, load_fixture("error_model_not_loaded.json")
            )

            with pytest.raises(httpx.HTTPStatusError) as raised:
                gateway.unload_model(MODEL)

            assert (
                raised.value.response.status_code,
                raised.value.response.json(),
            ) == (400, load_fixture("error_model_not_loaded.json"))

    class DescribeEmbeddings:
        def should_post_the_model_and_text_once_and_return_the_first_embedding(
            self, gateway, transport
        ):
            transport.post.return_value = ok(
                {"object": "list", "data": [{"index": 0, "embedding": [0.1, 0.2]}]}
            )

            embedding = gateway.calculate_embeddings("some text", model="embed-model")

            assert (
                transport.post.call_count,
                transport.post.call_args.args,
                embedding,
            ) == (
                1,
                ("/embeddings", {"model": "embed-model", "input": "some text"}),
                [0.1, 0.2],
            )

        @pytest.mark.parametrize("model", [None, "", " "])
        def should_reject_a_missing_or_empty_model_before_any_request(
            self, gateway, transport, model
        ):
            with pytest.raises(ValueError):
                gateway.calculate_embeddings("some text", model=model)

            assert transport.method_calls == []

        def should_report_a_chat_model_as_a_provider_error(self, gateway, transport):
            transport.post.side_effect = status_error(
                400, load_fixture("error_not_embedding_model.json")
            )

            with pytest.raises(httpx.HTTPStatusError) as raised:
                gateway.calculate_embeddings("some text", model=MODEL)

            assert (
                raised.value.response.status_code,
                raised.value.response.json(),
            ) == (400, load_fixture("error_not_embedding_model.json"))


def load_stream_usage(name):
    frames = [
        json.loads(line.removeprefix("data: "))
        for line in fixture_lines(name)
        if line.startswith("data: {")
    ]
    return next(frame["usage"] for frame in frames if frame.get("usage"))


class DescribeOMLXTransport:
    @pytest.fixture
    def requests(self):
        return []

    def transport_for(self, requests, response, api_key=None):
        def handler(request):
            requests.append(request)
            return response

        settings = OMLXSettings(
            base_url="http://studio.local:8000/v1",
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=600.0,
        )
        return OMLXTransport(settings, http_transport=httpx.MockTransport(handler))

    def should_prefix_paths_with_the_base_url(self, requests):
        transport = self.transport_for(
            requests, httpx.Response(200, json=load_fixture("models.json"))
        )

        transport.get("/models")

        assert str(requests[0].url) == "http://studio.local:8000/v1/models"

    def should_send_a_bearer_header_with_a_key(self, requests):
        transport = self.transport_for(
            requests, httpx.Response(200, json={}), api_key="secret"
        )

        transport.post("/chat/completions", {"model": MODEL})

        assert (
            requests[0].headers["Authorization"],
            json.loads(requests[0].content),
        ) == ("Bearer secret", {"model": MODEL})

    def should_send_no_authorization_header_without_a_key(self, requests):
        transport = self.transport_for(requests, httpx.Response(200, json={}))

        transport.post("/models/m/unload")

        assert "Authorization" not in requests[0].headers

    def should_raise_an_error_status_with_its_body(self, requests):
        transport = self.transport_for(
            requests,
            httpx.Response(400, json=load_fixture("error_model_not_loaded.json")),
        )

        with pytest.raises(httpx.HTTPStatusError) as raised:
            transport.post(f"/models/{MODEL}/unload")

        assert raised.value.response.json() == load_fixture(
            "error_model_not_loaded.json"
        )

    def should_yield_the_lines_of_a_stream(self, requests):
        body = (FIXTURES / "stream_length.sse").read_text()
        transport = self.transport_for(requests, httpx.Response(200, text=body))

        lines = list(transport.stream_lines("/chat/completions", {"stream": True}))

        assert lines == body.splitlines()

    def should_yield_whole_lines_when_a_frame_is_split_across_body_chunks(
        self, requests
    ):
        chunks = [
            b'data: {"model":"keep',
            b'alive","choices":[]}\n\ndata: [DO',
            b"NE]\n\n",
        ]
        transport = self.transport_for(
            requests, httpx.Response(200, content=iter(chunks))
        )

        lines = list(transport.stream_lines("/chat/completions", {"stream": True}))

        assert lines == [
            'data: {"model":"keepalive","choices":[]}',
            "",
            "data: [DONE]",
            "",
        ]

    def should_keep_a_percent_encoded_model_id_as_one_path_segment(self, requests):
        transport = self.transport_for(requests, httpx.Response(200, json={}))

        transport.post("/models/mlx-community%2FQwen3/load")

        assert requests[0].url.raw_path == b"/v1/models/mlx-community%2FQwen3/load"

    def should_raise_an_error_status_on_a_stream_with_its_body_read(self, requests):
        streamed_body = iter([(FIXTURES / "error_model_not_found.json").read_bytes()])
        transport = self.transport_for(
            requests, httpx.Response(404, content=streamed_body)
        )

        with pytest.raises(httpx.HTTPStatusError) as raised:
            list(transport.stream_lines("/chat/completions", {"stream": True}))

        assert raised.value.response.json() == load_fixture(
            "error_model_not_found.json"
        )


class DescribeOMLXGatewayOverTheRealHttpLayer:
    @pytest.fixture
    def routes(self):
        return {}

    @pytest.fixture
    def gateway(self, routes):
        def handler(request):
            return routes[(request.method, request.url.path)](request)

        settings = OMLXSettings(
            base_url="http://localhost:8000/v1", headers={}, timeout=600.0
        )
        return OMLXGateway(
            transport=OMLXTransport(
                settings, http_transport=httpx.MockTransport(handler)
            )
        )

    def json_response(self, name, headers=None):
        return lambda request: httpx.Response(
            200,
            content=(FIXTURES / name).read_bytes(),
            headers=[("Content-Type", "application/json"), *(headers or [])],
        )

    def should_list_models_from_a_json_response(self, gateway, routes):
        routes[("GET", "/v1/models")] = self.json_response("models.json")

        assert gateway.get_available_models() == [MODEL]

    def should_complete_from_a_json_response_with_a_warning_header(
        self, gateway, routes, messages
    ):
        routes[("POST", "/v1/chat/completions")] = self.json_response(
            "chat_json_schema.json", headers=[("Warning", "299 - degraded")]
        )

        response = gateway.complete(
            model=MODEL,
            messages=messages,
            object_model=Person,
            config=CompletionConfig(),
        )

        assert (response.object, response.metadata, response.usage["total_tokens"]) == (
            Person(name="Ada", age=36),
            {"response_format_warning": "299 - degraded"},
            82,
        )

    def should_load_and_unload_from_json_responses(self, gateway, routes):
        routes[("POST", f"/v1/models/{MODEL}/load")] = self.json_response(
            "model_load.json"
        )
        routes[("POST", f"/v1/models/{MODEL}/unload")] = self.json_response(
            "model_unload.json"
        )

        assert (gateway.load_model(MODEL), gateway.unload_model(MODEL)) == (None, None)

    def should_report_a_json_error_response_as_a_provider_error(self, gateway, routes):
        routes[("POST", f"/v1/models/{MODEL}/unload")] = lambda request: httpx.Response(
            400,
            content=(FIXTURES / "error_model_not_loaded.json").read_bytes(),
            headers={"Content-Type": "application/json"},
        )

        with pytest.raises(httpx.HTTPStatusError) as raised:
            gateway.unload_model(MODEL)

        assert (raised.value.response.status_code, raised.value.response.json()) == (
            400,
            load_fixture("error_model_not_loaded.json"),
        )

    def should_stream_events_from_an_event_stream_response(
        self, gateway, routes, messages
    ):
        routes[("POST", "/v1/chat/completions")] = lambda request: httpx.Response(
            200,
            content=iter([(FIXTURES / "stream_thinking.sse").read_bytes()]),
            headers={"Content-Type": "text/event-stream"},
        )

        events = list(
            gateway.complete_stream_events(
                model=MODEL, messages=messages, config=CompletionConfig()
            )
        )

        assert (events[0], events[-1].metadata.provider_model) == (
            StreamContent(text="\n\nhello"),
            MODEL,
        )

    def should_report_a_streamed_error_response_with_its_status_and_body(
        self, gateway, routes, messages
    ):
        routes[("POST", "/v1/chat/completions")] = lambda request: httpx.Response(
            404,
            content=iter([(FIXTURES / "error_model_not_found.json").read_bytes()]),
            headers={"Content-Type": "application/json"},
        )

        events = list(
            gateway.complete_stream_events(
                model="nope", messages=messages, config=CompletionConfig()
            )
        )

        assert events == [
            StreamError(
                reason=StreamErrorReason.PROVIDER_ERROR,
                detail={
                    "status_code": 404,
                    "error": load_fixture("error_model_not_found.json")["error"],
                },
            )
        ]
