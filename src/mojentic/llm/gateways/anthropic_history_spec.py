"""Anthropic history v1: local HTTP behavior, not paired vendor verification."""

import json

import pytest

from mojentic.llm.chat_session import ChatSession
from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways import omlx_recovery_spec as recovery_fixtures
from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.cloud_recovery_spec import success
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.recovery import RecoveryPolicy
from scripts.inprocess_http import clock, virtual_sleep

broker_factory = recovery_fixtures.broker_factory


class DescribeAnthropicHistory:
    async def should_resend_identical_full_history_with_stable_logical_identity(self):
        captures = []
        messages = [
            LLMMessage(role=MessageRole.System, content="Be precise"),
            LLMMessage(content="héllo 世界"),
            LLMMessage(role=MessageRole.Assistant, content="réponse 🌍"),
            LLMMessage(content="continue"),
            LLMMessage(role=MessageRole.Assistant, content=""),
            LLMMessage(content="finish"),
        ]
        expected = {
            "model": "claude-test",
            "system": "Be precise",
            "messages": [
                {"role": "user", "content": "héllo 世界"},
                {"role": "assistant", "content": "réponse 🌍"},
                {"role": "user", "content": "continue"},
                {"role": "assistant", "content": ""},
                {"role": "user", "content": "finish"},
            ],
            "temperature": 0.25,
            "max_tokens": 17,
        }
        policy = RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            sleeper=virtual_sleep,
            max_attempts=2,
            base_delay=0,
            wire_observer=captures.append,
        )
        with scripted_http([(503, {}, b"busy"), (200, {}, success("anthropic"))]) as (
            host,
            requests,
        ):
            gateway = AnthropicGateway(
                api_key="test-key", base_url=host, recovery_policy=policy
            )

            response = await gateway.complete_with_recovery(
                model="claude-test",
                messages=messages,
                config=CompletionConfig(temperature=0.25, max_tokens=17),
            )

        expected_bytes = json.dumps(
            expected, ensure_ascii=False, separators=(",", ":")
        ).encode()
        assert [(path, body) for path, body, _ in requests] == [
            ("/v1/messages", expected_bytes)
        ] * 2
        sent = [event for event in captures if event.kind == "request"]
        assert [event.body for event in sent] == [expected_bytes] * 2
        assert len({event.identity.logical_request_id for event in sent}) == 1
        assert all(event.identity.attempt_id for event in sent)
        assert len({event.identity.attempt_id for event in sent}) == 2
        assert [event.identity.wire_attempt for event in sent] == [1, 2]
        assert response.content == "answer"
        assert response.recovery_report.history[0].http_status == 503
        assert response.recovery_report.history[0].eligible
        assert (
            response.recovery_report.identity.logical_request_id
            == sent[0].identity.logical_request_id
        )

    @pytest.mark.parametrize(
        ("policy", "credential"),
        [
            (None, ("authorization", "Bearer test-key")),
            (
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=1,
                ),
                ("x-api-key", "test-key"),
            ),
        ],
    )
    def should_preserve_ordered_history_system_images_controls_and_response(
        self, policy, credential, tmp_path
    ):
        image = tmp_path / "pixel.png"
        image.write_bytes(b"image-bytes")
        messages = [
            LLMMessage(role=MessageRole.System, content="first instruction"),
            LLMMessage(content="héllo 世界", image_paths=[str(image)]),
            LLMMessage(role=MessageRole.Assistant, content="réponse 🌍"),
            LLMMessage(role=MessageRole.System, content="second instruction"),
            LLMMessage(content="continue"),
            LLMMessage(role=MessageRole.Assistant, content=""),
            LLMMessage(role=MessageRole.Tool, content="excluded tool result"),
            LLMMessage(content="finish"),
        ]
        with scripted_http([(200, {}, success("anthropic"))]) as (host, requests):
            gateway = AnthropicGateway(
                api_key="test-key", base_url=host, recovery_policy=policy
            )

            response = gateway.complete(
                model="claude-test",
                messages=messages,
                config=CompletionConfig(
                    temperature=0, max_tokens=17, top_p=0.7, top_k=4
                ),
                temperature=0.9,
                max_tokens=999,
            )

        assert [path for path, _, _ in requests] == ["/v1/messages"]
        assert json.loads(requests[0][1]) == {
            "model": "claude-test",
            "system": "first instruction second instruction",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "héllo 世界"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "aW1hZ2UtYnl0ZXM=",
                            },
                        },
                    ],
                },
                {"role": "assistant", "content": "réponse 🌍"},
                {"role": "user", "content": "continue"},
                {"role": "assistant", "content": ""},
                {"role": "user", "content": "finish"},
            ],
            "temperature": 0,
            "max_tokens": 17,
            "top_p": 0.7,
            "top_k": 4,
        }
        headers = {key.lower(): value for key, value in requests[0][2].items()}
        credential_header, credential_value = credential
        assert headers[credential_header] == credential_value
        assert headers["anthropic-version"] == "2023-06-01"
        assert response.content == "answer"
        assert response.model == "reported"
        assert response.finish_reason == "end_turn"
        assert response.usage["input_tokens"] == 2
        assert response.usage["output_tokens"] == 3
        assert response.tool_calls == []
        assert response.object is None

    @pytest.mark.parametrize(
        "policy",
        [
            None,
            RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=1,
            ),
        ],
    )
    @pytest.mark.parametrize(
        "controls,expected",
        [
            ({}, {"max_tokens": 4096}),
            (
                {"temperature": 0.2, "max_tokens": 23},
                {"temperature": 0.2, "max_tokens": 23},
            ),
            (
                {"max_tokens": 19},
                {"max_tokens": 19},
            ),
        ],
    )
    def should_preserve_explicit_controls_and_absent_system(
        self, policy, controls, expected
    ):
        with scripted_http([(200, {}, success("anthropic"))]) as (host, requests):
            gateway = AnthropicGateway(
                api_key="test-key", base_url=host, recovery_policy=policy
            )

            gateway.complete(
                model="claude-test",
                messages=[LLMMessage(content="plain user")],
                **controls,
            )

        assert [json.loads(body) for _, body, _ in requests] == [
            {
                "model": "claude-test",
                "system": None,
                "messages": [{"role": "user", "content": "plain user"}],
                **expected,
            }
        ]

    @pytest.mark.parametrize(
        "policy",
        [
            None,
            RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=1,
            ),
        ],
    )
    def should_send_first_assistant_answer_in_second_chat_turn(
        self, policy, broker_factory
    ):
        first = success("anthropic").replace(
            b'"answer"', '"première réponse 🌍"'.encode()
        )
        with scripted_http([(200, {}, first), (200, {}, success("anthropic"))]) as (
            host,
            requests,
        ):
            gateway = AnthropicGateway(
                api_key="test-key", base_url=host, recovery_policy=policy
            )
            broker = broker_factory(gateway)
            session = ChatSession(broker, tokenizer_gateway=broker.tokenizer)

            first_answer = session.send("héllo 世界")
            second_answer = session.send("continue please")

        assert first_answer == "première réponse 🌍"
        assert second_answer == "answer"
        assert [json.loads(body)["messages"] for _, body, _ in requests] == [
            [{"role": "user", "content": "héllo 世界"}],
            [
                {"role": "user", "content": "héllo 世界"},
                {"role": "assistant", "content": "première réponse 🌍"},
                {"role": "user", "content": "continue please"},
            ],
        ]
