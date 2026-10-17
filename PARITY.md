# Python 3.0.0 partial parity

| Owner decision | Python verification | Cross-port status |
| --- | --- | --- |
| Part 2: native reasoning | `native_reasoning_spec.py` executes shared `native-reasoning-v1` controls and broker continuations through real HTTP, profiles, structured output, recovery, cancellation and unsupported OpenAI requests; incomplete Ollama recovery cannot retain history or execute tools, with a completed continuation control | Rust reference consulted read-only; local consumer/provider roles verified together; external counterpart and live server verification unfinished |
| Part 1: Anthropic structured recovery and immutable requests | `anthropic-structured-v1` in `anthropic_structured_spec.py`: exact HTTP schema/history/control bytes, gateway and broker recovery, optional fields, typed terminal failures and bounded attempts | Local provider and broker consumer roles use the same executable set; live Anthropic and external consumer counterpart verification remain unfinished; tools/streaming separate |
| October 12 Typed errors decision | `python-typed-errors-v1` in `typed_errors_spec.py`: policy validation, capture and length types through supported gateways, brokers and sessions; real HTTP and exact request/history/progress assertions | Python provider and in-repository callers verified together; external consumers, other ports and live provider verification remain unavailable; not the Elixir `typed-errors-v1` executable set |
| October 12 Capabilities decision: five facilities with endpoint evidence | `recovery-capabilities-v1` in `recovery_capabilities_spec.py`: every gateway, old field projection, new serialization and invalid values | Local provider verification only; downstream consumer authorization and paired verification remain open; exact-attempt termination unknown |
| Part 5, issue #2: Anthropic ordered assistant history | `anthropic_history_spec.py`: SDK and owned recovery HTTP, two-turn ChatSession, byte-identical transient resends | Local Python verification only; live Anthropic and paired consumer/provider verification remain unavailable |
| Remote no-hook retries, local admission unless evidenced nonacceptance, and distinct undecided admission | [Recovery admission decision map](CONFORMANCE-3.0.0.md); ordinary, structured and supported stream APIs | Other ports and paired consumer verification remain unverified here |

The October 12 root recovery amendment governs these decisions. Exception
types alone do not establish nonacceptance. Metadata/request fidelity and
remaining initiative work are outside the native reasoning correction. The coordinated publication
hold remains until all six ports satisfy owner scope and required paired
consumer/provider verification is available.
