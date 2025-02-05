import ollama
import structlog

logger = structlog.get_logger()


class EmbeddingsGateway:
    def calculate(text: str):
        logger.debug("calculate", text=text)
        embed = ollama.embed(model="mxbai-embed-large", input=text)
        return embed.embeddings[0]
