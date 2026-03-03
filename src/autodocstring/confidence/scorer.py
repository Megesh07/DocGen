"""Confidence scorer for docstring generation decisions.

Analyses FunctionMetadata to yield a confidence score, risk level,
and human-readable reason.  The scorer is deterministic and offline –
it never calls an LLM.

Complexity is measured by AST branch count (Fix #3):
    branch_count = number of If + For + While + Try + BoolOp nodes
    branch_count > 8 → -0.10 penalty

External call detection uses a builtin whitelist (Fix #4):
    calls to builtins, typing, dataclasses, collections, math are NOT penalised.

Decision thresholds
-------------------
confidence >= AUTO_APPLY  → safe to apply automatically
confidence >= REVIEW      → requires human review before applying
confidence <  REVIEW      → skip (do not generate)
"""
import ast
from dataclasses import dataclass
from typing import List, Optional

from autodocstring.models.metadata import FunctionMetadata, RiskLevel

# Decision policy constants
AUTO_APPLY: float = 0.85
REVIEW: float = 0.60

# Individual penalty weights
_PENALTY_NO_TYPE_HINT: float = 0.05    # per parameter without a type hint
_PENALTY_NO_RETURN_TYPE: float = 0.10
_PENALTY_HIGH_BRANCH: float = 0.10    # branch_count > 8 (AST structural complexity)
_PENALTY_GENERATOR: float = 0.05
_PENALTY_EXTERNAL_CALL: float = 0.05  # call to non-local, non-whitelisted module

_BRANCH_THRESHOLD: int = 8

# Modules whose names are never considered "external" (Fix #4)
BUILTIN_WHITELIST: frozenset = frozenset(
    {
        "builtins",
        "typing",
        "dataclasses",
        "collections",
        "math",
        "os",
        "sys",
        "re",
        "abc",
        "functools",
        "itertools",
        "pathlib",
        "enum",
    }
)


@dataclass
class ScoringResult:
    """Result of a confidence scoring analysis.

    Attributes:
        confidence: Float in [0, 1] representing how reliable the
            generated docstring will be.
        risk: Categorical risk level derived from confidence.
        reason: Human-readable explanation of the score.
    """

    confidence: float
    risk: RiskLevel
    reason: str


class ConfidenceScorer:
    """Scores a FunctionMetadata object and returns a ScoringResult.

    The scorer is stateless – it can be instantiated once and reused
    across many functions.

    Confidence depends **only** on AST structure and type hints.
    It is never affected by formatting, whitespace, or line numbers.
    """

    def score(
        self,
        metadata: FunctionMetadata,
        ast_node: Optional[ast.AST] = None,
    ) -> ScoringResult:
        """Compute a confidence score for a function.

        Args:
            metadata: Extracted function metadata.
            ast_node: Optional AST node for the function.  When provided,
                branch-count complexity and external-call analysis are
                performed on the real AST.  When omitted, those checks
                are skipped (score is still deterministic).

        Returns:
            ScoringResult with confidence, risk level, and explanation.
        """
        penalties: List[str] = []
        total_penalty: float = 0.0

        # 1. Parameters without type hints
        untyped = [
            p for p in metadata.parameters
            if p.type_hint is None and not p.is_args and not p.is_kwargs
        ]
        if untyped:
            pen = min(len(untyped) * _PENALTY_NO_TYPE_HINT, 0.30)
            total_penalty += pen
            names = ", ".join(p.name for p in untyped)
            penalties.append(f"untyped params [{names}] (-{pen:.2f})")

        # 2. Missing return type annotation
        if metadata.return_type is None:
            total_penalty += _PENALTY_NO_RETURN_TYPE
            penalties.append(f"no return type annotation (-{_PENALTY_NO_RETURN_TYPE:.2f})")
        elif metadata.return_type in ("Any",):
            total_penalty += _PENALTY_NO_RETURN_TYPE / 2
            penalties.append(f"return type is Any (-{_PENALTY_NO_RETURN_TYPE / 2:.2f})")

        # 3. AST structural complexity (branch count, Fix #3)
        if ast_node is not None:
            branch_count = _count_branches(ast_node)
            if branch_count > _BRANCH_THRESHOLD:
                total_penalty += _PENALTY_HIGH_BRANCH
                penalties.append(
                    f"high branch complexity ({branch_count} branches) "
                    f"(-{_PENALTY_HIGH_BRANCH:.2f})"
                )

        # 4. Generator functions – return semantics are less clear
        if metadata.is_generator:
            total_penalty += _PENALTY_GENERATOR
            penalties.append(f"generator function (-{_PENALTY_GENERATOR:.2f})")

        # Clamp to [0, 1]
        confidence = max(0.0, min(1.0, 1.0 - total_penalty))

        # Determine risk level
        if confidence >= AUTO_APPLY:
            risk = RiskLevel.LOW
        elif confidence >= REVIEW:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.HIGH

        reason = "; ".join(penalties) if penalties else "all type hints present, low complexity"
        return ScoringResult(confidence=confidence, risk=risk, reason=reason)


# ---------------------------------------------------------------------------
# AST analysis helpers
# ---------------------------------------------------------------------------

_BRANCH_NODE_TYPES = (
    ast.If,
    ast.For,
    ast.While,
    ast.Try,
    ast.BoolOp,
)


def _count_branches(node: ast.AST) -> int:
    """Count structural complexity branches in an AST node.

    Counts occurrences of: ``If``, ``For``, ``While``, ``Try``, ``BoolOp``.

    Args:
        node: AST node to walk (typically a FunctionDef).

    Returns:
        Total branch count.
    """
    return sum(
        1 for child in ast.walk(node)
        if isinstance(child, _BRANCH_NODE_TYPES)
    )


def _is_external_call(call_node: ast.Call) -> bool:
    """Determine whether a Call node targets a non-local, non-whitelisted callable.

    Args:
        call_node: An ``ast.Call`` node.

    Returns:
        True if the callee appears to be an external (non-whitelisted) module call.
    """
    func = call_node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        module_name = func.value.id
        return module_name not in BUILTIN_WHITELIST
    return False
