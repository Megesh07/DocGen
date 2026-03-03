"""
DEMO SCENARIO 2 – Partial / Incomplete Docstrings.

These functions have a one-line summary only — they are MISSING
Args, Returns, and Raises sections. The tool should detect the
gap and upgrade each docstring to a full Google-style one.
"""
from __future__ import annotations

import re
from typing import Optional


class UserManager:
    """Manages user accounts in the system."""

    def __init__(self, db_url: str, max_users: int = 1000):
        """Initialize UserManager."""
        self._db_url = db_url
        self._max_users = max_users
        self._users: dict[str, dict] = {}

    def create_user(self, username: str, email: str, role: str = "viewer") -> dict:
        """Create a new user account."""
        if username in self._users:
            raise ValueError(f"Username '{username}' already taken.")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError(f"Invalid email address: {email}")
        if len(self._users) >= self._max_users:
            raise OverflowError("Maximum user limit reached.")
        user = {"username": username, "email": email, "role": role, "active": True}
        self._users[username] = user
        return user

    def get_user(self, username: str) -> Optional[dict]:
        """Retrieve user by username."""
        return self._users.get(username)

    def update_role(self, username: str, new_role: str) -> None:
        """Update a user's role."""
        allowed_roles = {"admin", "editor", "viewer"}
        if new_role not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}.")
        user = self._users.get(username)
        if user is None:
            raise KeyError(f"User '{username}' not found.")
        user["role"] = new_role

    def deactivate_user(self, username: str) -> None:
        """Deactivate a user account."""
        user = self._users.get(username)
        if user is None:
            raise KeyError(f"User '{username}' not found.")
        user["active"] = False

    def list_active_users(self) -> list[dict]:
        """Return all active users."""
        return [u for u in self._users.values() if u["active"]]

    def search_by_role(self, role: str) -> list[dict]:
        """Find users by role."""
        return [u for u in self._users.values() if u["role"] == role]

    def change_email(self, username: str, new_email: str) -> None:
        """Update a user's email."""
        if not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
            raise ValueError(f"Invalid email: {new_email}")
        user = self._users.get(username)
        if not user:
            raise KeyError(f"User '{username}' not found.")
        user["email"] = new_email

    def delete_user(self, username: str) -> dict:
        """Permanently remove a user."""
        if username not in self._users:
            raise KeyError(f"User '{username}' not found.")
        return self._users.pop(username)

    def user_count(self) -> int:
        """Return the total number of registered users."""
        return len(self._users)
