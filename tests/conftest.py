"""Test configuration."""
import pytest


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing.

    Returns:
        Sample Python source code.
    """
    return '''
"""Sample module for testing."""

def simple_function(x: int) -> int:
    """A simple function.

    Args:
        x: Input value.

    Returns:
        Output value.
    """
    return x * 2


class SampleClass:
    """A sample class."""

    def __init__(self, value: int):
        """Initialize with value.

        Args:
            value: Initial value.
        """
        self.value = value

    def get_value(self) -> int:
        """Get the value.

        Returns:
            The stored value.
        """
        return self.value
'''
