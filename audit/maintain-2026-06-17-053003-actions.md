Dependencies are fully up to date. Here's what was done:

**Updated (minor/patch):**
- `openai` 2.41.1 → 2.42.0
- `tqdm` 4.68.2 → 4.68.3 (transitive)

**Not updated — held by constraint:**
- `pydantic-core` 2.46.4 → 2.47.0 was shown as outdated by `pip list`, but `pydantic` 2.13.4 (the latest pydantic) pins it to 2.46.4 — can't upgrade independently

**All quality gates passed:**
- ✅ Lint: 0 issues
- ✅ Tests: 279 passed
- ✅ Security scan: 0 issues (bandit)
- ✅ Dependency audit: no known vulnerabilities (pip-audit)