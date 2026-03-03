"""Utility functions for file discovery and filtering."""
from pathlib import Path
from typing import List


def find_python_files(
    root_path: str,
    include_patterns: List[str],
    exclude_patterns: List[str],
) -> List[Path]:
    """Find Python files matching include/exclude patterns.

    Uses ``Path.match()`` for glob pattern matching, which correctly
    handles both Windows (backslash) and POSIX paths.

    Args:
        root_path: Root directory to search.
        include_patterns: Glob patterns to include (e.g. ``**/*.py``).
        exclude_patterns: Glob patterns to exclude.

    Returns:
        Sorted list of matching Python file paths.
    """
    root = Path(root_path)
    if not root.exists():
        return []

    # If root is a file, return it if it's Python
    if root.is_file():
        if root.suffix == ".py":
            return [root]
        return []

    # Discover all .py files recursively
    all_files = list(root.rglob("*.py"))

    # Filter by include patterns
    # Path.match() handles '**/*.py' AND bare '*.py' correctly on all platforms
    included_files = [
        f for f in all_files
        if any(f.match(pattern) for pattern in include_patterns)
    ]

    # Filter out excluded files
    filtered_files = [
        f for f in included_files
        if not any(
            _matches_exclude(f, root, pattern) for pattern in exclude_patterns
        )
    ]

    return sorted(filtered_files)


def _matches_exclude(file: Path, root: Path, pattern: str) -> bool:
    """Check if a file matches an exclude pattern.

    Uses both Path.match() and relative-path matching for robustness.

    Args:
        file: Absolute path to the file.
        root: Root directory of the search.
        pattern: Glob pattern to check against.

    Returns:
        True if the file should be excluded.
    """
    # Try direct Path.match() against the full path
    if file.match(pattern):
        return True
    # Also try matching the relative path (for patterns like 'tests/**')
    try:
        rel = file.relative_to(root)
        if rel.match(pattern):
            return True
    except ValueError:
        pass
    return False
