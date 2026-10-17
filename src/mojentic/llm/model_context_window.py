"""Provider-advertised context metadata; never applied to completion requests."""

import re

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from mojentic.llm.completion_config import CompletionConfig


class ModelMetadataError(ValueError):
    """The provider returned malformed model metadata."""


class ModelContextWindow(BaseModel):
    """An advertised positive window, its source field and optional model default."""

    model_config = ConfigDict(frozen=True)

    max_context_tokens: StrictInt = Field(gt=0)
    field: str
    model_num_ctx: StrictInt | None = Field(default=None, gt=0)


def effective_context_window(
    window_result: ModelContextWindow | None, config: CompletionConfig | None = None
) -> int | None:
    """Return the advertised upper bound clamped by caller or model context size.

    Parameters
    ----------
    window_result : ModelContextWindow | None
        Discovered metadata. Unknown metadata always yields None.
    config : CompletionConfig | None
        Explicit num_ctx takes precedence over the model's default.

    Returns
    -------
    int | None
        Effective upper bound; server environment defaults remain unknown.
    """
    if window_result is None:
        return None
    requested = config.num_ctx if config is not None else None
    selected = requested if requested is not None else window_result.model_num_ctx
    return (
        min(window_result.max_context_tokens, selected)
        if selected is not None
        else window_result.max_context_tokens
    )


def _object(value: object) -> dict:
    if not isinstance(value, dict):
        raise ModelMetadataError("Model metadata must be an object")
    return value


def omlx_context_window(body: object, model: str) -> ModelContextWindow | None:
    """Parse exact oMLX model metadata, raising ValueError for malformed data."""
    data = _object(body).get("data")
    if not isinstance(data, list):
        raise ModelMetadataError("Model metadata data must be a list")
    entries = [_object(entry) for entry in data]
    if any(not isinstance(entry.get("id"), str) for entry in entries):
        raise ModelMetadataError("Model metadata entries require string IDs")
    for entry in entries:
        if entry["id"] == model:
            if "max_model_len" not in entry:
                return None
            return ModelContextWindow(
                max_context_tokens=entry["max_model_len"], field="max_model_len"
            )
    return None


def _model_num_ctx(parameters: object) -> int | None:
    if not isinstance(parameters, str):
        raise ModelMetadataError("Model parameters must be text")
    for line in parameters.splitlines():
        parts = line.split()
        if parts and parts[0] == "num_ctx":
            if (
                len(parts) != 2
                or re.fullmatch(r"[+-]?[0-9]+", parts[1]) is None
                or int(parts[1]) <= 0
            ):
                raise ModelMetadataError("Model num_ctx must be a positive integer")
            return int(parts[1])
    return None


def ollama_context_window(body: object) -> ModelContextWindow | None:
    """Parse architecture-independent Ollama metadata, rejecting malformed values."""
    data = _object(body)
    info_value = data.get("model_info")
    info = {} if info_value is None else _object(info_value)
    parameters = data.get("parameters")
    model_num_ctx = _model_num_ctx("" if parameters is None else parameters)
    for key, value in sorted(info.items()):
        if key.endswith(".context_length"):
            return ModelContextWindow(
                max_context_tokens=value,
                field=f"model_info.{key}",
                model_num_ctx=model_num_ctx,
            )
    return None
