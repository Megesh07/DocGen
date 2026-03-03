"""Hard cases: partial google docstrings."""


def greet(name, title):
    """Greet a person.

    Args:
        name: Name of person.
    """
    return f"Hello {title} {name}"


def no_docstring(x, y):
    return x - y


def returns_but_missing_section(n):
    """Compute a value.

    Args:
        n: Input number.
    """
    return n * 2


def param_mismatch(alpha, beta):
    """Compute something.

    Args:
        alpha: The alpha value.
        gamma: Wrong param name.
    """
    return alpha + beta


class WithProperty:
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        """Value property.

        Returns:
            int: Current value.
        """
        return self._value
