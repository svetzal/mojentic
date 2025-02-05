import ollama
import structlog

logger = structlog.get_logger()


class EmbeddingsGateway:
    def __init__(self, model: str = "mxbai-embed-large"):
        self.model = model

    def calculate(self, text: str):
        logger.debug("calculate", text=text)
        embed = ollama.embed(model=self.model, input=text)
        return embed.embeddings[0]
