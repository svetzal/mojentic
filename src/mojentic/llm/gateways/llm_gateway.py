from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from mojentic.llm.gateways.models import LLMGatewayResponse, LLMMessage
from mojentic.llm.tools.llm_tool import LLMTool

if TYPE_CHECKING:
    from mojentic.llm.completion_config import CompletionConfig


class LLMGateway:
    """
    This is an abstract class from which specific LLM gateways are derived.

    To create a new gateway, inherit from this class and implement the `complete` method.
    """

    def complete(
        self,
        model: str,
        messages: list[LLMMessage],
        object_model: type[BaseModel] | None = None,
        tools: list[LLMTool] | None = None,
        config: Optional["CompletionConfig"] = None,
        temperature: float | None = None,
        num_ctx: int | None = None,
        max_tokens: int | None = None,
    ) -> LLMGatewayResponse:
        """
        Complete the LLM request.

        Parameters
        ----------
        model : str
            The name of the model to use, as appears in `ollama list`.
        messages : List[LLMMessage]
            A list of messages to send to the LLM.
        object_model : Optional[BaseModel]
            The model to use for validating the response.
        tools : Optional[List[LLMTool]]
            A list of tools to use with the LLM. If a tool call is requested, the tool will be called and the output
            will be included in the response.
        config : Optional[CompletionConfig]
            Configuration object for LLM completion (recommended over individual kwargs).
        temperature : float
            The temperature to use for the response. Unspecified by default. (Deprecated: use config)
        num_ctx : int
            The number of context tokens to use. Unspecified by default. (Deprecated: use config)
        max_tokens : int
            The maximum number of tokens to generate. Unspecified by default. (Deprecated: use config)

        Returns
        -------
        LLMGatewayResponse
            The response from the Ollama service.
        """
        raise NotImplementedError

    def get_available_models(self) -> list[str]:
        """
        Get the list of available models.

        Returns
        -------
        List[str]
            The list of available models.
        """
        raise NotImplementedError

    def calculate_embeddings(self, text: str, model: str | None = None) -> list[float]:
        """
        Calculate embeddings for the given text using the specified model.

        Parameters
        ----------
        text : str
            The text to calculate embeddings for.
        model : str, optional
            The name of the model to use for embeddings. Default value depends on the implementation.

        Returns
        -------
        List[Any]
            The embeddings for the text.
        """
        raise NotImplementedError
