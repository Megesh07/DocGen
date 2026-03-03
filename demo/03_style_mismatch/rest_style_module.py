"""
DEMO SCENARIO 3 – Style Mismatch.

reST / Sphinx-style docstrings in a project that uses Google style.
The coverage checker will mark ALL of these as "style mismatch"
and add them to the review queue automatically.
"""
from __future__ import annotations


def send_email(
    to: str,
    subject: str,
    body: str,
    sender: str = "noreply@example.com",
    html: bool = False,
) -> bool:
    """
    Send an email message.

    :param to: Recipient email address.
    :param subject: Email subject line.
    :param body: Plain-text or HTML body of the message.
    :param sender: Sender address. Defaults to ``noreply@example.com``.
    :param html: Set to True to send body as HTML. Defaults to False.
    :returns: True if the message was queued successfully.
    :rtype: bool
    :raises ValueError: If *to* is not a valid email address.
    :raises ConnectionError: If the mail server is unreachable.
    """
    import re
    if not re.match(r"[^@]+@[^@]+\.[^@]+", to):
        raise ValueError(f"Invalid recipient address: {to}")
    # Stub: real implementation would connect to SMTP
    return True


def parse_template(template: str, variables: dict) -> str:
    """
    Render a Jinja-like ``{{ var }}`` template string.

    :param template: Template string containing ``{{ variable }}`` placeholders.
    :param variables: Mapping of variable names to their substitution values.
    :returns: Rendered string with all placeholders replaced.
    :rtype: str
    :raises KeyError: If a placeholder variable is not present in *variables*.
    """
    import re

    def replace(match: re.Match) -> str:
        key = match.group(1).strip()
        if key not in variables:
            raise KeyError(f"Template variable not found: '{key}'")
        return str(variables[key])

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", replace, template)


def paginate(items: list, page: int, per_page: int = 20) -> dict:
    """
    Slice a list into a paginated result.

    :param items: Full list of items to paginate.
    :param page: 1-based page number to return.
    :param per_page: Number of items per page. Defaults to 20.
    :returns: Dict with keys ``items``, ``page``, ``per_page``, ``total``, ``pages``.
    :rtype: dict
    :raises ValueError: If *page* is less than 1 or *per_page* is not positive.
    """
    if page < 1:
        raise ValueError("Page number must be ≥ 1.")
    if per_page <= 0:
        raise ValueError("per_page must be a positive integer.")
    total = len(items)
    pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    return {
        "items": items[start : start + per_page],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
    }
