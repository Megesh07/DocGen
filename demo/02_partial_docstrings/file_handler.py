"""
DEMO SCENARIO 2 – Partial / Incomplete Docstrings.

File I/O and caching helpers. Each function has a one-sentence
docstring but is missing Args / Returns / Raises.
The tool will upgrade these in-place without destroying existing text.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


def read_json_file(filepath: str | Path) -> dict:
    """Read a JSON file and parse its contents."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    if path.suffix.lower() != ".json":
        raise ValueError(f"Expected a .json file, got: {path.suffix}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json_file(data: dict | list, filepath: str | Path, indent: int = 2) -> None:
    """Write data to a JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent, ensure_ascii=False)


def read_lines(filepath: str | Path, strip: bool = True) -> list[str]:
    """Read all lines from a text file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    return [line.rstrip("\n") for line in lines] if strip else lines


def safe_read(filepath: str | Path, default: Any = None) -> Optional[str]:
    """Read file contents, returning default on any error."""
    try:
        return Path(filepath).read_text(encoding="utf-8")
    except Exception:
        return default


def ensure_directory(path: str | Path) -> Path:
    """Create directory tree if it does not already exist."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_file_size(filepath: str | Path) -> int:
    """Return the size of a file in bytes."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    return path.stat().st_size


def list_files(directory: str | Path, pattern: str = "*") -> list[Path]:
    """List all files matching a glob pattern inside a directory."""
    return sorted(Path(directory).glob(pattern))


def copy_file(src: str | Path, dst: str | Path, overwrite: bool = False) -> Path:
    """Copy a file from src to dst."""
    import shutil
    src_path = Path(src)
    dst_path = Path(dst)
    if not src_path.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    if dst_path.exists() and not overwrite:
        raise FileExistsError(f"Destination already exists: {dst}")
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dst_path)
    return dst_path


def rotate_log(log_path: str | Path, max_backups: int = 3) -> None:
    """Rotate a log file, keeping the last N backups."""
    log = Path(log_path)
    if not log.exists():
        return
    for i in range(max_backups - 1, 0, -1):
        old = log.with_suffix(f".{i}.log")
        new = log.with_suffix(f".{i + 1}.log")
        if old.exists():
            old.rename(new)
    log.rename(log.with_suffix(".1.log"))


def count_lines(filepath: str | Path) -> int:
    """Count non-empty lines in a file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(path, encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())
