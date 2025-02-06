from pydantic import BaseModel

from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.agents.output_agent import OutputAgent
from mojentic.dispatcher import Dispatcher
from mojentic.event import Event
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.file_manager import ReadFileTool, WriteFileTool
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
        self.add_tool(ReadFileTool("/tmp"))
        self.add_tool(WriteFileTool("/tmp"))

    def receive_event(self, event):
        response = self.generate_response(event.text)
        return [ResponseEvent(source=type(self), correlation_id=event.correlation_id, text=response)]


with open("/tmp/ernie.md", 'w') as file:
    file.write("""
# Ernie the Caterpillar

This is an unfinished story about Ernie, the most adorable and colourful caterpillar.
""".strip())

#
# OK this example is fun, it shows trying to make 2 consecutive
# tool calls. The first tool call reads a file, the second writes a file.
#
# Ollama 3.1 70b seems to handle this consistently, 3.3 70b seems flakey, flakier when num_ctx is set to 32768
# Ollama 3.1 8b seems to handle it about 1/3 the time
# OpenAI gpt-4o-mini handles it perfectly every single time
#


# llm = LLMBroker("llama3.3-70b-32k")
# llm = LLMBroker("llama3.1:70b")
# llm = LLMBroker("llama3.1:8b")
llm = LLMBroker("qwen2.5:7b")
# llm = LLMBroker("llama3.3")
# api_key = os.getenv("OPENAI_API_KEY")
# gateway = OpenAIGateway(api_key)
# llm = LLMBroker(model="gpt-4o-mini", gateway=gateway)
request_agent = RequestAgent(llm)
output_agent = OutputAgent()

router = Router({
    RequestEvent: [request_agent, output_agent],
    ResponseEvent: [output_agent]
})

dispatcher = Dispatcher(router)
dispatcher.dispatch(RequestEvent(source=str, text="Step 1 - Read the unfinished story in ernie.md\n"
                                                  "Step 2 - Complete the story and store it in ernie2.md"))
