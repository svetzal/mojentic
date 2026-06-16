Dependency update complete. Here's the summary:

**Updated packages:**
- `anthropic` 0.109.1 → 0.109.2 (patch)
- `anyio` 4.13.0 → 4.14.0 (minor)

**Left unchanged:**
- `pydantic-core` 2.46.4 — the 2.47.0 available on PyPI is not compatible with pydantic 2.13.4 (the latest pydantic release), which pins its own pydantic-core version. This is expected.

**Quality gates:** ✅ lint clean, ✅ 279 tests passed, ✅ no known vulnerabilities.