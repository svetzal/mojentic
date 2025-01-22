from pydantic import BaseModel

from mojentic.base_llm_agent import BaseLLMAgent
from mojentic.dispatcher import Dispatcher
from mojentic.event import Event
from mojentic.llm_gateway import LLMGateway
from mojentic.output_agent import OutputAgent
from mojentic.router import Router
from mojentic.shared_working_memory import SharedWorkingMemory


class RequestEvent(Event):
    text: str


class ResponseEvent(Event):
    text: str
    memory: dict


class ResponseModel(BaseModel):
    text: str


class RequestAgent(BaseLLMAgent):
    def __init__(self, llm: LLMGateway, memory: SharedWorkingMemory, response_model: BaseModel):
        super().__init__(llm,
                         memory,
                         "You are a helpful assistant, and you like to make note of new things that you learn.",
                         "Respond to the user's question with a relevant answer.",
                         response_model)

    def receive_event(self, event):
        response = self.generate_response(event.text)
        return [ResponseEvent(source=type(self), correlation_id=event.correlation_id, text=response.text, memory=self.memory.get_working_memory())]


memory = SharedWorkingMemory({
    "User": {
        "name": "Stacey",
        "age": 56,
    }
})

llm = LLMGateway("llama3.3-instruct-70b-32k")
request_agent = RequestAgent(llm, memory, ResponseModel)
output_agent = OutputAgent()

router = Router({
    RequestEvent: [request_agent, output_agent],
    ResponseEvent: [output_agent]
})

dispatcher = Dispatcher(router)
dispatcher.dispatch(
    RequestEvent(source=str, text="What is my name, and how old am I? And, did you know I have a dog named Boomer, and two cats named Spot and Beau?"))
