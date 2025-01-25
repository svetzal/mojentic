import pytest
from pydantic import BaseModel

from mojentic.base_llm_agent import BaseLLMAgent
from mojentic.event import Event
from mojentic.llm.llm_broker import LLMBroker


class TestEvent(Event):
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
def llm_query():
    return "Question to ask"


def test_text_response_propagation(mock_llm, llm_behaviour, llm_query):
    class TestBaseLLMAgent(BaseLLMAgent):
        def receive_event(self, event):
            response = self.generate_response(llm_query)
            return [TestEvent(source=type(self), correlation_id=event.correlation_id, content=response)]

    agent = TestBaseLLMAgent(
        llm=mock_llm,
        behaviour=llm_behaviour)
    event = TestEvent(source=str, correlation_id="1234", content=llm_query)

    response_events = agent.receive_event(event)

    mock_llm.generate.assert_called_once_with(
        [
            {"role": "system", "content": llm_behaviour},
            {"role": "user", "content": llm_query},
        ],
        response_model=None,
        tools=[])
    assert len(response_events) == 1
    assert response_events[0].content == "Mocked response"


def test_model_response_propagation(mock_llm, llm_behaviour, llm_query):
    class ResponseConstraintModel(BaseModel):
        pass

    class TestBaseLLMAgent(BaseLLMAgent):
        def receive_event(self, event):
            response = self.generate_response(llm_query)
            return [TestEvent(source=type(self), correlation_id=event.correlation_id, content=response)]

    agent = TestBaseLLMAgent(
        llm=mock_llm,
        behaviour=llm_behaviour,
        response_model=ResponseConstraintModel)
    event = TestEvent(source=str, correlation_id="1234", content=llm_query)

    response_events = agent.receive_event(event)

    mock_llm.generate.assert_called_once_with(
        [
            {"role": "system", "content": llm_behaviour},
            {"role": "user", "content": llm_query},
        ],
        response_model=ResponseConstraintModel,
        tools=[])
    assert len(response_events) == 1
    assert response_events[0].content == "Mocked response"
