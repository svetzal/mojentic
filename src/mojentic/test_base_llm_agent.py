import pytest
from pydantic import BaseModel

from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.event import Event
from mojentic.llm.gateways.models import MessageRole, LLMMessage
from mojentic.llm.llm_broker import LLMBroker


class SampleEvent(Event):
    content: str


@pytest.fixture
def mock_llm(mocker):
    mock = mocker.Mock(spec=LLMBroker)
    mock.generate.return_value = "Mocked response"
    return mock


@pytest.fixture
def llm_behaviour():
    return "You are a helpful assistant."


@pytest.fixture
def llm_prompt():
    return "Question to ask"


def test_text_response_propagation(mock_llm, llm_behaviour, llm_prompt):
    class TestBaseLLMAgent(BaseLLMAgent):
        def receive_event(self, event):
            response = self.generate_response(llm_prompt)
            return [SampleEvent(source=type(self), correlation_id=event.correlation_id, content=response)]

    agent = TestBaseLLMAgent(
        llm=mock_llm,
        behaviour=llm_behaviour)
    event = SampleEvent(source=str, correlation_id="1234", content=llm_prompt)

    response_events = agent.receive_event(event)

    mock_llm.generate.assert_called_once_with(
        [
            LLMMessage(role=MessageRole.System, content=llm_behaviour),
            LLMMessage(role=MessageRole.User, content=llm_prompt),
        ],
        tools=[])
    assert len(response_events) == 1
    assert response_events[0].content == "Mocked response"


def test_model_response_propagation(mock_llm, llm_behaviour, llm_prompt):
    class ResponseConstraintModel(BaseModel):
        something_useful: str = "default"

    class TestBaseLLMAgent(BaseLLMAgent):
        def receive_event(self, event):
            response = self.generate_response(llm_prompt)
            return [
                SampleEvent(source=type(self), correlation_id=event.correlation_id, content=response.something_useful)]

    mock_llm.generate_object.return_value = ResponseConstraintModel()

    agent = TestBaseLLMAgent(
        llm=mock_llm,
        behaviour=llm_behaviour,
        response_model=ResponseConstraintModel)
    event = SampleEvent(source=str, correlation_id="1234", content=llm_prompt)

    response_events = agent.receive_event(event)

    mock_llm.generate_object.assert_called_once_with(
        [
            LLMMessage(role=MessageRole.System, content=llm_behaviour),
            LLMMessage(role=MessageRole.User, content=llm_prompt),
        ],
        object_model=ResponseConstraintModel)
    assert len(response_events) == 1
    assert response_events[0].content == "default"
