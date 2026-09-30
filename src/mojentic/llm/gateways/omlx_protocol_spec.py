import json
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel

from mojentic.llm.completion_config import CompletionConfig, ResponseFormat
from mojentic.llm.gateways.models import LLMMessage, LLMToolCall, MessageRole
from mojentic.llm.gateways.omlx_protocol import (
    DEFAULT_HOST,
    DEFAULT_TIMEOUT,
    omlx_chat_body,
    omlx_error_detail,
    omlx_gateway_response,
    omlx_settings,
    requests_structured_output,
)
from mojentic.llm.tools.date_resolver import ResolveDateTool

FIXTURES = Path(__file__).parent / "fixtures" / "omlx"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text())


class Person(BaseModel):
    name: str
    age: int


@pytest.fixture
def messages():
    return [LLMMessage(role=MessageRole.User, content="Hi")]


class DescribeOMLXSettings:

    def should_default_to_localhost_with_the_v1_prefix(self):
        settings = omlx_settings(environ={})

        assert settings.base_url == f"{DEFAULT_HOST}/v1"

    def should_use_the_environment_when_no_host_is_given(self):
        settings = omlx_settings(environ={"OMLX_HOST": "http://studio.local:9000"})

        assert settings.base_url == "http://studio.local:9000/v1"

    def should_prefer_an_explicit_host_over_the_environment(self):
        settings = omlx_settings(host="http://explicit:8000", environ={"OMLX_HOST": "http://env:8000"})

        assert settings.base_url == "http://explicit:8000/v1"

    def should_not_double_a_trailing_slash_on_the_host(self):
        settings = omlx_settings(host="http://explicit:8000/", environ={})

        assert settings.base_url == "http://explicit:8000/v1"

    def should_send_no_authorization_header_without_a_key(self):
        settings = omlx_settings(environ={})

        assert settings.headers == {}

    def should_send_a_bearer_header_with_the_environment_key(self):
        settings = omlx_settings(environ={"OMLX_API_KEY": "env-key"})

        assert settings.headers == {"Authorization": "Bearer env-key"}

    def should_prefer_an_explicit_key_over_the_environment(self):
        settings = omlx_settings(api_key="explicit-key", environ={"OMLX_API_KEY": "env-key"})

        assert settings.headers == {"Authorization": "Bearer explicit-key"}

    def should_treat_an_empty_key_as_no_key(self):
        settings = omlx_settings(environ={"OMLX_API_KEY": ""})

        assert settings.headers == {}

    def should_allow_an_explicit_empty_key_to_override_the_environment(self):
        settings = omlx_settings(api_key="", environ={"OMLX_API_KEY": "env-key"})

        assert settings.headers == {}

    def should_default_the_timeout(self):
        settings = omlx_settings(environ={})

        assert settings.timeout == DEFAULT_TIMEOUT

    def should_read_the_timeout_from_the_environment_in_milliseconds(self):
        settings = omlx_settings(environ={"OMLX_TIMEOUT": "42500"})

        assert settings.timeout == 42.5

    def should_default_to_ten_minutes(self):
        assert DEFAULT_TIMEOUT == 600000 / 1000

    def should_prefer_an_explicit_timeout_over_the_environment(self):
        settings = omlx_settings(timeout=7.0, environ={"OMLX_TIMEOUT": "42500"})

        assert settings.timeout == 7.0


class DescribeOMLXChatBody:

    def should_send_model_messages_temperature_and_max_tokens(self, messages):
        body = omlx_chat_body("Qwen3.8-27B-MLX-8bit", messages, CompletionConfig(temperature=0.2, max_tokens=512))

        assert body == {
            "model": "Qwen3.8-27B-MLX-8bit",
            "messages": [{"role": "user", "content": "Hi"}],
            "temperature": 0.2,
            "max_tokens": 512,
        }

    def should_never_send_max_completion_tokens_for_a_name_the_openai_registry_calls_reasoning(self, messages):
        body = omlx_chat_body("o3-local-mlx", messages, CompletionConfig(max_tokens=64))

        assert ("max_tokens" in body, "max_completion_tokens" in body) == (True, False)

    def should_not_send_context_or_prediction_lengths(self, messages):
        body = omlx_chat_body("m", messages, CompletionConfig(num_ctx=4096, num_predict=128))

        assert ("num_ctx" in body, "num_predict" in body) == (False, False)

    def should_forward_reasoning_effort_unchanged_for_any_model_name(self, messages):
        body = omlx_chat_body("Qwen3.8-27B-MLX-8bit", messages, CompletionConfig(reasoning_effort="low"))

        assert body["reasoning_effort"] == "low"

    def should_omit_reasoning_effort_when_not_set(self, messages):
        body = omlx_chat_body("m", messages, CompletionConfig())

        assert "reasoning_effort" not in body

    def should_send_tools_as_the_openai_gateway_does(self, messages):
        tool = ResolveDateTool()

        body = omlx_chat_body("o1-mini-local", messages, CompletionConfig(), tools=[tool])

        assert body["tools"] == [tool.descriptor]

    def should_omit_tools_when_none_are_given(self, messages):
        body = omlx_chat_body("m", messages, CompletionConfig())

        assert "tools" not in body

    def should_adapt_messages_through_the_openai_adapter(self):
        call = LLMToolCall(id="call_1", name="resolve_date", arguments={"relative": "today"})
        history = [
            LLMMessage(role=MessageRole.Assistant, content="", tool_calls=[call]),
            LLMMessage(role=MessageRole.Tool, content="2026-09-29", tool_calls=[call]),
        ]

        body = omlx_chat_body("m", history, CompletionConfig())

        assert body["messages"][1] == {"role": "tool", "content": "2026-09-29", "tool_call_id": "call_1"}

    @pytest.mark.parametrize("response_format, expected", [
        (ResponseFormat(type="text"), {"type": "text"}),
        (ResponseFormat(type="json_object"), {"type": "json_object"}),
        (ResponseFormat(type="json_object", json_schema={"type": "object"}),
         {"type": "json_schema", "json_schema": {"name": "response", "schema": {"type": "object"}}}),
    ])
    def should_forward_the_configured_response_format(self, messages, response_format, expected):
        body = omlx_chat_body("m", messages, CompletionConfig(response_format=response_format))

        assert body["response_format"] == expected

    def should_leave_the_response_format_out_when_not_configured(self, messages):
        body = omlx_chat_body("m", messages, CompletionConfig())

        assert "response_format" not in body

    def should_request_the_object_model_schema_as_json_schema(self, messages):
        body = omlx_chat_body("m", messages, CompletionConfig(), object_model=Person)

        assert body["response_format"] == {
            "type": "json_schema",
            "json_schema": {"name": "response", "schema": Person.model_json_schema()},
        }


class DescribeStructuredOutputRequested:

    @pytest.mark.parametrize("body, expected", [
        ({}, False),
        ({"response_format": {"type": "text"}}, False),
        ({"response_format": {"type": "json_object"}}, True),
        ({"response_format": {"type": "json_schema", "json_schema": {}}}, True),
    ])
    def should_recognize_json_object_and_json_schema_requests(self, body, expected):
        assert requests_structured_output(body) is expected


class DescribeOMLXGatewayResponse:

    def should_map_reasoning_content_to_thinking(self):
        response = omlx_gateway_response(load_fixture("chat_thinking.json"))

        assert (response.content, response.thinking) == (
            "hello",
            "We need to reply exactly: hello. User said \"Reply with exactly: hello\". Need final \"hello\". "
            "Ensure no extra.")

    def should_leave_thinking_empty_when_the_response_has_none(self):
        response = omlx_gateway_response(load_fixture("chat_thinking_disabled.json"))

        assert (response.content, response.thinking) == ("hello", None)

    def should_keep_usage_exactly_as_reported(self):
        payload = load_fixture("chat_thinking.json")

        response = omlx_gateway_response(payload)

        assert response.usage == payload["usage"]

    def should_report_the_provider_model_and_finish_reason(self):
        response = omlx_gateway_response(load_fixture("chat_thinking.json"))

        assert (response.model, response.finish_reason) == ("Qwen3.8-27B-MLX-8bit", "stop")

    def should_parse_tool_calls(self):
        response = omlx_gateway_response(load_fixture("chat_tool_call.json"))

        assert (response.tool_calls, response.content, response.finish_reason) == (
            [LLMToolCall(id="call_bd4d55c2", name="resolve_date", arguments={"relative": "today"})],
            None,
            "tool_calls")

    def should_keep_truncated_content_where_the_provider_put_it(self):
        response = omlx_gateway_response(load_fixture("chat_length.json"))

        assert (response.content, response.thinking, response.finish_reason) == (
            "We need to respond to", None, "length")

    def should_have_empty_metadata_without_a_warning(self):
        response = omlx_gateway_response(load_fixture("chat_json_schema.json"))

        assert response.metadata == {}

    def should_record_a_response_format_warning_in_metadata(self):
        response = omlx_gateway_response(load_fixture("chat_json_schema.json"),
                                         response_format_warning="299 - \"grammar not enforced\"")

        assert response.metadata == {"response_format_warning": "299 - \"grammar not enforced\""}


class DescribeOMLXErrorDetail:

    def should_carry_the_status_and_the_error_object(self):
        body = load_fixture("error_model_not_found.json")
        response = httpx.Response(404, json=body)

        assert omlx_error_detail(response) == {"status_code": 404, "error": body["error"]}

    def should_carry_a_body_that_is_not_json_as_text(self):
        response = httpx.Response(502, text="Bad Gateway")

        assert omlx_error_detail(response) == {"status_code": 502, "error": "Bad Gateway"}
