"""
Mojentic is an agentic framework that aims to provide a simple and flexible way to assemble teams of agents to solve
complex problems. Design goals are to be asynchronous with a pubsub messaging architecture.
"""
import importlib.metadata as _importlib_metadata

from mojentic.base_llm_agent import BaseLLMAgent

__version__: str
try:
    __version__ = _importlib_metadata.version(__name__)
except _importlib_metadata.PackageNotFoundError:
    __version__ = "unknown"
