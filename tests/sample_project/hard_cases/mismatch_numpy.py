"""Hard cases: numpy docstrings but request google."""


def add(a, b):
    """
    Add two numbers.

    Parameters
    ----------
    a : int
        First number.
    b : int
        Second number.

    Returns
    -------
    int
        Sum of a and b.
    """
    return a + b


class Calculator:
    """Simple calculator.

    Parameters
    ----------
    mode : str
        Mode name.
    """

    def __init__(self, mode):
        self.mode = mode

    def mul(self, x, y):
        """Multiply.

        Parameters
        ----------
        x : int
            First value.
        y : int
            Second value.
        """
        return x * y
