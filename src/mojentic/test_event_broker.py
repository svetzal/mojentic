import pytest

from base_agent import BaseAgent
from channel import Channel
from event import Event
from event_broker import EventBroker

@pytest.fixture
def broker():
    return EventBroker()

@pytest.fixture
def channel1():
    return Channel(name="channel1")

@pytest.fixture
def channel2():
    return Channel(name="channel2")

def test_event_broker_add_channel(broker, channel1):
    broker.add_channel(channel1)

    assert broker.channels == [channel1]

def test_event_broker_remove_channel(broker, channel1, channel2):
    broker.add_channel(channel1)
    broker.add_channel(channel2)

    broker.remove_channel(channel1)

    assert broker.channels == [channel2]

def test_event_broker_send(broker, channel1, mocker):
    broker.add_channel(channel1)
    event = Event()
    agent = BaseAgent() # I need a spy on agent.receive_event
    spy = mocker.spy(agent, 'receive_event')
    channel1.subscribe(agent)

    broker.send(channel_name=channel1.name, event=event)

    spy.assert_called_once_with(event)
