import pytest
from anthropic.types import Message, TextBlock, Usage

from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.models import LLMMessage, MessageRole


@pytest.fixture
def mock_anthropic_client(mocker):
    return mocker.MagicMock()


@pytest.fixture
def gateway(mocker, mock_anthropic_client):
    mocker.patch('mojentic.llm.gateways.anthropic.Anthropic', return_value=mock_anthropic_client)
    return AnthropicGateway(api_key="test_key")


class DescribeAnthropicGateway:

    class DescribeResponseEvidence:

        def should_report_provider_evidence_on_completion(self, gateway, mock_anthropic_client):
            mock_anthropic_client.messages.create.return_value = Message(
                id="msg_1", type="message", role="assistant", model="claude-reported",
                content=[TextBlock(type="text", text="Hi")], stop_reason="max_tokens",
                usage=Usage(input_tokens=10, output_tokens=2))

            response = gateway.complete(model="claude-configured",
                                        messages=[LLMMessage(role=MessageRole.User, content="Hello")],
                                        config=CompletionConfig())

            assert (response.usage["input_tokens"], response.usage["output_tokens"], response.model,
                    response.finish_reason) == (10, 2, "claude-reported", "max_tokens")
