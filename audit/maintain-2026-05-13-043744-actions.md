Dependencies are fully up to date. Here's the summary:

**Change made:** `idna` 3.14 → 3.15 (transitive dependency, updated in `uv.lock`)

All direct dependencies in `pyproject.toml` were already at their latest compatible versions — `uv lock --upgrade` only found the one transitive `idna` bump.

**Quality gates — all green:**
- ✅ Lint (`flake8`): 0 issues
- ✅ Tests: 244 passed in 2.24s (67% coverage)
- ✅ Security scan (`bandit`): No issues
- ✅ Dependency audit (`pip-audit`): No known vulnerabilities