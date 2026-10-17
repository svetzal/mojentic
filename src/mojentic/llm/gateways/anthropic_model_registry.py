"""Documented Anthropic output limits used for required request parameters.

Exact IDs and aliases only: unknown models use the section 3.4 fallback.
Sources (inspected 2026-10-17):
https://platform.claude.com/docs/en/models/sonnet-4-5/overview
https://platform.claude.com/docs/en/models/haiku-4-5/overview
"""

_OUTPUT_LIMITS: dict[str, int] = {
    "claude-sonnet-4-5": 64000,
    "claude-sonnet-4-5-20250929": 64000,
    "claude-haiku-4-5": 64000,
    "claude-haiku-4-5-20251001": 64000,
}


def max_output_tokens(model: str) -> int:
    """Return the registered output maximum or the unknown-model fallback.

    Parameters
    ----------
    model : str
        Exact Anthropic model ID or registered alias.

    Returns
    -------
    int
        Required output limit; 4096 when the model is not registered.
    """
    return _OUTPUT_LIMITS.get(model, 4096)
