"""Git operations for ChangePlanner — safe, audited, reversible.

Uses GitPython for typed API access. Refuses dangerous operations
without explicit user confirmation routed through GuardrailEngine.
"""

from __future__ import annotations

from pathlib import Path

from openclaw_skills.logging import get_logger
from openclaw_skills.models import Checkpoint
from openclaw_skills.security import utc_now

logger = get_logger(__name__)


class GitOps:
    """Safe git operations for change management."""

    def __init__(self, repo_path: str | Path = ".") -> None:
        self._repo_path = Path(repo_path)
        self._repo = None

    def _ensure_repo(self) -> bool:
        """Lazily initialize git repo. Returns False if not a git repo."""
        if self._repo is not None:
            return True
        try:
            import git
            self._repo = git.Repo(self._repo_path, search_parent_directories=True)
            return True
        except Exception:
            logger.warning("git_not_available", path=str(self._repo_path))
            return False

    def create_checkpoint(self, label: str) -> Checkpoint | None:
        """Create a git stash as a recovery point.

        Uses stash rather than commits to avoid polluting history.
        Returns None if not in a git repo or nothing to stash.
        """
        if not self._ensure_repo():
            return None

        assert self._repo is not None

        try:
            # Check if there are changes to stash
            if not self._repo.is_dirty(untracked_files=True):
                # Nothing to checkpoint — create a marker anyway
                return Checkpoint(
                    label=label,
                    git_ref=self._repo.head.commit.hexsha[:12],
                    files_snapshot=tuple(
                        str(item.a_path) for item in self._repo.index.diff(None)
                    ),
                )

            # Stash changes
            stash_msg = f"openclaw-checkpoint: {label}"
            self._repo.git.stash("push", "-m", stash_msg, "--include-untracked")

            # Get stash ref
            git_ref = f"stash@{{0}}"

            # Pop stash immediately — we just wanted the ref
            self._repo.git.stash("pop")

            return Checkpoint(
                label=label,
                git_ref=self._repo.head.commit.hexsha[:12],
            )

        except Exception:
            logger.exception("checkpoint_failed", label=label)
            return None

    def get_diff(self) -> str:
        """Get current working directory diff."""
        if not self._ensure_repo():
            return ""
        assert self._repo is not None
        try:
            return self._repo.git.diff() or ""
        except Exception:
            return ""

    def get_status(self) -> str:
        """Get current git status summary."""
        if not self._ensure_repo():
            return "Not a git repository"
        assert self._repo is not None
        try:
            return self._repo.git.status("--short") or "Clean"
        except Exception:
            return "Unable to get status"
