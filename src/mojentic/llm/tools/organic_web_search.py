import json
import os

import serpapi

from mojentic.llm.tools.llm_tool import LLMTool


class OrganicWebSearchTool(LLMTool):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")

    def run(self, query: str, engine: str = "google", location: str = None, hl: str = "en", gl="ca") -> str:
        results = serpapi.search(q=query, engine=engine, location=location, hl=hl, gl=gl, api_key=self.api_key)
        # Limiting this to the organic results cuts this from 60K to 3K tokens
        return json.dumps(results['organic_results'], indent=2)

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "organic_web_search",
                "description":
                    "Search the Internet for information matching the given query and return the organic search results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query."
                        },
                    },
                    "required": ["query"]
                },
            },
        }
