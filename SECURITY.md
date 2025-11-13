# Security Scanning

This project uses comprehensive security scanning to ensure code quality and dependency safety.

## Tools

### 1. Bandit - Code Security Linting

Bandit scans Python code for common security issues like:
- Hardcoded passwords
- SQL injection vulnerabilities
- Use of insecure functions (eval, exec, pickle)
- Weak cryptographic practices
- Shell injection risks

**Configuration:** `.bandit`

**Run locally:**
```bash
# Install dependencies
pip install -e ".[dev]"

# Scan source code
bandit -c .bandit -r src

# Generate JSON report
bandit -c .bandit -r src -f json -o bandit-report.json
```

### 2. pip-audit - Dependency Vulnerability Scanning

pip-audit checks installed packages against known vulnerability databases (PyPI Advisory Database, OSV).

**Run locally:**
```bash
# Install dependencies
pip install -e ".[dev]"

# Scan dependencies
pip-audit

# Generate JSON report
pip-audit --format json --output pip-audit-report.json
```

**Common options:**
- `--require-hashes` - Require hashes in requirements files
- `--ignore-vuln <ID>` - Ignore specific vulnerabilities
- `--fix` - Attempt to upgrade vulnerable dependencies

## CI/CD Integration

Both security scans run automatically on:
- Every push to main branch
- Every pull request
- Before releases

**Pipeline Job:** `security`
- Runs in parallel with lint and test jobs
- Generates JSON reports as artifacts
- Fails the build if critical issues are found

**View Reports:**
1. Go to Actions tab in GitHub
2. Select a workflow run
3. Download "security-scan-results" artifact
4. Review `bandit-report.json` and `pip-audit-report.json`

## Security Policy

### Severity Levels

**Bandit:**
- LOW: Minor issues, informational
- MEDIUM: Moderate security concerns
- HIGH: Critical security vulnerabilities

**pip-audit:**
- Vulnerabilities reported with CVSS scores and CVE identifiers

### Addressing Findings

1. **Code Issues (Bandit):**
   - Review the issue and context
   - Refactor code to eliminate the vulnerability
   - If false positive, add `# nosec` comment with justification

2. **Dependency Issues (pip-audit):**
   - Check if a patched version is available
   - Update dependency in `pyproject.toml`
   - If no fix available, assess risk and document decision
   - Consider alternative packages if vulnerability is critical

## Reporting Security Issues

If you discover a security vulnerability, please email security@vetzal.com rather than opening a public issue.
