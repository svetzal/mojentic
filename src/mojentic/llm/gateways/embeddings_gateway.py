import ollama
import structlog
import warnings

logger = structlog.get_logger()


class EmbeddingsGateway:
    """
    DEPRECATED: This class is deprecated and will be removed in a future version.
    Use OllamaGateway.calculate_embeddings() or OpenAIGateway.calculate_embeddings() instead.
    """
    def __init__(self, model: str = "mxbai-embed-large"):
        warnings.warn(
            "EmbeddingsGateway is deprecated and will be removed in a future version. "
            "Use OllamaGateway.calculate_embeddings() or OpenAIGateway.calculate_embeddings() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.model = model

    def calculate(self, text: str):
        """
        DEPRECATED: This method is deprecated and will be removed in a future version.
        Use OllamaGateway.calculate_embeddings() or OpenAIGateway.calculate_embeddings() instead.
        """
        warnings.warn(
            "EmbeddingsGateway.calculate() is deprecated and will be removed in a future version. "
            "Use OllamaGateway.calculate_embeddings() or OpenAIGateway.calculate_embeddings() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.debug("calculate", text=text)
        embed = ollama.embed(model=self.model, input=text)
        return embed.embeddings[0]
