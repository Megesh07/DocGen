"""Atomic multi-file apply with backup, full rollback, and crash recovery.

Before modifying any file this module:
1. Creates ``.autodocstring_backup/<session_id>/`` and copies originals.
2. Applies docstrings file-by-file via ``SafeApplier``.
3. On any failure: restores all files from backup, deletes backup dir.
4. On success: deletes backup dir.

Phase 2 (crash recovery):
    ``recover_orphan_backups()`` is called on server startup.
    Any backup directory left over from a crash is automatically restored
    and deleted so the repository is never left in a half-modified state.

The caller receives a ``TransactionResult`` with the outcome.
"""
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from autodocstring.safety.applier import SafeApplier

logger = logging.getLogger(__name__)

_BACKUP_ROOT = Path(".autodocstring_backup")


@dataclass
class FileApplyRecord:
    """Result for a single file within a transaction.

    Attributes:
        file: Absolute path string.
        applied: Number of docstrings applied.
        skipped: Number of functions skipped.
        rolled_back: True if this file's write triggered a rollback.
        error: Error message if the file failed.
    """

    file: str
    applied: int = 0
    skipped: int = 0
    rolled_back: bool = False
    error: str = ""


@dataclass
class TransactionResult:
    """Result of an atomic multi-file apply operation.

    Attributes:
        success: True if all files were applied without error.
        applied: Total docstrings inserted.
        skipped: Total functions skipped.
        files: Per-file results (sorted by path).
        error: Top-level error message if transaction failed.
        restored_files: Files restored from backup on failure.
    """

    success: bool
    applied: int = 0
    skipped: int = 0
    files: List[FileApplyRecord] = field(default_factory=list)
    error: str = ""
    restored_files: List[str] = field(default_factory=list)


def run_atomic_apply(
    session_id: str,
    by_file: Dict[str, list],
    dry_run: bool = False,
    backup_root: Optional[Path] = None,
    keep_backup: bool = False,
) -> TransactionResult:
    """Apply docstring results across multiple files atomically.

    If any file's apply raises an exception, all previously modified
    files are restored from backup and the backup directory is deleted.

    Args:
        session_id: Used to namespace the backup directory.
        by_file: Dict mapping file path → list of DocstringResult objects.
        dry_run: If True, compute diffs only (no file writes, no backup).
        backup_root: Override for backup root directory.
        keep_backup: If True, do not delete the backup on success to allow Undo.

    Returns:
        TransactionResult with success flag and per-file details.
    """
    backup_dir = (backup_root or _BACKUP_ROOT) / session_id
    applier = SafeApplier(dry_run=dry_run)

    if dry_run:
        return _apply_no_backup(applier, by_file)

    # --- Phase 1: create backup + write manifest ---
    written_files: List[str] = []
    manifest: Dict[str, str] = {}  # original_path -> backup_filename
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        for filepath in by_file.keys():
            src = Path(filepath)
            if src.exists():
                dest = backup_dir / src.name
                # Handle filename collisions by adding parent hash
                if dest.exists():
                    dest = backup_dir / (src.parent.name + "_" + src.name)
                shutil.copy2(str(src), str(dest))
                manifest[filepath] = dest.name
        # Write manifest so crash recovery knows original paths
        import json as _json
        (backup_dir / "manifest.json").write_text(
            _json.dumps(manifest, indent=2), encoding="utf-8"
        )
    except OSError as e:
        _safe_rm(backup_dir)
        return TransactionResult(
            success=False,
            error=f"Failed to create backup directory: {e}",
        )

    # --- Phase 2: apply file by file ---
    file_records: List[FileApplyRecord] = []
    total_applied = 0
    total_skipped = 0

    for filepath, results in sorted(by_file.items()):
        record = FileApplyRecord(file=filepath)
        try:
            ar = applier.apply_to_file(filepath, [r for r in results if not r.skipped])
            record.applied = ar.applied
            record.skipped = ar.skipped
            total_applied += ar.applied
            total_skipped += ar.skipped
            written_files.append(filepath)
        except Exception as exc:  # noqa: BLE001
            record.error = str(exc)
            record.rolled_back = True
            file_records.append(record)
            # --- Phase 3: rollback on any failure ---
            restored = _restore_from_backup(backup_dir, list(by_file.keys()))
            _safe_rm(backup_dir)
            return TransactionResult(
                success=False,
                applied=0,
                skipped=0,
                files=sorted(file_records, key=lambda r: r.file),
                error=f"Apply failed for {filepath}: {exc}. All files restored from backup.",
                restored_files=restored,
            )
        file_records.append(record)

    # --- Phase 4: success – clean up backup ---
    if not keep_backup:
        _safe_rm(backup_dir)
        
    return TransactionResult(
        success=True,
        applied=total_applied,
        skipped=total_skipped,
        files=sorted(file_records, key=lambda r: r.file),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_no_backup(applier: SafeApplier, by_file: Dict[str, list]) -> TransactionResult:
    """Dry-run apply without backup (fixes diffs only).

    Args:
        applier: SafeApplier in dry_run mode.
        by_file: Dict of filepath → DocstringResult list.

    Returns:
        TransactionResult (always success=True for dry-run).
    """
    file_records = []
    total_applied = total_skipped = 0
    for filepath, results in sorted(by_file.items()):
        ar = applier.apply_to_file(filepath, [r for r in results if not r.skipped])
        file_records.append(FileApplyRecord(
            file=filepath,
            applied=ar.applied,
            skipped=ar.skipped,
        ))
        total_applied += ar.applied
        total_skipped += ar.skipped
    return TransactionResult(
        success=True,
        applied=total_applied,
        skipped=total_skipped,
        files=file_records,
    )


def _restore_from_backup(backup_dir: Path, file_paths: List[str]) -> List[str]:
    """Restore files from the backup directory.

    Args:
        backup_dir: Directory where backups are stored.
        file_paths: Original file paths to restore.

    Returns:
        List of file paths that were successfully restored.
    """
    restored = []
    for filepath in file_paths:
        src = Path(filepath)
        backup = backup_dir / src.name
        if not backup.exists():
            backup = backup_dir / (src.parent.name + "_" + src.name)
        if backup.exists():
            try:
                shutil.copy2(str(backup), str(src))
                restored.append(filepath)
            except OSError:
                pass
    return restored


def _safe_rm(path: Path) -> None:
    """Remove a directory tree silently on failure.

    Args:
        path: Directory to remove.
    """
    try:
        if path.exists():
            shutil.rmtree(str(path), ignore_errors=True)
    except OSError:
        pass


def recover_orphan_backups(backup_root: Optional[Path] = None) -> List[str]:
    """Restore files from any backup directories left by a previous crash.

    Called once at server startup (Phase 2 – crash-safe recovery).
    Uses a ``manifest.json`` created during backup to find original paths
    in O(1) without scanning the filesystem.

    For every directory under ``.autodocstring_backup/``:
    1. Read ``manifest.json`` (maps original_path → backup filename).
    2. Copy each backup file back to its original location.
    3. Delete the backup directory.
    4. Log the recovery.

    Args:
        backup_root: Override for backup root. Defaults to ``.autodocstring_backup``.

    Returns:
        List of session IDs for which recovery was performed.
    """
    import json as _json

    root = backup_root or _BACKUP_ROOT
    if not root.exists():
        return []

    recovered: List[str] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        session_id = entry.name
        manifest_path = entry / "manifest.json"
        restored_count = 0

        if manifest_path.exists():
            try:
                manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
                for original_path, backup_name in manifest.items():
                    backup_file = entry / backup_name
                    if backup_file.exists():
                        try:
                            shutil.copy2(str(backup_file), original_path)
                            restored_count += 1
                        except OSError:
                            pass
            except Exception:  # noqa: BLE001
                pass  # Corrupt manifest – can't restore, just clean up

        _safe_rm(entry)
        logger.warning(
            "Recovered interrupted transaction %s (%d files restored).",
            session_id,
            restored_count,
        )
        recovered.append(session_id)
    return recovered

def restore_session_backup(session_id: str, backup_root: Optional[Path] = None) -> List[str]:
    """Restore files for a specific session backup explicitly (Undo feature).

    Args:
        session_id: The session to restore.
        backup_root: Override for backup root. Defaults to ``.autodocstring_backup``.

    Returns:
        List of file paths that were successfully restored.
    """
    import json as _json

    root = backup_root or _BACKUP_ROOT
    backup_dir = root / session_id
    if not backup_dir.exists() or not backup_dir.is_dir():
        return []

    manifest_path = backup_dir / "manifest.json"
    restored = []
    
    if manifest_path.exists():
        try:
            manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
            for original_path, backup_name in manifest.items():
                backup_file = backup_dir / backup_name
                if backup_file.exists():
                    try:
                        shutil.copy2(str(backup_file), original_path)
                        restored.append(original_path)
                    except OSError:
                        pass
        except Exception:  # noqa: BLE001
            pass  # Corrupt manifest
            
    _safe_rm(backup_dir)
    return restored
