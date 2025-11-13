from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from mojentic.llm.gateways.models import LLMMessage, MessageRole, LLMGatewayResponse, LLMToolCall
from mojentic.llm.llm_broker import LLMBroker


class SimpleModel(BaseModel):
    text: str
    number: int

class NestedModel(BaseModel):
    title: str
    details: SimpleModel

class ComplexModel(BaseModel):
    name: str
    items: list[SimpleModel]
    metadata: dict[str, str]


@pytest.fixture
def mock_gateway(mocker):
    return mocker.MagicMock()


@pytest.fixture
def llm_broker(mock_gateway):
    return LLMBroker(model="test-model", gateway=mock_gateway)


class DescribeLLMBroker:

    class DescribeMessageGeneration:

        def should_generate_simple_response_for_user_message(self, llm_broker, mock_gateway):
            test_response_content = "I am fine, thank you!"
            messages = [LLMMessage(role=MessageRole.User, content="Hello, how are you?")]
            mock_gateway.complete.return_value = LLMGatewayResponse(
                content=test_response_content,
                object=None,
                tool_calls=[]
            )

            result = llm_broker.generate(messages)

            assert result == test_response_content
            mock_gateway.complete.assert_called_once()

        def should_handle_tool_calls_during_generation(self, llm_broker, mock_gateway, mocker):
            messages = [LLMMessage(role=MessageRole.User, content="What is the date on Friday?")]
            tool_call = mocker.create_autospec(LLMToolCall, instance=True)
            tool_call.name = "resolve_date"
            tool_call.arguments = {"date": "Friday"}

            mock_gateway.complete.side_effect = [
                LLMGatewayResponse(content="", object=None, tool_calls=[tool_call]),
                LLMGatewayResponse(content="The date is Friday.", object=None, tool_calls=[])
            ]

            mock_tool = mocker.MagicMock()
            mock_tool.matches.return_value = True
            mock_tool.run.return_value = {"resolved_date": "Friday"}

            result = llm_broker.generate(messages, tools=[mock_tool])

            assert result == "The date is Friday."
            assert mock_gateway.complete.call_count == 2
            mock_tool.run.assert_called_once_with(date="Friday")

    class DescribeObjectGeneration:

        def should_generate_simple_model(self, llm_broker, mock_gateway):
            messages = [LLMMessage(role=MessageRole.User, content="Generate a simple object")]
            mock_object = SimpleModel(text="test", number=42)
            mock_gateway.complete.return_value = LLMGatewayResponse(
                content='{"text": "test", "number": 42}',
                object=mock_object,
                tool_calls=[]
            )

            result = llm_broker.generate_object(messages, object_model=SimpleModel)

            assert isinstance(result, SimpleModel)
            assert result.text == "test"
            assert result.number == 42
            mock_gateway.complete.assert_called_once()

        def should_generate_nested_model(self, llm_broker, mock_gateway):
            messages = [LLMMessage(role=MessageRole.User, content="Generate a nested object")]
            mock_object = NestedModel(
                title="main",
                details=SimpleModel(text="nested", number=123)
            )
            mock_gateway.complete.return_value = LLMGatewayResponse(
                content='{"title": "main", "details": {"text": "nested", "number": 123}}',
                object=mock_object,
                tool_calls=[]
            )

            result = llm_broker.generate_object(messages, object_model=NestedModel)

            assert isinstance(result, NestedModel)
            assert result.title == "main"
            assert isinstance(result.details, SimpleModel)
            assert result.details.text == "nested"
            assert result.details.number == 123
            mock_gateway.complete.assert_called_once()

        def should_generate_complex_model(self, llm_broker, mock_gateway):
            messages = [LLMMessage(role=MessageRole.User, content="Generate a complex object")]
            mock_object = ComplexModel(
                name="test",
                items=[
                    SimpleModel(text="item1", number=1),
                    SimpleModel(text="item2", number=2)
                ],
                metadata={"key1": "value1", "key2": "value2"}
            )
            mock_gateway.complete.return_value = LLMGatewayResponse(
                content='{"name": "test", "items": [{"text": "item1", "number": 1}, {"text": "item2", "number": 2}], "metadata": {"key1": "value1", "key2": "value2"}}',
                object=mock_object,
                tool_calls=[]
            )

            result = llm_broker.generate_object(messages, object_model=ComplexModel)

            assert isinstance(result, ComplexModel)
            assert result.name == "test"
            assert len(result.items) == 2
            assert all(isinstance(item, SimpleModel) for item in result.items)
            assert result.items[0].text == "item1"
            assert result.items[1].number == 2
            assert result.metadata == {"key1": "value1", "key2": "value2"}
            mock_gateway.complete.assert_called_once()

    class DescribeStreamingGeneration:

        def should_stream_simple_response(self, llm_broker, mock_gateway, mocker):
            from mojentic.llm.gateways.ollama import StreamingResponse

            messages = [LLMMessage(role=MessageRole.User, content="Tell me a story")]

            # Mock the complete_stream method to yield chunks
            mock_gateway.complete_stream = mocker.MagicMock()
            mock_gateway.complete_stream.return_value = iter([
                StreamingResponse(content="Once "),
                StreamingResponse(content="upon "),
                StreamingResponse(content="a "),
                StreamingResponse(content="time...")
            ])

            result_chunks = list(llm_broker.generate_stream(messages))

            assert result_chunks == ["Once ", "upon ", "a ", "time..."]
            mock_gateway.complete_stream.assert_called_once()

        def should_handle_tool_calls_during_streaming(self, llm_broker, mock_gateway, mocker):
            from mojentic.llm.gateways.ollama import StreamingResponse

            messages = [LLMMessage(role=MessageRole.User, content="What is the date on Friday?")]
            tool_call = mocker.create_autospec(LLMToolCall, instance=True)
            tool_call.name = "resolve_date"
            tool_call.arguments = {"date": "Friday"}

            # First stream has tool call, second stream has the response after tool execution
            mock_gateway.complete_stream = mocker.MagicMock()
            mock_gateway.complete_stream.side_effect = [
                iter([
                    StreamingResponse(content="Let "),
                    StreamingResponse(content="me "),
                    StreamingResponse(content="check..."),
                    StreamingResponse(tool_calls=[tool_call])
                ]),
                iter([
                    StreamingResponse(content="The "),
                    StreamingResponse(content="date "),
                    StreamingResponse(content="is "),
                    StreamingResponse(content="2024-11-15")
                ])
            ]

            mock_tool = mocker.MagicMock()
            mock_tool.matches.return_value = True
            mock_tool.run.return_value = {"resolved_date": "2024-11-15"}

            result_chunks = list(llm_broker.generate_stream(messages, tools=[mock_tool]))

            # Should get chunks from first response, then chunks from second response after tool execution
            assert result_chunks == ["Let ", "me ", "check...", "The ", "date ", "is ", "2024-11-15"]
            assert mock_gateway.complete_stream.call_count == 2
            mock_tool.run.assert_called_once_with(date="Friday")

        def should_raise_error_if_gateway_does_not_support_streaming(self, llm_broker, mock_gateway):
            messages = [LLMMessage(role=MessageRole.User, content="Hello")]

            # Remove complete_stream method to simulate unsupported gateway
            if hasattr(mock_gateway, 'complete_stream'):
                delattr(mock_gateway, 'complete_stream')

            with pytest.raises(NotImplementedError) as exc_info:
                list(llm_broker.generate_stream(messages))

            assert "does not support streaming" in str(exc_info.value)
