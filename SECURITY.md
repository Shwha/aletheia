# Security Model — Aletheia

> Unconcealment (aletheia) demands that the framework itself practice what it measures.
> No hidden state, no leaked secrets, no fabricated trust.

## Threat Model

### 1. Adversarial Evaluated Model
**Threat:** The model being evaluated may be adversarial, jailbroken, or actively attempting to extract information about the framework's internals, scoring criteria, or philosophy.

**Mitigations:**
- Probes never include framework metadata, scoring rules, or dimension names
- Probe prompts are validated at model construction time (`Probe.prompt_must_not_leak_internals`)
- All model responses are sanitized before processing (`sanitize_model_response`)
- Response length is capped at 50,000 characters to prevent memory exhaustion
- Model responses are never interpolated into system operations or further prompts

### 2. Supply Chain Attacks
**Threat:** Dependency compromise, specifically referencing the March 2026 LiteLLM PyPI supply-chain incident.

**Mitigations:**
- All dependencies pinned to exact versions in `pyproject.toml`
- Hash verification recommended: `uv pip compile --generate-hashes pyproject.toml -o requirements.txt`
- Isolated virtualenvs via `uv` (no system-level installation)
- Minimal dependency surface — only what's strictly necessary

### 3. Credential Exposure
**Threat:** API keys leaked through logs, reports, error messages, or version control.

**Mitigations:**
- All API keys use `pydantic.SecretStr` — never serialized to JSON/repr/logs
- `.env` file excluded from version control via `.gitignore`
- `.env.example` provided with empty values only
- `scan_for_secrets()` runs on all report output before writing to disk
- structlog configured to never log request/response bodies containing keys

### 4. Report Tampering
**Threat:** Evaluation reports modified after generation to misrepresent model performance.

**Mitigations:**
- Phase 1: SHA-256 hash signature on all reports (integrity check)
- Phase 2: Ed25519 cryptographic signing
- Git commit SHA included in every report for provenance
- Unique run ID with timestamp for audit trail

### 5. Network Interception
**Threat:** API calls intercepted, keys extracted, or responses modified in transit.

**Mitigations:**
- TLS 1.3 minimum enforced on all HTTP clients
- Certificate pinning option via `ALETHEIA_TLS_CERT_PATH`
- SOCKS5/HTTP proxy support for air-gapped or TOR environments
- Rate limiting with exponential backoff (prevents timing attacks)

### 6. Local Data Exposure
**Threat:** Temporary files, audit traces, or reports readable by other users/processes.

**Mitigations:**
- All output files written with 0600 permissions (owner read/write only)
- Audit directory excluded from version control
- No telemetry, no phone-home, no analytics
- Full offline operation supported (Ollama, vLLM, llama.cpp)

## Operational Security Posture

- **No telemetry:** Aletheia sends no data anywhere except the configured LLM endpoints
- **No analytics:** No usage tracking, no crash reporting, no feature flags
- **Offline-capable:** Once models are cached locally, no network access required
- **Audit trail:** `--audit` flag produces full prompt/response/score traces
- **Minimal privileges:** The framework requires only network access to LLM APIs and local filesystem write

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:
1. Do **not** open a public GitHub issue
2. Email the maintainer directly (see repository contact info)
3. Allow 90 days for remediation before public disclosure

## Dependencies Security Review

| Dependency | Purpose | Risk Level | Notes |
|-----------|---------|------------|-------|
| litellm | LLM routing | **High** | March 2026 incident; pin + hash verify |
| pydantic | Data validation | Low | Well-audited, Rust core |
| httpx | HTTP client | Low | Async, TLS support |
| typer | CLI framework | Low | Minimal surface |
| structlog | Logging | Low | No network, no persistence |
| pyyaml | Config loading | Medium | `safe_load` only, never `load` |
| python-dotenv | Env loading | Low | Read-only |
| rich | Terminal output | Low | Display only |
