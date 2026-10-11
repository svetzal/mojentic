# Independent source review: cycle 9 HTTP 429

Review performed by independent review agent, read-only for project source and Git. This document is Foundry scratch.

## Conclusion

No blocking defect found in the reviewed 39-case matrix. A review finding that structured success lacked an assertion on its validated object was corrected by the implementing agent; current source asserts `response.object == Result(answer="é")` for structured and None for ordinary/streaming. Runtime remains unchanged. Final gate receipts and complete captured logs were subsequently inspected; all final commands exited zero.

## Source findings

- Public `complete_with_recovery` exercises ordinary and structured (`object_model=Result`) and public `complete_stream_with_recovery` exercises streaming against actual threaded loopback HTTP. No SDK, HTTP-client internals or private methods are mocked.
- Expected requests are literal bytes, independently specified UTF-8 with exact schema and streaming controls. Every actual server-received send is compared as `(path, body)` against the literal, and every wire request capture against the same literal.
- The seven success inputs each run across all three entrypoints: seconds minimum, seconds jitter, date minimum, date jitter, past-date, invalid and absent. Delay assertions prove max(provider minimum, injected jitter), date against frozen wall=0 and past clamping to 0; jitter input ceiling is independently asserted.
- Retained history asserts numeric 429, provider, operation, category, eligibility, original HTTPStatusError with numeric status and original request bytes, private raw error body and attempt identity. Successful report has one retained failure, stable logical request ID and distinct attempt IDs, exact send identities and headers [429,200].
- Exact eight-transition success order and transition identities/delay prove admission, scheduling and retry precede success. Successful content, validated structured object, model, usage and finish are asserted; streaming terminal is completed with typed SUCCEEDED and report identity.
- Twelve refusal cases span delay ceiling, full budget, remaining budget before admission and remaining budget after admission. Each asserts exactly one independently specified wire request, unchanged cause/body/history, typed RecoveryError report outcome, no scheduled sleep, complete expected lifecycle with no retry start. Streaming failure asserts sole failed event, typed StreamOutcome, no response and matching identity/outcome. Six further cases refuse missing/rejecting admission. Counts complement detailed assertions.
- Existing 503 spec source has no Git diff and matches proof manifest hash. No production correction is warranted by this matrix.

## Proof inspection

Parsed and validated behavioral proof JSON shape, nonempty source_change, command strings, integer nonzero rejecting and zero corrected exit fields, and both existing full logs. Complete stdout/stderr capture files were read; rejecting records a typed admission_rejected HTTP-date 429 after the one-request and exact rejecting-lifecycle assertions, corrected records one passing probe. These actual process exit records are supplied by the implementing agent and are consistent with complete pytest logs; review does not independently reproduce historical process exits.

Rejecting and corrected snapshots differ in actual admission decision from reject to allow; this is a recovery input correction, not a runtime bug fix or marker toggle. The rejecting source executes assertions before propagating RecoveryError. Corrected source asserts two exact sends, date minimum three above jitter 0.5, retained cause/status/body/history, stable/distinct IDs and exact lifecycle through success. Original snapshot and proof-log hashes all match proof-hashes.json. Matrix and appended loopback evidence naturally evolved beyond that historical manifest and require separate final hashes. Evidence logs retain earlier cache failure and bad raw-response inspection attempts, which are not accepted proof.

New evidence cannot repair or establish historical chronology. No current controller reconciliation receipt was observed; local status or remote-tracking refs do not establish current upstream synchronization. Git finalization remains controller-owned.

## Limits

Only scripted HTTP is covered. High-level broker/session 429 coverage, other providers, live inference, remote termination and idempotency are not established. Final unfiltered audit inventories and full final-source test/lint/doc captures were assessed in the supplement below. No Git mutation performed.

## Reviewed hashes (SHA-256)

- `src/mojentic/llm/gateways/omlx_429_recovery_spec.py`: `e6f6a0f282df7040a567d071a9806c7a8bc967b9d93b9ca6d809e62d352588df`
- `src/mojentic/llm/gateways/omlx.py`: `86b039102ff67cdbc40ef3deb125dab4ea76d5452553a57fdcb921b510c95c6d`
- `src/mojentic/llm/gateways/omlx_recovery.py`: `e98044c8918d85ce060665cdc22c9aca8206f6c3e60e6fb92e94118d09d75d59`
- `src/mojentic/llm/gateways/omlx_recovery_spec.py`: `d88fd4d3783ea52c052d2fb65f8f57fa70122506c7c732ca7662ac1d9d0c88ce`
- `src/mojentic/llm/gateways/omlx_protocol.py`: `a3e09ed6061dfa095f29278599e5386827e288fab6dea13244b1bc67c57c6be8`
- `src/mojentic/llm/recovery.py`: `fa151571a488e042772bc864db759d6af99cb4067ad1b4a46ef8b326b84c0dab`
- `src/mojentic/llm/recovery_stream.py`: `eea6c66bf8aba0d0acc6327c52532c882b7696fcc4cd58d92396135caa402a95`
- `RECOVERY-CONFORMANCE.md`: `ada84bbcd4282aa492a85ce5d30003db196679341c760e2b1dc7bede57ea8263`
- `.foundry/proof.json`: `3b0120bb6abb777c97d109eef2b5595ce323241ca103ed089a1141ccac497cae`
- `.foundry/rejecting-source.py`: `0eb61c214eb4daeb63f8cb71f8c88992e707c6226a302deac83cd1fa79e850d0`
- `.foundry/corrected-source.py`: `e461411467b8c35920b45d9fef68fffa9239fefc42d52f00c1d067987c561a44`
- `.foundry/logs/rejecting.log`: `ba150ea3e1b4b2e45448c88e7238c165477c4f56447a4949120aa0cf0b1c5978`
- `.foundry/logs/corrected.log`: `9efa9cec975ab8eb5082cf1a6c616043380f66a2004d58ee89c379e21722544b`

## Final gate and documentation review

Inspected quality.json and final-small-gates.json, all referenced final stdout/stderr captures in full, and original failed Ruff capture. Final Ruff, format check, full Flake8 and required fatal selection, both pytest runs, MkDocs, Bandit, project pip-audit, uvx pip-audit and outdated-package inspection have zero exit receipts. Both test captures report 915 passed, including the 39 new cases. Default run coverage is 84%; explicit --cov reports 85%. No coverage floor was introduced or lowered. Ruff import-order failure was retained, fixed, and final Ruff checks rerun; current source hash below reflects that import-only correction.

Bandit reports no issues with preserved existing configuration. Both audit captures report no known vulnerabilities; JSON inventories each contain 96 dependency records with empty vulnerability lists. Independently normalized name/version pairs from both JSON inventories exactly equal all 96 distributions in environment.json, with no missing or extra packages. The supplied explicit PIPAPI_PYTHON_LOCATION targeted the project .venv, and inventory equality corroborates that scope. No audit ignores, dependency changes or suppression additions were observed. Read-only host pip-cache warnings and existing MkDocs migration notices remain disclosed in complete captures. Outdated inspection is informational; no unnecessary upgrades applied.

Updated RECOVERY-CONFORMANCE.md faithfully reports actual public entrypoints, assertion matrix, structured-object check, 39 focused and 915 full-test results, coverage values, gate/audit results, historical chronology limitation and absence of current controller receipt. It refers to archived Foundry evidence without treating scratch paths as committed project artifacts. No blocking source or documentation defect remains. This approval is for the reviewed increment; controller reconciliation and landing are still outstanding controller responsibilities.

Historical proof-loopback.jsonl SHA-256 matches the original loopback hash in proof-hashes.json, preserving pre-expansion evidence separately from the appended live log. The original proof hashes remain valid for rejecting/corrected snapshots and complete logs.

## Final reviewed SHA-256 hashes

- `src/mojentic/llm/gateways/omlx_429_recovery_spec.py`: `e6f6a0f282df7040a567d071a9806c7a8bc967b9d93b9ca6d809e62d352588df`
- `RECOVERY-CONFORMANCE.md`: `6a1be4850e2580d503ab53f067a51265f353df8fea1f36d9fab8262feb1f2347`
- `.foundry/quality.json`: `90d1a25c72d95b1e3533c20194de6e23db92d830f7f1e7f4c6e9495553861463`
- `.foundry/final-small-gates.json`: `2835780092cbbe52162427abd5b36c53cca3c4cb99931da3371508a12db48762`
- `.foundry/environment.json`: `3cd5fd40f0276fe5b7737e7c6b5364a1530e957dcd2b326e600192e8d8c9f497`
- `.foundry/unchanged-source-policy.json`: `661defcc0f7db5e2d3cfe265bbf37c9ed3a33e2c0656255d9818b28e01d61609`
- `.foundry/proof-loopback.jsonl`: `8deceaf895d3b85b3199689c402ad2710c66c1122ea6dfa83478e22885bcd16b`
- `.foundry/logs/final-ruff/2-1791687964596148354.stdout.log`: `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`
- `.foundry/logs/final-ruff/2-1791687964596148354.stderr.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/final-format-check/2-1791687964599379817.stdout.log`: `8f485afdff0bd8ee2565c955dd978868c94d264cb548bb6ebcfa0d7a6c6ec864`
- `.foundry/logs/final-format-check/2-1791687964599379817.stderr.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/final-flake8/2-1791687964625270901.stdout.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/final-flake8/2-1791687964625270901.stderr.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/final-lint/2-1791687964574873083.stdout.log`: `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`
- `.foundry/logs/final-lint/2-1791687964574873083.stderr.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/gates/test/115-1791687880754512939.stdout.log`: `9d3ed7dee114d70d57d14eae790f483e5c0e40197b20a1b972a96262b480bab2`
- `.foundry/logs/gates/test/115-1791687880754512939.stderr.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/gates/coverage/1031-1791687968497915910.stdout.log`: `11378c005ddff67dc2fd63748fb6b1c6d840ec8b132785fd84fea74981fc8e9d`
- `.foundry/logs/gates/coverage/1031-1791687968497915910.stderr.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/gates/docs/1948-1791687994644524590.stdout.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/gates/docs/1948-1791687994644524590.stderr.log`: `848cda5e9f6fdfb3d5bb7ffe694b5624c86b5bdcbbaa0bf298782dcb679f49ef`
- `.foundry/logs/gates/bandit/1972-1791688002040930862.stdout.log`: `e3bcf7dfc5e26080941f1ab1b52fd238009ca8677d536622bef0ced82499b2d6`
- `.foundry/logs/gates/bandit/1972-1791688002040930862.stderr.log`: `ba7ea0617f4deb18364678fa5d86bf20c61d1737ee5a5b0c6ca6895ffa77d7fa`
- `.foundry/logs/gates/audit/1987-1791688004145188768.stdout.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/gates/audit/1987-1791688004145188768.stderr.log`: `490155fe4205098c3473fe4669990b55b149c0839d4a11d77139e6c1528e2d6f`
- `.foundry/logs/gates/uvx-audit/2003-1791688006324608767.stdout.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/gates/uvx-audit/2003-1791688006324608767.stderr.log`: `490155fe4205098c3473fe4669990b55b149c0839d4a11d77139e6c1528e2d6f`
- `.foundry/logs/gates/outdated/2036-1791688007584392283.stdout.log`: `7702b77aff14bed3da36194ec88b601f98dc62cb219c9c26d5a3e9d8f0c3f745`
- `.foundry/logs/gates/outdated/2036-1791688007584392283.stderr.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `.foundry/logs/audit-inventory-project/2-1791688026894685888.stderr.log`: `490155fe4205098c3473fe4669990b55b149c0839d4a11d77139e6c1528e2d6f`
- `.foundry/logs/audit-inventory-project/2-1791688026894685888.stdout.log`: `150c227328c1db39329f2eb9d0dd87072da6e326f6ee946aa780bb6c76afb4af`
- `.foundry/logs/audit-inventory-uvx/2-1791688026895919691.stderr.log`: `490155fe4205098c3473fe4669990b55b149c0839d4a11d77139e6c1528e2d6f`
- `.foundry/logs/audit-inventory-uvx/2-1791688026895919691.stdout.log`: `150c227328c1db39329f2eb9d0dd87072da6e326f6ee946aa780bb6c76afb4af`
