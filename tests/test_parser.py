"""Tests for AST parser."""
import pytest
from pathlib import Path
import tempfile
import textwrap

from autodocstring.parser import parse_file, SourceCodeParser
from autodocstring.models.metadata import NodeType


def create_temp_file(content: str) -> str:
    """Create temporary Python file with content.

    Args:
        content: Python source code.

    Returns:
        Path to temporary file.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(textwrap.dedent(content))
        return f.name


def test_parse_simple_function():
    """Test parsing a simple function."""
    code = '''
    def hello(name: str) -> str:
        """Say hello."""
        return f"Hello, {name}"
    '''

    filepath = create_temp_file(code)
    metadata = parse_file(filepath)

    assert len(metadata.functions) == 1
    func = metadata.functions[0]
    assert func.name == "hello"
    assert len(func.parameters) == 1
    assert func.parameters[0].name == "name"
    assert func.return_type == "str"
    assert func.docstring == "Say hello."


def test_parse_async_function():
    """Test parsing async function."""
    code = '''
    async def fetch_data(url: str) -> dict:
        """Fetch data from URL."""
        return {}
    '''

    filepath = create_temp_file(code)
    metadata = parse_file(filepath)

    assert len(metadata.functions) == 1
    func = metadata.functions[0]
    assert func.is_async
    assert func.node_type == NodeType.ASYNC_FUNCTION


def test_parse_class_with_methods():
    """Test parsing class with methods."""
    code = '''
    class Calculator:
        """A simple calculator."""

        def add(self, a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        def subtract(self, a: int, b: int) -> int:
            """Subtract two numbers."""
            return a - b
    '''

    filepath = create_temp_file(code)
    metadata = parse_file(filepath)

    assert len(metadata.classes) == 1
    cls = metadata.classes[0]
    assert cls.name == "Calculator"
    assert cls.docstring == "A simple calculator."
    assert len(cls.methods) == 2


def test_parse_decorators():
    """Test parsing decorators."""
    code = '''
    class MyClass:
        @property
        def value(self):
            """Get value."""
            return self._value

        @staticmethod
        def static_method():
            """Static method."""
            pass

        @classmethod
        def class_method(cls):
            """Class method."""
            pass
    '''

    filepath = create_temp_file(code)
    metadata = parse_file(filepath)

    cls = metadata.classes[0]
    assert len(cls.methods) == 3

    # Check node types
    node_types = {m.name: m.node_type for m in cls.methods}
    assert node_types["value"] == NodeType.PROPERTY
    assert node_types["static_method"] == NodeType.STATICMETHOD
    assert node_types["class_method"] == NodeType.CLASSMETHOD


def test_parse_dataclass():
    """Test parsing dataclass."""
    code = '''
    from dataclasses import dataclass

    @dataclass
    class Person:
        """Person dataclass."""
        name: str
        age: int
    '''

    filepath = create_temp_file(code)
    metadata = parse_file(filepath)

    cls = metadata.classes[0]
    assert cls.is_dataclass
    assert len(cls.attributes) == 2


def test_parse_generator():
    """Test parsing generator function."""
    code = '''
    def count_up(n: int):
        """Count from 0 to n."""
        for i in range(n):
            yield i
    '''

    filepath = create_temp_file(code)
    metadata = parse_file(filepath)

    func = metadata.functions[0]
    assert func.is_generator


def test_parse_function_with_defaults():
    """Test parsing function with default parameters."""
    code = '''
    def greet(name: str, greeting: str = "Hello") -> str:
        """Greet someone."""
        return f"{greeting}, {name}"
    '''

    filepath = create_temp_file(code)
    metadata = parse_file(filepath)

    func = metadata.functions[0]
    assert len(func.parameters) == 2
    assert func.parameters[0].default_value is None
    assert func.parameters[1].default_value == '"Hello"'


def test_parse_raises():
    """Test extracting raised exceptions."""
    code = '''
    def divide(a: int, b: int) -> float:
        """Divide two numbers."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    '''

    filepath = create_temp_file(code)
    metadata = parse_file(filepath)

    func = metadata.functions[0]
    assert "ValueError" in func.raises


def test_coverage_calculation():
    """Test coverage calculation."""
    code = '''
    """Module docstring."""

    def documented():
        """This has a docstring."""
        pass

    def undocumented():
        pass

    class MyClass:
        """Class docstring."""

        def documented_method(self):
            """Method docstring."""
            pass

        def undocumented_method(self):
            pass
    '''

    filepath = create_temp_file(code)
    metadata = parse_file(filepath)

    # Module: documented
    # documented(): documented
    # undocumented(): not documented
    # MyClass: documented
    # documented_method(): documented
    # undocumented_method(): not documented

    # Total: 6 items (module + 2 funcs + class + 2 methods)
    # Documented: 4 (module + 1 func + class + 1 method)
    # Coverage: 4/6 = 66.67%

    coverage = metadata.coverage_percentage()
    assert 60 < coverage < 70  # Approximately 66.67%
