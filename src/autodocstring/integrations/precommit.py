"""Pre-commit hook implementation."""
import sys
import subprocess
from pathlib import Path
from typing import List

from autodocstring.parser import parse_file
from autodocstring.validation.coverage import CoverageAnalyzer
from autodocstring.config import load_config


def get_staged_python_files() -> List[str]:
    """Get list of staged Python files from git.

    Returns:
        List of staged Python file paths.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )

        files = result.stdout.strip().split("\n")
        python_files = [f for f in files if f.endswith(".py") and Path(f).exists()]

        return python_files

    except subprocess.CalledProcessError:
        return []


def check_docstring_coverage(files: List[str], threshold: float) -> bool:
    """Check docstring coverage for files.

    Args:
        files: List of Python file paths.
        threshold: Coverage threshold percentage.

    Returns:
        True if coverage meets threshold.
    """
    if not files:
        return True

    # Parse files
    modules = []
    for file in files:
        try:
            metadata = parse_file(file)
            modules.append(metadata)
        except Exception as e:
            print(f"Warning: Error parsing {file}: {e}", file=sys.stderr)

    if not modules:
        return True

    # Analyze coverage
    analyzer = CoverageAnalyzer(threshold=threshold)
    project_coverage = analyzer.analyze_project(modules)

    # Print summary
    print("\n" + "=" * 60)
    print("DOCSTRING COVERAGE CHECK (Pre-commit)")
    print("=" * 60)
    print(f"Files checked: {len(files)}")
    print(f"Coverage: {project_coverage['coverage_percentage']:.1f}%")
    print(f"Threshold: {threshold:.1f}%")
    print(f"Status: {'PASS' if project_coverage['meets_threshold'] else 'FAIL'}")
    print("=" * 60 + "\n")

    if not project_coverage["meets_threshold"]:
        # Show files below threshold
        below_threshold = analyzer.get_files_below_threshold(project_coverage)
        if below_threshold:
            print("Files below threshold:")
            for file_cov in below_threshold:
                print(
                    f"  ✗ {file_cov.filepath}: {file_cov.stats.coverage_percentage:.1f}%"
                )
                # Show missing items
                for item in file_cov.missing_docstrings[:3]:
                    print(f"    - {item['type']}: {item['name']} (line {item['line']})")
            print()

    return project_coverage["meets_threshold"]


def main() -> int:
    """Main entry point for pre-commit hook.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Load configuration
    config = load_config()

    # Get staged files
    staged_files = get_staged_python_files()

    if not staged_files:
        print("No Python files staged for commit")
        return 0

    # Check coverage
    passes = check_docstring_coverage(staged_files, config.coverage_threshold)

    if not passes:
        print("❌ Commit blocked: Docstring coverage below threshold")
        print("   Use the web UI or API to generate missing docstrings")
        return 1

    print("✅ Docstring coverage check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
