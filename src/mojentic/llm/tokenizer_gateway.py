from typing import List

import tiktoken


class TokenizerGateway:
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def encode(self, text: str) -> List:
        return self.tokenizer.encode(text)