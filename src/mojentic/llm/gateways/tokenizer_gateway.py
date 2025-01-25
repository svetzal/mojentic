from typing import List

import structlog
import tiktoken

logger = structlog.get_logger()


class TokenizerGateway:
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def encode(self, text: str) -> List:
        logger.debug("encode", text=text)
        return self.tokenizer.encode(text)
