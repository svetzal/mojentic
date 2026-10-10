"""
Mojentic agents module for creating and working with various agent types.
"""

# Base agent types
# Event adapters
from mojentic.agents.agent_event_adapter import AgentEventAdapter
from mojentic.agents.async_aggregator_agent import AsyncAggregatorAgent
from mojentic.agents.async_llm_agent import (
    BaseAsyncLLMAgent,
    BaseAsyncLLMAgentWithMemory,
)
from mojentic.agents.base_agent import BaseAgent
from mojentic.agents.base_async_agent import BaseAsyncAgent
from mojentic.agents.base_llm_agent import BaseLLMAgent

# Special purpose agents
from mojentic.agents.iterative_problem_solver import IterativeProblemSolver
from mojentic.agents.output_agent import OutputAgent
from mojentic.agents.simple_recursive_agent import SimpleRecursiveAgent

__all__ = [
    # Event adapters
    "AgentEventAdapter",
    "AsyncAggregatorAgent",
    # Base types
    "BaseAgent",
    "BaseAsyncAgent",
    "BaseAsyncLLMAgent",
    "BaseAsyncLLMAgentWithMemory",
    "BaseLLMAgent",
    # Special purpose
    "IterativeProblemSolver",
    "OutputAgent",
    "SimpleRecursiveAgent",
]
