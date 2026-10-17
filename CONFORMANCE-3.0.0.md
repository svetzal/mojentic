# Python 3.0.0 readiness self-assessment — October 17, 2026

This assessment supersedes the partial status and historical unverified statements
below. It evaluates RELEASE-3.0.0 parts 1–5 from Python baseline
`a3637ba7aad18ac0688a5aa98c6708648988eb69` plus the working-tree changes identified
in [the source manifest](docs/release_3_0_0_source.sha256). No version or Git ref
was changed. The unpublished candidate still identifies itself as **2.1.0**;
it must not be confused with the released 2.1.0 package.

The assessment covers library readiness, not live vendor certification or the
readiness of any other port. Publication remains held until all six ports meet
owner scope and the owner authorizes the coordinated release. Current commands,
results, artifact identities and import provenance appear in the verification
record following the decision maps.

## Binding inputs and authorization

The Foundry initiative brief was read and its recorded SHA-256 verified:
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
The read-only authoritative `mojentic-unify` checkout was at
`ef9339c6a9682ed5f060bd690b738f6b8eea1d2d`. Its binding documents hash to:

| Document | SHA-256 |
| --- | --- |
| RELEASE-3.0.0.md | `ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e` |
| TRANSIENT-RECOVERY-2026-10.md, including October 12 | `a53a3a4eb118fa4687dd703d6ce918dd40dd6cb4eda796abc6c429a6e932e7a3` |
| REASONING-PROTOTYPE-2026-10.md | `0a40f3ad45c593bc779411021e45db569e73d3ecce86c99b201e7f8ebb656809` |
| MODEL-METADATA-2026-10.md, including October 17 timing decisions | `d9945dca45ce09e2163843263a75b5e93028b00ee1baf191fc3ff13396830e9c` |

AGENTS.md already records Stacey's October 15 authorization for the full 3.0.0
scope, the October 17 library self-validation policy and coordinated publication
hold. Its narrower timing-correction description is historical task context,
not a restriction on this explicitly authorized final assessment. No additional
authorization is required for this assessment. Part 4 (removing iOS targets) is
**Kotlin-specific**. Part 5's Python issue #2 is verified below; Rust issue #3
and TypeScript issue #4 belong to those ports and are not claimed here.

## Current executable decision map

Names below are executable pytest methods; file names refer to
`src/mojentic/llm/gateways/` unless prefixed by `llm/`. Each listed test passed in
the final suite. All supported provider variants are collected by the normal
pytest gate. These reuse the existing executable contracts and captured provider
fixtures; no binding contract or shared JSON was changed.

### Part 1: base recovery contract

| Binding decision | Named executable evidence |
| --- | --- |
| Recovery owns one completion, never agent/tool replay; retries off by default | `ollama_recovery_spec.py::should_preserve_legacy_success_and_one_send_by_default`, `should_execute_tool_once_and_recover_only_the_subsequent_completion`; `ollama_stream_recovery_spec.py::should_keep_raw_event_api_single_turn_with_recovery_configured`, `should_keep_retry_accounting_separate_from_tool_depth` |
| Stable provider/operation/category, numeric status, phase/acceptance, identity, bounded history and private inspectable cause | `cloud_recovery_spec.py::should_recover_503_with_literal_bytes_private_evidence_and_exact_lifecycle`, `should_bound_504_with_complete_history`; `provider_metadata_spec.py::should_preserve_exact_validated_metadata_in_terminal_public_evidence` |
| Headers/raw bytes vs observed/delivered reasoning, content, fragments and completed tools; keepalive is raw only | `ollama_stream_recovery_spec.py::should_retain_observed_evidence_on_capture_failure_without_replay`; `completed_tool_recovery_spec.py::should_report_completed_calls_and_execute_each_once`; `omlx_recovery_spec.py::should_require_admission_after_keepalive_and_reset_frame_indices` |
| Safe default strings/repr/JSON/logs/events exclude payloads, credentials, arguments and causes | `omlx_recovery_spec.py::should_keep_echoed_secrets_out_of_safe_errors_events_and_logs`; `ollama_recovery_spec.py::should_keep_uuid_shaped_secret_echoes_private`; `llm/recovery_spec.py::should_keep_callback_secrets_out_of_policy_serialization_and_repr` |
| Positive attempts; delay/budget configuration validated; capped exponential full jitter, overflow avoided | `llm/recovery_spec.py::should_reject_invalid_recovery_policy`, `should_bound_exponential_jitter_without_overflow`; `ollama_recovery_spec.py::should_honor_retry_after_without_shortening_minima` |
| Default transport/429/500/502/503/504 eligibility; caller category/status controls; permanent authentication/request and malformed responses excluded | `omlx_429_recovery_spec.py::should_recover_429_only_after_admission_with_exact_wire_evidence`; `readiness_boundary_spec.py::should_apply_selected_eligibility_and_recover_server_errors`; `cloud_recovery_spec.py::should_bound_504_with_complete_history`; `ollama_recovery_spec.py::should_never_replay_permanent_status_even_when_body_transport_fails`, `should_reject_malformed_provider_responses_without_replay` |
| Retry-After seconds, HTTP dates, past/invalid/absent values; provider minimum never shortened by ceiling or budget | `llm/recovery_spec.py::should_parse_retry_after_without_serializing_untrusted_text`; `ollama_recovery_spec.py::should_honor_retry_after_without_shortening_minima`; `ollama_stream_recovery_spec.py::should_refuse_excessive_retry_after_without_admitting` |
| Budget starts on first failure, deadline constrains admission/backoff/resend, never times out admitted active generation | `ollama_recovery_spec.py::should_expire_budget_while_admission_is_pending`, `should_refuse_admission_that_consumed_the_recovery_budget`, `should_allow_active_generation_to_finish_after_recovery_deadline`, `should_refuse_callback_expiry_without_phantom_retry`; `cloud_recovery_spec.py::should_leave_active_generation_without_a_fixed_read_timeout` |
| Cancellation authoritative before dispatch, active HTTP, admission and delay; local resources close; no remote termination claim | `ollama_recovery_spec.py::should_cancel_before_dispatch_without_inventing_wire_attempt`, `should_cancel_active_request_retaining_headers_and_raw_progress`, `should_cancel_pending_waits_and_never_resend`, `should_make_native_task_cancellation_authoritative`; `openai_recovery_lifecycle_spec.py::should_cancel_active_request_and_close_local_socket` |
| Hook receives exact identity/progress; allow/reject/wait; local ambiguity needs permission, remote may retry | `recovery_admission_spec.py::should_apply_admission_without_changing_retry_bytes`, `should_stop_pending_admission`; `openai_recovery_lifecycle_spec.py::should_leave_admission_pending_until_explicit_allow` |
| Connection nonacceptance requires actual trace evidence; timeout/empty output/504 cannot prove termination | `recovery_admission_spec.py::should_retry_evidenced_connection_refusal_without_hook`, `should_not_invent_nonacceptance_from_a_capture_hook_exception`, `should_keep_acceptance_unknown_when_caller_validation_fails`; `ollama_recovery_spec.py::should_require_admission_after_an_actual_read_timeout` |
| Logical ID stable, attempts unique, one-based wire counts; no invented idempotency or hidden SDK retries/redirects | `recovery_admission_spec.py::should_apply_admission_without_changing_retry_bytes`; `cloud_recovery_spec.py::should_not_follow_redirects`; `ollama_recovery_spec.py::should_not_follow_redirects_or_count_hidden_attempts`; exact literal request/header assertions and capability tests |
| Immutable ordinary/structured/streaming payload, including messages, images, schema, tools, reasoning and sampling | `cloud_recovery_spec.py::should_reuse_frozen_literal_bytes_after_admission_mutates_caller_inputs`, `should_freeze_model_specific_controls_and_tool_capabilities`; `ollama_recovery_spec.py::should_freeze_images_and_controls_once_before_admission`; `anthropic_structured_spec.py::should_freeze_schema_and_history_before_admission_mutates_inputs` |
| After any semantic output, report interruption with failure/progress/history; exhaustion never succeeds | `readiness_boundary_spec.py::should_surface_partial_semantics_without_replay_through_public_streams`; `ollama_stream_recovery_spec.py::should_bound_persistent_504_history`; `openai_recovery_lifecycle_spec.py::should_interrupt_observed_semantics_without_replay` |
| Completed tools execute once; continuation recovery does not reset tool depth; session never inserts incomplete assistant | `completed_tool_recovery_spec.py::should_report_completed_calls_and_execute_each_once`; `ollama_stream_recovery_spec.py::should_execute_completed_tool_once_and_preserve_subsequent_failure`, `should_keep_retry_accounting_separate_from_tool_depth`; `readiness_boundary_spec.py::should_surface_partial_semantics_without_replay_through_public_streams` |
| Typed lifecycle transitions with exact IDs, phase/progress, delay and safe failure fields; explicit opt-in wire trace including final failures | `cloud_recovery_spec.py::should_recover_503_with_literal_bytes_private_evidence_and_exact_lifecycle`; `ollama_recovery_spec.py::should_capture_the_authenticated_request_actually_sent`; `readiness_boundary_spec.py::should_apply_selected_eligibility_and_recover_server_errors` |
| Typed capture/observer failures do not authorize replay; exact original evidence remains inspectable | `typed_errors_spec.py::should_preserve_capture_type_original_and_evidence_through_public_callers`; `ollama_recovery_spec.py::should_keep_observer_exceptions_private_and_prohibit_replay`; `cloud_recovery_spec.py::should_observe_content_before_failing_capture_without_delivery_or_replay` |

Harness experiment registration, Generation45 preservation and live efficacy are
application/experiment responsibilities; no harness, stopped benchmark or remote
application was changed. No claim about the original 504's origin is made.

### Part 1: every October 12 robustness decision

| Amendment decision | Named executable evidence |
| --- | --- |
| 1. No-hook remote retries; ambiguous local admission-required except proven nonacceptance | `recovery_admission_spec.py::should_apply_admission_without_changing_retry_bytes`, `should_retry_evidenced_connection_refusal_without_hook` |
| 2. Hook ends without decision: distinct `admission_undecided`, never permission or rejection | Same admission matrix and `should_surface_undecided_through_synchronous_public_apis` |
| 3. Five facilities on all four gateways; endpoint citations/date/basis; exact termination unknown | `recovery_capabilities_spec.py::should_report_local_cancellation_with_endpoint_evidence`, `should_report_remote_cancellation_with_endpoint_evidence`, `should_report_request_status_with_endpoint_evidence`, `should_report_idempotency_with_endpoint_evidence`, `should_report_exact_attempt_termination_with_endpoint_evidence`; legacy/new round-trip tests preserve supported serialized versions |
| 4. Allowlisted provider codes; IDs never credential/payload echoes; native provider field names | `provider_metadata_spec.py::should_reject_uuid_shaped_outbound_echoes_but_keep_private_wire`, `should_reject_recognized_error_code_echoes`, `should_preserve_anthropic_request_id_and_error_type`, `should_propagate_exact_metadata_through_public_broker_and_session` |
| 5. IMF-fixdate, RFC 850, asctime dates | `llm/recovery_spec.py::should_parse_retry_after_without_serializing_untrusted_text`; injected wall clocks and exact delay assertions in provider Retry-After specifications |
| 6. Closed provider and ordinary/structured/streaming operation vocabularies | `recovery_admission_spec.py::should_apply_admission_without_changing_retry_bytes` checks all supported provider/operation pairs; `typed_errors_spec.py::should_preserve_capture_type_original_and_evidence_through_public_callers` propagates typed Failure/RecoveryReport models; closed Literal fields enforce the vocabulary |
| 7. oMLX keepalive changes only raw progress, not frame index or provider metadata | `omlx_recovery_spec.py::should_require_admission_after_keepalive_and_reset_frame_indices`; `first_token_spec.py::should_measure_first_wire_frame_and_terminal_errors`; `omlx_stream_spec.py::should_drop_frames_whose_model_is_keepalive` |
| 8. Typed policy error on every validation/entrypoint; typed capture/length through broker/session | `typed_errors_spec.py::should_reject_missing_policy_with_the_same_type_before_dispatch`, `should_validate_policy_at_gateway_construction_without_disclosing_input`, `should_use_one_safe_policy_error_across_validation_entrypoints`, `should_preserve_capture_type_original_and_evidence_through_public_callers`, `should_preserve_length_cause_through_stream_consumers`; Anthropic structured decode/length tests |
| 9. Public broker/session partial reasoning/content/tools, safe lifecycle fields, selected categories/statuses, HTTP 500/502 | `readiness_boundary_spec.py::should_surface_partial_semantics_without_replay_through_public_streams`, `should_apply_selected_eligibility_and_recover_server_errors`: real HTTP, exact relevant request bodies, private original response, typed terminal and exact safe failure fields/delays |
| Python default formatting/reflection idiom, cancellation scope, naming | Privacy tests above cover repr/serialization/logging and explicit inspection; `openai_recovery_lifecycle_spec.py::should_cancel_while_terminal_telemetry_consumption_is_paused`; `ollama_stream_recovery_spec.py::should_close_local_resources_when_iterator_is_closed`; no remote inference termination is inferred from local close |

### Part 2: native reasoning

All names in this table are in `native_reasoning_spec.py`.

| Binding decision | Named executable evidence |
| --- | --- |
| Separate native reasoning/content/tool results; exact provider fields | `should_send_exact_controls_without_model_inference`, `should_preserve_distinct_payloads_in_broker_tool_history`, `should_preserve_ordered_multiple_native_tool_calls` |
| Disabled/Enabled/Low/Medium/High/XHigh remain distinct; omission unknown | `should_send_exact_controls_without_model_inference`: unchanged shared null and six-effort matrix through ordinary/structured/streaming/recovery, exact wire controls |
| Caller selects profile, never inferred from alias; supported efforts/history validated | `should_accept_exact_qwen_profile_controls`, `should_reject_unsupported_qwen_controls`, `should_reject_history_for_a_profile_without_history`, `should_reject_named_effort_for_boolean_only_profile`; generic alias control matrix |
| Qwen3.8 accepts disabled/low/medium/xhigh and native history | Exact Qwen profile acceptance/rejection tests above |
| Retention opt-in; completed ordinary and streamed tool responses only | `should_preserve_distinct_payloads_in_broker_tool_history` with retention on/off and recovery on/off; `should_retain_completed_recovery_ollama_history_and_execute_tool_once` |
| Never fabricate native history from cancelled, erroneous, incomplete or capped replies | `should_not_retain_unfinished_stream_history`, `should_not_fabricate_history_on_stream_failure_or_close`, `should_discard_partial_native_history_when_caller_closes`, `should_reject_incomplete_ordinary_ollama_history`, `should_reject_incomplete_recovery_ollama_history`, `should_exclude_capped_ordinary_reasoning_from_history`, `should_discard_reasoning_after_provider_error_frame` |
| oMLX preserve_thinking requested with retention, not proof of forced server enforcement | `should_retain_native_history_separately_through_tool_continuation`, `should_preserve_distinct_payloads_in_broker_tool_history` |
| Structured controls match ordinary/streaming | `should_send_exact_controls_without_model_inference[structured-*]` and `[recovery_structured-*]` |
| OpenAI new controls/history fail explicitly; legacy model adaptation retained | `should_reject_new_openai_controls_before_http`, `should_reject_native_history_on_openai`; existing OpenAI and request fidelity model-control specifications |

No local model, stochastic benchmark, harness context-accounting or outer-turn
retention experiment is certified by these library tests.

### Part 3: metadata, request fidelity and client timing

| Binding decision | Named executable evidence |
| --- | --- |
| Single-purpose context lookup returns positive window/source, None for unadvertised, typed error for malformed/non-2xx/transport | `context_window_spec.py::should_verify_provider_semantics_and_exact_http_request`, `should_distinguish_transport_failure`, `should_return_not_advertised_for_unsupported_gateway`: all unchanged context-window-v1 cases |
| oMLX authenticated configured endpoint, exact model ID; Ollama POST show, any architecture suffix, optional model_num_ctx; OpenAI exact registry/no HTTP | `context_window_spec.py::should_select_exact_model_through_authenticated_http`, `should_verify_provider_semantics_and_exact_http_request`, `should_lookup_only_exact_registry_entries_without_http` |
| Effective window caller/model/default precedence and clamp; unknown remains None, advertised-only is upper bound | `context_window_spec.py::should_apply_helper_precedence_and_clamping` |
| Discovery changes no subsequent completion bytes | `context_window_spec.py::should_leave_same_model_completion_request_unchanged_after_discovery`: now compares raw completion bodies as well as parsed semantics for every provider case and control combination; `should_preserve_registry_completion_semantics_after_discovery`: both OpenAI registry variants compare literal HTTP completion bodies, exact model and token-limit semantics, and exactly two completion POSTs |
| Omitted/null temperature/num_ctx/max_tokens off wire; zero preserved; sole output limit max_tokens maps once per provider | `request_fidelity_spec.py::should_execute_shared_cases`, `should_preserve_controls_through_broker_events`, `should_preserve_controls_and_history_through_session_stream`; `llm/completion_config_spec.py::should_use_default_values` |
| No gateway/deprecated broker defaults; session trimming budget remains local | `request_fidelity_spec.py::should_omit_controls_for_gateway_keywords_without_config`, `should_forward_only_explicit_deprecated_broker_keywords`, `should_omit_unset_session_controls_at_http_boundary`; session trimming specifications |
| top_p all gateways; top_k Ollama/oMLX/Anthropic; fixed temperature adapts only explicit controls; unsupported effort warns/drops | Shared fidelity cases plus `should_adapt_only_explicit_temperature_to_registered_fixed_value`, `should_warn_and_drop_effort_for_non_reasoning_model` |
| Required Anthropic output limit uses registry maximum/unknown 4096; oMLX has none; explicit values win | `request_fidelity_spec.py::should_apply_only_required_fallback_and_explicit_controls`, `should_reproduce_supported_former_sdk_and_config_limits`; shared unset/null cases |
| Migration reproduces supported old controls; immutable controls/history across retries/tool continuations | `request_fidelity_spec.py::should_forward_only_explicit_deprecated_broker_keywords`, `should_keep_controls_and_tool_history_on_admitted_resend`; Unreleased migration notes and broker guide |
| Monotonic clock starts at dispatch after request capture, not lazy construction; optional first-token kind/time and terminal duration on success/failure | `first_token_spec.py::should_exclude_capture_and_lazy_delay_at_actual_dispatch`, `should_measure_supported_public_routes`, `should_report_dispatched_failure_without_inventing_tokens`; `llm/stream_timing_spec.py::should_measure_exact_first_token_and_duration_with_injected_monotonic_clock`, `should_report_empty_completion_without_inventing_a_first_token`, `should_not_read_the_clock_before_dispatch` |
| First token only; ignore keepalive/empty frames; thinking > content > tool arguments in a shared frame | `first_token_spec.py::should_measure_first_wire_frame_and_terminal_errors`, `should_measure_argument_fragment_before_later_failure`, `should_ignore_token_frames_after_terminal_proof`; deterministic injected-clock tests above |
| Retry clock stays on first logical dispatch; continuation gets new clock; provider metrics retained separately | `first_token_spec.py::should_include_admitted_retry_delay_on_one_clock`, `should_reset_continuation_clock_and_preserve_exact_tool_history`; `ollama_stream_recovery_spec.py::should_emit_exact_length_terminal_progress_metrics_then_failure`, `should_preserve_only_reported_completion_evidence` |
| Supported close/cancellation retains timing, unsent closes do not invent it; malformed choices preserve parser errors; old optional metadata readable | `first_token_spec.py::should_retain_recovery_timing_immediately_after_public_close`, `should_leave_unsent_recovery_close_without_timing`, `should_keep_timing_on_explicit_recovery_cancellation`, `should_preserve_invalid_stream_event_for_noniterable_choices`, `should_preserve_content_timing_before_invalid_choices`, `should_accept_old_evidence_without_optional_client_fields` |
| Public guides, changelog and parity records for all three capabilities | `docs/model_context_window.md`, `docs/streaming.md`, `docs/broker.md`, `CHANGELOG.md` Unreleased and `PARITY.md`; MkDocs build verifies documentation wiring |

The deterministic clock checks supplement the real HTTP timing acceptance suite;
no library internals are mocked. StreamClock accepts an optional clock solely to
make exact timing semantics testable; its production default remains monotonic.
A later public HTTP timing mutation check rejected an intentionally constant
production clock (0ms rather than measured dispatch-to-thinking delay), then passed
after restoring the monotonic default. It followed the initial 111-test passing
acceptance and the first full suite; it is not evidence of an initial rejecting
probe. The recovered command, selected identities and actual results, including
separate verifier errors, are in [the acceptance record](docs/release_3_0_0_acceptance.json).
The temporary fault is absent from the candidate.

### Part 5 Python history audit and release records

`anthropic_history_spec.py::should_preserve_ordered_history_system_images_controls_and_response`
verifies ordinary SDK and recovery-backed public calls with exact expected full
history, Unicode, empty assistant messages, system extraction, images, controls
and response semantics. `should_resend_identical_full_history_with_stable_logical_identity`
compares literal UTF-8 HTTP bodies across a 503 retry and verifies full failure
metadata and actual stable/unique identities. The same file's two-turn session
tests verify prior assistant history through ordinary and recovery public routes.
Anthropic structured recovery is additionally exercised in `anthropic_structured_spec.py`.

CHANGELOG Unreleased was reconciled against `git log v2.1.0..HEAD` and the source
diff, including recovery, native reasoning, metadata, timing, request fidelity,
Anthropic history/SDK adaptation, FileManager containment, dependency maintenance,
formatting, and breaking API/migration notes. The stale ordinary-only Anthropic
entry was removed. Repeated Added/Fixed headings were consolidated. AGENTS.md's
3.0.0 authorization and PARITY.md rows already match owner scope; no artificial
rewrite or version bump was needed.

## Reconciliation and remaining limits

Historical entries below describe the source and commands at their own dates;
their source/artifact manifests are not claims about this candidate. In particular:

- Ordinary-only Anthropic recovery is superseded by ordinary **and structured**
  recovery; streaming/tools/JSON-mode recovery remain explicitly unsupported.
- The old metadata source hash predates the October 17 timing amendment. Current
  behavior tests the three added rules; shared fixture identities are unchanged.
- Old statements that metadata/request fidelity/reasoning/timing are future work
  are superseded by the current decision map and final executions.
- Old missing counterpart snapshots, external consumer runs and manifest mismatch
  observations remain historical facts, but are not unreleased-library blockers
  under the October 17 self-validation policy. No changed running service boundary
  needs another repository's authorization or contract verification in this task.
- Vendor live behavior, remote termination of an exact inference attempt, forced
  oMLX server settings, stochastic efficacy and the readiness of other ports are
  unverified. Capabilities retain their documented unsupported/unknown values.
- Python supports 3.11+; this run uses Python 3.13.15 on Linux. Other interpreters
  and platforms are not certified by this local run. Existing complexity debt is
  reported with the quality results; it is not suppressed.

No genuine unresolved contract ambiguity was found. No dependent adoption,
external executable snapshot, benchmark or live vendor credential is required
to establish this library's declared fixture behavior. The coordinated owner
publication hold remains authoritative.


## OpenAI raw-request evidence correction (cycle 15)

The regression in `context_window_spec.py` now captures the literal request bodies
received over HTTP from production `OpenAIGateway.complete` before and after
public `get_model_context_window`. Both `gpt-5.4` and `o1-custom` retain response
content, exact model identity, the registry-selected token-limit parameter with
value 17, parsed request equality and exactly two POSTs to `/v1/chat/completions`.
Literal byte equality is asserted after those checks; metadata lookup sends no
HTTP request. Production source, dependency versions and binding fixtures are
unchanged.

Before broader validation, the focused two-case command was exercised against a
temporary production mutation that appended one space to the second request body
after metadata lookup. All preceding semantic assertions passed; both literal
byte assertions failed (exit 1, two failed/229 deselected). Restoring production
source passed the same command (exit 0, two passed/229 deselected):

```bash
uv run pytest src/mojentic/llm/gateways/context_window_spec.py \
  -k should_preserve_registry_completion_semantics_after_discovery --no-cov -v
```

The initial mutation harness used an `httpx` stream with the SDK's `httpx2` client
and raised a transport type error. That verifier error is retained separately;
it is not the behavioral rejection. The corrected mutation preserves the actual
request stream type and reaches the HTTP server. No mutation remains in source.
Foundry retains complete rejecting/passing logs, actual process exit codes and
validated behavioral proof separately from repository documentation.

The [recovered historical acceptance record](docs/release_3_0_0_acceptance.json)
identifies the original session and archived log hashes. The earliest recovered
command selected all of `anthropic_history_spec.py` and `first_token_spec.py`,
passing 111 cases in 14.59s on clean baseline `44e416eb87b30859cc5628a0d51b6ff95d987048`
before expansion. Its focused coverage was 47%, not whole-suite coverage. Its
quiet output has no individual node IDs; all 111 identities were recovered from
the archived final JUnit, with both module sources verified byte-identical to
that baseline. The original command was:

```bash
UV_CACHE_DIR=/tmp/mojentic-uv-cache foundry capture --log-dir .foundry/logs -- \
  uv run pytest src/mojentic/llm/gateways/anthropic_history_spec.py \
  src/mojentic/llm/gateways/first_token_spec.py -q
```

That original command includes its historical scratch log argument for faithful
provenance; it is not a repository artifact reference. The first full suite
subsequently passed 2,565 tests. Expanded test drafts separately produced session
signature/expected-phase verifier errors, and the injected-clock draft produced
five unsupported-parameter TypeErrors. The later constant-clock HTTP mutation
failed one test with 99 deselected and passed after restoration. These are
separate events. No initial rejecting acceptance run was recovered; chronology
beyond the retained session and logs is unverified.

### Final candidate identities and validation

Tested baseline is `a3637ba7aad18ac0688a5aa98c6708648988eb69` plus this
uncommitted correction. The refreshed [source manifest](docs/release_3_0_0_source.sha256)
hashes to `bb7f81d1984b36541e33d2f4805177c3d1cf69fb7ae03e219f399a04a79ac7f7`.
The narrower timing verifier's `--source-id` manifest reports
`7a37c558d2b3d703cdc1bde2679e6596aae67fdbfafa805dca04406efa81bd3f`.
All 129 named decision-map methods passed among 2,636 collected cases. The
unchanged context-window-v1 and request-fidelity-v1 fixture hashes remain
`cfeee4702c0dd3b18e02fbd0c8bad82ae58ee1ca7eadcfd21683479ba24f3dc4`
and `6f02088311f50707b9c12154d888f844928c23d359043cb2e5d5654bf7e5eaea`.

| Final command/check | Actual result |
| --- | --- |
| Focused OpenAI regression command above | Exit 0; 2 passed, 229 deselected, after the byte-only rejecting mutation |
| All four `.hone-gates.json` commands | Exit 0 each: critical Flake8 lint, `uv run pytest` (2,636 passed), Bandit (zero issues), `uv run pip-audit` (no known vulnerabilities) |
| `uv run pytest --cov --cov-fail-under=85 --cov-report=term --junitxml=<scratch-result>` | Exit 0; 2,636 passed, 87.46% coverage, enforced 85% minimum |
| `uv run flake8 src` and `uv run ruff check src scripts/verify_readiness.py` | Exit 0 each; zero findings |
| Ruff format/check and Flake8 `--max-complexity=10` on the changed regression | Exit 0 each |
| `uv run ruff format src` | Exit 0; unchanged `file_manager_spec.py` formatting restored to preserve scope; candidate source unchanged |
| Locked requirements export piped to `uvx pip-audit -r /dev/stdin --disable-pip`, with pipefail | Exit 0; no known vulnerabilities, no suppressions |
| `uv pip list --outdated` | Exit 0; inventory reviewed; no advisory-driven upgrade required by either audit |
| `uv run mkdocs build` and `uv build` | Exit 0 each |

All commands and stdout/stderr hashes are in the refreshed
[validation record](docs/release_3_0_0_validation.json). Commands use writable
`UV_CACHE_DIR=/tmp/mojentic-c15-uv` and separate temporary tool/audit caches.
Existing full-tree optional formatting/complexity debt remains historical;
this correction changes only the regression and evidence records.

| Unpublished artifact, unchanged version | SHA-256 |
| --- | --- |
| `mojentic-2.1.0-py3-none-any.whl` | `6406b8fa60ea2f47e3e89041458f16c309fc942c2a6372d239153f3618446211` |
| `mojentic-2.1.0.tar.gz` | `29eb7262d4b5c0cba5b8448b71db0cd448e695c0857d3957d10e8a2914c1fc06` |

A new virtual environment at `/tmp/mojentic-c15-consumer-lcn2_j02/.venv`
installed this wheel with `uv pip install --python <consumer-python> <wheel>`.
Both existing public consumer verifiers passed through `uv run --no-project
--directory <consumer> --python <consumer-python>`: `scripts/verify_readiness.py
<checkout>` and `scripts/verify_stream_timing.py <first-token-fixture>`.
Imports resolved to `/tmp/mojentic-c15-consumer-lcn2_j02/.venv/lib/python3.13/site-packages/mojentic/__init__.py`;
all 165 packaged Python sources match this candidate byte-for-byte.

An additional temporary consumer probe, identified by its exact command and
SHA-256 in the validation record, reused the existing verifier's HTTP endpoint
and request-fidelity-v1 response bytes with the installed OpenAI gateway. Both
`gpt-5.4` and `o1-custom` passed literal before/after body equality, content,
model/token-limit assertions and exactly two completion POSTs. Its first run
passed those assertions but failed a diagnostic print on a nonexistent fixture
`id` key; correcting that print and rerunning passed (exit 0). This verifier
error is recorded separately from behavioral outcomes.

Provider and consumer roles therefore verify the same source, artifact and
unchanged contracts through real HTTP. No other repository boundary changed.
Live vendors, other ports, and owner release authorization remain unverified;
the coordinated publication hold remains. No production source, version,
contract, Git ref or sibling checkout was changed.

The cycle-14 tables that follow are historical and do not identify this candidate.

## Historical cycle-14 verification record and recommendation

**Python's owner feature scope is implemented and its library self-validation
passes. Recommend escalation to the owner for the coordinated release go-ahead.**
This is a readiness recommendation, not permission to publish: Foundry still
owns Git finalization and candidate CI, every other port must satisfy owner
scope, and the owner must authorize the coordinated release. Existing baseline
formatting/complexity debt below is explicitly retained for review.

The final source manifest SHA-256 is
`a8a7a7a3dde1d69f5aa6fb8167a3b6c66e0981795e84587cb613fc85093cc610`.
It identifies runtime code, tests, fixtures, verifier scripts and build/test
configuration; the evolving assessment/results themselves are excluded to avoid
self-referential hashes. Every manifest entry was rehashed successfully, and all
Python files in the final wheel were compared byte-for-byte with current source.
The older context-window source manifest remains historical, not a current
snapshot assertion. Machine-readable outcomes and log-content hashes are in
[the validation record](docs/release_3_0_0_validation.json).

| Executable contract | Current SHA-256 / identity |
| --- | --- |
| context-window-v1 | `cfeee4702c0dd3b18e02fbd0c8bad82ae58ee1ca7eadcfd21683479ba24f3dc4` |
| native-reasoning-v1 | `be212ff011125f1d0927e3a65a0d7cd87eedbf9f5ff69e803b4112a80ae6b1f6` |
| request-fidelity-v1 | `6f02088311f50707b9c12154d888f844928c23d359043cb2e5d5654bf7e5eaea` |
| py-stream-first-token-v1 | `c508e719670e851cf0a1eb7d89fbcfe2eae0ab5859df1ab0ddcbe7681140ac3e` |
| recovery-admission-v2, recovery-capabilities-v1, python-typed-errors-v1, anthropic-history-v1, anthropic-structured-v1 | Existing in-code executable sets, identified by their named spec files in the current source manifest; the added public-boundary and deterministic-clock specs are identified there too |

Both the library provider role (production gateway over controlled HTTP) and
consumer roles (gateway/broker/session public calls and fresh installed package)
verify this same Python source/artifact and unchanged fixture set. The final
JUnit results were checked against the current map: **all 129 named methods
exist in the executed suite and passed**, comprising their collected variants.
No independent mock or other port's executable run substitutes for these checks.
The TypeScript timing reference and fixture provenance remain recorded in the
historical timing section; its executable snapshot is not a prerequisite.

Commands ran from this worktree using `foundry capture` for verbose output, with
`UV_CACHE_DIR=/tmp/mojentic-uv-cache` and, for uvx, `UV_TOOL_DIR=/tmp/mojentic-uv-tools`.
The initial default uv cache attempt failed because the host cache is read-only;
redirecting the cache resolved it. The first new public-boundary test draft used
an invalid session call signature and an incorrect expected HTTP-body phase;
these verifier errors were corrected to the existing public contract. The first
fresh verifier compared serialized tool-argument whitespace; it now checks the
exact function name, typed argument values and continuation IDs/content. No
production semantics were weakened to satisfy those assertions.

| Final command/check | Actual result |
| --- | --- |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; required hone lint gate |
| `uv run pytest` | Exit 0; 2,636 passed, 86% configured source coverage; required hone test gate |
| `uv run pytest --cov --cov-report=term --junitxml=<scratch-result>` | Exit 0; 2,636 passed, 87% total coverage; metadata module 100%, timing module 99%. No repository fail-under threshold is configured; no threshold is invented or claimed |
| `uv run bandit -c .bandit -r src` | Exit 0; zero issues; hone security gate |
| `uv run pip-audit` | Exit 0; no known vulnerabilities; hone dependency gate |
| `uv run flake8 src` | Exit 0; zero findings |
| `uv run ruff check src scripts/verify_readiness.py` | Exit 0; zero findings |
| `uv run ruff format` and `ruff format --check` on all changed Python files | Exit 0; formatted and verified |
| `uv run ruff format --check src scripts/verify_readiness.py` | Exit 1; one pre-existing formatting mismatch in unchanged `file_manager_spec.py`; 231 files already formatted. No unrelated formatting rewrite was made |
| `uv run flake8 src --max-complexity=10` | Exit 1; 13 pre-existing C901 findings in examples, adapters, Ollama/OpenAI gateway functions, registry, broker, recovery stream and realtime session. No suppression added |
| `uv run flake8 <all five changed Python files> --max-complexity=10` | Exit 0; includes new public boundary tests and installed-package verifier |
| `uv export --format requirements-txt --no-emit-project \| uvx pip-audit -r /dev/stdin --disable-pip` under `bash -o pipefail` | Exit 0; locked dependencies have no known vulnerabilities |
| `uv pip list --outdated` | Exit 0; 17 newer packages listed; inventory reviewed, no advisory-driven upgrade required by either audit |
| `uv run mkdocs build` | Exit 0; existing Material/MkDocs notice only |
| `uv build` | Exit 0; final wheel and sdist built without a version change |
| Manifest, artifact/source and proof validation | Passed; actual rejecting exit 1 and corrected exit 0 logs exist; behavioral proof JSON field types and content checked |
| `git diff --check` | Exit 0 |

The full-repository complexity findings are unchanged functions:
`audit_openai_capabilities.main` (16), `tracer_demo.main` (13),
`TracerViewer._format_event_details` (11), `adapt_messages_to_anthropic` (11),
`OllamaGateway.complete_stream` (15), `OpenAIGateway.complete` (25),
`OpenAIGateway.complete_stream` (28), `adapt_messages_to_openai` (13),
`OpenAIModelRegistry._initialize_default_models` (13),
`LLMBroker.generate_stream` (12), `_StreamRecovery.run_stream` (12),
`RealtimeSession._handle_server_event` (30), and
`RealtimeSession._run_tool_batch_for_turn` (11). Their refactoring is outside
this bounded readiness correction; the record does not claim a clean optional
repository-wide complexity/formatting check.

### Fresh consumer installation of the final artifact

| Artifact (unpublished 2.1.0 candidate filename) | SHA-256 |
| --- | --- |
| `mojentic-2.1.0-py3-none-any.whl` | `27fc3261c33c849831ecb881a802a2e0582b775e2e17ba917083f3affc83e2db` |
| `mojentic-2.1.0.tar.gz` | `369c08f3e3fd7492fdf77465afc60acd01256b26ec5a7bc5c9f9b0380c0edab5` |

All commands below exited 0. `checkout` means this assessment's absolute
worktree path. The consumer directory is outside the checkout, with no editable
install or checkout production imports. JSON contracts are read-only inputs from
the identified fixture paths; they are not injected production modules.

```bash
uv venv /tmp/mojentic-c14-consumer/.venv
uv pip install --python /tmp/mojentic-c14-consumer/.venv/bin/python \
  dist/mojentic-2.1.0-py3-none-any.whl
# After the final source change/build, reinstall the final candidate:
uv pip install --reinstall --python /tmp/mojentic-c14-consumer/.venv/bin/python \
  dist/mojentic-2.1.0-py3-none-any.whl
uv run --no-project --directory /tmp/mojentic-c14-consumer \
  --python /tmp/mojentic-c14-consumer/.venv/bin/python \
  "$checkout/scripts/verify_readiness.py" "$checkout"
uv run --no-project --directory /tmp/mojentic-c14-consumer \
  --python /tmp/mojentic-c14-consumer/.venv/bin/python \
  "$checkout/scripts/verify_stream_timing.py" \
  "$checkout/src/mojentic/llm/gateways/fixtures/contracts/first_token_v1.json"
```

Both verifiers report installed provenance:
`/tmp/mojentic-c14-consumer/.venv/lib/python3.13/site-packages/mojentic/__init__.py`.
The readiness verifier rejects checkout imports and an in-checkout working
directory. It verifies all metadata provider cases, exact request semantics,
registry/no-network lookup, effective clamping, distinct reasoning controls,
structured responses and retained native tool continuation, omitted/default and
explicit zero request controls, Anthropic SDK/recovery history, byte-identical
retry and permanent HTTP failure. The timing verifier exercises every supported
streaming provider through event/session/recovery routes, empty completion,
parser failure, immediate close and unsent closure. Fixture IDs/hashes are printed
by the verifiers. The final wheel itself supplies all runtime Python modules;
no production file was altered in the fresh environment.

### Available CI evidence

Read-only `gh run list --repo svetzal/mojentic --limit 5 --json ...` and
`gh run view 39076064756 --repo svetzal/mojentic --json headSha,conclusion,url,jobs`
exited 0. [Validate, Test, and Publish run 39076064756](https://github.com/svetzal/mojentic/actions/runs/39076064756)
succeeded for baseline `44e416eb87b30859cc5628a0d51b6ff95d987048`: lint, test and
security jobs all succeeded; release-build, docs deploy and PyPI publish were
skipped. This does **not** certify CI for the uncommitted candidate. Foundry must
obtain candidate CI after finalization. No commit, push, merge, rebase, ref change,
version bump, tag or publication was performed in this task.

## Historical correction evidence (superseded where noted above)

## October 17 library self-validation policy (current)

This policy supersedes every older external/counterpart/paired verification
requirement for this unreleased package in the historical records below.
Library readiness is established by public API tests against binding documents
and identifiable fixtures, real production gateways against controlled HTTP,
and a fresh consumer installation of the packaged artifact. Dependents verify
when they adopt a released version; another port's executable snapshot is not
a prerequisite. Historical missing external checks remain accurate descriptions
of what was not run, but are no longer library readiness blockers. Changed
boundaries between running applications/services retain the shared versioned
producer/consumer contract requirement, with each repository separately
authorized. No live vendor compatibility or other port's readiness is claimed.
Publication remains on hold until all six ports satisfy owner scope and the
owner authorizes release.

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
| Ollama recovery requires explicit completion before native history or tool execution | `should_reject_incomplete_recovery_ollama_history`: HTTP 200 with `done:false`, `done_reason:stop`, native reasoning and tool calls raises public `RecoveryError` with inspectable `ValueError`; unchanged caller messages, zero executions, exactly one captured initial request. `should_retain_completed_recovery_ollama_history_and_execute_tool_once`: completed control retains separate native reasoning, content, typed arguments and tool result in the continuation and executes once |
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
uv run pytest src/mojentic/llm/gateways/native_reasoning_spec.py -k 'tool_continuation or broker_tool_history or unfinished or failure_or_close or partial_native or incomplete_ordinary or capped_ordinary or provider_error_frame or incomplete_recovery_ollama or completed_recovery_ollama' --no-cov
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

### Prior native reasoning correction verification results

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

### Cycle-8 Ollama recovery completion correction

Tested Python source: preserved native-reasoning commit
`a05b14d7d0fbf4053c2ae44b0e8859c88aa67947` plus this uncommitted correction.
The initiative brief SHA-256 was verified again against the recorded value above.
Only Python was changed; Rust remains the read-only reference recorded above.

Before the fix, the real-HTTP broker probe failed because no `RecoveryError`
was raised for HTTP 200 with `done:false`, `done_reason:stop`, native reasoning
and tool calls. The completed-response control already passed. Recovery now
requires literal `done:true` before converting a response into broker output.
The corrected probe passes both cases: incomplete output raises `RecoveryError`
with inspectable `ValueError("incomplete Ollama response")`, preserves caller
messages, executes no tools and sends only the captured initial request.
The existing recovery policy classifies observed semantic output as
`protocol` / `semantic_output`; it does not retry it. The completed control
retains native reasoning separately from content, preserves typed tool
arguments and the serialized result in the continuation, and executes once.
Both probes use public `LLMBroker.generate` with recovery enabled and
`CompletionConfig(retain_reasoning=True)` against real loopback HTTP, without
SDK or private-decoder mocks. Behavioral proof records actual exit codes 1
before correction and 0 afterward and was validated against the logs.

The shared executable inputs remain **native-reasoning-v1**, unchanged SHA-256
`be212ff011125f1d0927e3a65a0d7cd87eedbf9f5ff69e803b4112a80ae6b1f6`,
from Elixir `98b54a0cf0b028b82d38655ac59ebafcd7988077`.
Current Python executable set (`native_reasoning_spec.py`) SHA-256:
`558a9d9acfa14d716f3ea61cfdda4678e62234063f9e19bf50508d578dfe6b50`.
Current `ollama.py` SHA-256:
`dd300d374e094478c1946e49e340bb00f7dfb03d1425b080f43185ccc32fc309`.
The local provider command above passed **202 cases** (31 deselected);
the updated local broker consumer command above passed **31 cases**
(202 deselected), both on the Python source identity just recorded.
The entire shared-input specification passed **233 cases** with
`uv run pytest src/mojentic/llm/gateways/native_reasoning_spec.py --no-cov`.

**Unfinished coordination:** external consumer and provider tested commits,
verification commands and results against this same contract are unavailable,
not run here. The Elixir source identity identifies fixture provenance only.
Local HTTP verification does not establish external counterpart agreement.
The coordinated publication hold remains; metadata/request-fidelity and other
initiative work remain separate. No commit, ref, version or publication changed.

All commands below passed on the corrected worktree, through `foundry capture`:

| Verification | Result |
| --- | --- |
| `.hone-gates.json`: `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0, zero errors |
| `.hone-gates.json`: `uv run pytest` | Exit 0, 1,804 passed, 85% source coverage |
| `.hone-gates.json`: `uv run bandit -c .bandit -r src` | Exit 0, no issues |
| `.hone-gates.json`: `uv run pip-audit` | Exit 0, no known vulnerabilities |
| `uv run pytest --cov` | Exit 0, 1,804 passed, 85% source coverage; no repository minimum configured |
| `uv run flake8 src` | Exit 0 |
| `uv run --with ruff ruff check src` | Exit 0, zero findings |
| `uv run --with ruff ruff format src/mojentic/llm/gateways/native_reasoning_spec.py src/mojentic/llm/gateways/ollama.py` | Exit 0; scoped to changed Python files |
| `uv export --format requirements-txt --no-emit-project \| uvx pip-audit -r /dev/stdin --disable-pip` with shell pipefail | Exit 0, no known vulnerabilities in locked dependencies |
| `uv pip list --outdated` | Exit 0, inventory reviewed; audits required no advisory upgrade |
| `uv run mkdocs build` | Exit 0 |
| `git diff --check` | Exit 0 |

Dependencies, versions and unrelated characterized behavior are preserved.
Ruff was supplied ephemerally, with writable caches under `/tmp` as above.

## MODEL-METADATA section 3: request fidelity

Binding source SHA-256:
`a085da1c0d110f9d587a24ace6ac2854b653e1ac28905b3829d94d665b2c906e`.
The initiative brief hash remains verified as recorded above. This correction
starts at Python `3f9b474a71b0ba0b140d6f7bcb7c4d02f0a9e572`; the tested revision is
that base plus the uncommitted task worktree changes. No version or ref changed.
Context-window discovery and first-token timing remain separate objectives.

### Characterization before migration

Inspection established numeric CompletionConfig defaults (temperature 1.0,
context 32768, output 16384), the separate -1 num_predict sentinel, gateway
fallbacks, and ChatSession forwarding its local budget as num_ctx. A rejecting
real HTTP probe through ChatSession, broker, real TracerSystem and Ollama recovery
captured `options` containing temperature 1.0, num_ctx 8192 and num_predict 16384.
The corrected identical probe succeeds with empty options and the local budget
still 8192. Existing recovery byte assertions now supply explicit former settings
where necessary; their admission, identity, causes, progress and history assertions
remain intact. Structured boundary expectations reflect the new omitted controls.

### Named section-3 decision map

All names below are in `src/mojentic/llm/gateways/request_fidelity_spec.py` unless
another file is specified. Assertions inspect actual outbound HTTP and returned
content/objects/events, including terminal completion and byte-identical retries.

| Binding decision | Executable verification |
| --- | --- |
| 3.2.1: omitted and null temperature/context/output controls stay absent; zero survives | `DescribeSharedRequestFidelity.should_execute_shared_cases`: all seven shared cases, all three streaming providers, ordinary/structured/legacy/events, with and without recovery; `should_preserve_controls_through_broker_events` and `should_preserve_controls_and_history_through_session_stream` execute every case directly through both public streaming routes to HTTP |
| 3.2.2: max_tokens is the only public output control; Ollama options.num_predict is its wire mapping | Same shared cases inspect exact parameter sets and values; `completion_config_spec.py::should_use_default_values` checks removed public field; examples and signatures remove the sentinel |
| 3.2.3: no invented gateway or deprecated broker defaults | `DescribeMigrationFidelity.should_omit_controls_for_gateway_keywords_without_config` and `should_forward_only_explicit_deprecated_broker_keywords` |
| 3.2.3: session budget stays local, unspecified tracing works | `DescribeRequestFidelity.should_omit_unset_session_controls_at_http_boundary`; `DescribeSharedRequestFidelity.should_preserve_controls_through_public_routes` uses a real tracer; `should_preserve_controls_and_history_through_session_stream` checks the distinct local budget, outbound history and ordered history after consumption; existing `chat_session_spec.py::should_respect_context_capacity` and `should_maintain_newest_messages` preserve trimming |
| 3.2.4: sampling field coverage | Shared `sampling` and `all` cases: top_p on all four providers; top_k on Ollama/oMLX/Anthropic, absent on OpenAI, matching read-only Elixir's supported fields; both named public streaming tests inspect exact outbound parameter sets and values for Ollama/OpenAI/oMLX |
| 3.2.4: fixed-temperature OpenAI adaptation only for explicit controls | `DescribeMigrationFidelity.should_adapt_only_explicit_temperature_to_registered_fixed_value`, including an only-allowed value other than 1.0 |
| 3.2.4: unsupported effort warns and is dropped | `DescribeMigrationFidelity.should_warn_and_drop_effort_for_non_reasoning_model`; existing native reasoning preflight safeguards remain unchanged |
| 3.3 / 3.5: explicit migration preserves supported former defaults | `DescribeMigrationFidelity.should_forward_only_explicit_deprecated_broker_keywords`: explicit 1.0/32768/16384; `DescribeAnthropicMigration.should_reproduce_supported_former_sdk_and_config_limits` covers its former 2000/16384 limits; CHANGELOG and broker guide describe provider defaults and cost/context consequences |
| 3.4: Anthropic registry maximum or unknown-model 4096; explicit limit wins | `DescribeAnthropicFidelity.should_apply_only_required_fallback_and_explicit_controls`: known/unknown, all seven shared cases, SDK/recovery, gateway/broker/session and supported recovery structured route |
| 3.4: oMLX has no required output-limit fallback | Shared unset/null cases, including both streaming APIs and structured completion; both named public streaming tests verify absence at HTTP after broker/session forwarding |
| 3.6: continuations/retries retain exact controls | `DescribeContinuationFidelity.should_keep_controls_and_tool_history_on_admitted_resend`: shared tool response, real session/broker, single tool execution, continuation result/history and byte-identical resend |

### Contract identity, provenance and counterpart gap

Unchanged `request-fidelity-v1`, copied from Elixir
`ff479d92067b6ffbd99d3cd5533f96e13ebc09b0`:
`6f02088311f50707b9c12154d888f844928c23d359043cb2e5d5654bf7e5eaea`.
The source contract and clean read-only Elixir checkout have that revision.
Python's scripted responses derive their semantics, tool calls and retryable
errors from the shared set. Python's strict Ollama decoder additionally requires
an assistant role; Anthropic uses a native envelope around the shared content.
The shared file itself is not edited. API version is unreleased 3.0.0; former
2.1 config defaults require explicit migration settings, not a second default mode.

Python provider and in-repository broker/session consumer roles execute together
with `uv run pytest src/mojentic/llm/gateways/request_fidelity_spec.py`; the normal
pytest gate includes them. This is local scripted HTTP verification, not external
provider compatibility. Elixir's counterpart command is
`mix test test/mojentic/llm/immutable_request_wire_test.exs`; it was **not run** in
this Python-only authorized worktree task. A paired result at the cited revision, external
consumer verification and live provider runs remain unfinished coordination work.

Unverified alignment: neither the shared JSON nor Elixir supplies an Anthropic
model table. Python now registers exact Sonnet 4.5 and Haiku 4.5 IDs/aliases at
64000 from their official model pages (linked in `docs/broker.md`); other IDs use
the binding 4096 fallback. No pattern-based limit is inferred. Coordinate the
registry table across Anthropic ports before declaring initiative conformance.
The SDK's nonstream token heuristic rejects registered maxima; passing its own
configured timeout explicitly preserves that timeout and permits the required
HTTP payload, covered by the known-model SDK probe.

Recovery admission and typed causes, immutable resends, Anthropic assistant
history, and native reasoning completion/retention safeguards remain frozen and
are covered by the full regression suite. The coordinated publication hold stays
in effect until all six ports meet owner scope and required paired verification
is available.

### Verification results before cycle 10

- `uv run pytest --cov`: **2195 passed**, **87% total coverage**; no coverage
  fail-under threshold is configured in this repository.
- Both required flake8 gate and full `uv run flake8 src`: pass.
- `uv run ruff check src`: pass, zero findings. Changed Python files were
  formatted with `uv run ruff format` and pass its format check.
- `uv run bandit -c .bandit -r src`: pass, zero findings.
- `uv run pip-audit` and the locked export audit
  `uv export --format requirements-txt --no-emit-project | uvx pip-audit -r /dev/stdin --disable-pip`:
  pass, no known vulnerabilities. No suppressions or dependency changes added.
- `uv pip list --outdated`: completed; newer packages exist but the audits are
  clean, so dependency upgrades are outside this correction.
- `uv run mkdocs build`: pass.
- Extra whole-tree `uv run ruff format --check src` identifies one pre-existing
  unformatted file, `src/mojentic/llm/tools/file_manager_spec.py`. Checking the
  same file from HEAD reproduces it. It is unchanged to preserve authorized scope.

uv cache/tool/cache-home directories were redirected to writable temporary paths
because the default home cache is read-only in this sandbox. This changes neither
locked dependencies nor request behavior. Complete command logs and the validated
rejecting/corrected proof are retained as Foundry execution evidence, not package
assets. External counterpart results remain unverified as specified above.

### Cycle 10: direct public streaming-route verification

Tested Python source identity: base
`4f8a8afbe3fc553bf54cd372f7a84d8c803baaf3` plus this uncommitted correction.
The changed `src/mojentic/llm/gateways/request_fidelity_spec.py` has SHA-256
`2fdf85d383efe7586c9a9c722828c2ca6af44db3322cb97c33e566bc96be2214`.
The initiative brief was read and its recorded SHA-256
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`
verified. `request-fidelity-v1` retains SHA-256
`6f02088311f50707b9c12154d888f844928c23d359043cb2e5d5654bf7e5eaea`.

The two new named tests in the section-3 map execute all seven existing cases
through `LLMBroker.generate_stream_events` and `ChatSession.send_stream`, with
real Ollama, OpenAI and oMLX gateways against loopback HTTP: 42 new checks.
They inspect actual outbound parameter presence, absence and values, and assert
exact returned content. The event route asserts exactly one terminal event,
successful completion with finish reason `stop`, and terminal ordering. The
session route checks outbound history and the ordered system/user/assistant
history after full consumption, retaining an earlier conversation turn. Its
4096-token local budget is distinct from the contract's explicit 8192 context.

Before extending the matrix or documentation, a focused real HTTP event-route
probe rejected a temporary source mutation that discarded temperature zero.
Restoring forwarding passed the same probe. The final matrix's six
zero-temperature cases were then run with temperature temporarily discarded in
both public routes: **6 failed**, each on missing HTTP temperature, exit **1**.
Restoring both production files passed the identical command, **6 passed**,
exit **0**:

```bash
uv run pytest src/mojentic/llm/gateways/request_fidelity_spec.py -k '(through_broker_events or through_session_stream) and zero-temperature'
```

These mutations were removed. Runtime code, recovery safeguards, shared
responses and contracts are unchanged. The Unreleased changelog adds only the
new regression coverage; it does not claim a runtime fix. Foundry retains the
validated behavioral proof and complete command logs as execution evidence.

Local Python consumer execution and real gateway provider verification run
together using the same contract with
`uv run pytest src/mojentic/llm/gateways/request_fidelity_spec.py`:
**433 passed**, exit **0**. The normal pytest gate includes this verification.
The unchanged Elixir contract provenance is
`ff479d92067b6ffbd99d3cd5533f96e13ebc09b0`; its counterpart command
`mix test test/mojentic/llm/immutable_request_wire_test.exs` was **not run**.
Elixir paired verification at a reported source identity remains **open** for
initiative coordination. Loopback verification does not establish live provider
compatibility. The coordinated publication hold remains until all six ports
satisfy the owner scope and required paired verification is available.

Cycle 10 command results (all exit **0** unless noted):

| Command | Result |
| --- | --- |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Required lint gate: zero errors |
| `uv run pytest` | Required test gate: 2,237 passed, 86% source coverage |
| `uv run pytest --cov` | 2,237 passed, 87% reported coverage; no repository fail-under threshold configured |
| `uv run bandit -c .bandit -r src` | Security scan gate: no issues |
| `uv run pip-audit` | Dependency audit gate: no known vulnerabilities |
| `uv run flake8 src` | Full lint: zero findings |
| `uv run --with ruff ruff check src` | Zero findings |
| `uv run --with ruff ruff format src/mojentic/llm/gateways/request_fidelity_spec.py` | Changed Python source formatted |
| `uv run --with ruff ruff format --check src/mojentic/llm/gateways/request_fidelity_spec.py` | Format check passed |
| `uv export --format requirements-txt --no-emit-project \| uvx pip-audit -r /dev/stdin --disable-pip` under `bash -o pipefail` | Locked dependencies: no known vulnerabilities |
| `uv pip list --outdated` | Inventory reviewed; audits found no required advisory upgrades |
| `uv run mkdocs build` | Documentation build passed |
| `git diff --check` | Clean |

The export audit initially exited 2 because uvx's default tool directory is
read-only. Rerunning with a writable `UV_TOOL_DIR` passed. uv caches, tool and
XDG cache directories were redirected under `/tmp`; dependency files are
unchanged. Formatting is scoped to the changed Python file, preserving the
previously documented unrelated formatting gap. No Git finalization, version
change, metadata/timing expansion or sibling repository modification was made.

### Cycle 11: provider context-window discovery (section 1)

Python base HEAD: `8dccb4a329176435f87194f5e0df161a179906f1` plus this
uncommitted correction. The initiative brief SHA-256 was verified as
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
Only MODEL-METADATA-2026-10.md section 1 is implemented here. Completion
recovery, reasoning, request fidelity, versions and first-token timing are unchanged.

The unchanged `context-window-v1` JSON was located read-only at the authorized
Elixir Foundry worktree `mojentic-3-0-ex-c11-25cb56`, base HEAD
`4ca97881bfe5249a3b4ebe0e3a640ec25e28cb1c`, and copied into
`src/mojentic/llm/contracts/context_window_v1.json`. Its SHA-256 matches the
initiative finding:
`cfeee4702c0dd3b18e02fbd0c8bad82ae58ee1ca7eadcfd21683479ba24f3dc4`.
No independent replacement fixtures were invented.

Snapshot identity discrepancy: the supplied finding reports Elixir manifest
`c71163faa50dd12ff22137b80f7ea2db22478b917d809559db0bec54ccb3b426`.
The available manifest hashes to
`1c25185664b06c07e0d105a69e17ced6b5d238af615c2d3ff35ce2f58d138b76`;
all 17 entries pass `sha256sum --check test/contracts/context_window_v1.manifest.sha256`
from that read-only checkout. The finding's exact executable snapshot is therefore
**unverified**, although the JSON identity matches. The Elixir reference parser
was consulted for null optional containers, sorted architecture-key selection,
and signed positive integer text parsing; no ambiguous contract decision was
changed locally. No command that writes or executes tests in Elixir was run.

| Section 1 decision | Named Python verification in `context_window_spec.py` |
| --- | --- |
| oMLX configured host/key, exact model identity, positive max_model_len; missing model/field | `should_select_exact_model_through_authenticated_http`; `should_verify_provider_semantics_and_exact_http_request` |
| Ollama exact POST body, architecture-independent field, optional model_num_ctx | `should_verify_provider_semantics_and_exact_http_request` |
| Missing vs malformed values; JSON shape; HTTP status and unknown-model 404 | `should_verify_provider_semantics_and_exact_http_request` asserts every applicable contract case's result/error and full captured method/path/body/authentication |
| Transport errors remain distinct from HTTP and ValueError | `should_distinguish_transport_failure` through non-listening loopback endpoints |
| OpenAI exact registry-only lookup, unknown patterns not advertised | `should_lookup_only_exact_registry_entries_without_http`; `should_preserve_registry_completion_semantics_after_discovery` |
| Unsupported/legacy gateways return None | `should_return_not_advertised_for_unsupported_gateway` |
| Pure effective helper: caller precedence, model fallback, clamping, unknown metadata | `should_apply_helper_precedence_and_clamping` executes all eight shared effective cases |
| Doubles derive from verified provider cases | `should_derive_gateway_double_from_verified_provider_case` uses a spec-constrained owned gateway and the same semantic outcomes, not independently authored mocks |
| Discovery cannot alter subsequent requests, including failed discovery | `should_leave_same_model_completion_request_unchanged_after_discovery` runs every shared provider case with omitted controls and explicit zero temperature/context/output controls, using the exact same model before/after; compares full completion requests and asserts control presence/values |
| Registry completion fallback remains intact | `should_preserve_registry_completion_semantics_after_discovery` checks known gpt-5.4 and unknown o1-custom requests, output-limit mapping and no discovery HTTP |

`ModelContextWindow` is immutable, validates strict positive integers, and keeps
source `field` separate from model defaults. HTTP and transport exceptions retain
their existing httpx types. Malformed JSON/metadata raises ValueError (including
Pydantic validation errors); missing advertisement returns None. Discovery does
not cache, retry, or write completion configuration. `effective_context_window`
is an explicit pure application helper; its advertised result remains an upper
bound when the server environment is unknown.

Python provider verification runs through public gateways and actual loopback
HTTP. Doubles are contract-derived and checked, but do not prove an external
consumer agrees. The JSON's `lookup_cases` record existing Elixir model-list
behavior; this change does not modify Python's pre-existing sorted model lists.
These unrelated lookup rows are not claimed as shared metadata verification.
Semantic completion replies are reused from the existing `request-fidelity-v1`
contract via its existing Python envelope adapter.

Local executable command:
`uv run pytest src/mojentic/llm/gateways/context_window_spec.py`.
The normal pytest gate collects this verifier. The Python source snapshot is
identified by `src/mojentic/llm/contracts/context_window_v1.manifest.sha256`;
run `sha256sum --check` on it from the repository root.

External counterpart status: the initiative finding reports Elixir
`scripts/verify-context-window-contract` exited 0 with 194 tests at the reported
snapshot. This run did **not** reproduce that result and the available manifest
differs. Actual oMLX/Ollama server producer verification and external consumer
verification against the same contract remain **MISSING**: no tested external
revision, command/result pair is available here. Coordinate these in separately
authorized repositories. Do not infer paired compatibility. The coordinated
publication hold remains until all six ports satisfy owner scope and required
paired consumer/provider verification is available.

Cycle 11 local results (all exit 0 unless explicitly marked):

| Command | Result |
| --- | --- |
| `uv run pytest src/mojentic/llm/gateways/context_window_spec.py --no-cov` | 231 passed: all 53 provider cases plus 53 contract-derived double cases, eight effective cases, four registry cases, transport/unsupported tests, 106 same-model comparisons and registry request controls |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Required gate: zero errors |
| `uv run pytest` | Required gate: 2,468 passed; 86% source coverage; new metadata module 100% |
| `uv run pytest --cov` | 2,468 passed; 87% coverage; new metadata module 100%. No repository fail-under threshold is configured. |
| `uv run bandit -c .bandit -r src` | Gate: zero issues |
| `uv run pip-audit` | Gate: no known vulnerabilities |
| `uv run flake8 src` | Full lint: zero findings |
| `uv run --with ruff ruff check src` | Zero findings |
| `uv run --with ruff ruff format` and `ruff format --check` on the seven changed Python files | Formatted and passing; unrelated existing formatting left outside scope |
| `uv export --format requirements-txt --no-emit-project \| uvx pip-audit -r /dev/stdin --disable-pip` under `bash -o pipefail` | Locked dependencies: no known vulnerabilities |
| `uv pip list --outdated` | Inventory reviewed; no advisory upgrades required by either audit |
| `uv run mkdocs build` | Passed |
| `sha256sum --check src/mojentic/llm/contracts/context_window_v1.manifest.sha256` | All 11 Python snapshot entries verified |
| `git diff --check` | Clean |

The Python executable/source manifest SHA-256 is
`59ec8e6ae69cd9bf004f6408b1d14b454651f014f5a88662460caf1f0e617950`.
The root metadata specification matches the JSON's `source_sha256`:
`a085da1c0d110f9d587a24ace6ac2854b653e1ac28905b3829d94d665b2c906e`.

Before fixture/test expansion and the full suite, the focused authenticated
exact-selection HTTP test failed on the absent operation, then passed after
implementation. A further fault-injection probe temporarily replaced exact ID
equality with prefix matching: the real HTTP test failed with the neighbor's
1-token window instead of the requested model's 262144 (exit 1). Restoring exact
matching passed the same command (exit 0). The mutation was removed and the
source manifest reverified. Foundry's behavioral proof records the semantic
failure/pass commands, actual exit codes and complete logs. No markers or
case-count assertions stand in for semantic verification.

Tool caches were redirected to writable temporary directories; no dependencies,
Git refs, versions, sibling repositories or publication state were changed.

## Section 2: client-measured first-token timing (October 17)

### Characterized public surfaces and dispatch boundary

Before implementation, Ollama/OpenAI/oMLX exposed synchronous legacy chunks,
single-turn `complete_stream_events` terminals (`CompletionMetadata`), and
owned recovery stream terminals (`RecoveryStreamEvent`). `StreamMetrics`
previously held provider counters/durations; completed recovery responses also
had provider metadata. Broker/session text streams yielded strings without a
terminal object. Anthropic had no supported streaming route; model capability
checks and unsupported structured routes rejected before sending.

The rejecting production-loopback probe
`DescribeFirstTokenTiming.should_exclude_capture_and_lazy_delay_at_actual_dispatch`
failed because the completed recovery event had no timing metrics. The corrected
probe verifies a 250ms request-capture callback and 250ms lazy-consumption delay
are excluded, a 40ms delayed HTTP response is measured, thinking wins over
content in the same frame, and Ollama's `eval_duration=123` survives. Both actual
exit codes (1 then 0) and complete logs were retained for Foundry review.

Synchronous gateway methods now use a clock scoped only to advancing their
iterator. HTTP request hooks start it at send; raw frame observation precedes
splitting thinking/content/tool chunks. Scope is removed while the caller is
paused. Owned recovery starts its clock immediately before `client.send`,
after request capture and lifecycle callbacks and their dispatch checks; the
same clock survives admitted retries. Frame observation precedes body capture
so capture failure/cancellation does not erase already-observed first-token
evidence. Clock observation stops at terminal proof, including when extra
frames follow in the same received chunk.

### Section-2 executable decision map

All new named tests below are in
`src/mojentic/llm/gateways/first_token_spec.py::DescribeFirstTokenTiming`.
They consume production gateways over a controlled loopback HTTP server,
without SDK mocks or private-method patches.

| Binding decision | Named verification and measured assertions |
| --- | --- |
| Timing on supported gateway/broker/session APIs | `should_measure_supported_public_routes`: Ollama/OpenAI/oMLX event, legacy, broker and session routes; content kind and measured first-token/duration ordering |
| Monotonic clock starts at send; lazy construction and blocking initial capture excluded | `should_exclude_capture_and_lazy_delay_at_actual_dispatch`: measured 25–200ms bounds exclude both 250ms delays; production request reaches `/api/chat` |
| Keepalives, empty frames, name-only/empty argument strings are not tokens | `should_measure_first_wire_frame_and_terminal_errors`: versioned fixture cases assert exact first kind or absent first-token time, plus dispatched duration; Ollama's complete argument objects count |
| Thinking > content > tool arguments within the first token frame | `should_measure_first_wire_frame_and_terminal_errors`: combined-kind fixtures on every streaming provider; proof probe also verifies thinking/content on recovery |
| First argument fragment counts before call assembly | `should_measure_argument_fragment_before_later_failure`: OpenAI/oMLX recovery observe `{` at 25ms, fail after an additional 150ms; kind is `tool_call`, duration exceeds first-token time by at least 100ms, observed fragment progress is retained |
| Empty completion; failure before and after tokens | `should_measure_first_wire_frame_and_terminal_errors` and `should_report_dispatched_failure_without_inventing_tokens`: empty success/error, provider errors, HTTP errors and malformed response bodies; first-token fields stay null without a token, duration remains measured |
| No post-terminal tokens are invented | `should_ignore_token_frames_after_terminal_proof`: empty completion followed by token-bearing frames in one HTTP body still has no first token, across all three recovery providers |
| Admitted retries retain the initial clock | `should_include_admitted_retry_delay_on_one_clock`: real 503 followed by admitted resend, a 120ms admission delay and 30ms token delay yield at least 140ms first-token time; resent request bytes are identical |
| Tool continuations start fresh clocks | `should_reset_continuation_clock_and_preserve_exact_tool_history`: all providers, recovery on/off; first request >=100ms, 200ms tool execution excluded from second request's <180ms duration; exact full continuation request and tool history, including existing Ollama SDK/recovery encoding differences |
| Provider metrics preserved | Proof probe retains Ollama `eval_duration`; existing `DescribeStreamTelemetry.should_emit_exact_length_terminal_progress_metrics_then_failure` and `should_preserve_only_reported_completion_evidence` assert exact provider projections and unchanged response evidence alongside new timing fields; all original stream-provider evidence specs still run |
| Supported cancellation/close evidence | `should_keep_timing_on_explicit_recovery_cancellation`: cancelled at headers or body, no invented token before body, measured content after body observation; `should_keep_local_close_evidence_without_a_synthetic_terminal`: synchronous iterator close retains timing, closes resources and yields no fabricated terminal |
| Never dispatched means no invented duration | `should_not_report_duration_if_request_capture_rejects_dispatch`: rejecting capture, zero HTTP requests, no duration/kind; `should_not_invent_dispatch_evidence_for_unsupported_model`: unchanged unsupported error, no metadata, no request |
| Old evidence remains readable; new fields optional | `should_accept_old_evidence_without_optional_client_fields`: both public terminal models accept old evidence with all three new fields absent |
| Packaged public API is usable from a fresh consumer | `scripts/verify_stream_timing.py`: imported installed wheel path outside source tree; event empty-completion evidence, session content timing and recovery terminal timing for all three providers |

Legacy streams preserve their exact chunk/text ordering and exception types.
`last_stream_metrics` exposes terminal/local-close diagnostics through gateway,
broker and session, with `stream_metrics` attached to legacy exceptions. Event
APIs use terminal `CompletionMetadata`; recovery terminals use `StreamMetrics`
and completed response metadata. Closing an async recovery iterator releases
resources without yielding a synthetic terminal; explicit `RecoveryCall`
cancellation keeps the existing typed terminal. Remote termination is unknown.
No provider streaming capability, retry admission rule, reasoning retention,
model discovery behavior or request parameter/default changed.

### Contract identities and self-validation roles

The binding `MODEL-METADATA-2026-10.md` was read at SHA-256
`d9945dca45ce09e2163843263a75b5e93028b00ee1baf191fc3ff13396830e9c`.
The initiative brief's recorded SHA-256 was verified as
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
`ts-stream-first-token-v1` and its raw-frame observation rules were consulted
read-only as the behavioral reference; no TypeScript executable snapshot or
external consumer verification is required under the October 17 policy.

The local versioned executable set is **`py-stream-first-token-v1`**, implemented
by the named tests and `fixtures/contracts/first_token_v1.json` beside them.
Its declared per-provider expected kinds account for Ollama's complete argument
objects. It reuses **`request-fidelity-v1`** for successful provider response
frames, exact request controls and the shared tool call/history identity. The
fresh-wheel consumer uses the same two contract fixtures; Ollama envelopes add
the required assistant role without changing the shared semantic content.
OpenAI recovery receives its supported OpenAI envelope; oMLX-specific keepalive
acceptance is preserved only where already supported. Provider-side verification
runs the real gateways against those fixtures at HTTP; in-repository broker and
session consumers exercise the same implementation and wire inputs. These are
library self-validation roles, not claims that a live vendor server or another
repository verified this contract.

No unresolved section-2 contract ambiguity was found. Other ports' readiness,
live provider behavior outside the declared fixtures, and owner release
authorization remain unverified here. The coordinated publication hold remains.

### Tested source, fixture and artifact identities

The following identities and results are historical cycle-12 evidence. The
cycle-13 correction below supersedes them for the current candidate and corrects
the overbroad recovery-close claim above.

Tested baseline commit: **`34b0dc9242b8e01e5311a4a919b8ed29cce3083e`**, plus
this uncommitted correction. Reproduce the corrected source identity with:

```bash
uv run python scripts/verify_stream_timing.py --source-id
```

The manifest hashes sorted `src/` Python/JSON/SSE files, `pyproject.toml`,
`uv.lock`, and the consumer verifier (paths and SHA-256 bytes). Its SHA-256 is
**`cec93bbdf90fa893cce1a5dba0b1a8e301bf29ab7e9b2e93787f0e1fb6615e75`**.
This identifies the actual tested worktree rather than claiming a nonexistent
new commit. Documentation is recorded separately here.

| Input/artifact | SHA-256 |
| --- | --- |
| `fixtures/contracts/first_token_v1.json` (`py-stream-first-token-v1`) | `c508e719670e851cf0a1eb7d89fbcfe2eae0ab5859df1ab0ddcbe7681140ac3e` |
| `fixtures/contracts/request_fidelity_v1.json` (`request-fidelity-v1`, unchanged) | `6f02088311f50707b9c12154d888f844928c23d359043cb2e5d5654bf7e5eaea` |
| Built `mojentic-2.1.0-py3-none-any.whl` | `580bfa19c9d3c31c51afca1ff0a67815b04c5a11e760bd7399a04c3587b02e49` |

The wheel retains the existing version because Foundry forbids version bumps
or publication in this task. It is an unpublished candidate containing the
identified correction, installed into a newly created temporary virtualenv.
The verifier prints the installed `site-packages/mojentic/__init__.py` location
and rejects imports from this checkout's `src`. For the final check that location
was `/tmp/mojentic-timing-verified.pxsGbi/.venv/lib/python3.13/site-packages/mojentic/__init__.py`.
All three providers passed empty event, content session and recovery terminal
timing assertions against the recorded contracts. No dependent or sibling
repository was edited or asked to verify an unreleased version.

### Actual verification commands and results

Commands were captured with Foundry, with writable temporary uv/audit cache
directories selected by environment variables because the default home caches
are read-only in this worktree. No advisory suppression was added. `ruff` was
added to the uv development group so the mandated lint command is reproducible.

| Command | Actual result |
| --- | --- |
| `uv run pytest src/mojentic/llm/gateways/first_token_spec.py --no-cov -q` | Exit 0; 78 passed, measured values and exact histories asserted |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; required lint gate, zero errors |
| `uv run pytest` | Exit 0; required test gate, 2,543 passed, 86% coverage |
| `uv run pytest --cov --cov-fail-under=85` | Exit 0; 2,543 passed, 87.44% coverage exceeds enforced 85% minimum; timing module 99% |
| `uv run flake8 src` | Exit 0; full lint, zero findings |
| `uv run ruff check src` | Exit 0; zero findings |
| `uv run ruff format src` and final formatting of changed sources | Exit 0; unrelated pre-existing formatting in `file_manager_spec.py` restored to keep this correction scoped |
| `uv run flake8 src/mojentic/llm/stream_timing.py --max-complexity=10` | Exit 0; new timing module satisfies the complexity bound |
| `uv run bandit -c .bandit -r src` | Exit 0; security-scan gate, zero issues |
| `uv run pip-audit` | Exit 0; dependency-audit gate, no known vulnerabilities |
| `uv export --format requirements-txt --no-emit-project \| uvx pip-audit -r /dev/stdin --disable-pip` under `bash -o pipefail` | Exit 0; locked dependencies, no known vulnerabilities |
| `uv pip list --outdated` | Exit 0; inventory reviewed, no advisory-driven upgrade required; unrelated upgrades left outside scope |
| `uv run mkdocs build` | Exit 0; documentation builds |
| `uv build` | Exit 0; sdist and wheel built, no version change |
| `git diff --check` | Exit 0 |

The fresh-install verification commands were (all exit 0):

```bash
uv venv "$consumer_dir/.venv"
uv pip install --python "$consumer_dir/.venv/bin/python" dist/mojentic-2.1.0-py3-none-any.whl
uv run --no-project --directory "$consumer_dir" \
  --python "$consumer_dir/.venv/bin/python" \
  "$checkout/scripts/verify_stream_timing.py" \
  "$checkout/src/mojentic/llm/gateways/fixtures/contracts/first_token_v1.json"
```

Here `consumer_dir` was a fresh `mktemp -d` directory and `checkout` this
worktree. Source-side gateway/provider and broker/session consumer verification
use the same source identity and fixtures above; artifact-side verification uses
the wheel SHA-256 and the same fixture identities. This is the required library
self-validation, with no assertion of external running-service compatibility.
The behavioral proof's JSON types, captured exit codes, nonempty logs and
referenced complete stdout/stderr logs were validated before handoff.


## Cycle-13 timing repair (October 17)

This correction preserves cycle-12 implementation at
`e0cccae7dbe584e02e8709a3515cb06c05d53c1d` and supersedes its broad claims
about malformed-frame transparency and recovery-backed local close. The old
local-close test covered the direct event route only; it did not establish
recovery-backed gateway, broker or session close behavior. The old malformed
fixtures did not include a noniterable `choices` value.

The first real-loopback regression run rejected the preserved implementation:
OpenAI/oMLX `choices: 1` raised `TypeError` before the parser could return
`INVALID_STREAM_EVENT`, and all nine recovery-backed public-close combinations
returned no metrics after content. An initial unsent probe also attempted direct
access to an uninitialized gateway diagnostic; it now checks absent evidence
without requiring an attribute before first use. The corrected behavioral probe
passes all 20 cases. Proof logs and actual nonzero/zero exit codes are retained
as Foundry execution evidence.

| Regression in `DescribeFirstTokenTiming` | Verified behavior |
| --- | --- |
| `should_preserve_invalid_stream_event_for_noniterable_choices` | OpenAI/oMLX production parser returns exactly one typed `StreamError` with `INVALID_STREAM_EVENT`, measured dispatched duration, no invented first token |
| `should_preserve_content_timing_before_invalid_choices` | Exact emitted content followed by typed invalid-event failure; non-null content kind and first-token time survive |
| `should_retain_recovery_timing_immediately_after_public_close` | Ollama/OpenAI/oMLX through `complete_stream`, `LLMBroker.generate_stream`, `ChatSession.send_stream`: consume exactly the content chunk, close that actual public iterator before terminal evidence, inspect timing immediately; preserve Ollama `eval_duration=123` or exact OpenAI/oMLX usage |
| `should_leave_unsent_recovery_close_without_timing` | All nine public combinations close before first advancement, send zero HTTP requests, retain no timing |

No clocks, observers, parsers or transport internals are mocked. Delayed HTTP
frames exercise actual provider gateways. Observation now tolerates malformed
`choices` without taking parser ownership. Recovery shares the advancing
synchronous iterator's clock through the existing context propagation into its
owned loop; direct async calls still own a fresh clock. Thus the public wrapper
can snapshot timing after the inner stream has closed, without draining or
inventing a terminal. Already available typed terminal/error metadata is retained
rather than replaced by a timing-only snapshot.

Close propagation was inspected end to end: session and broker `ExitStack`
callbacks close their child iterators; gateways use `closing` or `yield from`;
the synchronous bridge awaits async closure; cloud recovery closes its nested
iterator; async recovery cancels and awaits the producer, whose HTTP response
is closed in `finally`. The bridge now also awaits `shutdown_asyncgens()` before
stopping its owned loop. This resolves the real-close regression's unawaited
transport cleanup warnings. The full timing suite passes with runtime warnings
promoted to errors. No garbage collection or iterator draining is used as proof.
Existing tests still exercise first-dispatch clocks across admitted retries,
thinking/content/tool precedence, fresh clocks on tool continuations, exact
request/history fidelity and unchanged typed recovery/cancellation behavior.

The initiative brief hash was verified as
`ea6a0efa56bfb3cd74b5ce728f80cc33c6fbd853114bec94b8aabe79f5d28e6e`.
The read-only TypeScript reference `ts-stream-first-token-v1.test.ts` was
consulted at SHA-256
`e94d4f53928b3ea519eceedcb0f7e7a41ae2eb5da52076369d92374108b3d2a8`.
The existing `py-stream-first-token-v1` fixture remains unchanged at
`c508e719670e851cf0a1eb7d89fbcfe2eae0ab5859df1ab0ddcbe7681140ac3e`;
`request-fidelity-v1` also remains unchanged. Named Python regressions extend
local behavioral coverage without asserting another port's executable results.

### Current candidate and verification

Tested source is baseline `e0cccae7dbe584e02e8709a3515cb06c05d53c1d` plus
these uncommitted changes. `uv run python scripts/verify_stream_timing.py
--source-id` reports the source/fixture/verifier manifest SHA-256
`53f349288a7f1089344d7a8c3e7082e5e9683167fb445d7a49fa85e77f6a7c86`.
The unpublished candidate retains version 2.1.0:

| Artifact | SHA-256 |
| --- | --- |
| `mojentic-2.1.0-py3-none-any.whl` | `76e216bb42c09b744effba622e8862fc49f8509dfae3086fe383772d0fa9a208` |
| `mojentic-2.1.0.tar.gz` | `09bde01eab6d95f3e04de573d47c552b0812a212107f5b91701db019cbb9c5c9` |

Commands use `foundry capture --log-dir .foundry/logs --` for complete execution
logs. Set `UV_CACHE_DIR=/tmp/mojentic-uv-cache`; the locked export audit also
uses `UV_TOOL_DIR=/tmp/mojentic-uv-tools` because default home caches/tool
directories are read-only. These environment settings do not change dependencies.

| Command | Actual result |
| --- | --- |
| `uv run pytest src/mojentic/llm/gateways/first_token_spec.py -k 'noniterable_choices or immediately_after_public_close or unsent_recovery_close' --no-cov` | Rejecting exit 1; corrected exit 0, 20 passed |
| `uv run pytest src/mojentic/llm/gateways/first_token_spec.py --no-cov -W error::RuntimeWarning` | Exit 0; final 100 passed, including two content-before-invalid-event cases |
| `uv run flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; required lint gate, zero errors |
| `uv run pytest` | Exit 0; final required test gate, 2,565 passed, 86% coverage (5,973 statements, 826 missed), above 85% |
| `uv run pytest --cov --cov-fail-under=85` | Exit 0; initial repaired suite 2,563 passed, 87.46%; final two additional error cases verified by the full gate and focused suite above |
| `uv run flake8 src` / `uv run ruff check src` | Both exit 0; zero lint findings |
| `uv run ruff format src` | Exit 0; unrelated pre-existing formatting in `file_manager_spec.py` restored to keep scope bounded |
| `uv run flake8 src/mojentic/llm/stream_timing.py --max-complexity=10` | Exit 0; timing code meets the complexity limit |
| `uv run flake8 src/mojentic/llm/stream_timing.py src/mojentic/llm/recovery_stream.py --max-complexity=10` | Exit 1; unchanged `_StreamRecovery.run_stream` has pre-existing complexity 12. No suppression or unrelated refactoring added |
| `uv run bandit -c .bandit -r src` | Exit 0; zero issues |
| `uv run pip-audit` | Exit 0; no known vulnerabilities |
| `uv export --format requirements-txt --no-emit-project \| uvx pip-audit -r /dev/stdin --disable-pip` under `bash -o pipefail` | Exit 0; no known vulnerabilities in locked dependencies |
| `uv pip list --outdated` | Exit 0; inventory reviewed, no advisory-driven upgrade needed; unrelated updates remain outside scope |
| `uv run mkdocs build` | Exit 0; docs built; existing Material/MkDocs 2 notice remains |
| `uv build` | Exit 0; current wheel and sdist built without version change |
| `git diff --check` | Exit 0 after documentation whitespace cleanup |

Fresh artifact installation and verification (all exit 0):

```bash
uv venv /tmp/mojentic-c13-final.2ULCmw/.venv
uv pip install --python /tmp/mojentic-c13-final.2ULCmw/.venv/bin/python \
  dist/mojentic-2.1.0-py3-none-any.whl
uv run --no-project --directory /tmp/mojentic-c13-final.2ULCmw \
  --python /tmp/mojentic-c13-final.2ULCmw/.venv/bin/python \
  "$checkout/scripts/verify_stream_timing.py" \
  "$checkout/src/mojentic/llm/gateways/fixtures/contracts/first_token_v1.json"
```

Here `checkout` is this worktree's absolute path. Installed imports resolved to
`/tmp/mojentic-c13-final.2ULCmw/.venv/lib/python3.13/site-packages/mojentic/__init__.py`,
and the verifier explicitly rejects source-checkout imports. Every streaming
provider passed empty event, session content and async recovery terminal checks,
plus immediate explicit close through all three public legacy routes and unsent
closure; OpenAI/oMLX malformed choices retain the typed parser failure.
The same unchanged fixture identity is printed by the installed-package probe.

All required Foundry gates pass. Remaining limitations: the unchanged complexity
12 noted above, live vendor behavior outside controlled fixtures, other ports'
readiness, and coordinated owner release authorization are unverified here.
The Python library self-validates public consumer/provider roles and the fresh
artifact; no dependent or other-port executable snapshot is required. No
application/service boundary in another repository was changed. The publication
hold remains; no Git finalization, version bump or publication was performed.
