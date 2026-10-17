"""Endpoint documentation decisions inspected on 2026-10-17.

These describe documented facilities, not whether closing a local HTTP task
works. Local cancellation is implemented by RecoveryCall, but the inspected
endpoint documentation does not establish that facility's semantics.
"""

from mojentic.llm.recovery import Capabilities, CapabilityEvidence, RecoveryProvider


def completion_capabilities(provider: RecoveryProvider) -> Capabilities:
    """Return cited facilities and unchanged operation support for an adapter.

    Parameters
    ----------
    provider : RecoveryProvider
        Completion adapter whose endpoint documentation was inspected.

    Returns
    -------
    Capabilities
        Documented facilities with a separate evidence record for each value.
    """
    endpoint, source, description = {
        "ollama": (
            "POST /api/chat",
            "https://docs.ollama.com/api/chat",
            "Chat documents generation, streaming and model keep_alive",
        ),
        "omlx": (
            "POST /v1/chat/completions",
            "https://github.com/jundot/omlx/blob/main/README.md#api-compatibility",
            "API Compatibility lists chat completions and model/admin endpoints",
        ),
        "openai": (
            "POST /v1/chat/completions",
            "https://developers.openai.com/api/reference/resources/chat",
            "Chat documents creation and stored completions; Responses and Batch are separate APIs",
        ),
        "anthropic": (
            "POST /v1/messages",
            "https://platform.claude.com/docs/en/api/messages/create",
            "Messages documents request creation and streaming",
        ),
    }[provider]
    bases = {
        "local_cancellation": (
            f"{description}, but is silent on local HTTP cancellation. "
            "RecoveryCall cancels local work; that implementation does not establish "
            "a documented endpoint guarantee."
        ),
        "remote_cancellation": (
            f"{description}; no remote cancellation facility for an in-flight "
            "request is described on this endpoint. Closing HTTP is not remote cancellation."
        ),
        "request_status": (
            f"{description}; no status lookup for an in-flight request is described. "
            "Stored outputs and model activity are not request execution status."
        ),
        "idempotency": (
            f"{description}; no inference idempotency key or deduplication guarantee "
            "is described for this endpoint. Local correlation IDs do not deduplicate inference."
        ),
        "inference_termination": (
            f"{description}; no evidence establishes termination of this exact "
            "attempt. A disconnect, model unload or aggregate activity is insufficient."
        ),
    }
    return Capabilities(
        ordinary_recovery=True,
        structured_recovery=provider != "anthropic",
        streaming_recovery=provider != "anthropic",
        local_cancellation="unknown",
        remote_cancellation="unsupported",
        request_status="unsupported",
        idempotency="unsupported",
        inference_termination="unknown",
        evidence={
            name: CapabilityEvidence(
                endpoint=endpoint,
                source=source,
                inspected_on="2026-10-17",
                basis=basis,
            )
            for name, basis in bases.items()
        },
    )
