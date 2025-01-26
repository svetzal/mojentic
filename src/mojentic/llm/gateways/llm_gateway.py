from mojentic.llm.gateways.models import LLMGatewayResponse


class LLMGateway:
    def complete(self, **args) -> LLMGatewayResponse:
        raise NotImplementedError
