"""Owned cloud HTTP recovery; SDK retry layers are outside these operations."""

import json
from collections.abc import AsyncIterator, Iterator
from contextlib import closing
from typing import TYPE_CHECKING

import httpx

from mojentic.llm.gateways.models import LLMGatewayResponse
from mojentic.llm.gateways.ollama import StreamingResponse
from mojentic.llm.recovery import (
    RecoveryCall,
    RecoveryPolicyError,
    Timeout,
    _Recovery,
    preparation_error,
)
from mojentic.llm.recovery_stream import (
    RecoveryStreamEvent,
    recover_stream,
    synchronous_stream,
)

if TYPE_CHECKING:
    from mojentic.llm.gateways.anthropic import AnthropicGateway
    from mojentic.llm.gateways.openai import OpenAIGateway


def freeze_request(payload: dict) -> bytes:
    """Freeze one literal UTF-8 payload before dispatch or caller admission."""
    return json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def active_timeout(timeout: Timeout) -> httpx.Timeout:
    """Preserve connect/write/pool controls while allowing an active generation to finish."""
    values = (
        timeout.as_dict()
        if hasattr(timeout, "as_dict")
        else httpx.Timeout(timeout).as_dict()
    )
    return httpx.Timeout(**(values | {"read": None}))


async def complete(
    gateway: "OpenAIGateway | AnthropicGateway", call: RecoveryCall | None, args: dict
) -> LLMGatewayResponse:
    """Run one ordinary or structured cloud completion over owned HTTP."""
    if gateway.recovery_policy is None:
        raise RecoveryPolicyError("configure recovery_policy before using recovery")
    operation = "structured" if args.get("object_model") is not None else "ordinary"
    try:
        body = gateway._recovery_body(args, False)
    except (ValueError, TypeError, KeyError, OSError, NotImplementedError) as cause:
        raise preparation_error(cause, operation, gateway._recovery_provider) from None
    engine = _Recovery(
        gateway.recovery_policy,
        call or gateway.recovery_call or RecoveryCall(),
        operation,
    )
    engine.provider = gateway._recovery_provider
    result, report = await engine.run(
        gateway._recovery_url,
        body,
        gateway._recovery_headers(),
        active_timeout(gateway.client.timeout),
        lambda frame: gateway._decode_recovery(frame, args.get("object_model")),
    )
    result.recovery_report = report
    result.metadata |= {"recovery": report.model_dump(mode="json")}
    return result


async def stream(
    gateway: "OpenAIGateway", call: RecoveryCall | None, args: dict
) -> AsyncIterator[RecoveryStreamEvent]:
    """Own streaming resources through cancellation, capture and consumer closure."""
    from mojentic.llm.gateways.openai_recovery import OpenAIStreamRecovery

    if gateway.recovery_policy is None:
        raise RecoveryPolicyError("configure recovery_policy before using recovery")
    try:
        body = gateway._recovery_body(args, True)
    except (ValueError, TypeError, KeyError, OSError, NotImplementedError) as cause:
        error = preparation_error(cause, "streaming", gateway._recovery_provider)
        yield RecoveryStreamEvent(
            kind="failed",
            identity=error.report.identity,
            progress=error.report.progress,
            report=error.report,
            error=error,
            outcome="ineligible",
        )
        return
    events = recover_stream(
        gateway._recovery_url,
        body,
        gateway._recovery_headers(),
        active_timeout(gateway.client.timeout),
        gateway._decode_recovery,
        gateway.recovery_policy,
        call or gateway.recovery_call or RecoveryCall(),
        _engine_type=OpenAIStreamRecovery,
    )
    try:
        async for event in events:
            yield event
    finally:
        await events.aclose()


def legacy_chunks(gateway: "OpenAIGateway", args: dict) -> Iterator[StreamingResponse]:
    """Adapt recovery events to the existing synchronous streaming contract."""
    events = synchronous_stream(gateway.complete_stream_with_recovery(**args))
    with closing(events):
        for event in events:
            if event.kind == "failed":
                raise event.error
            if event.kind == "content":
                yield StreamingResponse(content=event.text)
            elif event.kind == "reasoning":
                yield StreamingResponse(thinking=event.text)
            elif event.kind == "completed" and event.response.tool_calls:
                yield StreamingResponse(tool_calls=event.response.tool_calls)
