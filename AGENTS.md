# Usage Rules for Mojentic Python

**IMPORTANT**: Consult these usage rules early and often when working with this Python project.
Review these guidelines to understand the correct patterns, conventions, and best practices.

## Python Core Usage Rules

### Error Handling
- Use exceptions for error conditions
- Raise specific exception types, not generic `Exception`
- Document exceptions in docstrings with `Raises` section
- Use `try/except` for expected errors, let unexpected ones propagate
- Use context managers (`with`) for resource management

### Testing
- Tests are co-located with implementation files (test file must be in the same folder as the implementation)
- We write tests as specifications, therefore you can find all the tests in the *_spec.py files
- Use pytest for testing, with mocker if you require mocking
- Do not use unittest or MagicMock directly, use it through the mocker wrapper
- Use @fixture markers for pytest fixtures
- Break up fixtures into smaller fixtures if they are too large
- Do not write Given/When/Then or Act/Arrange/Assert comments
- Do not write docstring comments on your should_ methods
- Separate test phases with a single blank line
- Do not write conditional statements in tests
- Each test must fail for only one clear reason

### Code Style
- Follow PEP 8 style guide
- Max line length: 127
- Max complexity: 10
- Use numpy-style docstrings
- Use type hints for function signatures
- Use `black` for formatting (if configured)
- Use `flake8` for linting

### Common Mistakes to Avoid
- Don't use mutable default arguments: `def func(items=[]):` ❌ Use `def func(items=None):` ✅
- Don't use bare `except:` - always specify exception types
- Don't use `is` for value comparison - use `==` (except for `None`, `True`, `False`)
- Don't mutate function arguments unexpectedly
- Don't use `eval()` or `exec()` on untrusted input

### Data Structures
- Use `dataclasses` or Pydantic models for structured data
- Use type hints: `List[str]`, `Dict[str, int]`, `Optional[int]`
- Use list comprehensions over `map()`/`filter()` when clearer
- Use `set()` for membership testing on large collections

## Quality Guidelines

### MANDATORY Pre-Commit Quality Gates

**STOP**: Before considering ANY work complete or committing code, you MUST run ALL quality checks:

```bash
# Complete quality gate check (run this EVERY TIME)
flake8 src && \
pytest && \
pip-audit
```

**Why this matters**: Examples and tests must pass. When examples fail, users cannot learn from them. The `flake8` command validates Python files including examples, not just library code.

**If any check fails**:
- STOP immediately
- Fix the root cause (don't suppress warnings)
- Re-run all checks
- Only proceed when all pass

### Additional Quality Practices

- Write unit tests for new functions
- Run tests: `pytest`
- Run linting: `flake8 src`
- Code style:
  - Max line length: 127
  - Max complexity: 10
  - Follow numpy docstring style

## Security Guidelines

### Dependency Security
- Run `pip-audit` to check for known vulnerabilities
- Keep dependencies up to date, especially security patches
- Review security advisories regularly
- Use virtual environments to isolate dependencies

### Secure Coding
- Validate all inputs, especially from external sources
- Never use `eval()` or `exec()` on user input
- Use `secrets` module for cryptographic operations, not `random`
- Don't log sensitive data (API keys, passwords, tokens)
- Use environment variables for configuration, not hardcoded values

## Project-Specific Guidelines

### Mojentic Framework
- This is the **reference implementation** for all language ports
- All other implementations (Elixir, Rust, TypeScript) follow this design
- Changes here should be reflected in PARITY.md
- Use structlog for structured logging
- Use Pydantic for data validation and models

### Documentation
- Use MkDocs for user documentation in `docs/`
- Write numpy-style docstrings for all public APIs
- Include examples in docstrings where helpful
- Keep README.md synchronized with actual functionality

## Useful Commands

### Development Setup

This project supports both **uv** (preferred) and **pip** for dependency management.

#### Using uv (Preferred)
```bash
# Install uv if not present (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (includes dev dependencies)
uv sync --extra dev

# Run commands in the virtual environment
.venv/bin/pytest           # Run tests
.venv/bin/flake8 src       # Run linting
.venv/bin/pip-audit        # Security audit

# Or activate the virtual environment first
source .venv/bin/activate  # then use pytest, flake8, etc. directly
```

#### Using pip (Alternative)
```bash
# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -e ".[dev]"

# Run tests, linting, etc.
pytest
flake8 src
pip-audit
```

### Running Tests
```bash
pytest                                      # All tests with coverage
pytest src/mojentic/llm/llm_broker_spec.py  # Single test file
pytest -k test_name                         # Specific test by name
```

### Linting & Security
```bash
flake8 src          # Python linting
bandit -c .bandit -r src  # Security scan (with config)
pip-audit           # Dependency vulnerability check
```

### Documentation
```bash
mkdocs serve  # Serve docs locally at http://127.0.0.1:8000
mkdocs build  # Build static site
```

### Before Committing
```bash
# Run all quality checks
flake8 src && pytest && pip-audit
```

## Resources

- [Python Official Documentation](https://docs.python.org/)
- [PEP 8 Style Guide](https://pep8.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [numpy Docstring Guide](https://numpydoc.readthedocs.io/)

---

*Last Updated: November 2025 • Python 3.11+*
