from pydantic import BaseModel

from mojentic.agents.base_llm_agent import BaseLLMAgentWithMemory
from mojentic.agents.output_agent import OutputAgent
from mojentic.context.shared_working_memory import SharedWorkingMemory
from mojentic.dispatcher import Dispatcher
from mojentic.event import Event
from mojentic.llm.llm_broker import LLMBroker
from mojentic.router import Router


class RequestEvent(Event):
    text: str


class ResponseEvent(Event):
    text: str
    memory: dict


class ResponseModel(BaseModel):
    text: str


class RequestAgent(BaseLLMAgentWithMemory):
    def __init__(self, llm: LLMBroker, memory: SharedWorkingMemory):
        super().__init__(llm,
                         memory,
                         "You are a helpful assistant, and you like to make note of new things"
                         " that you learn.",
                         "Answer the user's question, use what you know, and what you remember.",
                         ResponseModel)

    def receive_event(self, event):
        response = self.generate_response(event.text)
        return [
            ResponseEvent(
                source=type(self),
                correlation_id=event.correlation_id,
                text=response.text,
                memory=self.memory.get_working_memory()
            )
        ]


memory = SharedWorkingMemory({
    "User": {
        "name": "Stacey",
        "age": 56,
    }
})

llm = LLMBroker("deepseek-r1:70b")
# llm = LLMBroker("llama3.3-instruct-70b-32k")
request_agent = RequestAgent(llm, memory)
output_agent = OutputAgent()

router = Router({
    RequestEvent: [request_agent, output_agent],
    ResponseEvent: [output_agent]
})

dispatcher = Dispatcher(router)
dispatcher.dispatch(
    RequestEvent(source=str,
                 text="What is my name, and how old am I? And, did you know I have a dog named Boomer, and two cats"
                      " named Spot and Beau?"))
