# Python 3.0.0 partial parity

| Owner decision | Python verification | Cross-port status |
| --- | --- | --- |
| Part 5, issue #2: Anthropic ordered assistant history | `anthropic_history_spec.py`: SDK and owned recovery HTTP, two-turn ChatSession, byte-identical transient resends | Local Python verification only; live Anthropic and paired consumer/provider verification remain unavailable |
| Remote no-hook retries, local admission unless evidenced nonacceptance, and distinct undecided admission | [Recovery admission decision map](CONFORMANCE-3.0.0.md); ordinary, structured and supported stream APIs | Other ports and paired consumer verification remain unverified here |

The October 12 root recovery amendment governs these decisions. Exception
types alone do not establish nonacceptance. Native reasoning, metadata and
remaining initiative work are outside this correction. The coordinated publication
hold remains until all six ports satisfy owner scope and required paired
consumer/provider verification is available.
