"""Hard cases: strings that look like docstrings."""


def string_after_code(a):
    x = a + 1
    """This is not a docstring because it is not the first statement."""
    return x


def nested_defs(flag):
    """Top-level function.

    Args:
        flag: Control flag.
    """
    def inner(z):
        return z * 2
    return inner(3) if flag else 0


async def async_worker(items):
    """Process items asynchronously.

    Args:
        items: Iterable of items.

    Returns:
        list: Results.
    """
    results = []
    for item in items:
        results.append(item)
    return results


def gen_values(limit):
    """Yield values.

    Args:
        limit: Max value.

    Yields:
        int: Next value.
    """
    for i in range(limit):
        yield i
