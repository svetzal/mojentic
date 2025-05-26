import json
from unittest.mock import Mock

import pytest

from mojentic.llm.gateways.models import TextContent
from mojentic.llm.tools.llm_tool import LLMTool


class MockLLMTool(LLMTool):
    """A mock implementation of LLMTool for testing purposes."""

    def __init__(self, run_result=None, tracer=None):
        super().__init__(tracer=tracer)
        self._run_result = run_result
        self._descriptor = {
            "function": {
                "name": "mock_tool",
                "description": "A mock tool for testing"
            }
        }

    def run(self, **kwargs):
        return self._run_result

    @property
    def descriptor(self):
        return self._descriptor


@pytest.fixture
def mock_tool_with_dict_result():
    return MockLLMTool(run_result={"key": "value"})


@pytest.fixture
def mock_tool_with_string_result():
    return MockLLMTool(run_result="test result")


class DescribeLLMTool:
    class DescribeCallTool:

        def should_convert_dict_result_to_json_string(self, mock_tool_with_dict_result):
            result = mock_tool_with_dict_result.call_tool()

            assert result == {
                "content": [
                    {
                        "type": "text",
                        "text": '{"key": "value"}',
                        "annotations": None
                    }
                ]
            }

        def should_handle_string_result_directly(self, mock_tool_with_string_result):
            result = mock_tool_with_string_result.call_tool()

            assert result == {
                "content": [
                    {
                        "type": "text",
                        "text": "test result",
                        "annotations": None
                    }
                ]
            }

        def should_pass_kwargs_to_run_method(self):
            mock_run = Mock(return_value="test result")
            tool = MockLLMTool()
            tool.run = mock_run

            tool.call_tool(param1="value1", param2="value2")

            mock_run.assert_called_once_with(param1="value1", param2="value2")
