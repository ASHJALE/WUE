"""Database CRUD helpers for the WUE API."""


class ConflictError(Exception):
    """Raised when an operation conflicts with existing database state."""
