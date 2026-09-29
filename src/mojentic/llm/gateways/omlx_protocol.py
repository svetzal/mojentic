"""
Pure request and response mapping for the oMLX gateway.

oMLX speaks the OpenAI chat completions protocol. These functions build request bodies
with no per-model adaptation and map responses exactly as the server reports them, so the
gateway itself only moves bytes.
"""
import json
from typing import Dict, List, Mapping, Optional, Type, TYPE_CHECKING

import httpx
from pydantic import BaseModel, ConfigDict

from mojentic.llm.gateways.models import LLMGatewayResponse, LLMMessage, LLMToolCall
from mojentic.llm.gateways.openai import openai_response_format
from mojentic.llm.gateways.openai_messages_adapter import adapt_messages_to_openai
from mojentic.llm.tools.llm_tool import LLMTool

if TYPE_CHECKING:
    from mojentic.llm.completion_config import CompletionConfig

DEFAULT_HOST = "http://localhost:8000"
"""The oMLX host when neither ``host`` nor ``OMLX_HOST`` is set."""

DEFAULT_TIMEOUT = 600.0
"""Request timeout in seconds (10 minutes) when neither ``timeout`` nor ``OMLX_TIMEOUT`` is set."""

STRUCTURED_RESPONSE_FORMATS = {"json_object", "json_schema"}


class OMLXSettings(BaseModel):
    """
    Resolved connection settings for an oMLX server.

    Attributes
    ----------
    base_url : str
        The host with ``/v1`` appended.
    headers : Dict[str, str]
        Headers sent with every request: a bearer ``Authorization`` header when a key is set, otherwise none.
    timeout : float
        The timeout in seconds for every request, including model load.
    """
    model_config = ConfigDict(frozen=True)

    base_url: str
    headers: Dict[str, str]
    timeout: float


def omlx_settings(host: Optional[str] = None, api_key: Optional[str] = None, timeout: Optional[float] = None,
                  environ: Optional[Mapping[str, str]] = None) -> OMLXSettings:
    """
    Resolve oMLX settings: an explicit value, then the environment, then the default.

    Parameters
    ----------
    host : Optional[str]
        The server host without ``/v1``. Falls back to ``OMLX_HOST``, then ``http://localhost:8000``.
    api_key : Optional[str]
        The API key. Falls back to ``OMLX_API_KEY``. An empty key counts as no key.
    timeout : Optional[float]
        The timeout in seconds for every request, including model load. Falls back to
        ``OMLX_TIMEOUT``, which is in milliseconds, then 600 seconds.
    environ : Optional[Mapping[str, str]]
        The environment to read. None reads nothing.

    Returns
    -------
    OMLXSettings
        The resolved settings.
    """
    environ = environ or {}
    host = host or environ.get("OMLX_HOST") or DEFAULT_HOST
    api_key = api_key or environ.get("OMLX_API_KEY")
    if timeout is None:
        timeout = float(environ["OMLX_TIMEOUT"]) / 1000 if environ.get("OMLX_TIMEOUT") else DEFAULT_TIMEOUT
    return OMLXSettings(
        base_url=f"{host.rstrip('/')}/v1",
        headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        timeout=timeout,
    )


def omlx_chat_body(model: str, messages: List[LLMMessage], config: 'CompletionConfig',
                   tools: Optional[List[LLMTool]] = None,
                   object_model: Optional[Type[BaseModel]] = None) -> dict:
    """
    Build a chat completions request body with no per-model adaptation.

    ``num_ctx`` and ``num_predict`` are not sent, because oMLX sets context length per model.
    ``reasoning_effort`` goes to the model's chat template unchanged.

    Parameters
    ----------
    model : str
        The model id, as ``GET /v1/models`` reports it.
    messages : List[LLMMessage]
        The conversation, adapted with the OpenAI message adapter.
    config : CompletionConfig
        Temperature, token limit, reasoning effort and response format.
    tools : Optional[List[LLMTool]]
        Tools to offer, sent as the OpenAI gateway sends them.
    object_model : Optional[Type[BaseModel]]
        When set, request JSON schema output with this model's schema. It overrides
        ``config.response_format``.

    Returns
    -------
    dict
        The request body, without the ``stream`` flag.
    """
    body = {
        "model": model,
        "messages": adapt_messages_to_openai(messages),
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    if config.reasoning_effort is not None:
        body["reasoning_effort"] = config.reasoning_effort
    response_format = _response_format(config, object_model)
    if response_format is not None:
        body["response_format"] = response_format
    if tools is not None:
        body["tools"] = [tool.descriptor for tool in tools]
    return body


def _response_format(config: 'CompletionConfig', object_model: Optional[Type[BaseModel]]) -> Optional[dict]:
    if object_model is not None:
        return {"type": "json_schema", "json_schema": {"name": "response", "schema": object_model.model_json_schema()}}
    return openai_response_format(config.response_format)


def requests_structured_output(body: dict) -> bool:
    """Return True when ``body`` asks for JSON object or JSON schema output."""
    return body.get("response_format", {}).get("type") in STRUCTURED_RESPONSE_FORMATS


def omlx_gateway_response(payload: dict, response_format_warning: Optional[str] = None) -> LLMGatewayResponse:
    """
    Map a chat completions response to a gateway response, exactly as reported.

    ``reasoning_content`` becomes ``thinking``. Text is never moved between ``content`` and
    ``thinking``: when a token limit ends generation during thinking, oMLX puts the partial
    reasoning in ``content`` with a ``length`` finish reason, and so does this response.

    Parameters
    ----------
    payload : dict
        The decoded response body.
    response_format_warning : Optional[str]
        The ``Warning`` header of a structured output request, recorded in metadata.

    Returns
    -------
    LLMGatewayResponse
        Content, thinking, tool calls, usage, provider model, finish reason and metadata.
    """
    choice = payload["choices"][0]
    message = choice["message"]
    return LLMGatewayResponse(
        content=message.get("content"),
        thinking=message.get("reasoning_content"),
        tool_calls=[_tool_call(call) for call in message.get("tool_calls") or []],
        usage=payload.get("usage"),
        model=payload.get("model"),
        finish_reason=choice.get("finish_reason"),
        metadata={"response_format_warning": response_format_warning} if response_format_warning is not None else {},
    )


def _tool_call(call: dict) -> LLMToolCall:
    function = call["function"]
    return LLMToolCall(id=call.get("id"), name=function["name"], arguments=json.loads(function["arguments"]))


def omlx_error_detail(response: httpx.Response) -> dict:
    """
    Describe an oMLX error response as a provider error detail.

    Parameters
    ----------
    response : httpx.Response
        A non-2xx response whose body has been read.

    Returns
    -------
    dict
        ``status_code`` and ``error``: the body's ``error`` object, the whole JSON body when
        it has none, or the raw text when the body is not JSON.
    """
    try:
        body = response.json()
    except ValueError:
        body = response.text
    error = body.get("error", body) if isinstance(body, dict) else body
    return {"status_code": response.status_code, "error": error}
