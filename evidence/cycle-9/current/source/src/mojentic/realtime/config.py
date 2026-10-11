"""
Configuration for the realtime voice subsystem.

Mirrors the slice of OpenAI's Realtime session config that ports cleanly
to other Mojentic implementations. Provider-specific knobs live in
``provider_extras``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mojentic.llm.tools.llm_tool import LLMTool

RealtimeVoice = str
"""Voice id rendered by the assistant (``alloy``, ``verse``, etc.). Accepts
arbitrary strings so new voices land without a library update."""

RealtimeModality = Literal["audio", "text"]

RealtimeAudioFormat = Literal["pcm16", "g711_ulaw", "g711_alaw"]

InterruptOutputPolicy = Literal["drop", "submit", "submit-completed-only"]


class ServerVadConfig(BaseModel):
    """
    Tunable parameters for server-side voice-activity detection.

    Bump ``threshold`` up (e.g. 0.7–0.9) to make the VAD less sensitive to
    background noise. Set ``interrupt_response=False`` to disable barge-in
    entirely so the assistant's reply can't be cancelled mid-sentence by a
    cough or keyboard click.
    """

    type: Literal["server_vad"] = "server_vad"
    threshold: float | None = None
    """Activation threshold (0.0–1.0). Lower fires on quieter speech."""

    prefix_padding_ms: int | None = None
    """Padding (ms) added to the start of a detected utterance."""

    silence_duration_ms: int | None = None
    """Silence (ms) before declaring the user is done speaking."""

    create_response: bool | None = None
    """Whether VAD should auto-fire a ``response.create`` after the user stops."""

    interrupt_response: bool | None = None
    """Whether speech mid-response cancels the assistant. Default True."""

    idle_timeout_ms: int | None = None
    """Max silence (ms) before the server idles the session."""


class SemanticVadConfig(BaseModel):
    """
    LLM-classifier-driven VAD. More robust than energy-threshold VAD in
    noisy environments.
    """

    type: Literal["semantic_vad"] = "semantic_vad"
    eagerness: Literal["low", "medium", "high", "auto"] | None = None
    create_response: bool | None = None
    interrupt_response: bool | None = None


TurnDetectionMode = (
    Literal["server_vad", "semantic_vad", "none"] | ServerVadConfig | SemanticVadConfig
)
"""Turn-detection strategy.

- ``"server_vad"`` — energy-threshold VAD; natural phone-call mode.
- ``"semantic_vad"`` — LLM-classifier VAD; better for noisy environments.
- ``"none"`` — client decides; useful for push-to-talk and tests.
- A :class:`ServerVadConfig` or :class:`SemanticVadConfig` to tune.
"""


class RealtimeToolChoiceFunction(BaseModel):
    """Force a specific tool to be invoked."""

    name: str


RealtimeToolChoice = Literal["auto", "none", "required"] | RealtimeToolChoiceFunction


class InputAudioTranscriptionConfig(BaseModel):
    """Whisper transcription config for user audio."""

    model: Literal["whisper-1"] = "whisper-1"


class RealtimeVoiceConfig(BaseModel):
    """
    Vendor-neutral configuration for a realtime voice session.

    The library forwards a curated subset to the active gateway and
    translates vendor-specific shapes at the boundary.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    instructions: str | None = None
    """System-level instructions injected into every assistant turn."""

    voice: RealtimeVoice | None = None
    """Voice id to render assistant audio with."""

    modalities: list[RealtimeModality] | None = None
    """Active modalities. Default ``['audio', 'text']``."""

    input_audio_format: RealtimeAudioFormat | None = None
    """Encoding of audio frames the client sends. Default ``pcm16``."""

    output_audio_format: RealtimeAudioFormat | None = None
    """Encoding of audio frames the server returns. Default ``pcm16``."""

    turn_detection: TurnDetectionMode | None = None
    """Turn-detection strategy. Default ``server_vad``."""

    input_audio_transcription: InputAudioTranscriptionConfig | Literal[False] | None = (
        None
    )
    """Whisper transcription config for user audio. Pass ``False`` to disable."""

    tools: list[LLMTool] | None = None
    """Tools available to the model in this session."""

    tool_choice: RealtimeToolChoice | None = None
    """Tool-selection strategy. Default ``auto``."""

    temperature: float | None = None

    max_response_output_tokens: int | None = None

    on_interrupt: InterruptOutputPolicy | None = None
    """How to treat tool outputs from interrupted/cancelled responses."""

    provider_extras: dict[str, Any] | None = Field(default=None)
    """Provider-specific escape hatch — passed through verbatim to the gateway."""


class _DefaultsModel(BaseModel):
    """Defaults applied when a field is omitted. Surfaced for inspection."""

    modalities: list[RealtimeModality]
    input_audio_format: RealtimeAudioFormat
    output_audio_format: RealtimeAudioFormat
    turn_detection: TurnDetectionMode
    tool_choice: RealtimeToolChoice
    on_interrupt: InterruptOutputPolicy


REALTIME_DEFAULTS = _DefaultsModel(
    modalities=["audio", "text"],
    input_audio_format="pcm16",
    output_audio_format="pcm16",
    turn_detection="server_vad",
    tool_choice="auto",
    on_interrupt="drop",
)
