"""Stateful review session management with disk persistence, file hashing, and background cleanup.

Sessions survive server restarts by writing atomic JSON files to
``.autodocstring_sessions/``.

Phase 3 (file conflict detection):
    At scan time, a SHA256 hash of each file is stored in the session.
    At apply time the hash is recomputed; a mismatch means the file
    changed since the scan and apply is aborted with a 409 conflict.

Background cleanup:
    ``schedule_background_cleanup()`` starts an asyncio task that runs
    every 30 minutes, purging expired sessions and orphan backup dirs.

Session lifecycle
-----------------
1. POST /scan   → creates session, stores file hashes, writes JSON file
2. POST /generate → attaches results, rewrites JSON file
3. POST /review → records decisions, rewrites JSON file
4. POST /apply  → validates hashes, applies approved decisions
5. Session expires after SESSION_TTL_HOURS of inactivity
"""
import asyncio
import hashlib
import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from autodocstring.core.decision_model import DecisionRecord

logger = logging.getLogger(__name__)

SESSION_TTL_HOURS: int = 2
# Allow the sessions directory to be overridden via env var so that
# cloud deployments (e.g. Render) can point to /tmp which is always writable.
_SESSIONS_DIR = Path(os.getenv("SESSION_DIR", ".autodocstring_sessions"))
_BACKUP_ROOT = Path(os.getenv("BACKUP_DIR", ".autodocstring_backup"))
_CLEANUP_INTERVAL_SECS: int = 30 * 60  # 30 minutes


# ---------------------------------------------------------------------------
# SHA256 file hash helper
# ---------------------------------------------------------------------------

def compute_file_hash(path: str) -> str:
    """Compute SHA256 hex digest of a file's contents.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        64-character hex string, or empty string if file is unreadable.
    """
    try:
        data = Path(path).read_bytes()
        return hashlib.sha256(data).hexdigest()
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# ReviewSession
# ---------------------------------------------------------------------------

@dataclass
class ReviewSession:
    """A single docstring review session with disk-backed persistence.

    Attributes:
        session_id: Unique UUID4 string.
        created_at: UTC datetime of creation.
        last_accessed: UTC datetime of last activity (for TTL).
        decisions: Map of (file, function) → DecisionRecord.
        scan_results: Raw dicts from the last scan or generate call.
        file_hashes: SHA256 hashes of scanned files (Phase 3 conflict detection).
    """

    session_id: str
    created_at: datetime
    last_accessed: datetime
    decisions: Dict[Tuple[str, str], DecisionRecord] = field(default_factory=dict)
    scan_results: List[dict] = field(default_factory=list)
    file_hashes: Dict[str, str] = field(default_factory=dict)  # Phase 3
    docstring_style: str = "google"
    current_batch_id: str = ""
    is_cancelled: bool = False

    def touch(self) -> None:
        """Reset last_accessed to now."""
        self.last_accessed = datetime.utcnow()

    def is_expired(self) -> bool:
        """Return True if the session has exceeded its TTL.

        Returns:
            True if expired.
        """
        return datetime.utcnow() - self.last_accessed > timedelta(hours=SESSION_TTL_HOURS)

    def set_decision(self, file: str, function: str, approved: bool) -> None:
        """Record an approve/skip decision.

        Args:
            file: File path.
            function: Function name.
            approved: True to approve.
        """
        key = (file, function)
        if key in self.decisions:
            self.decisions[key].approved = approved

    def approved_decisions(self) -> List[DecisionRecord]:
        """Return only approved DecisionRecords.

        Returns:
            List of records with approved=True.
        """
        return [r for r in self.decisions.values() if r.approved is True]

    def check_file_conflict(self, filepath: str) -> bool:
        """Check if a file has changed since the last scan (Phase 3).

        Args:
            filepath: File path to check.

        Returns:
            True if the file has been modified (hash mismatch).
        """
        stored = self.file_hashes.get(filepath)
        if not stored:
            return False  # No hash stored → no conflict detection
        current = compute_file_hash(filepath)
        return current != stored

    def get_snapshot_path(self, filepath: str):
        """Get the path to the file in the current batch snapshot."""
        if not self.current_batch_id:
            return Path(filepath)
        safe_name = hashlib.md5(filepath.encode("utf-8")).hexdigest() + "_" + Path(filepath).name
        return _SESSIONS_DIR / self.current_batch_id / safe_name

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the session to a JSON-compatible dictionary.

        Returns:
            Plain dict representation.
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "decisions": {
                f"{file}::{func}": record.to_dict()
                for (file, func), record in self.decisions.items()
            },
            "scan_results": self.scan_results,
            "file_hashes": self.file_hashes,
            "docstring_style": self.docstring_style,
            "current_batch_id": self.current_batch_id,
            "is_cancelled": self.is_cancelled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewSession":
        """Deserialise a session from a saved dictionary.

        Args:
            data: Dictionary loaded from a session JSON file.

        Returns:
            ReviewSession instance.
        """
        session = cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            scan_results=data.get("scan_results", []),
            file_hashes=data.get("file_hashes", {}),
            docstring_style=data.get("docstring_style", "google"),
            current_batch_id=data.get("current_batch_id", ""),
            is_cancelled=data.get("is_cancelled", False),
        )
        for composite_key, record_dict in data.get("decisions", {}).items():
            try:
                file, func = composite_key.split("::", 1)
            except ValueError:
                continue
            session.decisions[(file, func)] = DecisionRecord.from_dict(record_dict)
        return session


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------

class SessionManager:
    """Thread-safe session store with TTL, disk persistence, and file hashes.

    On ``__init__``:
    * Creates ``.autodocstring_sessions/`` if missing.
    * Loads all non-expired session JSON files.

    On every create/update:
    * Writes an atomic JSON file (temp → rename).

    On purge:
    * Deletes expired session JSON files and orphan backup directories.
    """

    def __init__(self, sessions_dir: Optional[Path] = None) -> None:
        """Initialize the session manager and load persisted sessions.

        Args:
            sessions_dir: Override for the sessions directory.
                Defaults to ``.autodocstring_sessions`` in cwd.
        """
        self._sessions: Dict[str, ReviewSession] = {}
        self._lock = threading.RLock()
        self._dir: Path = sessions_dir or _SESSIONS_DIR

        self._init_dir()
        self._load_from_disk()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(self) -> ReviewSession:
        """Create a new session and persist it to disk.

        Returns:
            Fresh ReviewSession.
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        session = ReviewSession(
            session_id=session_id,
            created_at=now,
            last_accessed=now,
        )
        with self._lock:
            self._sessions[session_id] = session
        self._save_to_disk(session)
        return session

    def get_session(self, session_id: str) -> Optional[ReviewSession]:
        """Retrieve an active session, or None if missing/expired.

        Args:
            session_id: UUID string.

        Returns:
            ReviewSession or None.
        """
        self._purge_expired()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.is_expired():
                if session and session.is_expired():
                    self._delete_from_disk(session_id)
                    del self._sessions[session_id]
                return None
            session.touch()
        self._save_to_disk(session)
        return session

    def delete_session(self, session_id: str) -> bool:
        """Remove a session from memory and disk.

        Args:
            session_id: UUID string.

        Returns:
            True if deleted, False not found.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._delete_from_disk(session_id)
                return True
        return False

    def attach_scan_results(
        self,
        session: ReviewSession,
        scan_results: List[dict],
        file_hashes: Optional[Dict[str, str]] = None,
        docstring_style: Optional[str] = None,
    ) -> None:
        """Attach scan/generate results and file hashes to a session.

        Args:
            session: Active ReviewSession.
            scan_results: List of DocstringResultSchema-compatible dicts.
            file_hashes: Optional SHA256 hashes by file path (Phase 3).
        """
        with self._lock:
            session.scan_results = scan_results
            if file_hashes is not None:
                session.file_hashes = file_hashes
            if docstring_style:
                session.docstring_style = docstring_style
            session.decisions = {
                (r["file"], r["function"]): DecisionRecord.from_scan_result(r)
                for r in scan_results
            }
        self._save_to_disk(session)

    def update_decisions(
        self,
        session: ReviewSession,
        decisions: List[dict],
    ) -> int:
        """Apply reviewer decisions to a session and persist.

        Args:
            session: Active ReviewSession.
            decisions: List of dicts with ``file``, ``function``, ``approved``.

        Returns:
            Number of matching decisions recorded.
        """
        count = 0
        with self._lock:
            for d in decisions:
                key = (d["file"], d["function"])
                if key in session.decisions:
                    session.decisions[key].approved = d.get("approved")
                    count += 1
        self._save_to_disk(session)
        return count

    def set_docstring_style(self, session: ReviewSession, style: str) -> None:
        """Persist the docstring style for a session.

        Args:
            session: Active ReviewSession.
            style: Docstring style identifier.
        """
        with self._lock:
            session.docstring_style = style
        self._save_to_disk(session)

    def active_count(self) -> int:
        """Return the number of active (non-expired) sessions.

        Returns:
            Active session count.
        """
        self._purge_expired()
        with self._lock:
            return len(self._sessions)

    def active_session_ids(self) -> List[str]:
        """Return list of active session IDs.

        Returns:
            List of UUID strings.
        """
        self._purge_expired()
        with self._lock:
            return list(self._sessions.keys())

    # ------------------------------------------------------------------
    # Disk I/O
    # ------------------------------------------------------------------

    def _init_dir(self) -> None:
        """Create the sessions directory if it does not exist."""
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def _session_path(self, session_id: str) -> Path:
        """Return the path for a session's JSON file.

        Args:
            session_id: UUID string.

        Returns:
            Path to ``session_<id>.json``.
        """
        return self._dir / f"session_{session_id}.json"

    def _save_to_disk(self, session: ReviewSession) -> None:
        """Atomically write session to disk (temp → rename).

        Args:
            session: Session to persist.
        """
        target = self._session_path(session.session_id)
        tmp = target.with_suffix(".tmp")
        try:
            payload = json.dumps(session.to_dict(), indent=2, ensure_ascii=False)
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(target)
        except OSError:
            pass

    def _delete_from_disk(self, session_id: str) -> None:
        """Delete a session's JSON file.

        Args:
            session_id: UUID string.
        """
        try:
            self._session_path(session_id).unlink(missing_ok=True)
        except OSError:
            pass

    def _load_from_disk(self) -> None:
        """Load all non-expired session files from disk."""
        if not self._dir.exists():
            return
        for path in self._dir.glob("session_*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                session = ReviewSession.from_dict(data)
                if session.is_expired():
                    path.unlink(missing_ok=True)
                else:
                    with self._lock:
                        self._sessions[session.session_id] = session
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def _purge_expired(self) -> int:
        """Remove all expired sessions from memory and disk.

        Returns:
            Number removed.
        """
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
            for sid in expired:
                del self._sessions[sid]
                self._delete_from_disk(sid)
        return len(expired)

    def purge_orphan_backups(self) -> int:
        """Delete backup directories with no corresponding active session.

        Returns:
            Number of orphan backup directories removed.
        """
        if not _BACKUP_ROOT.exists():
            return 0
        active = set(self.active_session_ids())
        removed = 0
        for entry in _BACKUP_ROOT.iterdir():
            if entry.is_dir() and entry.name not in active:
                try:
                    import shutil as _sh
                    _sh.rmtree(str(entry), ignore_errors=True)
                    removed += 1
                    logger.info("Removed orphan backup directory: %s", entry.name)
                except OSError:
                    pass
        return removed


# ---------------------------------------------------------------------------
# Background cleanup task (Phase 1)
# ---------------------------------------------------------------------------

async def _background_cleanup_loop(manager: "SessionManager") -> None:
    """Async loop that cleans up expired sessions and orphan backups every 30 min.

    Args:
        manager: The shared SessionManager instance.
    """
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL_SECS)
        try:
            purged = manager._purge_expired()
            orphans = manager.purge_orphan_backups()
            if purged or orphans:
                logger.info(
                    "Background cleanup: %d sessions purged, %d orphan backups removed.",
                    purged,
                    orphans,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Background cleanup error: %s", exc)


def schedule_background_cleanup(manager: "SessionManager") -> asyncio.Task:
    """Start the background cleanup asyncio task.

    Must be called from within an asyncio event loop (e.g. FastAPI lifespan).

    Args:
        manager: The shared SessionManager instance.

    Returns:
        The created asyncio.Task.
    """
    return asyncio.create_task(_background_cleanup_loop(manager))


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Return the global SessionManager singleton.

    Returns:
        Shared SessionManager instance.
    """
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager
