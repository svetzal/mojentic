from typing import List, Optional

from pydantic import BaseModel

from mojentic.llm.gateways.models import LLMGatewayResponse, LLMMessage
from mojentic.llm.tools.llm_tool import LLMTool


class LLMGateway:
    """
    This is an abstract class from which specific LLM gateways are derived.

    To create a new gateway, inherit from this class and implement the `complete` method.
    """
    def complete(self,
                 model: str,
                 messages: List[LLMMessage],
                 object_model: Optional[BaseModel] = None,
                 tools: Optional[List[LLMTool]] = None,
                 temperature: float = 1.0,
                 num_ctx: int = 32768,
                 num_predict: int = -1) -> LLMGatewayResponse:
        """
        This method should be implemented by derived classes to complete the LLM request.

        Args:
            model (str): The name of the model to use, as appears in `ollama list`
            messages (List[LLMMessage]): A list of messages to send to the LLM.
            object_model (Optional[BaseModel]): The model to use for validating the response.
            tools (List[LLMTool]): A list of tools to use with the LLM. If a tool call is requested, the tool will be called and the output will be included in the response.
            temperature (float): The temperature to use for the response. Defaults to 1.0
            num_ctx (int): The number of context tokens to use. Defaults to 32768.
            num_predict (int): The number of tokens to predict. Defaults to no limit.
        Returns:
            LLMGatewayResponse: The response from the Ollama service.
        """
        raise NotImplementedError
