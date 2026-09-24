import pytest
from ollama import ChatResponse, Message

from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.ollama import OllamaGateway


@pytest.fixture
def mock_ollama_client(mocker):
    return mocker.MagicMock()


@pytest.fixture
def gateway(mocker, mock_ollama_client):
    mocker.patch('mojentic.llm.gateways.ollama.Client', return_value=mock_ollama_client)
    return OllamaGateway()


@pytest.fixture
def messages():
    return [LLMMessage(role=MessageRole.User, content="Hello")]


def _final_frame(**overrides):
    fields = dict(model="qwen3:32b", done=True, done_reason="stop", prompt_eval_count=11, eval_count=5,
                  total_duration=900, load_duration=100, prompt_eval_duration=300, eval_duration=500,
                  message=Message(role="assistant", content="Hi"))
    return ChatResponse(**(fields | overrides))


class DescribeOllamaGateway:

    class DescribeResponseEvidence:

        def should_report_provider_evidence_on_completion(self, gateway, mock_ollama_client, messages):
            mock_ollama_client.chat.return_value = _final_frame()

            response = gateway.complete(model="qwen3:32b", messages=messages, config=CompletionConfig())

            assert (response.usage, response.model, response.finish_reason, response.metadata) == (
                {"prompt_eval_count": 11, "eval_count": 5}, "qwen3:32b", "stop",
                {"total_duration": 900, "load_duration": 100, "prompt_eval_duration": 300, "eval_duration": 500})

        def should_leave_usage_unknown_when_counts_are_not_reported(self, gateway, mock_ollama_client, messages):
            mock_ollama_client.chat.return_value = _final_frame(prompt_eval_count=None, eval_count=None)

            response = gateway.complete(model="qwen3:32b", messages=messages, config=CompletionConfig())

            assert response.usage is None
