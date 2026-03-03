"""Git integration for determining changed Python files.

Uses ``git diff`` to identify files modified since HEAD (or staged),
so the ``changed`` CLI command only processes files touched in the
current working tree.
"""
import subprocess
from pathlib import Path
from typing import List


def get_changed_files(root: str = ".") -> List[Path]:
    """Return Python files changed relative to HEAD.

    Combines unstaged (``git diff --name-only``) and staged
    (``git diff --cached --name-only``) changes.

    Args:
        root: Root directory of the git repository. Defaults to ``"."``.

    Returns:
        List of Path objects for modified ``.py`` files that exist on disk.
        Returns an empty list if not inside a git repository.
    """
    try:
        unstaged = _git_diff(root, cached=False)
        staged = _git_diff(root, cached=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    changed: set = set(unstaged) | set(staged)
    root_path = Path(root).resolve()

    result: List[Path] = []
    for rel_path in sorted(changed):
        p = root_path / rel_path
        if p.suffix == ".py" and p.exists():
            result.append(p)

    return result


def _git_diff(root: str, cached: bool) -> List[str]:
    """Run git diff and return list of relative file paths.

    Args:
        root: Root directory for the git command.
        cached: If True, show staged changes (``--cached`` flag).

    Returns:
        List of relative file path strings.

    Raises:
        subprocess.CalledProcessError: If git exits with non-zero status.
        FileNotFoundError: If git is not installed.
    """
    cmd = ["git", "diff", "--name-only"]
    if cached:
        cmd.append("--cached")
    cmd.append("HEAD")

    result = subprocess.run(
        cmd,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode not in (0, 1):
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
