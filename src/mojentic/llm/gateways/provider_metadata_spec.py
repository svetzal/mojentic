"""Validated metadata crosses in-process HTTP and public recovery surfaces."""

import asyncio
import json
import os

import pytest

from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.cloud_recovery_spec import Result
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.ollama_recovery_spec import (
    retain_wire_evidence,
    scripted_http,
)
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.recovery import RecoveryError, RecoveryPolicy
from scripts.inprocess_http import clock, virtual_sleep


async def allow(context):
    return "allow"


REQUEST_ID = "req_12345678-1234-4234-8234-123456789abc"


def gateway_for(provider, host, policy, credential="credential-sentinel"):
    if os.environ.get("MOJENTIC_RECOVERY_EVIDENCE") == "1":
        observer = policy.wire_observer

        def capture(event):
            retain_wire_evidence([event])
            if observer is not None:
                observer(event)

        policy = policy.model_copy(update={"wire_observer": capture})
    if provider == "ollama":
        return OllamaGateway(
            host=host, recovery_policy=policy, headers={"Authorization": credential}
        )
    if provider == "omlx":
        return OMLXGateway(host=host, recovery_policy=policy, api_key=credential)
    gateway = OpenAIGateway if provider == "openai" else AnthropicGateway
    return gateway(base_url=host, api_key=credential, recovery_policy=policy)


async def invoke(gateway, operation, content="payload-sentinel"):
    args = {"model": "test", "messages": [LLMMessage(content=content)]}
    if operation == "structured":
        args["object_model"] = Result
    if operation == "streaming":
        events = [
            event async for event in gateway.complete_stream_with_recovery(**args)
        ]
        if events[-1].error is not None:
            raise events[-1].error
        return events[-1].response
    return await gateway.complete_with_recovery(**args)


PATHS = [
    (provider, operation)
    for provider in ("ollama", "omlx", "openai", "anthropic")
    for operation in ("ordinary", "structured", "streaming")
    if provider != "anthropic" or operation == "ordinary"
]


def success_body(provider, operation):
    from mojentic.llm.gateways.cloud_recovery_spec import success
    from mojentic.llm.gateways.ollama_recovery_spec import frame

    if provider == "ollama":
        return (
            frame('{"answer":"answer"}' if operation == "structured" else "answer")
            + b"\n"
        )
    return success("anthropic" if provider == "anthropic" else operation)


def in_band_error_body(provider, operation):
    body = b'{"error":{"code":"server_error"}}'
    if operation == "streaming" and provider != "ollama":
        return b"data: " + body + b"\n\n"
    return body


class DescribeProviderMetadata:
    @pytest.mark.parametrize("provider,operation", PATHS)
    def should_preserve_exact_validated_metadata_in_terminal_public_evidence(
        self, provider, operation
    ):
        lifecycle, wire = [], []
        body = b'{"error":{"code":"invalid_api_key","message":"private-response"}}'
        with scripted_http([(401, {"x-request-id": REQUEST_ID}, body)]) as (
            host,
            requests,
        ):
            gateway = gateway_for(
                provider,
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                    observer=lifecycle.append,
                    wire_observer=wire.append,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                asyncio.run(invoke(gateway, operation))

        error = caught.value
        failure = error.report.final_failure
        assert failure.provider_request_id == REQUEST_ID
        assert failure.provider_code == "invalid_api_key"
        assert error.report.history[0].provider_request_id == REQUEST_ID
        assert error.report.history[0].provider_code == "invalid_api_key"
        assert failure.http_status == 401
        assert not failure.eligible
        assert len(requests) == 1
        assert error.inspect_response() == body
        assert ("x-request-id", REQUEST_ID) in error.inspect_headers()
        assert failure.inspect_cause() is not None
        safe = (
            repr(error) + str(error) + error.report.model_dump_json() + repr(lifecycle)
        )
        assert "private-response" not in safe
        assert "credential-sentinel" not in safe
        assert "payload-sentinel" not in safe
        assert REQUEST_ID in json.dumps(
            [event.model_dump(mode="json") for event in lifecycle]
        )
        assert any(event.body == body for event in wire)

    @pytest.mark.parametrize("provider,operation", PATHS)
    def should_retain_distinct_failed_attempt_metadata_after_success(
        self, provider, operation
    ):
        ids = [REQUEST_ID, "87654321-4321-4321-8321-cba987654321"]
        codes = ["rate_limit_exceeded", "server_error"]
        body = success_body(provider, operation)
        replies = [
            (
                503,
                {"x-request-id": value},
                json.dumps({"error": {"code": code}}).encode(),
            )
            for value, code in zip(ids, codes, strict=True)
        ] + [(200, {}, body)]
        lifecycle = []
        with scripted_http(replies) as (host, requests):
            gateway = gateway_for(
                provider,
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                    admission=allow,
                    base_delay=0,
                    observer=lifecycle.append,
                ),
            )
            response = asyncio.run(invoke(gateway, operation))

        assert response.content == (
            '{"answer":"answer"}' if operation == "structured" else "answer"
        )
        assert [
            failure.provider_request_id for failure in response.recovery_report.history
        ] == ids
        assert [
            failure.provider_code for failure in response.recovery_report.history
        ] == codes
        assert [
            failure["provider_request_id"]
            for failure in response.recovery_report.model_dump(mode="json")["history"]
        ] == ids
        assert [
            event.failure.provider_request_id
            for event in lifecycle
            if event.transition == "attempt_failed"
        ] == ids
        assert [
            event.failure.provider_code
            for event in lifecycle
            if event.transition == "attempt_failed"
        ] == codes
        assert requests[0][1] == requests[1][1] == requests[2][1]

    @pytest.mark.parametrize("provider,operation", PATHS)
    @pytest.mark.parametrize(
        "source,prefix",
        [
            ("credential", ""),
            ("credential", "req_"),
            ("payload", ""),
            ("payload", "req_"),
        ],
    )
    def should_reject_uuid_shaped_outbound_echoes_but_keep_private_wire(
        self, provider, operation, source, prefix
    ):
        secret = "abcdefab-1234-4234-8234-abcdefabcdef"
        value = prefix + secret
        body = json.dumps({"error": {"code": secret, "message": secret}}).encode()
        lifecycle, wire = [], []
        credential = secret if source == "credential" else "credential-sentinel"
        content = secret if source == "payload" else "payload-sentinel"
        with scripted_http([(401, {"x-request-id": value}, body)]) as (host, requests):
            gateway = gateway_for(
                provider,
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    observer=lifecycle.append,
                    wire_observer=wire.append,
                ),
                credential,
            )
            with pytest.raises(RecoveryError) as caught:
                asyncio.run(invoke(gateway, operation, content))

        error = caught.value
        assert error.report.final_failure.provider_request_id is None
        assert error.report.final_failure.provider_code is None
        assert dict(error.inspect_headers())["x-request-id"] == value
        assert error.inspect_response() == body
        assert error.inspect_cause() is not None
        safe = str(error) + repr(error) + error.report.model_dump_json()
        safe += json.dumps(
            [event.model_dump(mode="json") for event in lifecycle]
        ) + repr(lifecycle)
        assert secret not in safe
        assert any(event.body == body for event in wire)
        assert (
            value
            in dict(
                next(event for event in wire if event.kind == "headers").headers
            ).values()
        )
        assert len(requests) == 1

    @pytest.mark.parametrize("provider,operation", PATHS)
    @pytest.mark.parametrize(
        "value,code",
        [
            ("untrusted-payload", "unrecognized"),
            ("req_not-a-uuid", {"nested": "invalid_api_key"}),
            ("123456781-234-4234-8234-123456789abc", "bad"),
            ("12345678-1234-4234-8234-123456789abc trailing", 401),
        ],
    )
    def should_omit_malformed_values(self, provider, operation, value, code):
        body = json.dumps({"error": {"code": code}}).encode()
        with (
            scripted_http([(401, {"x-request-id": value}, body)]) as (host, requests),
            pytest.raises(RecoveryError) as caught,
        ):
            asyncio.run(
                invoke(
                    gateway_for(
                        provider,
                        host,
                        RecoveryPolicy(
                            monotonic=clock,
                            wall=lambda: 0,
                            jitter=lambda ceiling: ceiling / 2,
                            sleeper=virtual_sleep,
                        ),
                    ),
                    operation,
                )
            )
        assert caught.value.report.final_failure.provider_request_id is None
        assert caught.value.report.final_failure.provider_code is None
        assert len(requests) == 1

    @pytest.mark.parametrize("provider,operation", PATHS)
    def should_keep_status_and_header_metadata_after_truncated_permanent_body(
        self, provider, operation
    ):
        body = b'{"error":{"code":"invalid_api_key"'
        with (
            scripted_http(
                [(403, {"x-request-id": REQUEST_ID, "Content-Length": "1000"}, body)]
            ) as (host, requests),
            pytest.raises(RecoveryError) as caught,
        ):
            asyncio.run(
                invoke(
                    gateway_for(
                        provider,
                        host,
                        RecoveryPolicy(
                            monotonic=clock,
                            wall=lambda: 0,
                            jitter=lambda ceiling: ceiling / 2,
                            sleeper=virtual_sleep,
                            max_attempts=3,
                            admission=allow,
                        ),
                    ),
                    operation,
                )
            )
        failure = caught.value.report.final_failure
        assert failure.provider_request_id == REQUEST_ID
        assert failure.provider_code is None
        assert failure.http_status == 403
        assert failure.reason == "permanent"
        assert not failure.eligible
        assert caught.value.inspect_response() == body
        assert len(requests) == 1

    def should_preserve_anthropic_request_id_and_error_type(self):
        body = (
            b'{"type":"error","error":{"type":"overloaded_error","message":"private"}}'
        )
        with (
            scripted_http([(529, {"request-id": REQUEST_ID}, body)]) as (
                host,
                requests,
            ),
            pytest.raises(RecoveryError) as caught,
        ):
            asyncio.run(
                invoke(
                    gateway_for(
                        "anthropic",
                        host,
                        RecoveryPolicy(
                            monotonic=clock,
                            wall=lambda: 0,
                            jitter=lambda ceiling: ceiling / 2,
                            sleeper=virtual_sleep,
                        ),
                    ),
                    "ordinary",
                )
            )
        assert caught.value.report.final_failure.provider_code == "overloaded_error"
        assert caught.value.report.final_failure.provider_request_id == REQUEST_ID
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai", "anthropic"])
    @pytest.mark.parametrize("surface", ["broker", "session"])
    def should_propagate_exact_metadata_through_public_broker_and_session(
        self, provider, surface, mocker
    ):
        from mojentic.llm.chat_session import ChatSession
        from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway
        from mojentic.llm.llm_broker import LLMBroker

        tokenizer = mocker.Mock(spec=TokenizerGateway)
        tokenizer.encode.return_value = [1]
        body = b'{"error":{"code":"invalid_api_key"}}'
        with scripted_http([(401, {"x-request-id": REQUEST_ID}, body)]) as (
            host,
            requests,
        ):
            gateway = gateway_for(
                provider,
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                ),
            )
            broker = LLMBroker(model="test", gateway=gateway, tokenizer=tokenizer)
            session = ChatSession(broker, tokenizer_gateway=tokenizer)
            with pytest.raises(RecoveryError) as caught:
                actions = {
                    "session": lambda: session.send("payload-sentinel"),
                    "broker": lambda: broker.generate_response(
                        [LLMMessage(content="payload-sentinel")]
                    ),
                }
                actions[surface]()
        assert caught.value.report.final_failure.provider_request_id == REQUEST_ID
        assert caught.value.report.final_failure.provider_code == "invalid_api_key"
        assert caught.value.report.history[0].provider_request_id == REQUEST_ID
        assert len(requests) == 1

    @pytest.mark.parametrize("source", ["payload", "credential", "basic"])
    def should_reject_recognized_error_code_echoes(self, source):
        import base64

        code = "invalid_api_key"
        credentials = {
            "payload": "credential",
            "credential": code,
            "basic": "Basic " + base64.b64encode(f"user:{code}".encode()).decode(),
        }
        body = json.dumps({"error": {"code": code}}).encode()
        lifecycle = []
        with scripted_http([(401, {"x-request-id": REQUEST_ID}, body)]) as (
            host,
            requests,
        ):
            gateway = gateway_for(
                "ollama",
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    observer=lifecycle.append,
                ),
                credentials[source],
            )
            with pytest.raises(RecoveryError) as caught:
                asyncio.run(
                    invoke(
                        gateway, "ordinary", code if source == "payload" else "payload"
                    )
                )
        failure = caught.value.report.final_failure
        assert failure.provider_request_id == REQUEST_ID
        assert failure.provider_code is None
        assert code not in caught.value.report.model_dump_json() + repr(lifecycle)
        assert caught.value.inspect_response() == body
        assert len(requests) == 1

    @pytest.mark.parametrize("prefix", ["", "req_"])
    def should_reject_ids_echoing_explicit_basic_password(self, prefix):
        import base64

        secret = "abcdefab-1234-4234-8234-abcdefabcdef"
        credential = "Basic " + base64.b64encode(f"user:{secret}".encode()).decode()
        with (
            scripted_http([(401, {"x-request-id": prefix + secret}, b"private")]) as (
                host,
                requests,
            ),
            pytest.raises(RecoveryError) as caught,
        ):
            asyncio.run(
                invoke(
                    gateway_for(
                        "ollama",
                        host,
                        RecoveryPolicy(
                            monotonic=clock,
                            wall=lambda: 0,
                            jitter=lambda ceiling: ceiling / 2,
                            sleeper=virtual_sleep,
                        ),
                        credential,
                    ),
                    "ordinary",
                )
            )
        assert caught.value.report.final_failure.provider_request_id is None
        assert secret not in caught.value.report.model_dump_json()
        assert dict(caught.value.inspect_headers())["x-request-id"] == prefix + secret
        assert len(requests) == 1

    @pytest.mark.parametrize("provider,operation", PATHS)
    def should_reject_ambiguous_header_values(self, provider, operation):
        with (
            scripted_http(
                [(401, {"x-request-id": REQUEST_ID + ", " + REQUEST_ID}, b"private")]
            ) as (host, requests),
            pytest.raises(RecoveryError) as caught,
        ):
            asyncio.run(
                invoke(
                    gateway_for(
                        provider,
                        host,
                        RecoveryPolicy(
                            monotonic=clock,
                            wall=lambda: 0,
                            jitter=lambda ceiling: ceiling / 2,
                            sleeper=virtual_sleep,
                        ),
                    ),
                    operation,
                )
            )
        assert caught.value.report.final_failure.provider_request_id is None
        assert len(requests) == 1

    @pytest.mark.parametrize("provider,operation", PATHS)
    def should_retain_metadata_from_in_band_provider_error(self, provider, operation):
        body = in_band_error_body(provider, operation)
        lifecycle = []
        with (
            scripted_http([(200, {"x-request-id": REQUEST_ID}, body)]) as (
                host,
                requests,
            ),
            pytest.raises(RecoveryError) as caught,
        ):
            asyncio.run(
                invoke(
                    gateway_for(
                        provider,
                        host,
                        RecoveryPolicy(
                            monotonic=clock,
                            wall=lambda: 0,
                            jitter=lambda ceiling: ceiling / 2,
                            sleeper=virtual_sleep,
                            observer=lifecycle.append,
                        ),
                    ),
                    operation,
                )
            )
        failure = caught.value.report.final_failure
        assert failure.provider_request_id == REQUEST_ID
        assert failure.provider_code == "server_error"
        assert lifecycle[-1].failure.provider_code == "server_error"
        assert len(requests) == 1
