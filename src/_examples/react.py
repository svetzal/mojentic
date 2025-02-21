from _examples.react.agents.decisioning_agent import DecisioningAgent
from _examples.react.agents.thinking_agent import ThinkingAgent
from _examples.react.models.base import CurrentContext
from _examples.react.models.events import InvokeThinking, InvokeDecisioning
from mojentic import Router, Dispatcher
from mojentic.agents import OutputAgent
from mojentic.llm import LLMBroker

# llm = LLMBroker("llama3.3-70b-32k")
llm = LLMBroker("deepseek-r1:70b")
thinking_agent = ThinkingAgent(llm)
decisioning_agent = DecisioningAgent(llm)

output_agent = OutputAgent()

router = Router({
    InvokeThinking: [thinking_agent, output_agent],
    InvokeDecisioning: [decisioning_agent, output_agent],
})

dispatcher = Dispatcher(router)

event = thinking_agent.receive_event(
    InvokeThinking(
        source=str,
        context=CurrentContext(
            user_query="What is the date next Friday?"
        )
    )
)

dispatcher.dispatch(event)
