"""
Security utilities for the Aletheia framework.

Ontological ground: Unconcealment (aletheia) demands that the framework
itself practice what it measures. No hidden state, no leaked secrets,
no fabricated trust. Security is not an add-on — it is constitutive of
the framework's own authenticity.

Threat model (SECURITY.md):
- The evaluated model may be adversarial or jailbroken
- Supply chain attacks on dependencies (ref: March 2026 LiteLLM incident)
- API key exposure through logs or reports
- Prompt injection via model responses

Ref: SCOPE.md §4 (Technical Architecture)
"""

from __future__ import annotations

import hashlib
import os
import platform
import stat
import subprocess
from datetime import UTC
from pathlib import Path

import structlog

logger = structlog.get_logger()


def get_git_commit_sha() -> str | None:
    """Retrieve current git commit SHA for audit trail.

    Returns None if not in a git repository or git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def set_restrictive_permissions(path: Path) -> None:
    """Set file permissions to 0600 (owner read/write only).

    OpSec requirement: temporary files (probe outputs, reports) must not be
    world-readable. On Windows, this is a best-effort operation.
    """
    if platform.system() != "Windows":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    # Windows: rely on NTFS ACLs; no-op here but logged
    logger.debug("permissions_set", path=str(path), platform=platform.system())


def generate_run_id() -> str:
    """Generate a unique run ID for audit trail.

    Format: YYYYMMDD_HHMMSS_{random_hex}
    The timestamp gives human-readability; the hex prevents collisions.
    """
    from datetime import datetime

    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    random_hex = os.urandom(4).hex()
    return f"{timestamp}_{random_hex}"


def hash_content(content: str) -> str:
    """SHA-256 hash for content integrity verification."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sign_report(report_json: str) -> str | None:
    """Sign a JSON report for tamper detection.

    Phase 1 STUB: returns a SHA-256 hash of the report content.
    Phase 2 will implement proper Ed25519 signing with the key from
    ALETHEIA_SIGNING_KEY_PATH.

    The interface is defined now so that all Phase 1 reports include
    the signature field, enabling forward-compatible verification.
    """
    # TODO(phase2): Implement Ed25519 signing with ALETHEIA_SIGNING_KEY_PATH
    return f"sha256:{hash_content(report_json)}"


def scan_for_secrets(text: str) -> list[str]:
    """Scan text for accidentally included secrets.

    Phase 1 STUB: checks for common API key patterns.
    Phase 2 will use a more comprehensive ruleset.

    This runs on all report output before writing to disk — an agent that
    practices unconcealment about its limitations but conceals API keys.
    """
    import re

    findings: list[str] = []
    patterns = [
        (r"sk-[a-zA-Z0-9]{20,}", "Possible OpenAI API key detected"),
        (r"sk-ant-[a-zA-Z0-9-]{20,}", "Possible Anthropic API key detected"),
        (r"AIza[a-zA-Z0-9_-]{35}", "Possible Google API key detected"),
        (r"-----BEGIN.*PRIVATE KEY-----", "Possible private key detected"),
    ]
    for pattern, description in patterns:
        if re.search(pattern, text):
            findings.append(description)
    return findings


def create_audit_directory(base_path: Path, run_id: str, model_name: str) -> Path:
    """Create an audit directory for a specific run.

    Format: audit/{run_id}_{model_name}/
    All audit files get restrictive permissions.
    """
    # Sanitize model name for filesystem safety
    safe_model = "".join(c if c.isalnum() or c in "-_" else "_" for c in model_name)
    audit_dir = base_path / "audit" / f"{run_id}_{safe_model}"
    audit_dir.mkdir(parents=True, exist_ok=True)
    set_restrictive_permissions(audit_dir)
    return audit_dir
