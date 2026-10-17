"""Explicit native reasoning controls, independent of model names."""

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from mojentic.llm.completion_config import CompletionConfig
    from mojentic.llm.gateways.models import LLMMessage


class ReasoningEffort(str, Enum):
    """Distinct provider controls; omission imposes no default."""

    Disabled = "disabled"
    Enabled = "enabled"
    Low = "low"
    Medium = "medium"
    High = "high"
    XHigh = "xhigh"


class ReasoningProfile(BaseModel):
    """
    Caller-selected capabilities, never inferred from a model identifier.

    Attributes
    ----------
    name : str
        Caller-visible profile identifier.
    supported_efforts : tuple[ReasoningEffort, ...]
        Accepted explicit efforts. Omitted effort is always unspecified.
    supports_reasoning_history : bool
        Whether native assistant reasoning can be retained.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    supported_efforts: tuple[ReasoningEffort, ...]
    supports_reasoning_history: bool

    @classmethod
    def qwen3_8(cls) -> "ReasoningProfile":
        """
        Return the contracted Qwen3.8 capabilities without a default effort.

        Returns
        -------
        ReasoningProfile
            Disabled, Low, Medium and XHigh with native history support.
        """
        return cls(
            name="qwen3.8",
            supported_efforts=(
                ReasoningEffort.Disabled,
                ReasoningEffort.Low,
                ReasoningEffort.Medium,
                ReasoningEffort.XHigh,
            ),
            supports_reasoning_history=True,
        )

    def validate_controls(self, effort: ReasoningEffort | None, retain: bool) -> None:
        """
        Validate controls against this explicit profile.

        Parameters
        ----------
        effort : ReasoningEffort | None
            The explicit effort, or None to leave it unspecified.
        retain : bool
            Whether native assistant history is requested.

        Raises
        ------
        ValueError
            The effort or history capability is unsupported.
        """
        if effort is not None and effort not in self.supported_efforts:
            raise ValueError(
                f"Reasoning effort {effort.value} unsupported by profile {self.name}"
            )
        if retain and not self.supports_reasoning_history:
            raise ValueError(
                f"Profile {self.name} does not support native reasoning history"
            )


def reasoning_controls(
    effort: ReasoningEffort | None, provider: str, retain: bool = False
) -> dict:
    """
    Translate distinct efforts into exact provider request controls.

    Parameters
    ----------
    effort : ReasoningEffort | None
        The explicit effort. None omits the control.
    provider : str
        Either "ollama" or "omlx".
    retain : bool
        Request oMLX preservation of native assistant reasoning.

    Returns
    -------
    dict
        Exact provider controls, without an inferred default effort.
    """
    controls = {}
    if effort is not None:
        value = {ReasoningEffort.Disabled: False, ReasoningEffort.Enabled: True}.get(
            effort, effort.value
        )
        if provider == "ollama":
            controls["think"] = value
        elif effort in (ReasoningEffort.Disabled, ReasoningEffort.Enabled):
            controls["enable_thinking"] = value
        else:
            controls["reasoning_effort"] = value
    if provider == "omlx" and retain:
        controls["chat_template_kwargs"] = {"preserve_thinking": True}
    return controls


def validate_openai_reasoning(
    config: "CompletionConfig | None", messages: "list[LLMMessage] | None"
) -> None:
    """
    Reject native history and new controls unsupported by the OpenAI gateway.

    Parameters
    ----------
    config : CompletionConfig | None
        Explicit request controls, when supplied.
    messages : list[LLMMessage] | None
        History to inspect for unsupported native assistant reasoning.

    Raises
    ------
    ValueError
        New controls, explicit profiles or native reasoning history are present.
    """
    if config is not None and (
        config.retain_reasoning
        or config.reasoning_profile is not None
        or config.reasoning_effort
        in (ReasoningEffort.Disabled, ReasoningEffort.Enabled, ReasoningEffort.XHigh)
    ):
        raise ValueError(
            "OpenAI gateway does not support native reasoning controls or profiles"
        )
    if any(message.thinking is not None for message in messages or []):
        raise ValueError("OpenAI gateway does not support native reasoning history")
