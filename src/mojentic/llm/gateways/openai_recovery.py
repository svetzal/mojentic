"""OpenAI SSE uses the owned OpenAI-compatible decoder without oMLX identity."""

from mojentic.llm.gateways.omlx_recovery import OMLXStreamRecovery, _OMLXDecoder


class _OpenAIDecoder(_OMLXDecoder):
    provider = "openai"


class OpenAIStreamRecovery(OMLXStreamRecovery):
    """Retain actual model, usage and finish evidence without inferred counters."""

    provider = "openai"

    def decoder(self) -> _OpenAIDecoder:
        return _OpenAIDecoder()
