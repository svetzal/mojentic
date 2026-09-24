import pytest
from pydantic import ValidationError

from mojentic.llm.completion_config import CompletionConfig, ResponseFormat


class DescribeCompletionConfig:

    def should_use_default_values(self):
        config = CompletionConfig()
        assert config.temperature == 1.0
        assert config.num_ctx == 32768
        assert config.max_tokens == 16384
        assert config.num_predict == -1
        assert config.reasoning_effort is None

    def should_accept_custom_values(self):
        config = CompletionConfig(
            temperature=0.5,
            num_ctx=16384,
            max_tokens=8192,
            num_predict=100,
            reasoning_effort="high"
        )
        assert config.temperature == 0.5
        assert config.num_ctx == 16384
        assert config.max_tokens == 8192
        assert config.num_predict == 100
        assert config.reasoning_effort == "high"

    def should_accept_valid_reasoning_effort_levels(self):
        for level in ["low", "medium", "high"]:
            config = CompletionConfig(reasoning_effort=level)
            assert config.reasoning_effort == level

    def should_reject_invalid_reasoning_effort_levels(self):
        with pytest.raises(ValidationError) as exc_info:
            CompletionConfig(reasoning_effort="invalid")

        assert "reasoning_effort" in str(exc_info.value)

    def should_accept_none_reasoning_effort(self):
        config = CompletionConfig(reasoning_effort=None)
        assert config.reasoning_effort is None


class DescribeResponseFormat:

    def should_default_to_absent_on_config(self):
        config = CompletionConfig()

        assert config.response_format is None

    def should_accept_text_format(self):
        config = CompletionConfig(response_format=ResponseFormat(type="text"))

        assert config.response_format.type == "text"

    def should_accept_json_object_without_schema(self):
        response_format = ResponseFormat(type="json_object")

        assert response_format.json_schema is None

    def should_accept_json_object_with_schema(self):
        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}

        response_format = ResponseFormat(type="json_object", json_schema=schema)

        assert response_format.json_schema == schema

    def should_reject_schema_on_text_format(self):
        with pytest.raises(ValidationError):
            ResponseFormat(type="text", json_schema={"type": "object"})

    def should_reject_unknown_format_type(self):
        with pytest.raises(ValidationError):
            ResponseFormat(type="yaml")
