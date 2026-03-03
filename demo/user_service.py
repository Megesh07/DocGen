"""
Demo file 2 – PARTIAL DOCSTRINGS (one-line summaries only).

Every function has a one-sentence docstring but is missing
Args, Returns, and Raises sections. The tool detects incomplete
documentation and upgrades each docstring in-place.
"""
from __future__ import annotations

import re
from typing import Optional


class UserService:
    """Manages user accounts."""

    def __init__(self, max_users: int = 500):
        """Initialize the service."""
        self._users: dict[str, dict] = {}
        self._max_users = max_users

    def create_user(self, username: str, email: str, role: str = "viewer") -> dict:
        """Create a new user account."""
        if username in self._users:
            raise ValueError(f"Username '{username}' already taken.")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError(f"Invalid email: {email}")
        if len(self._users) >= self._max_users:
            raise OverflowError("User limit reached.")
        user = {"username": username, "email": email, "role": role, "active": True}
        self._users[username] = user
        return user

    def get_user(self, username: str) -> Optional[dict]:
        """Fetch a user by username."""
        return self._users.get(username)

    def update_role(self, username: str, new_role: str) -> None:
        """Change a user's role."""
        allowed = {"admin", "editor", "viewer"}
        if new_role not in allowed:
            raise ValueError(f"Role must be one of {allowed}.")
        user = self._users.get(username)
        if user is None:
            raise KeyError(f"User '{username}' not found.")
        user["role"] = new_role

    def deactivate(self, username: str) -> None:
        """Deactivate a user account."""
        user = self._users.get(username)
        if user is None:
            raise KeyError(f"User '{username}' not found.")
        user["active"] = False

    def list_active(self) -> list[dict]:
        """Return all active users."""
        return [u for u in self._users.values() if u["active"]]

    def count(self) -> int:
        """Return total registered user count."""
        return len(self._users)


def validate_password(password: str) -> bool:
    """Check if a password meets security requirements."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*]", password):
        return False
    return True


def generate_slug(title: str) -> str:
    """Convert a title string into a URL-friendly slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")
