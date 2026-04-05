"""Tool call audit trail — unconcealment in action.

Every tool call is logged, whether it succeeds or fails.
This cannot be disabled — transparency is structural.
"""

from __future__ import annotations

import json
from pathlib import Path

from openclaw_skills.models import ToolCallRecord
from openclaw_skills.security import ensure_secure_directory, set_restrictive_permissions


class ToolAuditLog:
    """Append-only audit log for tool calls."""

    def __init__(self, audit_dir: str | Path) -> None:
        self._dir = ensure_secure_directory(Path(audit_dir))

    def log(self, session_id: str, record: ToolCallRecord) -> None:
        """Append a tool call record to the session's audit log."""
        path = self._dir / f"{session_id}_tools.jsonl"
        data = record.model_dump(mode="json")
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")
        set_restrictive_permissions(path)

    def get_session_log(self, session_id: str) -> list[dict[str, object]]:
        """Read all tool call records for a session."""
        path = self._dir / f"{session_id}_tools.jsonl"
        if not path.exists():
            return []
        entries: list[dict[str, object]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
        return entries
