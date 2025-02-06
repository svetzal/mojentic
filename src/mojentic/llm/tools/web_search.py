import os

import serpapi

api_key = os.getenv("SERPAPI_API_KEY")


def organic_search(query: str, engine: str = "google", location: str = None, hl: str = "en", gl="ca") -> dict:
    results = serpapi.search(q=query, engine=engine, location=location, hl=hl, gl=gl, api_key=api_key)
    # Limiting this to the organic results cuts this from 60K to 3K tokens
    return results['organic_results']


organic_search_tool = {
    "descriptor": {
        "type": "function",
        "function": {
            "name": "organic_search",
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
                "additionalProperties": False,
                "required": ["query"]
            },
        },
    },
    "python_function": organic_search,
}
