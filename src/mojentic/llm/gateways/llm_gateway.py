class LLMGateway:
    def complete(self, **args):
        raise NotImplementedError

    def complete_with_object(self, **args):
        raise NotImplementedError
