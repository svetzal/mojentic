from pydantic import BaseModel

from mojentic.base_agent import BaseAgent
from mojentic.base_llm_agent import BaseLLMAgent
from mojentic.dispatcher import Dispatcher
from mojentic.event import Event
from mojentic.llm_gateway import LLMGateway
from mojentic.router import Router


class RequestEvent(Event):
    text: str


class ResponseEvent(Event):
    text: str


class ResponseModel(BaseModel):
    text: str


class RequestAgent(BaseLLMAgent):
    def __init__(self, llm: LLMGateway, response_model: BaseModel):
        super().__init__(llm,
                         "You are a friendly encyclopedia, with a focus on geography.",
                         "Respond to the user's question with a relevant answer.",
                         response_model)

    def receive_event(self, event):
        response = self.generate_response(event.text)
        return [ResponseEvent(source=type(self), correlation_id=event.correlation_id, text=response.text)]


class OutputAgent(BaseAgent):
    def receive_event(self, event):
        print(event)
        return []


request_agent = RequestAgent(LLMGateway("llama3.1-instruct-8b-32k"), ResponseModel)
output_agent = OutputAgent()

router = Router({
    RequestEvent: [request_agent, output_agent],
    ResponseEvent: [output_agent]
})

dispatcher = Dispatcher(router)

dispatcher.dispatch(RequestEvent(source=str, text="What is the capital of Canada?"))
