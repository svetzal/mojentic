import re
from enum import Enum

from pydantic import BaseModel

from mojentic.llm.gateways.llm_gateway import LLMGateway


class LLMSize(str, Enum):
    tiny = "tiny"
    small = "small"
    medium = "medium"
    large = "large"
    giant = "giant"


class LLMType(str, Enum):
    instruct = "instruct"
    chat = "chat"


class LLMCharacteristics(BaseModel):
    model: str
    quantization_level: str
    parameter_size: str
    family: str
    tools: bool
    structured_output: bool
    embeddings: bool

    @property
    def parameter_size_float(self):
        size = re.sub(r"[a-zA-Z]", "", self.parameter_size)
        return float(size) / 1000 if self.parameter_size.endswith("M") else float(size)


class LLMRegistryEntry:
    def __init__(
        self, name: str, characteristics: LLMCharacteristics, adapter: LLMGateway
    ):
        self.name = name
        self.characteristics = characteristics
        self.adapter = adapter


class LLMRegistry:
    def __init__(self):
        self.llms = []

    def register(self, entry: LLMRegistryEntry):
        self.llms.append(entry)

    def find_first(
        self, tools: bool, structured_output: bool
    ) -> LLMRegistryEntry | None:
        return next(
            (
                llm
                for llm in self.llms
                if llm.characteristics.tools == tools
                and llm.characteristics.structured_output == structured_output
            ),
            None,
        )

    def find_fastest(
        self, tools: bool | None = None, structured_output: bool | None = None
    ) -> LLMRegistryEntry | None:
        return self._find_by_criteria(tools, structured_output, reverse=False)

    def find_smartest(
        self, tools: bool | None = None, structured_output: bool | None = None
    ) -> LLMRegistryEntry | None:
        return self._find_by_criteria(tools, structured_output, reverse=True)

    def _find_by_criteria(
        self, tools: bool | None, structured_output: bool | None, reverse: bool
    ) -> LLMRegistryEntry | None:
        filtered = sorted(
            self.llms,
            key=lambda x: x.characteristics.parameter_size_float,
            reverse=reverse,
        )
        filtered = [llm for llm in filtered if not llm.characteristics.embeddings]
        if tools is not None:
            filtered = [llm for llm in filtered if llm.characteristics.tools == tools]
        if structured_output is not None:
            filtered = [
                llm
                for llm in filtered
                if llm.characteristics.structured_output == structured_output
            ]
        return filtered[0] if filtered else None
