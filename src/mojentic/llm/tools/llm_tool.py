import json

from mojentic.llm.gateways.models import TextContent


class LLMTool:
    def run(self, **kwargs):
        raise NotImplementedError

    def call_tool(self, **kwargs):
        result = self.run(**kwargs)
        if isinstance(result, dict):
            result = json.dumps(result)
        return {
            "content": [
                TextContent(type="text", text=result),
            ]
        }

    @property
    def descriptor(self):
        raise NotImplementedError

    @property
    def name(self):
        return self.descriptor["function"]["name"]

    @property
    def description(self):
        return self.descriptor["function"]["description"]

    def matches(self, name: str):
        return name == self.name
