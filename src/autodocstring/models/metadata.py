"""Data models for code metadata extracted from AST parsing."""
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from enum import Enum


class NodeType(Enum):
    """Types of code nodes that can be documented."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    ASYNC_FUNCTION = "async_function"
    ASYNC_METHOD = "async_method"
    PROPERTY = "property"
    STATICMETHOD = "staticmethod"
    CLASSMETHOD = "classmethod"


@dataclass
class ParameterMetadata:
    """Metadata for a function parameter.

    Attributes:
        name: Parameter name.
        type_hint: Type annotation if present.
        default_value: Default value if present.
        is_args: Whether this is *args.
        is_kwargs: Whether this is **kwargs.
        description: Generated description for the parameter.
    """

    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    is_args: bool = False
    is_kwargs: bool = False
    description: str = ""


@dataclass
class FunctionMetadata:
    """Metadata for a function or method.

    Attributes:
        name: Function name.
        node_type: Type of node (function, method, async, etc.).
        lineno: Starting line number.
        end_lineno: Ending line number.
        parameters: List of parameter metadata.
        return_type: Return type annotation if present.
        decorators: List of decorator names.
        is_async: Whether function is async.
        is_generator: Whether function is a generator (yields).
        raises: List of exceptions that may be raised.
        docstring: Existing docstring if present.
        parent_class: Parent class name if this is a method.
    """

    name: str
    node_type: NodeType
    lineno: int
    end_lineno: int
    parameters: List[ParameterMetadata] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False
    is_generator: bool = False
    raises: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    parent_class: Optional[str] = None


@dataclass
class ClassMetadata:
    """Metadata for a class.

    Attributes:
        name: Class name.
        lineno: Starting line number.
        end_lineno: Ending line number.
        bases: List of base class names.
        decorators: List of decorator names.
        methods: List of method metadata.
        attributes: List of class attributes.
        docstring: Existing docstring if present.
        is_dataclass: Whether this is a dataclass.
    """

    name: str
    lineno: int
    end_lineno: int
    bases: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    methods: List[FunctionMetadata] = field(default_factory=list)
    attributes: List[Dict[str, Any]] = field(default_factory=list)
    docstring: Optional[str] = None
    is_dataclass: bool = False


@dataclass
class ModuleMetadata:
    """Metadata for a Python module.

    Attributes:
        filepath: Path to the module file.
        module_name: Module name.
        docstring: Module-level docstring if present.
        imports: List of import statements.
        classes: List of class metadata.
        functions: List of function metadata.
        constants: List of module-level constants.
    """

    filepath: str
    module_name: str
    docstring: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    classes: List[ClassMetadata] = field(default_factory=list)
    functions: List[FunctionMetadata] = field(default_factory=list)
    constants: List[Dict[str, Any]] = field(default_factory=list)

    def get_all_functions(self) -> List[FunctionMetadata]:
        """Get all functions including class methods.

        Returns:
            List of all function metadata objects.
        """
        all_funcs = list(self.functions)
        for cls in self.classes:
            all_funcs.extend(cls.methods)
        return all_funcs

    def count_documented(self) -> int:
        """Count functions with docstrings.

        Returns:
            Number of documented functions.
        """
        return sum(1 for func in self.get_all_functions() if func.docstring)

    def count_total(self) -> int:
        """Count total documentable items.

        Returns:
            Total number of functions, classes, and module.
        """
        # Count module + classes + all functions (including methods)
        return 1 + len(self.classes) + len(self.get_all_functions())

    def coverage_percentage(self) -> float:
        """Calculate documentation coverage percentage.

        Returns:
            Coverage percentage (0-100).
        """
        total = self.count_total()
        if total == 0:
            return 100.0
        
        # Count documented items: module + classes + functions
        documented = 0
        
        # Count module docstring
        if self.docstring:
            documented += 1
        
        # Count documented classes
        documented += sum(1 for cls in self.classes if cls.docstring)
        
        # Count documented functions (including methods)
        documented += sum(1 for func in self.get_all_functions() if func.docstring)
        
        return (documented / total) * 100.0


# ---------------------------------------------------------------------------
# Confidence / Risk models
# ---------------------------------------------------------------------------

class RiskLevel(Enum):
    """Risk level for a generated docstring."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class DocstringResult:
    """The result of generating a docstring for a single function or class.

    Attributes:
        file: Absolute path to the source file.
        function: Fully qualified function name (Class.method or function).
        lineno: Starting line number of the function.
        docstring: The generated docstring text.
        confidence: Confidence score between 0 and 1.
        risk: Risk level (LOW, MEDIUM, HIGH).
        reason: Human-readable explanation for the confidence score.
        diff: Unified diff string of the change (empty if dry-run not requested).
        skipped: Whether generation was skipped for this item.
        skip_reason: Reason for skipping, if applicable.
        generation_type: Source of the generation (template, hybrid, existing).
    """

    file: str
    function: str
    lineno: int
    docstring: str = ""
    confidence: float = 1.0
    risk: RiskLevel = RiskLevel.LOW
    reason: str = ""
    diff: str = ""
    skipped: bool = False
    skip_reason: str = ""
    generation_type: str = "none"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to a JSON-compatible dictionary.

        Returns:
            Dictionary representation of this result.
        """
        return {
            "file": self.file,
            "function": self.function,
            "lineno": self.lineno,
            "docstring": self.docstring,
            "confidence": round(self.confidence, 4),
            "risk": self.risk.value,
            "reason": self.reason,
            "diff": self.diff,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "generation_type": self.generation_type,
        }
