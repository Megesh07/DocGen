"""Tests for docstring generator."""
import pytest

from autodocstring.generator import DocstringGenerator
from autodocstring.models.metadata import (
    FunctionMetadata,
    ClassMetadata,
    ParameterMetadata,
    NodeType,
)


def test_google_style_function():
    """Test Google-style function docstring generation."""
    metadata = FunctionMetadata(
        name="calculate_sum",
        node_type=NodeType.FUNCTION,
        lineno=1,
        end_lineno=5,
        parameters=[
            ParameterMetadata(name="a", type_hint="int"),
            ParameterMetadata(name="b", type_hint="int", default_value="0"),
        ],
        return_type="int",
    )

    generator = DocstringGenerator(style="google")
    docstring = generator.generate_function_docstring(metadata)

    assert '"""Calculate Sum function.' in docstring
    assert "Args:" in docstring
    assert "a: The a parameter." in docstring
    assert "b: The b parameter. Defaults to 0." in docstring
    assert "Returns:" in docstring
    assert "int: Return value description." in docstring


def test_numpy_style_function():
    """Test NumPy-style function docstring generation."""
    metadata = FunctionMetadata(
        name="process_data",
        node_type=NodeType.FUNCTION,
        lineno=1,
        end_lineno=5,
        parameters=[
            ParameterMetadata(name="data", type_hint="list"),
        ],
        return_type="dict",
    )

    generator = DocstringGenerator(style="numpy")
    docstring = generator.generate_function_docstring(metadata)

    assert "Process Data function." in docstring
    assert "Parameters" in docstring
    assert "----------" in docstring
    assert "data : list" in docstring
    assert "Returns" in docstring
    assert "-------" in docstring


def test_rest_style_function():
    """Test reST-style function docstring generation."""
    metadata = FunctionMetadata(
        name="validate_input",
        node_type=NodeType.FUNCTION,
        lineno=1,
        end_lineno=5,
        parameters=[
            ParameterMetadata(name="value", type_hint="str"),
        ],
        return_type="bool",
        raises=["ValueError"],
    )

    generator = DocstringGenerator(style="rest")
    docstring = generator.generate_function_docstring(metadata)

    assert "Validate Input function." in docstring
    assert ":param value:" in docstring
    assert ":type value: str" in docstring
    assert ":return:" in docstring
    assert ":rtype: bool" in docstring
    assert ":raises ValueError:" in docstring


def test_generator_function():
    """Test generator function docstring."""
    metadata = FunctionMetadata(
        name="count_items",
        node_type=NodeType.FUNCTION,
        lineno=1,
        end_lineno=5,
        is_generator=True,
        return_type="int",
    )

    generator = DocstringGenerator(style="google")
    docstring = generator.generate_function_docstring(metadata)

    assert "Yields:" in docstring


def test_class_docstring():
    """Test class docstring generation."""
    metadata = ClassMetadata(
        name="DataProcessor",
        lineno=1,
        end_lineno=10,
        attributes=[
            {"name": "data", "type": "list"},
            {"name": "config", "type": "dict"},
        ],
    )

    generator = DocstringGenerator(style="google")
    docstring = generator.generate_class_docstring(metadata)

    assert "DataProcessor class." in docstring
    assert "Attributes:" in docstring
    assert "data: list attribute." in docstring
    assert "config: dict attribute." in docstring


def test_dataclass_docstring():
    """Test dataclass docstring generation."""
    metadata = ClassMetadata(
        name="Person",
        lineno=1,
        end_lineno=5,
        is_dataclass=True,
        attributes=[
            {"name": "name", "type": "str"},
            {"name": "age", "type": "int"},
        ],
    )

    generator = DocstringGenerator(style="google")
    docstring = generator.generate_class_docstring(metadata)

    assert "Person dataclass." in docstring


def test_async_function():
    """Test async function docstring."""
    metadata = FunctionMetadata(
        name="fetch_data",
        node_type=NodeType.ASYNC_FUNCTION,
        lineno=1,
        end_lineno=5,
        is_async=True,
        return_type="dict",
    )

    generator = DocstringGenerator(style="google")
    docstring = generator.generate_function_docstring(metadata)

    assert "Fetch Data function." in docstring


def test_method_docstring():
    """Test method docstring generation."""
    metadata = FunctionMetadata(
        name="process",
        node_type=NodeType.METHOD,
        lineno=1,
        end_lineno=5,
        parent_class="DataHandler",
    )

    generator = DocstringGenerator(style="google")
    docstring = generator.generate_function_docstring(metadata)

    assert "Process method." in docstring
