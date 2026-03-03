"""Tests for validation and coverage."""
import pytest

from autodocstring.validation.validator import DocstringValidator, ValidationIssue
from autodocstring.validation.coverage import CoverageAnalyzer, CoverageStats
from autodocstring.validation.rules import PEP257Rules, AutofixRules
from autodocstring.models.metadata import ModuleMetadata, FunctionMetadata, NodeType


def test_missing_docstring_validation():
    """Test missing docstring detection."""
    validator = DocstringValidator()
    issues = validator.validate_docstring("", {"type": "function", "name": "test"})

    assert len(issues) > 0
    assert issues[0].code == "D100"


def test_missing_period_validation():
    """Test missing period detection."""
    docstring = "This is a one-line docstring"
    context = {"type": "function"}

    assert PEP257Rules.missing_period(docstring, context)


def test_autofix_add_period():
    """Test adding period autofix."""
    docstring = "This is a docstring"
    fixed = AutofixRules.add_period(docstring)

    assert fixed.endswith(".")


def test_autofix_spacing():
    """Test spacing autofix."""
    docstring = "Line 1  \n\n\n\nLine 2  \n"
    fixed = AutofixRules.fix_spacing(docstring)

    # Should remove trailing spaces and excessive blank lines
    assert "  \n" not in fixed
    assert "\n\n\n" not in fixed


def test_coverage_stats():
    """Test coverage statistics calculation."""
    stats = CoverageStats(
        total_items=10,
        documented_items=8,
    )

    assert stats.coverage_percentage == 80.0
    assert stats.missing_items == 2


def test_coverage_analyzer():
    """Test coverage analyzer."""
    # Create module with mixed documentation
    module = ModuleMetadata(
        filepath="test.py",
        module_name="test",
        docstring="Module docstring",
        functions=[
            FunctionMetadata(
                name="documented",
                node_type=NodeType.FUNCTION,
                lineno=1,
                end_lineno=3,
                docstring="Function docstring",
            ),
            FunctionMetadata(
                name="undocumented",
                node_type=NodeType.FUNCTION,
                lineno=5,
                end_lineno=7,
            ),
        ],
    )

    analyzer = CoverageAnalyzer(threshold=80.0)
    file_coverage = analyzer.analyze_module(module)

    # Module + 2 functions = 3 items
    # Module + 1 documented function = 2 documented
    # Coverage = 2/3 = 66.67%

    assert file_coverage.stats.total_items == 3
    assert file_coverage.stats.documented_items == 2
    assert 60 < file_coverage.stats.coverage_percentage < 70


def test_project_coverage():
    """Test project-level coverage analysis."""
    modules = [
        ModuleMetadata(
            filepath="file1.py",
            module_name="file1",
            docstring="Module 1",
            functions=[
                FunctionMetadata(
                    name="func1",
                    node_type=NodeType.FUNCTION,
                    lineno=1,
                    end_lineno=3,
                    docstring="Func 1",
                ),
            ],
        ),
        ModuleMetadata(
            filepath="file2.py",
            module_name="file2",
            functions=[
                FunctionMetadata(
                    name="func2",
                    node_type=NodeType.FUNCTION,
                    lineno=1,
                    end_lineno=3,
                ),
            ],
        ),
    ]

    analyzer = CoverageAnalyzer(threshold=75.0)
    project_coverage = analyzer.analyze_project(modules)

    assert project_coverage["total_files"] == 2
    assert project_coverage["total_items"] == 4  # 2 modules + 2 functions
    assert project_coverage["documented_items"] == 2  # 1 module + 1 function


def test_threshold_validation():
    """Test threshold validation."""
    modules = [
        ModuleMetadata(
            filepath="test.py",
            module_name="test",
            docstring="Module",
            functions=[
                FunctionMetadata(
                    name="func",
                    node_type=NodeType.FUNCTION,
                    lineno=1,
                    end_lineno=3,
                    docstring="Function",
                ),
            ],
        ),
    ]

    analyzer = CoverageAnalyzer(threshold=90.0)
    project_coverage = analyzer.analyze_project(modules)

    # 100% coverage (module + function both documented)
    assert project_coverage["meets_threshold"]

    analyzer = CoverageAnalyzer(threshold=100.0)
    project_coverage = analyzer.analyze_project(modules)

    assert project_coverage["meets_threshold"]
