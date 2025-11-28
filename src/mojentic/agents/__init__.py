"""
Mojentic agents module for creating and working with various agent types.
"""

# Base agent types
from mojentic.agents.base_agent import BaseAgent
from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.agents.base_async_agent import BaseAsyncAgent
from mojentic.agents.async_llm_agent import BaseAsyncLLMAgent, BaseAsyncLLMAgentWithMemory
from mojentic.agents.async_aggregator_agent import AsyncAggregatorAgent

# Special purpose agents
from mojentic.agents.iterative_problem_solver import IterativeProblemSolver
from mojentic.agents.simple_recursive_agent import SimpleRecursiveAgent
from mojentic.agents.output_agent import OutputAgent

# Event adapters
from mojentic.agents.agent_event_adapter import AgentEventAdapter

__all__ = [
    # Base types
    "BaseAgent",
    "BaseLLMAgent",
    "BaseAsyncAgent",
    "BaseAsyncLLMAgent",
    "BaseAsyncLLMAgentWithMemory",
    "AsyncAggregatorAgent",
    # Special purpose
    "IterativeProblemSolver",
    "SimpleRecursiveAgent",
    "OutputAgent",
    # Event adapters
    "AgentEventAdapter",
]
