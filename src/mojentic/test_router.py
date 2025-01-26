import pytest

from mojentic.base_agent import BaseAgent
from mojentic.event import Event
from mojentic.router import Router


@pytest.fixture
def router():
    return Router()


class TestEvent(Event):
    pass


def test_router_add_route(mocker, router):
    test_agent = BaseAgent()
    router.add_route(TestEvent, test_agent)

    event = TestEvent(source=str)
    assert router.get_agents(event) == [test_agent]


def test_router_add_multiple_agents(mocker, router):
    test_agent1 = BaseAgent()
    test_agent2 = BaseAgent()
    router.add_route(TestEvent, test_agent1)
    router.add_route(TestEvent, test_agent2)

    event = TestEvent(source=str)
    assert router.get_agents(event) == [test_agent1, test_agent2]


def test_router_get_agents_no_agents(mocker, router):
    event = TestEvent(source=str)
    assert router.get_agents(event) == []
