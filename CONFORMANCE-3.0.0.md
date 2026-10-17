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
SHA-256: `c780d497a8202fa4fb509b543a02e39bb06f8ae923e4752c3b42ce6ac503252c`.
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
- Native reasoning, model metadata/request fidelity and remaining initiative audit
  fixes remain **unverified here** and outside this correction. Anthropic history
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
