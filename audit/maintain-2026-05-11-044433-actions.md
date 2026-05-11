All done. Here's a summary of what happened:

**Dependencies updated (transitive):**
| Package | Before | After |
|---------|--------|-------|
| `coverage` | 7.13.5 | 7.14.0 |
| `idna` | 3.13 | 3.14 |

All direct dependencies in `pyproject.toml` were already pinned to their latest releases — no changes needed there.

**Quality gates:** All clean
- ✅ Lint (`flake8`): 0 issues
- ✅ Tests (`pytest`): 227 passed in 1.20s
- ✅ Security scan (`bandit`): No issues
- ✅ Dependency audit (`pip-audit`): No known vulnerabilities

Changes committed and pushed to `main`.