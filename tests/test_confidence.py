"""Tests for confidence scorer."""
import pytest

from autodocstring.confidence.scorer import ConfidenceScorer, AUTO_APPLY, REVIEW
from autodocstring.models.metadata import FunctionMetadata, ParameterMetadata, NodeType, RiskLevel


def _make_func(
    name="func",
    params=None,
    return_type=None,
    lineno=1,
    end_lineno=5,
    is_generator=False,
):
    """Helper: build a FunctionMetadata with given properties."""
    return FunctionMetadata(
        name=name,
        node_type=NodeType.FUNCTION,
        lineno=lineno,
        end_lineno=end_lineno,
        parameters=params or [],
        return_type=return_type,
        is_generator=is_generator,
    )


def _typed_param(name: str) -> ParameterMetadata:
    return ParameterMetadata(name=name, type_hint="int")


def _untyped_param(name: str) -> ParameterMetadata:
    return ParameterMetadata(name=name, type_hint=None)


class TestConfidenceScorer:
    """Tests for ConfidenceScorer.score()."""

    def setup_method(self):
        """Set up scorer."""
        self.scorer = ConfidenceScorer()

    def test_perfect_function_has_max_confidence(self):
        """A fully annotated short function should have confidence = 1.0."""
        func = _make_func(
            params=[_typed_param("a"), _typed_param("b")],
            return_type="int",
        )
        result = self.scorer.score(func)
        assert result.confidence == 1.0
        assert result.risk == RiskLevel.LOW

    def test_untyped_params_reduce_confidence(self):
        """Missing type hints on parameters should reduce confidence."""
        func = _make_func(
            params=[_untyped_param("a"), _untyped_param("b")],
            return_type="int",
        )
        result = self.scorer.score(func)
        assert result.confidence < 1.0
        assert "untyped params" in result.reason

    def test_missing_return_type_reduces_confidence(self):
        """Missing return annotation should apply a penalty."""
        func = _make_func(params=[_typed_param("x")], return_type=None)
        result = self.scorer.score(func)
        assert result.confidence < 1.0
        assert "return type" in result.reason

    def test_high_complexity_reduces_confidence(self):
        """A function with > 8 branch nodes should have reduced confidence."""
        import ast as _ast
        # Build a real AST node with many If/For/While branches
        code = (
            "def complex(x: int) -> int:\n" +
            "    if x: pass\n" * 9 +  # 9 If nodes → branch_count = 9 > 8
            "    return x\n"
        )
        tree = _ast.parse(code)
        func_node = tree.body[0]

        func = _make_func(
            params=[_typed_param("x")],
            return_type="int",
        )
        result = self.scorer.score(func, ast_node=func_node)
        assert result.confidence < 1.0, "Expected < 1.0 for high-branch function"
        assert "branch" in result.reason.lower() or "complexity" in result.reason.lower()

    def test_generator_reduces_confidence(self):
        """Generator functions should have a confidence penalty."""
        func = _make_func(return_type="Iterator[int]", is_generator=True)
        result = self.scorer.score(func)
        assert result.confidence < 1.0

    def test_auto_apply_threshold(self):
        """Well-typed function should exceed AUTO_APPLY threshold."""
        func = _make_func(
            params=[_typed_param("x")],
            return_type="str",
        )
        result = self.scorer.score(func)
        assert result.confidence >= AUTO_APPLY

    def test_fully_untyped_function_is_high_risk(self):
        """A function with no types and many params should be HIGH risk."""
        func = _make_func(
            params=[_untyped_param(f"p{i}") for i in range(6)],
            return_type=None,
            lineno=1,
            end_lineno=60,
            is_generator=True,
        )
        result = self.scorer.score(func)
        assert result.risk == RiskLevel.HIGH

    def test_confidence_clamped_to_zero(self):
        """Confidence should never go below 0."""
        func = _make_func(
            params=[_untyped_param(f"p{i}") for i in range(20)],
            return_type=None,
            lineno=1,
            end_lineno=200,
            is_generator=True,
        )
        result = self.scorer.score(func)
        assert result.confidence >= 0.0
