from mojentic.agents import BaseAgent
from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.dispatcher import Dispatcher
from mojentic.event import Event
from mojentic.llm.llm_broker import LLMBroker
from mojentic.router import Router


class RequestEvent(Event):
    text: str


class ResponseEvent(Event):
    text: str


# We don't need to override the system prompt, so that simplifies the instantiation of the agent
class ChatAgent(BaseLLMAgent):
    def receive_event(self, event):
        response = self.generate_response(event.text)
        return [ResponseEvent(source=type(self), correlation_id=event.correlation_id, text=response)]


class ChatOutputAgent(BaseAgent):
    def receive_event(self, event):
        print(f"LLM: {event.text}")
        return []


llm = LLMBroker("llama3.1-instruct-8b-32k")
request_agent = ChatAgent(llm)
output_agent = ChatOutputAgent()

router = Router({
    RequestEvent: [request_agent],
    ResponseEvent: [output_agent]
})

dispatcher = Dispatcher(router)

# This is the REPL loop, gather query from user, send it as a message to the agent system
# Doesn't work particularly well due to calls being async
running = True
print("Welcome to the REPL, use exit to quit.")
while running:
    query = input("You: ")
    if query.lower() == "exit":
        running = False
    else:
        dispatcher.dispatch(RequestEvent(source=str, text=query))
