"""State storage backends for the StateTracker.

Default implementation: JSON files with restrictive permissions.
The StateStorage protocol allows swapping for SQLite, Redis, etc.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from openclaw_skills.models import SessionState
from openclaw_skills.security import ensure_secure_directory, set_restrictive_permissions


class StateStorage(Protocol):
    """Protocol for state persistence backends."""

    def save(self, state: SessionState) -> None: ...
    def load(self, session_id: str) -> SessionState | None: ...
    def list_sessions(self) -> list[str]: ...
    def delete(self, session_id: str) -> None: ...


class JsonFileStorage:
    """JSON file-backed state storage with 0600 permissions.

    Each session gets its own file: {state_dir}/{session_id}.json
    Files contain sensitive context (paths, code snippets) so
    restrictive permissions are mandatory.
    """

    def __init__(self, state_dir: str | Path) -> None:
        self._dir = ensure_secure_directory(Path(state_dir))

    def save(self, state: SessionState) -> None:
        """Persist session state to JSON file."""
        path = self._dir / f"{state.session_id}.json"
        data = state.model_dump(mode="json")
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        set_restrictive_permissions(path)

    def load(self, session_id: str) -> SessionState | None:
        """Load session state from JSON file, or None if not found."""
        path = self._dir / f"{session_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return SessionState(**data)

    def list_sessions(self) -> list[str]:
        """List all stored session IDs."""
        return [p.stem for p in self._dir.glob("*.json") if p.is_file()]

    def delete(self, session_id: str) -> None:
        """Delete a session's state file."""
        path = self._dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
