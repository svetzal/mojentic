# Python 3.0.0 conformance — partial decision map

This is a partial decision map for the owner scope in
`mojentic-unify/RELEASE-3.0.0.md`. It does not declare Python or the
coordinated release ready. Versions and publication remain on hold.

## October 12 Capabilities decision

This correction implements only the Capabilities decision in part 1 of the
owner scope. The Foundry initiative brief was read and its SHA-256 verified as
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
The binding root amendment was inspected at
`mojentic-unify/TRANSIENT-RECOVERY-2026-10.md`, October 12, Capabilities;
the older local October 9 copy does not replace that decision.

### Characterized representation and migration

Before the source change, inspection of `Capabilities`, all four public
`recovery_capabilities()` methods, the exact dictionary in
`ollama_recovery_spec.py::should_expose_success_history_and_truthful_capabilities`,
and `cloud_recovery_spec.py::DescribeAnthropicCapabilityBoundary` established:
eight serialized fields, string-valued remote/status/idempotency `unsupported`,
termination `unknown`, and boolean operation/capture indicators. Anthropic
supported only ordinary recovery. The initial public Anthropic probe printed
that original representation and rejected missing `local_cancellation`.

Existing attributes, serialized values, operation support and capture flags
are preserved. Serialization adds `local_cancellation` and `evidence`;
strict older readers must receive a projection excluding those fields.
New readers accept legacy payloads without them (unknown local cancellation,
empty evidence). No evidence on an old payload proves documented support.
The facility vocabulary permits supported/unsupported/unknown, while
`inference_termination` still accepts only unknown. The original Ollama exact
dictionary assertion now checks the explicit legacy projection; the new
contract checks each addition and full Python/JSON round trips.
Anthropic's ordinary-only assertions and pre-dispatch rejection checks remain
unchanged. No admission, completion, reasoning or metadata behavior changed.

### Verified documentation decisions

All four actual completion endpoints were inspected on **2026-10-17**; their
sources and the five-value matrix are in the recovery guide's
[capability boundaries](docs/transient_recovery.md#capability-boundaries).
Every returned value carries endpoint, source, date and basis, including
unsupported and unknown values. Local cancellation is unknown because the
endpoint documentation is silent, despite implemented `RecoveryCall`
cancellation. Remote cancellation, in-flight status and idempotency are
unsupported because the inspected endpoint references describe no such
facilities. Exact-attempt termination remains unknown for every gateway.
OpenAI Responses/Batch facilities, stored completed output, model unload,
aggregate model activity and closing HTTP do not establish these facilities
for an in-flight completion attempt.

Unverified: documented local-cancellation guarantees, remote termination for
any individual attempt, live vendor behavior, custom proxy extensions and
other ports. Static reports describe the cited provider endpoint documentation;
they are not active probes of caller-selected deployments.

### Executable contract and coordination finding

The existing pytest specification mechanism is reused for the versioned
executable set **recovery-capabilities-v1**:
[recovery_capabilities_spec.py](src/mojentic/llm/gateways/recovery_capabilities_spec.py).
Original SHA-256: `c780d497a8202fa4fb509b543a02e39bb06f8ae923e4752c3b42ce6ac503252c`.
The Anthropic structured correction below records the updated artifact identity;
the original results in this section describe the earlier tested revision.
It runs in the required `.hone-gates.json` pytest gate. There are no new test
doubles or independent consumer mocks.

| Decision | Named tests in `DescribeRecoveryCapabilitiesV1` (each gateway) |
| --- | --- |
| Local cancellation value and exact endpoint evidence | `should_report_local_cancellation_with_endpoint_evidence` |
| Remote cancellation value and exact endpoint evidence | `should_report_remote_cancellation_with_endpoint_evidence` |
| Request status value and exact endpoint evidence | `should_report_request_status_with_endpoint_evidence` |
| Idempotency value and exact endpoint evidence | `should_report_idempotency_with_endpoint_evidence` |
| Exact-attempt termination value and exact endpoint evidence | `should_report_exact_attempt_termination_with_endpoint_evidence` |
| Legacy access, serialization and omitted additions | `should_preserve_legacy_access_and_serialized_values` |
| New evidence and JSON serialization | `should_round_trip_new_evidence_in_python_and_json` |
| Invalid vocabulary and unsupported termination claims | `should_reject_invalid_capability_values`, `should_reject_claims_of_exact_attempt_termination` |

Provider tested commit: `af1de0c685632edca77bdc35285b6ff76a90b862` plus this
uncommitted correction. Provider verification command:
`uv run pytest src/mojentic/llm/gateways/recovery_capabilities_spec.py --no-cov`.
This verifies the real Python capability entrypoints, without network mocks.
Result: **exit 0, 53 passed**, including 20 separately named facility cases
across four gateways. The combined capability, Ollama recovery and cloud
recovery suite passed **248 tests**.

**PY-CAPABILITIES-PAIRED-VERIFICATION (open):** downstream consumer repositories
are not authorized in this task. Consumer tested commits, verification commands
and results: **unavailable, not run**. They must verify this same executable
contract version/hash against both supported legacy projections and new
payloads before paired compatibility can be declared. Relay that work as a
separate initiative assignment. Local provider verification alone does not
complete cross-repository compatibility. Preserve the coordinated publication
hold until all six ports satisfy owner scope and required paired verification
is available. No sibling repository was modified.

### Capability correction quality verification

Commands run through `foundry capture --log-dir .foundry/logs --`, with a
writable temporary uv cache and tool directory because the default home cache
is read-only. The initial public-entrypoint behavioral probe failed with exit 1
for the absent field and passed with exit 0 after the source correction.
The proof JSON records both actual exit codes and logs.

| Command | Result |
| --- | --- |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; required lint gate |
| `uv run pytest` | Exit 0; 1,440 passed; 85% configured coverage |
| `uv run bandit -c .bandit -r src` | Exit 0; zero issues |
| `uv run pip-audit` | Exit 0; no known vulnerabilities |
| `uv run flake8 src` | Exit 0 |
| `uv run ruff check src` | Exit 0; zero findings after sorting the new imports |
| `uv run ruff format src` | Exit 0; unrelated formatter edit restored to keep scope |
| `uv run pytest --cov` | Exit 0; 1,440 passed; 86% coverage; no repository minimum configured; capability decision module 100% |
| `uv run mkdocs build` | Exit 0; rebuilt after recovery documentation updates |
| `uv pip list --outdated` | Exit 0; available updates reported; no dependencies changed |
| `uv export --format requirements-txt --no-emit-project` piped to `uvx pip-audit -r /dev/stdin --disable-pip` under `bash -o pipefail` | Exit 0; no known vulnerabilities (rerun with writable uv tool directory) |

The root `.hone-gates.json` is the only discovered gate file. All four gates
passed, including both advisory gates. No audit suppression was added. All
changes remain uncommitted for Foundry; Git refs and package versions remain
unchanged. The behavioral proof JSON was validated for field types, actual
exit codes (1 then 0), existing logs and their failing/passing test summaries.

## Executable admission decisions

The local executable set is **recovery-admission-v2** in
[src/mojentic/llm/gateways/recovery_admission_spec.py](src/mojentic/llm/gateways/recovery_admission_spec.py).
All named tests below belong to `DescribeRecoveryAdmission`. The matrix covers
Ollama, oMLX and OpenAI ordinary, structured and streaming recovery, and
Anthropic ordinary recovery (its only supported recovery operation). Requests
cross real loopback HTTP, rather than independently mocked SDKs. Existing
provider-specific specs continue covering tool variants and unsupported APIs.

| Decision | Named executable verification |
| --- | --- |
| Eligible OpenAI/Anthropic failures retry without a hook | `should_apply_admission_without_changing_retry_bytes[absent-*]` |
| Ambiguous Ollama/oMLX acceptance requires a hook | `should_apply_admission_without_changing_retry_bytes[absent-*]` |
| Explicit allow authorizes resend; explicit reject prevents it | `should_apply_admission_without_changing_retry_bytes[allow-*]` and `[reject-*]` |
| Hook completion without a decision prevents resend with distinct `admission_undecided` | `should_apply_admission_without_changing_retry_bytes[None-*]` |
| Ordinary and streaming synchronous APIs expose the same stable undecided outcome | `should_surface_undecided_through_synchronous_public_apis` |
| Local nonacceptance permits no-hook retry only with evidence | `should_retry_evidenced_connection_refusal_without_hook`: a bound, non-listening socket actually refuses the first connection, then starts a real HTTP server for the retry |
| Capture hooks raising a connection-shaped exception cannot fabricate nonacceptance | `should_not_invent_nonacceptance_from_a_capture_hook_exception` verifies an actual HTTP 200 remains acceptance `unknown` and terminal |
| Caller validation after HTTP 200 cannot fabricate nonacceptance | `should_keep_acceptance_unknown_when_caller_validation_fails[ConnectError/ConnectTimeout-ollama/omlx/openai]` asserts status, headers/raw progress, original cause, unknown acceptance, ineligibility and one request |
| Pending admission cancels or expires without another dispatch and closes its task | `should_stop_pending_admission[cancelled-*]` and `[budget_exhausted-*]` |
| Semantic delivery prevents replay, even with an allow hook | `should_never_replay_after_delivering_content`: receives content followed by EOF without a terminal marker |
| Retry payload remains byte-identical; logical IDs stable and attempt IDs unique; safe lifecycle serialization | `assert_wire` assertions in each test above compare real outbound requests to captured bytes, identities, paths, payload semantics, reports and lifecycle fields |

The preserved v1 admission behavior remains: absent hooks allow eligible remote
retries; ambiguous local failures require admission; explicit and undecided
outcomes remain distinct. The v2 set retains every v1 case and adds validator
and capture-hook exception coverage. Before this correction, all six validator
cases received real HTTP 200 and retained its progress/cause but failed because
acceptance was `no`. After the source correction, acceptance is `unknown`, the
failure is ineligible, and no second HTTP request occurs.

Only transport trace evidence of failed TCP, Unix-socket or TLS connection
establishment establishes nonacceptance for a dispatched request. Both ordinary
and streaming paths install the same per-attempt trace callback, and
`_Attempt.failure` consumes that evidence. Beginning to send request headers
clears earlier connection failure evidence. A received response overrides it.
An exception class alone, HTTP 429/5xx, read/write failures or missing output
cannot establish nonacceptance. Transports without such trace evidence remain
conservative. This uses the documented [HTTPCore trace extension](https://www.encode.io/httpcore/extensions/#trace).
No provider or operation support was removed. Cancellation, immutable encoding,
bounded history, privacy and stream interruption rules remain in place.

## Authoritative scope inspected

The initiative brief SHA-256 was verified as
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
The authoritative root files were available read-only in the local
`mojentic-unify` checkout at commit
`4b08dcd1d87f520a4c70928c33a2bc84c228093d`:

- `RELEASE-3.0.0.md`: SHA-256
  `ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
- `TRANSIENT-RECOVERY-2026-10.md`, including the October 12 amendment: SHA-256
  `a53a3a4eb118fa4687dd703d6ce918dd40dd6cb4eda796abc6c429a6e932e7a3`.

The root amendment requires a distinct stable undecided reason and permits
idiomatic names; `admission_undecided` satisfies that decision. The port's older
October 9 contract copy does not supersede the root amendment.

## Contract boundary and initiative finding

The changed consumer/provider boundary is the caller or experiment harness
consuming Mojentic Python's public recovery reports, admission context and
terminal stream outcome. Mojentic Python is the provider of this API. The
change does not alter the HTTP request/response contract with Ollama, oMLX,
OpenAI or Anthropic. Those services are upstream providers, not consumers of
the changed acceptance/outcome fields. Other language ports implement parallel
APIs; running their tests would not verify a Python consumer.

Reuse the existing executable admission mechanism at
`src/mojentic/llm/gateways/recovery_admission_spec.py`, now
**recovery-admission-v2**, preserving the v1 supported cases. The existing live
oMLX fixtures (documented under `fixtures/omlx/README.md` in the gateways tree,
from root fixture revision `63409fa`) remain unchanged; they describe a different
boundary and do not verify Python admission consumers. No shared consumer-side
admission runner or paired verification record was found in the available
root contracts, root fixtures or this port.

**Initiative finding PY-ADMISSION-CONSUMER-VERIFICATION (open):** identify every
Python recovery consumer/harness and authorize its repository separately. Have
that consumer express its required reports, optional metadata, errors,
undecided outcome, conservative acceptance, retry permissions and supported
v1/v2 behavior in this same identifiable executable set; run consumer and
Mojentic-provider verification against the identical version/hash in both
repositories' gates. Record both commits, commands and results, deriving any
doubles from those verified contracts. Include the real harness journey and
trace/history/tool-count continuity checks required by the root contract.

No Python consumer repository or tested consumer revision is identified by the
initiative brief (its named downstream projects consume Elixir or Rust).
Consumer verification command, commit and result: **unavailable, not run**.
The local loopback tests verify the Python implementation through real HTTP;
their independently authored response fixtures are not paired contracts or
live vendor verification. This correction cannot close the cross-repository
finding. No other repository was edited. Keep the coordinated publication hold
until this gap and all six ports' owner scope are satisfied.

## Unverified decisions

- Remaining October 12 robustness decisions are **unverified by this decision
  map**; the older recovery map and provider specs are prior evidence, not a
  completed 3.0.0 audit.
- Native reasoning is mapped in the part-2 section below. Model metadata/request
  fidelity and remaining initiative audit fixes remain **unverified here**. Anthropic history
  (part 5, issue #2) is verified locally below.
- Actual connection timeout, Unix-socket and TLS failure paths are **not
  exercised** by the deterministic TCP-refusal tests. Remote execution,
  inference termination, idempotency and provider request-status APIs remain
  **unverified/unsupported**. Admission does not prove termination or idempotency.

## Prior recovery-admission verification record

Provider tested commit: preserved `3e3b353c4893a9153a194e7123b668aecfae9ea0`
plus the uncommitted correction in this worktree. Foundry owns finalization;
no refs changed. Executable set: **recovery-admission-v2**, SHA-256
`0c6e83d37a7c7e78ffa568d45bbbf3c22788dd6aa5254cdfd9863e9b6c8a558b`.

All verification commands run through `foundry capture --log-dir .foundry/logs --`.
Writable caches use `UV_CACHE_DIR=/tmp/mojentic-uv-cache`,
`UV_TOOL_DIR=/tmp/mojentic-uv-tools` and `XDG_CACHE_HOME=/tmp/mojentic-cache`.
Dependency versions and audit scope are unchanged.

| Command | Result |
| --- | --- |
| `uv run pytest src/mojentic/llm/gateways/recovery_admission_spec.py --no-cov` | Exit 0; 105 passed |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0 |
| `uv run pytest` | Exit 0; 1,376 passed, 85% configured coverage |
| `uv run bandit -c .bandit -r src` | Exit 0; zero issues |
| `uv run pip-audit` | Exit 0; no known vulnerabilities |
| `uv run flake8 src` | Exit 0 |
| `uv run ruff check src` | Exit 0; zero findings |
| `uv run pytest --cov` | Exit 0; 1,376 passed, 86% coverage |
| `uv run mkdocs build` | Exit 0 |
| `uv export --format requirements-txt --no-emit-project` piped to `uvx pip-audit -r /dev/stdin --disable-pip` under `bash -o pipefail` | Exit 0; no known vulnerabilities |
| `uv pip list --outdated` | Exit 0; available updates reported, no dependency changes |

`uv run ruff format src` ran successfully. Its unrelated formatter-only edit
was restored; only the correction's Python files retain formatting changes.
The sole discovered gate file is the root `.hone-gates.json`; all four gates,
including both advisory gates, passed. No coverage minimum is configured in
this repository. No dependencies, versions, release tags or Git refs changed.

Behavioral proof was validated as JSON with the required field types and
existing logs. The six public validator cases rejected the preserved defect
(exit 1) and passed with corrected evidence (exit 0); the probe asserts real
HTTP responses, status/progress/cause and conservative acceptance.
The same probe was rerun successfully on the final source. This proof and the
105-case matrix are local implementation evidence, not paired verification.

## Anthropic assistant history — part 5, issue #2

Owner brief SHA-256 was verified as
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
The referenced `../RELEASE-3.0.0.md` is unavailable in this isolated worktree;
the supplied Foundry initiative brief records the binding owner scope and issue.
This correction implements only assistant-history preservation and the SDK
wiring needed to exercise its existing temperature control. It does not
implement reasoning, model metadata, broader request fidelity or recovery
expansion. The recovery-admission-v2 set above remains unchanged.

The local executable set **anthropic-history-v1** is
[src/mojentic/llm/gateways/anthropic_history_spec.py](src/mojentic/llm/gateways/anthropic_history_spec.py),
SHA-256 `db19a66cbc73500885c6c3bb74e3d727d9330e068adde8ede705701f34b8dfc4`.
All tests below belong to `DescribeAnthropicHistory`; the public SDK completion
and owned recovery paths use real loopback HTTP. Only the owned tokenizer
gateway is mocked, using the existing spec-constrained broker fixture.

| Decision | Named executable verification |
| --- | --- |
| Preserve exact ordered user/assistant contents, including Unicode and empty assistant text | `should_preserve_ordered_history_system_images_controls_and_response` with recovery disabled/enabled |
| Keep system extraction (space-joined, separate field), user/image serialization, tool-message exclusion, config precedence and zero temperature | Same test compares the full decoded request, path and authentication/version headers |
| Keep first text-block response, model, finish reason, usage and absent object/tool calls | Same test checks actual SDK/owned HTTP response evidence |
| Preserve absent system as null, default controls, legacy temperature/num_predict and max_tokens precedence | `should_preserve_legacy_controls_and_absent_system`, six SDK/recovery cases |
| Two-turn ChatSession through LLMBroker sends the first assistant answer with the next query | `should_send_first_assistant_answer_in_second_chat_turn`, SDK/recovery cases compare both exact message lists |
| Eligible 503 then success retains full-history bytes and one logical ID with two distinct nonempty attempt IDs | `should_resend_identical_full_history_with_stable_logical_identity` compares both server-received and captured request bytes, ordered roles/contents and report evidence |
| Unsupported recovery JSON, structured output and tools fail before dispatch; no streaming implementation | Existing `DescribeAnthropicCapabilityBoundary.should_reject_unsupported_configured_json_format_before_dispatch` and `should_reject_unsupported_recovery_before_dispatch` in `cloud_recovery_spec.py` |

Characterization found that locked Anthropic SDK **1.15.0** rejects the old
`temperature=` keyword before HTTP. Passing the identical control through SDK
`extra_body` restores dispatch while retaining its wire value. No dependency
or version changed. Older allowed SDK versions have not been exercised here.
The loopback image payload checks serialization, not live vendor image validity.
Empty assistant content is retained; live vendor/model acceptance is unverified.

### Boundary verification and coordination gap

Provider tested base commit: `1b1ff5e930fe66c3165134bc2cae0e638f30ae6e`
plus this uncommitted correction. The local HTTP suite exercises the Python
client implementation against scripted responses, reusing existing HTTP and
recovery fixtures. These are local executable specifications, not a shared
Anthropic-provider or downstream-consumer contract. No external contract
format, protocol version or consumer repository was changed.

**PY-ANTHROPIC-HISTORY-PAIRED-VERIFICATION (open):** paired consumer and provider
verification against the same versioned executable contract set is unavailable.
Consumer tested commit, command and result: **unavailable, not run**. Live
Anthropic provider tested revision, verification command and result:
**unavailable, not run**. The local `anthropic-history-v1` hash identifies the
cases for coordination; it does not establish cross-repository compatibility.
Any required counterpart work needs separate authorization in its repository.
Keep the publication hold until all six ports meet owner scope and required
paired verification is available. No sibling repository or Git ref was changed.

### Current correction verification

All tool/test commands below run through `foundry capture --log-dir .foundry/logs --`.
The behavioral proof first rejected missing full-history bytes (exit 1), then
passed with the source correction (exit 0), through actual HTTP after 503.
The proof records the actual exit codes and existing logs; it is local evidence.

| Command | Result |
| --- | --- |
| `uv run pytest src/mojentic/llm/gateways/anthropic_history_spec.py --no-cov` | Exit 0; 11 passed on final source (initial hardest probe: exit 1, missing assistant history) |
| `uv run pytest src/mojentic/llm/gateways/anthropic_history_spec.py src/mojentic/llm/gateways/cloud_recovery_spec.py --no-cov` | Exit 0; 120 passed |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0 |
| `uv run pytest` | Exit 0; 1,387 passed, 85% configured coverage |
| `uv run bandit -c .bandit -r src` | Exit 0; zero issues |
| `uv run pip-audit` | Exit 0; no known vulnerabilities |
| `uv run flake8 src` | Exit 0 |
| `uv run ruff check src` | Exit 0; zero findings after correcting fixture import style |
| `uv run ruff format src` | Exit 0; unrelated formatter edit restored; correction files retain formatting |
| `uv run pytest --cov` | Exit 0; 1,387 passed, 86% coverage; no repository coverage minimum configured |
| `uv run mkdocs build` | Exit 0; rerun after final documentation edits |
| `uv export --format requirements-txt --no-emit-project` piped to `uvx pip-audit -r /dev/stdin --disable-pip` under `bash -o pipefail` | Exit 0; no known vulnerabilities |
| `uv pip list --outdated` | Exit 0; available updates reported; no dependencies changed |

The root `.hone-gates.json` is the only discovered gate file. All four gates,
including both advisory gates, passed. The final behavioral proof JSON has the
required string/object/integer fields, rejecting exit 1 and corrected exit 0;
its two existing logs were inspected against the failing/passing test summaries.
The final probe passes all 11 history cases. No advisory suppression was added.
Changes remain in this worktree for Foundry; no commit, push, merge, rebase,
tag, publication, dependency change, version bump or Git ref update occurred.

## October 12 Typed errors decision

This correction implements the Typed errors decision in Python only. The
initiative brief SHA-256 was verified as
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
The authoritative root amendment was read in the read-only `mojentic-unify`
checkout; its SHA-256 is
`a53a3a4eb118fa4687dd703d6ce918dd40dd6cb4eda796abc6c429a6e932e7a3`.
The local October 9 contract copy does not supersede that amendment.

### Characterized behavior and verified decisions

Before the change, invalid policies exposed Pydantic `ValidationError`, missing
policies on explicit recovery APIs raised `ValueError`, capture failures exposed
the raw callback exception, and unsafe stream finishes exposed a generic
`ValueError`. OpenAI shares the oMLX stream decoder and the common stream
consumer. The initial real-HTTP OpenAI probe delivered content, encountered a
length finish and rejected the generic cause; after the source change the same
probe passed with a concrete `LengthTerminationError`, preserved progress,
one wire request and an exact request-body assertion.

Policies now fail with `RecoveryPolicyError` across construction, Python/JSON/
string validation, gateway construction with invalid policy input and explicit
recovery calls missing a policy. Pydantic validation details are not included in
default formatting. Frozen assignment remains unsupported. The policy error is
an `Exception` subtype rather than a Pydantic validator's `ValueError`, which
would otherwise be wrapped back into `ValidationError`.

Wire-hook failures retain `CaptureError` as the concrete inspectable cause;
its own `inspect_cause()` returns the identical original callback exception.
Existing capture evidence specifications were migrated to this explicit
inspection step without weakening their request, semantics, cancellation or
admission assertions. Other hook failures retain their existing types.

Ollama, oMLX and OpenAI recovery streams retain `LengthTerminationError` as a
`ValueError` subtype; other unsafe finishes remain generic protocol failures.
OpenAI structured length rejection carries the same concrete type through
`generate_object`. Ordinary successful length metadata and Ollama/oMLX
structured parsing remain unchanged. Anthropic ordinary-only recovery and
unsupported-operation refusals remain unchanged. ChatSession has no structured
operation. Native raw single-turn event APIs remain separate from recovery.

### Executable verification map

The existing co-located pytest mechanism and scripted HTTP server are reused.
The versioned Python binding is **python-typed-errors-v1** in
[typed_errors_spec.py](src/mojentic/llm/gateways/typed_errors_spec.py), SHA-256
`b42bdbbb3734019738f470a39d51e4e7c036a369b54c69aaf323e1fc269f6137`.
It runs automatically in the required pytest gate. Test responses are scripted
at a real loopback HTTP boundary; no independently authored SDK mocks are used.
The only mock in these caller paths is the existing typed tokenizer gateway.

| Decision | Named test in `DescribeTypedErrorsV1` |
| --- | --- |
| OpenAI delivered content followed by typed length cause, no replay, exact bytes and safe formatting | `should_preserve_typed_length_after_delivered_openai_content` |
| Capture type, exact original exception, identity/history/progress, exact requests and sentinel privacy through every supported sync/async gateway, broker and session operation | `should_preserve_capture_type_original_and_evidence_through_public_callers` |
| Shared stream length handling through gateways, brokers and sessions, including truthful delivered counts | `should_preserve_length_cause_through_stream_consumers` |
| Prior transient HTTP cause retained beside typed capture cause; stable logical identity, distinct attempt IDs and identical resends | `should_retain_prior_failure_and_request_identity_when_capture_stops_a_retry` |
| Capture failure before dispatch or semantics remains terminal with truthful zero/one attempt accounting | `should_stop_capture_before_semantics_without_inventing_attempts` |
| OpenAI structured length rejection through sync/async gateways and broker | `should_retain_typed_length_for_openai_structured_completion` |
| Old ordinary completion length behavior remains successful | `should_preserve_successful_ordinary_length_metadata` |
| Missing policy type on each supported explicit recovery operation, before HTTP | `should_reject_missing_policy_with_the_same_type_before_dispatch` |
| Invalid gateway policy inputs are typed and private for all four adapters | `should_validate_policy_at_gateway_construction_without_disclosing_input` |
| Invalid policy fields, malformed JSON and string validation expose the same safe type | `should_use_one_safe_policy_error_across_validation_entrypoints` |

Existing `recovery_spec.py` covers numeric bounds, NaN/infinity and immutable
policy behavior. Existing capture tests cover reasoning, tool fragments and
completed tools as well as content; the admission tests retain acceptance
`unknown` for connection-shaped exceptions raised by capture hooks. Existing
Anthropic history and capability contracts remain in the full suite.

### Contract identities and coordination gaps

Provider source: `mojentic-py@fe1a94bba6e3ab7fb02c6c17d30cbe3695d449a8`
plus this uncommitted correction. In-repository broker/session consumer source:
the same revision plus this correction, tested with the same executable file
and hash above. Both roles are exercised together by:

```bash
uv run pytest src/mojentic/llm/gateways/typed_errors_spec.py
```

This Python binding is distinct from Elixir's existing `typed-errors-v1`
executable set. Matching the decision name or error schema does not establish
cross-language or cross-repository compatibility. No sibling was changed.
External consumer revision, supported old/new package versions, shared
executable contract identity and consumer verification commands/results are
**unavailable / not run**. Those remain unfinished coordination work; no paired
external compatibility or live provider verification is claimed. The named
Bedrock and microgentic follow-ups remain assigned to their respective ports.
No published 3.0.0 package or external optional-field/version migration was
verified here. The coordinated publication hold remains until all six ports
satisfy owner scope and required paired verification is available.

### Verification results for this correction

All commands used the task's writable uv cache. The exported-lock audit also
used a writable uv tool directory and audit cache after the default read-only
locations rejected writes. Commands were captured with their actual exit codes.

| Command | Result |
| --- | --- |
| `uv run pytest src/mojentic/llm/gateways/typed_errors_spec.py -q` | Exit 0; all 101 Python contract/caller cases pass together |
| `uv run pytest --cov` | Exit 0; 1,541 passed, 86% coverage; no repository coverage minimum is configured |
| `uv run pytest` | Exit 0; 1,541 passed, 85% configured source coverage |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0 |
| `uv run flake8 src` | Exit 0 |
| `uv run ruff check src` | Exit 0; zero findings |
| `uv run --with ruff ruff format src` | Exit 0; unrelated `file_manager_spec.py` formatting restored to keep scope |
| `uv run bandit -c .bandit -r src` | Exit 0; zero issues |
| `uv run pip-audit` | Exit 0; no known vulnerabilities |
| `uv export --format requirements-txt --no-emit-project` piped to `uvx pip-audit -r /dev/stdin --disable-pip`, with `bash -o pipefail` | Exit 0; no known vulnerabilities |
| `uv pip list --outdated` | Exit 0; available updates reported; no dependency changes required by the audits |
| `uv run mkdocs build` | Exit 0; rebuilt after documentation edits |

The sole discovered gate file is the root `.hone-gates.json`; all four gates
passed. An additional explicit complexity diagnostic on the touched recovery
modules and contract file (`ruff check ... --select C901 --config
lint.mccabe.max-complexity=10`) exits 1 solely for the existing OpenAI legacy
`complete` (21) and `complete_stream` (25) methods. Running the same diagnostic
on that file extracted from the tested base commit reproduces both counts.
Neither method was changed by this correction; no new or changed function is
reported over ten. This pre-existing complexity debt remains outside the typed
errors scope; no lint suppression or rule relaxation was added.

Behavioral proof was validated as JSON with string/object/integer fields,
actual rejecting exit 1 and corrected exit 0, and both existing logs inspected.
The rejecting run failed on generic `ValueError` after delivered OpenAI content;
the final corrected run passed all 101 contract cases, including that probe.
Changes remain uncommitted in this worktree for Foundry. No sibling edits,
Git ref updates, version bumps, publication or advisory suppressions occurred.

## Anthropic structured recovery correction — 2026-10-17

This correction implements RELEASE-3.0.0 part 1, “Streaming and immutable
payloads”, for Anthropic Pydantic completion only. It supersedes earlier
ordinary-only support statements. The starting and tested base revision is
`1633b145bc5f8161c161782feb543e6c0cfbf5c5`; the corrected implementation is the
uncommitted worktree on that revision, pending Foundry finalization. The
initiative brief SHA-256 was verified as
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
The authoritative root recovery amendment and release scope were read from
the initiative repository; no files there were changed.

### Verified decisions and executable contract

The existing versioned pytest specification/loopback HTTP mechanism is reused.
Contract `anthropic-structured-v1` is
`src/mojentic/llm/gateways/anthropic_structured_spec.py`, SHA-256
`3b58a2f05c0a7513747291fb3faa1f8924c9ddc6423d0b7cd4e6b71002926686`.
Its scripted provider responses and expected requests are shared by both roles;
neither role mocks SDK internals. Provider verification exercises the real
AnthropicGateway HTTP implementation; the in-repository consumer calls
`LLMBroker.generate_object` through that same implementation and contract cases.

| Decision | Named executable evidence in `DescribeAnthropicStructuredContract` |
| --- | --- |
| Native JSON schema, exact UTF-8 request bytes, ordered assistant/user history and controls; stable logical and distinct attempt identity; safe lifecycle and report metadata | `should_replay_frozen_schema_history_and_controls_at_http_boundary` |
| Same 503-then-success contract and typed result through gateway and broker | `should_verify_identical_recovery_contract_for_gateway_and_broker` |
| One default attempt, bounded exhaustion, permanent 400/401 failures | `should_bound_attempts_and_refuse_permanent_errors` |
| Malformed JSON and schema violations retain `ValidationError`; max_tokens retains `LengthTerminationError` even for valid JSON; no replay | `should_preserve_typed_decode_failures_without_replay` |
| Capture failure preserves observed/undelivered content and `CaptureError` with original cause; no replay | `should_stop_on_capture_failure_with_original_cause` |
| Optional fields present/absent and original Pydantic validation after SDK schema transformation | `should_validate_optional_fields_with_original_pydantic_model`, `should_validate_constraints_removed_from_provider_schema` |
| Schema, history and controls frozen before admission changes caller inputs; explicit rejection/undecided hook never resends | `should_freeze_schema_and_history_before_admission_mutates_inputs`, `should_require_explicit_admission_decision_when_hook_is_present` |

Provider-supported semantics use `output_config.format` (`json_schema`) and
the SDK's public `transform_schema`; local validation retains the original
model's constraints. Source inspected:
[Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
This is documentation evidence for request shape, not a live service check.
The existing `anthropic-version: 2023-06-01` remains the wire version. Ordinary
SDK history/control/default/length behavior remains covered by
`DescribeAnthropicHistory` at actual HTTP. Configured arbitrary JSON formats,
tools and streaming remain unsupported. `DescribeAnthropicCapabilityBoundary`
retains their appropriate rejection/absence assertions. Structured capability
is now true; `should_accept_old_anthropic_unsupported_structured_projection`
keeps old false capability records readable. Facility evidence values remain
unchanged and are still verified by `DescribeRecoveryCapabilitiesV1`.
The updated `recovery-capabilities-v1` artifact SHA-256 is
`6025e3995d4c01e825c5d6a7dec3dc44aa43920a300d9e943aae7dec45f93c7a`;
this identifies the precise operation-flag change and added legacy-record case
without changing the five documented facility guarantees.

Migration: configure a recovery policy for structured requests, including
`RecoveryPolicy()` for one attempt; use the explicit async entrypoint or broker
`generate_object`. No-policy SDK completion retains its existing behavior.
Error consumers inspect the typed cause through `RecoveryError.inspect_cause()`.

### Unfinished counterpart verification and publication hold

Both local roles test the uncommitted Python implementation on the revision
above. No external Anthropic provider revision is available or tested, and no
authorized external consumer repository has verified this executable set.
External counterpart commands/results are **unavailable, not run**. This is an
unfinished initiative coordination finding, not evidence of compatibility with
the service, another port, or downstream repositories. Coordinate verification
against this identical version/hash, recording both tested revisions, commands
and results; preserve old/new capability projections and optional/error cases.
Streaming, tools and unrelated initiative work remain separate. The coordinated
publication hold remains until all six ports and required paired contracts meet
owner scope. No contract ambiguity or unilateral root-contract change was needed.

### Commands and results on the corrected worktree

All verbose checks used `foundry capture`. `UV_CACHE_DIR` was redirected to
`/tmp/mojentic-uv-cache` because the default cache is read-only in this sandbox;
the ephemeral audit also used writable `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR`.
No dependency or version changes were needed.

| Command | Result |
| --- | --- |
| `uv run pytest src/mojentic/llm/gateways/anthropic_structured_spec.py -q` | Exit 0; 30 cases, including shared roles and HTTP proof |
| `uv run pytest src/mojentic/llm/gateways/anthropic_structured_spec.py -q -k 'provider and not consumer'` | Exit 0; 13 provider cases, 17 deselected; contract hash above |
| `uv run pytest src/mojentic/llm/gateways/anthropic_structured_spec.py -q -k consumer` | Exit 0; the same 13 consumer cases, 17 deselected; same hash and tested base/worktree |
| `uv run pytest src/mojentic/llm/gateways/recovery_capabilities_spec.py --no-cov -q` | Exit 0; 54 cases against the updated capability artifact hash above |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; required hone lint gate |
| `uv run pytest` | Exit 0; 1,571 passed; required hone test gate |
| `uv run pytest --cov` | Exit 0; 1,571 passed; 86% overall, Anthropic gateway 94%; no numeric fail-under threshold is configured |
| `uv run flake8 src` | Exit 0 |
| `uv run --with ruff ruff check src` | Exit 0; zero warnings |
| `uv run ruff check src` | Exit 0; zero warnings |
| `uv run bandit -c .bandit -r src` | Exit 0; hone security gate |
| `uv run pip-audit` | Exit 0; no known vulnerabilities; hone audit gate |
| `uv export --format requirements-txt --no-emit-project \| uvx pip-audit -r /dev/stdin --disable-pip` (bash pipefail) | Exit 0; locked dependencies, no known vulnerabilities |
| `uv pip list --outdated` | Exit 0; newer versions listed, no audit findings requiring updates |
| `uv run mkdocs build` | Exit 0 |
| `git diff --check` | Exit 0 |

Changed Python files were formatted with `uv run --with ruff ruff format`;
their format check and C901 check with maximum complexity 10 both pass.
The broader C901 diagnostic reports ten pre-existing violations in untouched
example, Ollama/OpenAI, broker and realtime functions. Whole-source format check
reports the untouched `file_manager_spec.py`. Both diagnostics reproduce on
files extracted from the tested base revision; this correction does not change
them, add suppressions or relax rules. They remain outside this scoped correction.

The behavioral proof records the original rejection (actual exit 1) and
corrected HTTP behavior (actual exit 0); JSON shape/types and both existing logs
were validated and inspected. An early overlapping test run interfered with
coverage storage and hit a read-timeout assertion; subsequent isolated full
runs passed, including that assertion. Intermediate contract assertions were
corrected to match exact SDK schema serialization and the existing no-hook
lifecycle. These failures were not suppressed. Source, tests and documentation
remain uncommitted for Foundry; no Git refs or sibling repositories were changed.

## Native reasoning — release part 2

The binding source is `REASONING-PROTOTYPE-2026-10.md`, SHA-256
`0a40f3ad45c593bc779411021e45db569e73d3ecce86c99b201e7f8ebb656809`,
authorized by release part 2. The Foundry initiative brief was read and its
recorded SHA-256 verified:
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
Python starts at `03a8ca4237ad45b5faedcf284b05c96b73d2afac`; verification below
applies to the uncommitted correction in this worktree. Foundry owns finalization.
Rust was consulted read-only at `17ad0cb1a6b5895f5dbe9f758189d61b266bb336`
(`reasoning.rs` and `tests/reasoning_contract.rs`). No Rust run or modification
is claimed.

### Characterization before implementation

The starting Python `CompletionConfig` accepted only low/medium/high. Ollama's
ordinary and stream builders collapsed all three to `think: true`; oMLX sent
named effort directly. Gateway responses already separated `thinking` from
content, but `LLMMessage` had no native reasoning field. Ordinary and streamed
broker tool continuations retained visible content and tool calls without
reasoning. The first HTTP-boundary probe failed because the broker's second
oMLX request lacked `reasoning_content`; the same probe passed after adding
opt-in completed history. Existing captured oMLX responses from the root
`63409fa` fixture set supplied this proof case.

### Verified decisions mapped to executable tests

All names below are in `src/mojentic/llm/gateways/native_reasoning_spec.py`.
The provider tests send public requests through actual SDK/HTTP transports;
broker consumer tests send the continuation through the same gateway boundary.

| Part-2 decision | Named executable behavior |
| --- | --- |
| Six distinct efforts; omitted effort stays unspecified; no model-name inference | `should_send_exact_controls_without_model_inference`: shared null/disabled/enabled/low/medium/high/xhigh matrix, exact Ollama/oMLX request controls, separate response reasoning and content |
| Caller-selected profiles validate supported effort/history | `should_accept_exact_qwen_profile_controls`, `should_reject_unsupported_qwen_controls`, `should_reject_history_for_a_profile_without_history`, `should_reject_named_effort_for_boolean_only_profile`; Qwen accepts only omitted/disabled/low/medium/xhigh and rejects enabled/high |
| Native assistant history separate from visible content and tool results | `should_retain_native_history_separately_through_tool_continuation` and `should_preserve_distinct_payloads_in_broker_tool_history`: exact native field, content, typed arguments and serialized result; oMLX call IDs and continuation result IDs |
| Broker retention opt-in for completed ordinary and streamed tool turns | `should_preserve_distinct_payloads_in_broker_tool_history`: both providers, retention on/off, ordinary/stream, recovery on/off |
| oMLX requests preserve_thinking; server enforcement not implied | Same continuation test checks the exact `chat_template_kwargs` request; no server override/enforcement claim |
| Structured output uses equivalent controls | `should_send_exact_controls_without_model_inference[structured-*]`: schema request plus exact shared effort matrix |
| Interrupted, failed, capped and cancelled responses never fabricate retained history | `should_not_retain_unfinished_stream_history`, `should_not_fabricate_history_on_stream_failure_or_close`, `should_discard_partial_native_history_when_caller_closes`, `should_reject_incomplete_ordinary_ollama_history`, `should_exclude_capped_ordinary_reasoning_from_history`, `should_discard_reasoning_after_provider_error_frame` |
| Content, tool identity, argument types, ordering and results stay distinct | Continuation tests plus `should_preserve_ordered_multiple_native_tool_calls`; oMLX carries IDs, while the Ollama SDK protocol uses function names/arguments without native call IDs. Ordinary Ollama arguments retain JSON types and all assistant tool calls survive in order |
| OpenAI rejects new controls/history explicitly; legacy behavior remains | `should_reject_new_openai_controls_before_http` and `should_reject_native_history_on_openai`; existing OpenAI specs verify legacy low/medium/high/model adaptation alongside the full regression suite |

The additive `StreamingResponse.completed` signal allows the broker to retain
reasoning only after a safe provider terminal (Ollama done/stop; oMLX safe finish
plus `[DONE]`; recovery completed). It does not change raw recovery admission,
retry policy or provider capabilities. Legacy streams without retention continue
to expose their previous content/thinking/tool chunks. Existing temperature,
context and token defaults remain unchanged; metadata/request fidelity is
separate work. Ordinary capped responses keep legacy handling but contribute no
retained reasoning. Retention requires an explicit completion signal and never
extracts native reasoning from visible content.

### Shared contract identities and verification roles

Reuse `native-reasoning-v1` from Elixir revision
`98b54a0cf0b028b82d38655ac59ebafcd7988077`, copied without modification to
`src/mojentic/llm/gateways/fixtures/contracts/native_reasoning_v1.json`.
SHA-256: `be212ff011125f1d0927e3a65a0d7cd87eedbf9f5ff69e803b4112a80ae6b1f6`.
The source hash inside it matches the binding reasoning contract above. The
Python executable set derives controls, tool request, tool result, native
reasoning and visible content from this same fixture; these are behavioral HTTP
checks, not schema-only or independently authored gateway mocks.

Local provider adapter verification:

```bash
uv run pytest src/mojentic/llm/gateways/native_reasoning_spec.py -k 'exact_controls or qwen or profile or openai or ordered_multiple' --no-cov
```

Local broker consumer verification against the same executable set:

```bash
uv run pytest src/mojentic/llm/gateways/native_reasoning_spec.py -k 'tool_continuation or broker_tool_history or unfinished or failure_or_close or partial_native or incomplete_ordinary or capped_ordinary or provider_error_frame' --no-cov
```

The ordinary `uv run pytest` repository gate executes both roles. Exact command
results and the final executable-set hash are recorded below.

**Unfinished external counterpart verification:** the oMLX/Ollama servers and
external consumers have not run this executable set here. Their tested revisions,
commands and results are unavailable. Elixir's counterpart command is
`scripts/verify-native-reasoning-contract`, but it was only inspected, not run.
Rust reference tests were only read. The shared fixture alone does not establish
cross-port or live-provider compatibility. Forced server thinking settings,
model efficacy, stochastic benchmarks and external outer-turn retention remain
unverified. Coordinate those runs in their authorized repositories; no sibling
repository was changed. Preserve the coordinated publication hold until all six
ports satisfy the owner scope and required paired verification is available.

### Native reasoning correction verification results

Executable Python set SHA-256 (`native_reasoning_spec.py`):
`59a73d635c3fc8c7186df15662c8eb821eca5e53fae8c79b016ff1c6d8a9e4d5`.
Both local roles below ran on Python base
`03a8ca4237ad45b5faedcf284b05c96b73d2afac` plus this uncommitted correction,
against the shared `native-reasoning-v1` fixture hash above.

| Verification command | Result |
| --- | --- |
| Local provider command above | PASS: 202 passed, 29 deselected |
| Local broker consumer command above | PASS: 29 passed, 202 deselected |
| `.hone-gates.json` lint: `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | PASS: 0 errors |
| `.hone-gates.json` test: `uv run pytest` | PASS: 1,802 tests; 85% coverage over `src` |
| Required explicit coverage run: `uv run pytest --cov` | PASS: 1,802 tests; 87% over imported modules (bare `--cov` differs from the configured `--cov=src` scope) |
| Full lint: `uv run flake8 src` | PASS |
| `uv run --with ruff ruff check src` | PASS: zero findings; Ruff supplied ephemerally without dependency changes |
| `uv run --with ruff ruff format` on the changed Python files | PASS; formatting scoped to this correction |
| `.hone-gates.json` security scan: `uv run bandit -c .bandit -r src` | PASS: no issues |
| `.hone-gates.json` dependency audit: `uv run pip-audit` | PASS: no known vulnerabilities |
| `uv export --format requirements-txt --no-emit-project \| uvx pip-audit -r /dev/stdin --disable-pip` with shell pipefail | PASS: no known vulnerabilities in exported locked dependencies |
| `uv pip list --outdated` | PASS: inventory reviewed; no advisory finding required an upgrade in this correction |
| `uv run mkdocs build` | PASS |
| `git diff --check` | PASS |

The repository has no configured coverage minimum. The full source coverage
figure above includes unimported modules. In this restricted worktree, commands
used a writable `UV_CACHE_DIR` under `/tmp`; the ephemeral audit also used writable
`UV_TOOL_DIR`/`UV_TOOL_BIN_DIR`. An initial default-cache permission failure was
resolved by those paths, without changing dependencies or suppressing advisories.
The first full regression run exposed seven recovery assertions for the obsolete
`think: true` mapping of `high`; they now assert exact `"high"` while preserving
immutable retry bytes and the original recovery checks.

Behavioral proof JSON and its rejecting/passing logs were validated for their
shape, types, observed exit codes (1 and 0), existence and actual failure/pass
results. They remain Foundry scratch evidence, outside committed project paths.
External counterpart verification remains **unfinished** as described above;
these local results do not authorize publication, and no Git finalization or
version change was performed.
