from typing import List

import structlog
import tiktoken

logger = structlog.get_logger()


class TokenizerGateway:
    def __init__(self, model: str = "cl100k_base"):
        self.tokenizer = tiktoken.get_encoding(model)

    def encode(self, text: str) -> List:
        logger.debug("encode", text=text)
        return self.tokenizer.encode(text)

    def decode(self, tokens: List) -> str:
        logger.debug("decode", tokens=tokens)
        return self.tokenizer.decode(tokens)
