import json

import pytest
from pydantic import BaseModel, field_validator

from mojentic.llm.gateways.file_gateway import FileGateway
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.openai import OpenAIGateway


class BrokenResult(BaseModel):
    answer: str

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value):
        raise TypeError("validator programming defect")


class DescribeLintBoundaries:
    def should_propagate_openai_validator_defects_after_one_http_request(self):
        response = json.dumps(
            {
                "id": "test",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-4o",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": '{"answer":"ok"}',
                        },
                    }
                ],
            }
        ).encode()
        with scripted_http([(200, {}, response)]) as (host, requests):
            gateway = OpenAIGateway(api_key="test-key", base_url=host)

            with pytest.raises(TypeError, match="validator programming defect"):
                gateway.complete(
                    model="gpt-4o",
                    messages=[LLMMessage(role=MessageRole.User, content="test")],
                    object_model=BrokenResult,
                )

            assert len(requests) == 1
            assert requests[0][0] == "/chat/completions"
            headers = {key.lower(): value for key, value in requests[0][2].items()}
            assert headers["authorization"] == "Bearer test-key"
            payload = json.loads(requests[0][1])
            assert payload["messages"] == [{"role": "user", "content": "test"}]
            assert payload["model"] == "gpt-4o"
            assert payload["stream"] is False
            assert payload["response_format"] == {
                "type": "json_schema",
                "json_schema": {
                    "name": "BrokenResult",
                    "strict": True,
                    "schema": {
                        "properties": {"answer": {"title": "Answer", "type": "string"}},
                        "required": ["answer"],
                        "title": "BrokenResult",
                        "type": "object",
                        "additionalProperties": False,
                    },
                },
            }

    def should_propagate_invalid_path_programming_errors(self):
        class BrokenPath:
            def __fspath__(self):
                raise TypeError("path programming defect")

        with pytest.raises(TypeError, match="path programming defect"):
            FileGateway().is_binary(BrokenPath())

    def should_preserve_unreadable_file_binary_fallback(self, tmp_path):
        assert FileGateway().is_binary(tmp_path / "absent") is True


class DescribeImageAdapterFailures:
    @pytest.mark.parametrize(
        "adapter",
        [
            pytest.param("openai", id="openai"),
            pytest.param("anthropic", id="anthropic"),
        ],
    )
    def should_propagate_path_programming_errors_after_reading_a_real_image(
        self, tmp_path, adapter
    ):
        from mojentic.llm.gateways.anthropic_messages_adapter import (
            adapt_messages_to_anthropic,
        )
        from mojentic.llm.gateways.openai_messages_adapter import (
            adapt_messages_to_openai,
        )

        class BrokenPath(str):
            def rfind(self, *args):
                raise TypeError("image path programming defect")

        image = tmp_path / "image.png"
        image.write_bytes(b"actual image bytes")
        message = LLMMessage.model_construct(
            role=MessageRole.User, content="image", image_paths=[BrokenPath(str(image))]
        )
        adapters = {
            "openai": adapt_messages_to_openai,
            "anthropic": adapt_messages_to_anthropic,
        }

        with pytest.raises(TypeError, match="image path programming defect"):
            adapters[adapter]([message])

    @pytest.mark.parametrize("adapter", ["openai", "anthropic"])
    def should_preserve_unreadable_image_text_fallback(self, tmp_path, adapter):
        from mojentic.llm.gateways.anthropic_messages_adapter import (
            adapt_messages_to_anthropic,
        )
        from mojentic.llm.gateways.openai_messages_adapter import (
            adapt_messages_to_openai,
        )

        message = LLMMessage(
            role=MessageRole.User,
            content="image",
            image_paths=[str(tmp_path / "absent.png")],
        )
        adapters = {
            "openai": adapt_messages_to_openai,
            "anthropic": adapt_messages_to_anthropic,
        }

        result = adapters[adapter]([message])

        assert result == [
            {"role": "user", "content": [{"type": "text", "text": "image"}]}
        ]


class HeaderAnswer(BaseModel):
    answer: str


def ordinary_completion(gateway):
    return gateway.complete(model="test", messages=[]).content


def structured_completion(gateway):
    return gateway.complete(
        model="test", messages=[], object_model=HeaderAnswer
    ).object.answer


def streaming_completion(gateway):
    return "".join(
        chunk.content or ""
        for chunk in gateway.complete_stream(model="test", messages=[])
    )


class DescribeOllamaHeaderCompatibility:
    @pytest.mark.parametrize(
        "headers,expected",
        [
            ({}, None),
            ({"headers": None}, None),
            ({"headers": {}}, None),
            ({"headers": {"X-Lint-Probe": "present"}}, "present"),
        ],
    )
    @pytest.mark.parametrize(
        "operation,response",
        [
            (ordinary_completion, "ok"),
            (structured_completion, '{"answer":"ok"}'),
            (streaming_completion, "ok"),
        ],
    )
    def should_preserve_headers_through_every_completion_path(
        self, headers, expected, operation, response
    ):
        from mojentic.llm.gateways.ollama import OllamaGateway
        from mojentic.llm.gateways.ollama_recovery_spec import frame

        with scripted_http([(200, {}, frame(response) + b"\n")]) as (host, requests):
            gateway = OllamaGateway(host=host, **headers)

            result = operation(gateway)

            assert result == "ok"
            assert len(requests) == 1
            assert requests[0][2].get("x-lint-probe") == expected
