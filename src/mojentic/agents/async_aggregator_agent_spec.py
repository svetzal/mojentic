import asyncio

import pytest

from mojentic.agents.async_aggregator_agent import AsyncAggregatorAgent
from mojentic.event import Event


class FirstEvent(Event):
    message: str


class SecondEvent(Event):
    data: str


class ResultEvent(Event):
    result: str


class CollectingAggregator(AsyncAggregatorAgent):
    async def process_events(self, events: list[Event]) -> list[Event]:
        first = next(event for event in events if isinstance(event, FirstEvent))
        second = next(event for event in events if isinstance(event, SecondEvent))
        return [
            ResultEvent(
                source=type(self),
                correlation_id=first.correlation_id,
                result=f"{first.message} - {second.data}",
            )
        ]


@pytest.fixture
def aggregator():
    return CollectingAggregator(event_types_needed=[FirstEvent, SecondEvent])


@pytest.fixture
def pair():
    return (
        FirstEvent(source=str, correlation_id="test-id", message="Hello"),
        SecondEvent(source=str, correlation_id="test-id", data="World"),
    )


def should_initialize_aggregator(aggregator):
    assert aggregator.event_types_needed == [FirstEvent, SecondEvent]
    assert aggregator.results == {}
    assert aggregator.futures == {}


async def should_capture_partial_results_through_public_receive(aggregator, pair):
    result = await aggregator.receive_event_async(pair[0])

    assert result == []
    assert aggregator.results == {"test-id": [pair[0]]}


async def should_return_empty_results_on_immediate_timeout(aggregator):
    result = await aggregator.wait_for_events("test-id", timeout=0)

    assert result == []


async def should_reset_results_after_processing(aggregator, pair):
    await aggregator.receive_event_async(pair[0])
    await aggregator.receive_event_async(pair[1])

    assert aggregator.results["test-id"] is None


async def should_wait_for_events_without_a_timer(aggregator, pair):
    waiting = asyncio.create_task(aggregator.wait_for_events("test-id"))
    await asyncio.sleep(0)
    assert not waiting.done()
    await aggregator.receive_event_async(pair[0])
    assert not waiting.done()
    await aggregator.receive_event_async(pair[1])

    results = await waiting

    assert results == list(pair)


async def should_return_partial_results_on_immediate_timeout(aggregator, pair):
    await aggregator.receive_event_async(pair[0])

    results = await aggregator.wait_for_events("test-id", timeout=0)

    assert results == [pair[0]]


async def should_process_complete_event_sets(aggregator, pair):
    first = await aggregator.receive_event_async(pair[0])
    complete = await aggregator.receive_event_async(pair[1])

    assert first == []
    assert complete == [
        ResultEvent(
            source=CollectingAggregator,
            correlation_id="test-id",
            result="Hello - World",
        )
    ]


async def should_process_reversed_event_order(aggregator, pair):
    first = await aggregator.receive_event_async(pair[1])
    complete = await aggregator.receive_event_async(pair[0])

    assert first == []
    assert complete == [
        ResultEvent(
            source=CollectingAggregator,
            correlation_id="test-id",
            result="Hello - World",
        )
    ]


async def should_isolate_different_correlation_ids(aggregator, pair):
    other_first = FirstEvent(source=str, correlation_id="other-id", message="Goodbye")
    other_second = SecondEvent(source=str, correlation_id="other-id", data="Universe")
    await aggregator.receive_event_async(pair[0])
    await aggregator.receive_event_async(other_first)

    first_result = await aggregator.receive_event_async(pair[1])
    other_result = await aggregator.receive_event_async(other_second)

    assert first_result == [
        ResultEvent(
            source=CollectingAggregator,
            correlation_id="test-id",
            result="Hello - World",
        )
    ]
    assert other_result == [
        ResultEvent(
            source=CollectingAggregator,
            correlation_id="other-id",
            result="Goodbye - Universe",
        )
    ]


async def should_preserve_base_no_output_behavior(pair):
    aggregator = AsyncAggregatorAgent(event_types_needed=[FirstEvent, SecondEvent])

    await aggregator.receive_event_async(pair[0])
    result = await aggregator.receive_event_async(pair[1])

    assert result == []
