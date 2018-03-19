"""Job Type Enum Module."""
from enum import unique, Enum


@unique
class JobType(Enum):
    """Job type enum."""

    LIST = 'ls'
    COPY = 'cp'
    REMOVE = 'rm'
