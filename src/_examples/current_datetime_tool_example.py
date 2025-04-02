from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.current_datetime import CurrentDateTimeTool

# Create an LLM broker with a specified model
# You can change the model to any supported model
llm = LLMBroker(model="qwen2.5:7b")  # Using the same model as in simple_tool.py

# Create our custom tool
datetime_tool = CurrentDateTimeTool()

# Generate a response with tool assistance
result = llm.generate(
    messages=[LLMMessage(content="What time is it right now? Also, what day of the week is it today?")],
    tools=[datetime_tool]
)

print("LLM Response:")
print(result)

# You can also try with a custom format string
result = llm.generate(
    messages=[LLMMessage(content="Tell me the current date in a friendly format, like 'Monday, January 1, 2023'")],
    tools=[datetime_tool]
)

print("\nLLM Response with custom format:")
print(result)