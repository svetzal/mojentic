class LLMTool:
    def run(self, **kwargs):
        raise NotImplementedError

    @property
    def descriptor(self):
        raise NotImplementedError

    def matches(self, name: str):
        return name == self.descriptor["function"]["name"]