import pytest
from pydantic import ValidationError

from mojentic.llm.completion_config import CompletionConfig


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
