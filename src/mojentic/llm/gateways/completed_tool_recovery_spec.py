"""Completed non-stream tool counts through public broker calls."""

import json

import pytest

from mojentic.llm.gateways import omlx_recovery_spec as recovery_fixtures
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.ollama_recovery_spec import frame, scripted_http
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.omlx_recovery_spec import allow, completion
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.gateways.openai_strict_tool_recovery_spec import StrictTool
from mojentic.llm.recovery import RecoveryPolicy

broker_factory = recovery_fixtures.broker_factory


@pytest.fixture
def tool_round(provider, count):
    cities = ["Paris", "London"][:count]
    calls = [
        {
            "id": f"call-{index}",
            "type": "function",
            "function": {"name": "lookup", "arguments": {"city": city}},
        }
        for index, city in enumerate(cities)
    ]
    if provider == "ollama":
        tool_body = frame("", tool_calls=calls)
        final_body = frame("done")
    else:
        for call in calls:
            call["function"]["arguments"] = json.dumps(call["function"]["arguments"])
        tool_body = completion("", tool_calls=calls).replace(
            b'"finish_reason": "length"', b'"finish_reason": "tool_calls"'
        )
        final_body = completion("done").replace(
            b'"finish_reason": "length"', b'"finish_reason": "stop"'
        )
    lifecycle = []
    policy = RecoveryPolicy(
        max_attempts=2, base_delay=0, admission=allow, observer=lifecycle.append
    )
    with scripted_http(
        [
            (200, {}, tool_body),
            (200, {}, tool_body),
            (503, {}, b"temporarily unavailable"),
            (200, {}, final_body),
        ]
    ) as (host, requests):
        gateways = {
            "openai": lambda: OpenAIGateway(
                api_key="loopback", base_url=host + "/v1", recovery_policy=policy
            ),
            "ollama": lambda: OllamaGateway(host=host, recovery_policy=policy),
            "omlx": lambda: OMLXGateway(host=host, recovery_policy=policy),
        }
        gateway = gateways[provider]()
        try:
            yield gateway, requests, lifecycle, cities
        finally:
            if provider == "openai":
                gateway.client.close()


class DescribeCompletedToolRecovery:
    @pytest.mark.parametrize("provider", ["openai", "ollama", "omlx"])
    @pytest.mark.parametrize("count", [1, 2])
    def should_report_completed_calls_and_execute_each_once(
        self, count, tool_round, broker_factory
    ):
        gateway, requests, lifecycle, cities = tool_round
        tool = StrictTool()
        messages = [LLMMessage(content="Look up these cities")]
        broker = broker_factory(gateway)

        response = broker.generate_response(messages, tools=[tool])

        assert response.recovery_report.progress.completed_tool_calls == count
        assert (
            response.metadata["recovery"]["progress"]["completed_tool_calls"] == count
        )
        assert lifecycle[-1].transition == "attempt_succeeded"
        assert lifecycle[-1].progress.completed_tool_calls == count

        result = broker.generate(messages, tools=[tool])

        assert result == "done"
        assert tool.calls == cities
        assert len(requests) == 4
        assert requests[2][1] == requests[3][1]
        successes = [
            event for event in lifecycle if event.transition == "attempt_succeeded"
        ]
        assert [event.progress.completed_tool_calls for event in successes] == [
            count,
            count,
            0,
        ]
