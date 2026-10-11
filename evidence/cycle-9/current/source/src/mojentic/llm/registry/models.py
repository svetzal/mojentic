from enum import Enum

from pydantic import BaseModel, Field


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    MULTIMODAL = "multimodal"
    VIDEO = "video"
    # You can add more as needed


class Quantization(str, Enum):
    BIT4 = "4-bit"
    BIT8 = "8-bit"
    BIT16 = "16-bit"
    BIT32 = "32-bit"
    FP16 = "fp16"
    # etc...


class ModelInfo(BaseModel):
    """
    A Pydantic model capturing metadata for a given AI model.
    """

    name: str
    vendor: str
    foundation_model: str | None = Field(
        default=None, description="Base or family, e.g., LLaMA, GPT-3.5, Qwen..."
    )
    parameter_count: str | None = Field(
        default=None,
        description="Parameter size like '7B', '70B', or 'N/A' if unknown.",
    )
    quantization: Quantization | None = Field(
        default=None, description="Quantization level, e.g. 4-bit, 8-bit, 16-bit..."
    )
    # Instead of a free-form string list, we now use a list of Modality enum members
    modalities: list[Modality] = Field(
        default_factory=list,
        description="Modalities the model handles, e.g. [Modality.TEXT, Modality.IMAGE].",
    )
    # You could also use an enum for capabilities if you have a known set.
    # For illustration, we'll keep it free-form for now.
    capabilities: list[str] = Field(
        default_factory=list,
        description="Functions the model supports, e.g. ['text-gen', 'embeddings']. Could also be enumerated.",
    )
    is_local: bool = Field(default=False, description="Whether the model runs locally.")
    is_open_source: bool = Field(
        default=False, description="Whether the model is open source."
    )
    can_be_fine_tuned: bool = Field(
        default=False, description="Whether the model can be fine-tuned by end users."
    )
    notes: str | None = Field(
        default=None, description="Additional commentary about the model."
    )
