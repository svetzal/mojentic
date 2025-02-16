from pydantic import BaseModel

from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.agents.output_agent import OutputAgent
from mojentic.dispatcher import Dispatcher
from mojentic.event import Event
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.router import Router


class RequestEvent(Event):
    text: str


class ResponseEvent(Event):
    text: str


class ResponseModel(BaseModel):
    text: str


class RequestAgent(BaseLLMAgent):
    def __init__(self, llm: LLMBroker):
        super().__init__(llm,
                         "You are a helpful assistant.")
        self.add_tool(ResolveDateTool())

    def receive_event(self, event):
        response = self.generate_response(event.text)
        return [ResponseEvent(source=type(self), correlation_id=event.correlation_id, text=response)]


# llm = LLMBroker("deepseek-r1:70b")
# llm = LLMBroker("llama3.3-70b-32k")
llm = LLMBroker("qwen2.5:7b")
request_agent = RequestAgent(llm)
output_agent = OutputAgent()

router = Router({
    RequestEvent: [request_agent, output_agent],
    ResponseEvent: [output_agent]
})

dispatcher = Dispatcher(router)
dispatcher.dispatch(RequestEvent(source=str, text="What will be the date this Friday?"))
