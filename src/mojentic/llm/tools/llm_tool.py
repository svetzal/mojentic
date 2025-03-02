class LLMTool:
    def run(self, **kwargs):
        raise NotImplementedError

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
