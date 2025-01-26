from enum import Enum
from typing import List

from pydantic import BaseModel

from mojentic.llm.gateways.llm_gateway import LLMGateway


class LLMSize(str, Enum):
    tiny = 'tiny'
    small = "small"
    medium = 'medium'
    large = 'large'
    giant = 'giant'


class LLMCapability(str, Enum):
    tool_use = "tool_use"
    structured_output = "structured_output"


class LLMType(str, Enum):
    instruct = 'instruct'
    chat = 'chat'


class LLMCapabilities(BaseModel):
    size: LLMSize
    type: LLMType
    capabilities: List[LLMCapability]

    def supports(self, capability: LLMCapability) -> bool:
        return capability in self.capabilities

    @property
    def supports_tools(self) -> bool:
        return self.supports(LLMCapability.tool_use)

    @property
    def supports_structured_output(self) -> bool:
        return self.supports(LLMCapability.structured_output)


class LLMRegistryEntry:
    def __init__(self, name: str, capabilities: LLMCapabilities, adapter: LLMGateway):
        self.name = name
        self.capabilities = capabilities
        self.adapter = adapter


class LLMRegistry:
    def __init__(self):
        self.llms = []

    def register(self, entry: LLMRegistryEntry):
        self.llms.append(entry)

    def find_first(self, size: LLMSize, type: LLMType, capabiilties: List[LLMCapability]) -> LLMRegistryEntry:
        return next((llm for llm in self.llms \
                     if llm.capabilities.size == size \
                         and llm.capabilities.type == type \
                         and all([llm.capabilities.supports(capability) for capability in capabiilties])), None)
