"""Coverage analysis for docstring documentation."""
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, field

from autodocstring.models.metadata import ModuleMetadata, FunctionMetadata, ClassMetadata


@dataclass
class CoverageStats:
    """Coverage statistics for documentation.

    Attributes:
        total_items: Total number of documentable items.
        documented_items: Number of items with docstrings.
        missing_items: Number of items without docstrings.
        coverage_percentage: Coverage percentage (0-100).
        details: Detailed breakdown by type.
    """

    total_items: int = 0
    documented_items: int = 0
    missing_items: int = 0
    coverage_percentage: float = 0.0
    details: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate derived values after initialization."""
        if self.total_items > 0:
            self.coverage_percentage = (self.documented_items / self.total_items) * 100.0
        else:
            self.coverage_percentage = 100.0

        self.missing_items = self.total_items - self.documented_items


@dataclass
class FileCoverage:
    """Coverage information for a single file.

    Attributes:
        filepath: Path to the file.
        stats: Coverage statistics.
        missing_docstrings: List of items missing docstrings.
    """

    filepath: str
    stats: CoverageStats
    missing_docstrings: List[Dict[str, any]] = field(default_factory=list)


class CoverageAnalyzer:
    """Analyzer for documentation coverage.

    Computes coverage metrics at function, file, and project levels.

    Attributes:
        threshold: Minimum acceptable coverage percentage.
    """

    def __init__(self, threshold: float = 80.0):
        """Initialize coverage analyzer.

        Args:
            threshold: Minimum coverage percentage. Defaults to 80.0.
        """
        self.threshold = threshold

    def analyze_module(self, metadata: ModuleMetadata) -> FileCoverage:
        """Analyze coverage for a single module.

        Args:
            metadata: Module metadata.

        Returns:
            FileCoverage object with statistics.
        """
        total = 0
        documented = 0
        missing = []

        details = {
            "module": {"total": 0, "documented": 0},
            "class": {"total": 0, "documented": 0},
            "function": {"total": 0, "documented": 0},
            "method": {"total": 0, "documented": 0},
        }

        # Module docstring
        total += 1
        details["module"]["total"] += 1
        if metadata.docstring:
            documented += 1
            details["module"]["documented"] += 1
        else:
            missing.append(
                {
                    "type": "module",
                    "name": metadata.module_name,
                    "line": 1,
                }
            )

        # Classes
        for cls in metadata.classes:
            total += 1
            details["class"]["total"] += 1
            if cls.docstring:
                documented += 1
                details["class"]["documented"] += 1
            else:
                missing.append(
                    {
                        "type": "class",
                        "name": cls.name,
                        "line": cls.lineno,
                    }
                )

            # Methods
            for method in cls.methods:
                # Skip private methods (starting with _) unless they're special methods
                if method.name.startswith("_") and not (
                    method.name.startswith("__") and method.name.endswith("__")
                ):
                    continue

                total += 1
                details["method"]["total"] += 1
                if method.docstring:
                    documented += 1
                    details["method"]["documented"] += 1
                else:
                    missing.append(
                        {
                            "type": "method",
                            "name": f"{cls.name}.{method.name}",
                            "line": method.lineno,
                        }
                    )

        # Functions
        for func in metadata.functions:
            # Skip private functions
            if func.name.startswith("_"):
                continue

            total += 1
            details["function"]["total"] += 1
            if func.docstring:
                documented += 1
                details["function"]["documented"] += 1
            else:
                missing.append(
                    {
                        "type": "function",
                        "name": func.name,
                        "line": func.lineno,
                    }
                )

        stats = CoverageStats(
            total_items=total,
            documented_items=documented,
            details=details,
        )

        return FileCoverage(
            filepath=metadata.filepath,
            stats=stats,
            missing_docstrings=missing,
        )

    def analyze_project(self, modules: List[ModuleMetadata]) -> Dict[str, any]:
        """Analyze coverage for entire project.

        Args:
            modules: List of module metadata objects.

        Returns:
            Dictionary with project-level coverage statistics.
        """
        file_coverages = []
        total_items = 0
        total_documented = 0

        for module in modules:
            file_cov = self.analyze_module(module)
            file_coverages.append(file_cov)
            total_items += file_cov.stats.total_items
            total_documented += file_cov.stats.documented_items

        overall_coverage = (
            (total_documented / total_items * 100.0) if total_items > 0 else 100.0
        )

        return {
            "total_files": len(modules),
            "total_items": total_items,
            "documented_items": total_documented,
            "missing_items": total_items - total_documented,
            "coverage_percentage": overall_coverage,
            "meets_threshold": overall_coverage >= self.threshold,
            "threshold": self.threshold,
            "file_coverages": file_coverages,
        }

    def get_files_below_threshold(
        self, project_coverage: Dict[str, any]
    ) -> List[FileCoverage]:
        """Get files with coverage below threshold.

        Args:
            project_coverage: Project coverage dictionary.

        Returns:
            List of FileCoverage objects below threshold.
        """
        below_threshold = []

        for file_cov in project_coverage["file_coverages"]:
            if file_cov.stats.coverage_percentage < self.threshold:
                below_threshold.append(file_cov)

        return below_threshold

    def format_coverage_report(
        self, project_coverage: Dict[str, any], detailed: bool = False
    ) -> str:
        """Format coverage report as text.

        Args:
            project_coverage: Project coverage dictionary.
            detailed: Include detailed file-by-file breakdown. Defaults to False.

        Returns:
            Formatted coverage report.
        """
        lines = []
        lines.append("=" * 60)
        lines.append("DOCSTRING COVERAGE REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Overall statistics
        lines.append(f"Total Files: {project_coverage['total_files']}")
        lines.append(f"Total Items: {project_coverage['total_items']}")
        lines.append(f"Documented: {project_coverage['documented_items']}")
        lines.append(f"Missing: {project_coverage['missing_items']}")
        lines.append(
            f"Coverage: {project_coverage['coverage_percentage']:.1f}%"
        )
        lines.append(f"Threshold: {project_coverage['threshold']:.1f}%")
        lines.append(
            f"Status: {'PASS' if project_coverage['meets_threshold'] else 'FAIL'}"
        )
        lines.append("")

        if detailed:
            lines.append("-" * 60)
            lines.append("FILE BREAKDOWN")
            lines.append("-" * 60)
            lines.append("")

            for file_cov in project_coverage["file_coverages"]:
                filepath = Path(file_cov.filepath).name
                stats = file_cov.stats
                status = "✓" if stats.coverage_percentage >= self.threshold else "✗"

                lines.append(
                    f"{status} {filepath}: {stats.coverage_percentage:.1f}% "
                    f"({stats.documented_items}/{stats.total_items})"
                )

                if file_cov.missing_docstrings:
                    for item in file_cov.missing_docstrings[:5]:  # Show first 5
                        lines.append(
                            f"    - {item['type']}: {item['name']} (line {item['line']})"
                        )
                    if len(file_cov.missing_docstrings) > 5:
                        remaining = len(file_cov.missing_docstrings) - 5
                        lines.append(f"    ... and {remaining} more")

                lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)
