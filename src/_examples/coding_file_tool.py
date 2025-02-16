import os
from pathlib import Path

from pydantic import BaseModel

from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.agents.output_agent import OutputAgent
from mojentic.dispatcher import Dispatcher
from mojentic.event import Event
from mojentic.llm.gateways import OpenAIGateway
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.file_manager import ReadFileTool, WriteFileTool
from mojentic.router import Router


class RequestEvent(Event):
    text: str


class ResponseEvent(Event):
    text: str


class ResponseModel(BaseModel):
    text: str


base_dir = Path(__file__).parent.parent.parent.parent / "code-playground"


class RequestAgent(BaseLLMAgent):
    def __init__(self, llm: LLMBroker):
        super().__init__(llm,
                         "You are a helpful assistant.")
        self.add_tool(ReadFileTool(str(base_dir)))
        self.add_tool(WriteFileTool(str(base_dir)))

    def receive_event(self, event):
        response = self.generate_response(event.text)
        return [ResponseEvent(source=type(self), correlation_id=event.correlation_id, text=response)]


# with open(base_dir / "spec.md", 'w') as file:
#     file.write("""
# Primes
#
# You are to write some python code that will generate the first 100 prime numbers.
#
# Store the code in a file called primes.py
# """.strip())

#
# OK this example is fun, it shows trying to make 2 consecutive
# tool calls. The first tool call reads a file, the second writes a file.
#
# Ollama 3.1 70b seems to handle this consistently, 3.3 70b seems flakey, flakier when num_ctx is set to 32768
# Ollama 3.1 8b seems to handle it about 1/3 the time
# OpenAI gpt-4o-mini handles it perfectly every single time
#


# llm = LLMBroker("qwen2.5-coder:32b")
# llm = LLMBroker("llama3.3")
api_key = os.getenv("OPENAI_API_KEY")
gateway = OpenAIGateway(api_key)
llm = LLMBroker(model="gpt-4o", gateway=gateway)
request_agent = RequestAgent(llm)
output_agent = OutputAgent()

router = Router({
    RequestEvent: [request_agent, output_agent],
    ResponseEvent: [output_agent]
})

dispatcher = Dispatcher(router)
dispatcher.dispatch(RequestEvent(source=str, text="""
# Mandelbrodt Set

You are to implement a program that will generate an image of the Mandelbrot set.

The program should be written in Swift for macOS utilizing SwiftUI.

The program should generate an image of the Mandelbrot set and display it in a window.

Generate any files you require to store the source code.

Generate a README.md file that includes instructions on how to run the program.
"""))
