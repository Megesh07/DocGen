"""Hard cases: reST style docstrings."""


def divide(a, b):
    """Divide two numbers.

    :param a: Numerator.
    :param b: Denominator.
    :return: Quotient.
    """
    return a / b


def missing_param_doc(x, y):
    """Compute ratio.

    :param x: First value.
    :return: Ratio.
    """
    return x / y
