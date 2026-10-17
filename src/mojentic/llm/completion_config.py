from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mojentic.llm.reasoning import ReasoningEffort, ReasoningProfile


class ResponseFormat(BaseModel):
    """
    The output format requested from the provider.

    This records what was requested. It is not proof that the provider enforced it,
    so callers must still validate the returned content.

    Attributes
    ----------
    type : Literal["text", "json_object"]
        ``"text"`` requests plain text. ``"json_object"`` requests JSON object mode,
        or JSON schema mode when ``json_schema`` is set.
    json_schema : Optional[Dict[str, Any]]
        The JSON schema the response must follow. Only valid with ``"json_object"``.
    """

    type: Literal["text", "json_object"] = Field(description="Requested output format")
    json_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON schema for schema mode; only valid with type 'json_object'",
    )

    @model_validator(mode="after")
    def _schema_requires_json_object(self) -> "ResponseFormat":
        if self.json_schema is not None and self.type != "json_object":
            raise ValueError("json_schema is only valid when type is 'json_object'")
        return self


class CompletionConfig(BaseModel):
    """
    Configuration object for LLM completion requests.

    This model provides a unified way to configure LLM behavior across different
    providers and models. It replaces loose kwargs with a structured configuration
    object.

    Attributes
    ----------
    temperature : float | None
        Controls randomness in the output. Higher values (e.g., 1.5) make output
        more random, while lower values (e.g., 0.1) make it more deterministic.
        Unspecified by default.
    num_ctx : int | None
        The number of context tokens to use. This sets the context window size.
        Unspecified by default.
    max_tokens : int | None
        The maximum number of tokens to generate in the response.
        Unspecified by default.
    top_p : float | None
        Optional nucleus sampling probability.
    top_k : int | None
        Optional candidate count (not sent by OpenAI).
    reasoning_effort : ReasoningEffort | None
        Disabled, Enabled, Low, Medium, High or XHigh. None leaves effort unspecified.
        Ollama sends exact booleans/levels; oMLX sends enable_thinking or reasoning_effort.
        OpenAI retains legacy Low/Medium/High behavior and rejects new controls.
    reasoning_profile : ReasoningProfile | None
        Explicit caller-selected capabilities. Unsupported efforts/history raise ValueError
        during configuration validation. Model names never select a profile.
    retain_reasoning : bool
        Opt in to completed native assistant reasoning in broker tool history. Default False.
        oMLX also requests chat_template_kwargs.preserve_thinking; server settings may override it.
    max_tool_iterations : int
        Maximum number of tool-call recursion steps allowed before raising
        MaxToolIterationsExceededError. Defaults to 10.
    response_format : Optional[ResponseFormat]
        The output format to request from the provider. Defaults to None, which leaves
        the request unchanged and uses the provider default.
    """

    temperature: float | None = Field(
        default=None, description="Temperature for sampling"
    )
    num_ctx: int | None = Field(default=None, description="Number of context tokens")
    max_tokens: int | None = Field(
        default=None, description="Maximum tokens to generate"
    )
    top_p: float | None = Field(
        default=None, description="Nucleus sampling probability"
    )
    top_k: int | None = Field(default=None, description="Top-k sampling candidates")
    reasoning_effort: ReasoningEffort | None = Field(
        default=None, description="Reasoning effort level for extended thinking"
    )
    max_tool_iterations: int | None = Field(
        default=10,
        description="Maximum number of tool-call recursion steps allowed; None means unlimited",
    )
    response_format: ResponseFormat | None = Field(
        default=None,
        description="Requested output format; None leaves the provider default",
    )

    reasoning_profile: ReasoningProfile | None = None
    retain_reasoning: bool = False

    @model_validator(mode="after")
    def _validate_reasoning(self) -> "CompletionConfig":
        if self.reasoning_profile is not None:
            self.reasoning_profile.validate_controls(
                self.reasoning_effort, self.retain_reasoning
            )
        return self
