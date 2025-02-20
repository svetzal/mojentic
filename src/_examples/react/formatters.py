from .models.base import CurrentContext


def format_current_context(context: CurrentContext):
    user_query = f"The user has asked us to answer the following query:\n> {context.user_query}\n"

    plan = "You have not yet made a plan.\n"
    if context.plan.steps:
        plan = "Current plan:\n"
        plan += "\n".join(f"- {step}" for step in context.plan.steps)
        plan += "\n"

    history = "No steps have yet been taken.\n"
    if context.history:
        history = "What's been done so far':\n"
        history += "\n".join(
            f"{i + 1}.\n    Thought: {step.thought}\n    Action: {step.action}\n    Observation: {step.observation}"
            for i, step in enumerate(context.history))
        history += "\n"

    return f"Current Context:\n{user_query}{plan}{history}\n"

def format_available_tools(tools):
    output = ""
    if tools:
        output += "Tools available:\n"
        for tool in tools:
            output += f"- {tool.descriptor["function"]["name"]}: {tool.descriptor["function"]["description"]}\n"

    return output
