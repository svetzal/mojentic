import json
from typing import Annotated, List, Optional, Type

from pydantic import BaseModel, Field

from mojentic.agents.base_async_agent import BaseAsyncAgent
from mojentic.context.shared_working_memory import SharedWorkingMemory
from mojentic.event import Event
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.llm_tool import LLMTool


class BaseAsyncLLMAgent(BaseAsyncAgent):
    """
    BaseAsyncLLMAgent is an asynchronous version of the BaseLLMAgent.
    It uses an LLM to generate responses asynchronously.
    """
    llm: LLMBroker
    behaviour: Annotated[str, "The personality and behavioural traits of the agent."]

    def __init__(self, llm: LLMBroker, behaviour: str = "You are a helpful assistant.",
                 tools: Optional[List[LLMTool]] = None, response_model: Optional[Type[BaseModel]] = None):
        """
        Initialize the BaseAsyncLLMAgent.

        Parameters
        ----------
        llm : LLMBroker
            The LLM broker to use for generating responses
        behaviour : str, optional
            The personality and behavioural traits of the agent
        tools : List[LLMTool], optional
            The tools available to the agent
        response_model : Type[BaseModel], optional
            The model to use for responses
        """
        super().__init__()
        self.llm = llm
        self.behaviour = behaviour
        self.response_model = response_model
        self.tools = tools or []

    def _create_initial_messages(self):
        """
        Create the initial messages for the LLM.

        Returns
        -------
        list
            The initial messages for the LLM
        """
        return [
            LLMMessage(role=MessageRole.System, content=self.behaviour),
        ]

    def add_tool(self, tool):
        """
        Add a tool to the agent.

        Parameters
        ----------
        tool : LLMTool
            The tool to add
        """
        self.tools.append(tool)

    async def generate_response(self, content):
        """
        Generate a response using the LLM asynchronously.

        Parameters
        ----------
        content : str
            The content to generate a response for

        Returns
        -------
        str or BaseModel
            The generated response
        """
        messages = self._create_initial_messages()
        messages.append(LLMMessage(content=content))

        if self.response_model is not None:
            # Use asyncio.to_thread to run the synchronous generate_object method in a separate thread
            import asyncio
            response = await asyncio.to_thread(self.llm.generate_object, messages, object_model=self.response_model)
        else:
            # Use asyncio.to_thread to run the synchronous generate method in a separate thread
            import asyncio
            response = await asyncio.to_thread(self.llm.generate, messages, tools=self.tools)

        return response

    async def receive_event_async(self, event: Event) -> List[Event]:
        """
        Receive an event and process it asynchronously.
        This method should be overridden by subclasses.

        Parameters
        ----------
        event : Event
            The event to process

        Returns
        -------
        List[Event]
            The events to be processed next
        """
        return []


class BaseAsyncLLMAgentWithMemory(BaseAsyncLLMAgent):
    """
    BaseAsyncLLMAgentWithMemory is an asynchronous version of the BaseLLMAgentWithMemory.
    It uses an LLM to generate responses asynchronously and maintains a shared working memory.
    """
    instructions: Annotated[str, "The instructions for the agent to follow when receiving events."]

    def __init__(self, llm: LLMBroker, memory: SharedWorkingMemory, behaviour: str, instructions: str,
                 response_model: BaseModel):
        """
        Initialize the BaseAsyncLLMAgentWithMemory.

        Parameters
        ----------
        llm : LLMBroker
            The LLM broker to use for generating responses
        memory : SharedWorkingMemory
            The shared working memory to use
        behaviour : str
            The personality and behavioural traits of the agent
        instructions : str
            The instructions for the agent to follow when receiving events
        response_model : BaseModel
            The model to use for responses
        """
        super().__init__(llm, behaviour)
        self.instructions = instructions
        self.memory = memory
        self.response_model = response_model

    def _create_initial_messages(self):
        """
        Create the initial messages for the LLM.

        Returns
        -------
        list
            The initial messages for the LLM
        """
        messages = super()._create_initial_messages()
        messages.extend([
            LLMMessage(content=f"This is what you remember:\n{json.dumps(self.memory.get_working_memory(), indent=2)}"
                               f"\n\nRemember anything new you learn by storing it to your working memory in your response."),
            LLMMessage(role=MessageRole.User, content=self.instructions),
        ])
        return messages

    async def generate_response(self, content):
        """
        Generate a response using the LLM asynchronously.

        Parameters
        ----------
        content : str
            The content to generate a response for

        Returns
        -------
        BaseModel
            The generated response
        """
        class ResponseWithMemory(self.response_model):
            memory: dict = Field(self.memory.get_working_memory(),
                                 description="Add anything new that you have learned here.")

        messages = self._create_initial_messages()
        messages.extend([
            LLMMessage(content=content),
        ])
        
        # Use asyncio.to_thread to run the synchronous generate_object method in a separate thread
        import asyncio
        response = await asyncio.to_thread(
            self.llm.generate_object,
            messages=messages,
            object_model=ResponseWithMemory
        )
        
        self.memory.merge_to_working_memory(response.memory)

        d = response.model_dump()
        del d["memory"]

        return self.response_model.model_validate(d)