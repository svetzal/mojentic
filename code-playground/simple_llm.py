from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.agents.output_agent import OutputAgent
from mojentic.dispatcher import Dispatcher
from mojentic.event import Event
from mojentic.llm.llm_broker import LLMBroker
from mojentic.router import Router


class RequestEvent(Event):
    text: str


class ResponseEvent(Event):
    text: str


class RequestAgent(BaseLLMAgent):
    def __init__(self, llm: LLMBroker):
        super().__init__(llm,
                         "You are a friendly encyclopedia, specializing in geography.")

    def receive_event(self, event):
        response = self.generate_response(event.text)
        return [ResponseEvent(source=type(self), correlation_id=event.correlation_id, text=response)]


# llm = LLMBroker("deepseek-r1:70b")
# llm = LLMBroker("qwen3:14b")
from mojentic.llm.llm_broker import LLMBroker

llm = LLMBroker("phi4:14b")
# llm = LLMBroker("qwen3:7b", gateway=OllamaGateway(host="http://odin.local:11434"))
request_agent = RequestAgent(llm)
output_agent = OutputAgent()

router = Router({
    RequestEvent: [request_agent, output_agent],
    ResponseEvent: [output_agent]
})

dispatcher = Dispatcher(router)
dispatcher.dispatch(RequestEvent(source=str, text="What is the capitol of Canada?"))
