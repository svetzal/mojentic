from time import sleep

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
    spy = mocker.spy(test_agent, 'receive_event')
    router.add_route(TestEvent, test_agent)

    event = TestEvent(source=str)
    router.dispatch(event)

    sleep(1)

    spy.assert_called_once()

    router.stop()