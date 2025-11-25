"""Formatting utilities for the ReAct pattern implementation.

This module provides helper functions for formatting context and tool information
into human-readable strings for LLM prompts.
"""
from .models.base import CurrentContext


def format_current_context(context: CurrentContext) -> str:
    """Format the current context into a readable string.

    Args:
        context: The current context containing query, plan, and history.

    Returns:
        A formatted multi-line string describing the current context.
    """
    user_query = f"The user has asked us to answer the following query:\n> {context.user_query}\n"

    plan = "You have not yet made a plan.\n"
    if context.plan.steps:
        plan = "Current plan:\n"
        plan += "\n".join(f"- {step}" for step in context.plan.steps)
        plan += "\n"

    history = "No steps have yet been taken.\n"
    if context.history:
        history = "What's been done so far:\n"
        history += "\n".join(
            f"{i + 1}.\n    Thought: {step.thought}\n    Action: {step.action}\n    Observation: {step.observation}"
            for i, step in enumerate(context.history))
        history += "\n"

    return f"Current Context:\n{user_query}{plan}{history}\n"


def format_available_tools(tools) -> str:
    """Format the available tools into a readable list.

    Args:
        tools: A list of tool objects with descriptor dictionaries.

    Returns:
        A formatted string listing available tools and their descriptions.
    """
    output = ""
    if tools:
        output += "Tools available:\n"
        for tool in tools:
            func_descriptor = tool.descriptor['function']
            output += f"- {func_descriptor['name']}: {func_descriptor['description']}\n"

            # Add parameter information
            if 'parameters' in func_descriptor:
                params = func_descriptor['parameters']
                if 'properties' in params:
                    output += "  Parameters:\n"
                    for param_name, param_info in params['properties'].items():
                        param_desc = param_info.get('description', '')
                        is_required = param_name in params.get('required', [])
                        req_str = " (required)" if is_required else " (optional)"
                        output += f"    - {param_name}{req_str}: {param_desc}\n"

    return output
