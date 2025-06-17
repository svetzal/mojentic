from pydantic import BaseModel, Field

from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.agents.output_agent import OutputAgent
from mojentic.dispatcher import Dispatcher
from mojentic.event import Event
from mojentic.llm.llm_broker import LLMBroker
from mojentic.router import Router


class RequestEvent(Event):
    text: str


class CapitolCityModel(BaseModel):
    country: str = Field(..., description="The name of the country")
    capitol_city: str = Field(..., description="The name of the capitol city")


class ResponseEvent(Event):
    capitol: CapitolCityModel


class RequestAgent(BaseLLMAgent):
    def __init__(self, llm: LLMBroker):
        super().__init__(llm,
                         "You are a helpful assistant.",
                         CapitolCityModel)

    def receive_event(self, event):
        response = self.generate_response(event.text)
        return [ResponseEvent(source=type(self), correlation_id=event.correlation_id, capitol=response)]


llm = LLMBroker("llama3.1-instruct-8b-32k")
request_agent = RequestAgent(llm)
output_agent = OutputAgent()

router = Router({
    RequestEvent: [request_agent, output_agent],
    ResponseEvent: [output_agent]
})

dispatcher = Dispatcher(router)
dispatcher.dispatch(RequestEvent(source=str, text="What is the capitol of Canada?"))
