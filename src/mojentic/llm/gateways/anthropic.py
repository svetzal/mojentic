import asyncio

import structlog
from anthropic import Anthropic, transform_schema
from pydantic import BaseModel

from mojentic.llm.gateways import cloud_recovery
from mojentic.llm.gateways.anthropic_messages_adapter import adapt_messages_to_anthropic
from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMGatewayResponse, LLMToolCall, MessageRole
from mojentic.llm.gateways.recovery_capabilities import completion_capabilities
from mojentic.llm.recovery import (
    Capabilities,
    LengthTerminationError,
    RecoveryCall,
    RecoveryPolicy,
)

logger = structlog.get_logger()


class AnthropicGateway(LLMGateway):
    """Anthropic completion with optional owned HTTP recovery.

    Parameters
    ----------
    api_key : str
        Anthropic API key.
    base_url : str, optional
        Service root; defaults to the SDK's configured endpoint.
    recovery_policy : RecoveryPolicy, optional
        Opt in for ordinary and structured completion. Streaming and tools remain
        unsupported. Recovery bypasses SDK retries and redirects.
    recovery_call : RecoveryCall, optional
        Cancellation for a synchronous operation. Use a fresh call per operation.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        recovery_policy: RecoveryPolicy | None = None,
        recovery_call: RecoveryCall | None = None,
    ):
        self.client = Anthropic(
            api_key=api_key, **({"base_url": base_url} if base_url else {})
        )
        self.recovery_policy = (
            RecoveryPolicy.model_validate(recovery_policy)
            if recovery_policy is not None
            else None
        )
        self.recovery_call = recovery_call

    _recovery_provider = "anthropic"

    @property
    def _recovery_url(self) -> str:
        return str(self.client.base_url).rstrip("/") + "/v1/messages"

    def _recovery_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.client.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
        }

    def recovery_capabilities(self) -> Capabilities:
        """Report ordinary and structured recovery; streaming and tools remain unsupported."""
        return completion_capabilities("anthropic")

    def _recovery_body(self, args: dict, streaming: bool) -> bytes:
        if streaming or args.get("tools"):
            raise NotImplementedError(
                "Anthropic recovery does not support streaming or tools"
            )
        config = args.get("config")
        if config and config.response_format and config.response_format.type != "text":
            raise NotImplementedError(
                "Anthropic recovery does not support JSON output formats"
            )
        messages = args["messages"]
        system = [m for m in messages if m.role == MessageRole.System]
        history = [
            m for m in messages if m.role in {MessageRole.User, MessageRole.Assistant}
        ]
        payload = {
            "model": args["model"],
            "system": " ".join(m.content for m in system) if system else None,
            "messages": adapt_messages_to_anthropic(history),
            "temperature": config.temperature
            if config
            else args.get("temperature", 1.0),
            "max_tokens": config.max_tokens
            if config
            else args.get("max_tokens", args.get("num_predict", 2000)),
        }
        if args.get("object_model") is not None:
            payload["output_config"] = {
                "format": {
                    "type": "json_schema",
                    "schema": transform_schema(args["object_model"]),
                }
            }
        return cloud_recovery.freeze_request(payload)

    @staticmethod
    def _decode_recovery(
        frame: object, object_model: type[BaseModel] | None = None
    ) -> LLMGatewayResponse:
        from anthropic.types import Message

        response = Message.model_validate(frame)
        if object_model is not None and response.stop_reason == "max_tokens":
            raise LengthTerminationError("completion length limit reached")
        if not response.content or response.content[0].type != "text":
            raise ValueError("expected ordinary text completion")
        return LLMGatewayResponse(
            content=response.content[0].text,
            object=object_model.model_validate_json(response.content[0].text)
            if object_model is not None
            else None,
            usage=response.usage.model_dump(),
            model=response.model,
            finish_reason=response.stop_reason,
        )

    async def complete_with_recovery(
        self, call: RecoveryCall | None = None, **args
    ) -> LLMGatewayResponse:
        """Recover ordinary or Pydantic completion; reject streaming and tools before dispatch.

        Parameters
        ----------
        call : RecoveryCall, optional
            Cancellation for this operation, overriding the gateway call.
        **args
            Model, messages and controls accepted by ``complete``.

        Returns
        -------
        LLMGatewayResponse
            Provider text, validated object and telemetry with a typed recovery report.

        Raises
        ------
        RecoveryError
            Request failed or was cancelled; unsupported tool requests retain
            an original ``NotImplementedError`` through private cause inspection.
        ValueError
            No recovery policy is configured.
        """
        return await cloud_recovery.complete(self, call, args)

    def complete(self, **args) -> LLMGatewayResponse:

        if self.recovery_policy is not None:
            return asyncio.run(self.complete_with_recovery(**args))

        messages = args.get("messages")
        config = args.get("config", None)

        # Extract temperature and max_tokens from config if provided
        if config:
            temperature = config.temperature
            max_tokens = config.max_tokens
            # Note: reasoning_effort not supported by Anthropic yet
            if config.reasoning_effort is not None:
                logger.warning(
                    "Anthropic gateway does not yet support reasoning_effort parameter",
                    reasoning_effort=config.reasoning_effort,
                )
        else:
            temperature = args.get("temperature", 1.0)
            max_tokens = args.get("max_tokens", args.get("num_predict", 2000))

        system_messages = [m for m in messages if m.role == MessageRole.System]
        history = [
            m for m in messages if m.role in {MessageRole.User, MessageRole.Assistant}
        ]

        anthropic_args = {
            "model": args["model"],
            "system": " ".join([m.content for m in system_messages])
            if system_messages
            else None,
            "messages": adapt_messages_to_anthropic(history),
        }

        response = self.client.messages.create(
            **anthropic_args,
            # SDK 1.15 removed the keyword; retain the existing wire control.
            extra_body={"temperature": temperature},
            max_tokens=max_tokens,
            # thinking={
            #     "type": "enabled",
            #     "budget_tokens": 32768,
            # }
        )

        object = None
        tool_calls: list[LLMToolCall] = []

        return LLMGatewayResponse(
            content=response.content[0].text,
            object=object,
            tool_calls=tool_calls,
            usage=response.usage.model_dump() if response.usage is not None else None,
            model=response.model,
            finish_reason=response.stop_reason,
        )

    def get_available_models(self) -> list[str]:
        return sorted([m.id for m in self.client.models.list()])

    def calculate_embeddings(
        self, text: str, model: str = "voyage-3-large"
    ) -> list[float]:
        raise NotImplementedError(
            "The Anthropic API does not support embedding generation."
        )
